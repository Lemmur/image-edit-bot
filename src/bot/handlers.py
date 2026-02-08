"""Обработчики команд и сообщений Telegram бота"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from pathlib import Path
from loguru import logger

from src.bot.states import ImageEditStates
from src.bot.keyboards import (
    create_confirm_keyboard, 
    create_settings_keyboard,
    create_sampler_keyboard,
    create_skip_keyboard
)
from src.models.task import Task, WorkflowParams
from src.queue.task_queue import TaskQueue
from src.models.config import Config
from src.storage.file_manager import FileManager

router = Router()


# =============================================================================
# Команды
# =============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start — приветствие"""
    logger.info(f"User {message.from_user.id} started bot")
    
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Я бот для редактирования изображений с помощью AI.\n\n"
        "📝 <b>Как использовать:</b>\n"
        "1. Отправь команду /new чтобы начать\n"
        "2. Загрузи изображение\n"
        "3. Опиши что нужно изменить\n"
        "4. Настрой параметры (опционально)\n"
        "5. Получи результат!\n\n"
        "📋 <b>Команды:</b>\n"
        "/new — начать новую задачу\n"
        "/status — статус очереди\n"
        "/cancel — отменить задачу\n"
        "/help — справка",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help — справка"""
    logger.debug(f"User {message.from_user.id} requested help")
    
    await message.answer(
        "📖 <b>Справка</b>\n\n"
        "<b>Процесс редактирования:</b>\n"
        "1. /new — начать новую задачу\n"
        "2. Отправьте изображение (фото или файл)\n"
        "3. Опишите желаемые изменения\n"
        "4. Опционально: negative prompt или /skip\n"
        "5. Настройте параметры и подтвердите\n\n"
        "<b>Параметры генерации:</b>\n"
        "• <b>Steps</b> — количество шагов (больше = качественнее, но дольше)\n"
        "• <b>CFG</b> — сила следования промпту\n"
        "• <b>Seed</b> — фиксированный seed для воспроизводимости\n"
        "• <b>Sampler</b> — алгоритм семплирования\n\n"
        "<b>Форматы изображений:</b>\n"
        "• JPG, PNG, WEBP\n"
        "• Максимум 10 МБ\n"
        "• Для лучшего качества отправляйте как файл\n\n"
        "💡 <i>Совет: отправка как файл сохраняет оригинальное качество</i>",
        parse_mode="HTML"
    )


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    """Команда /new — начать новую задачу"""
    logger.info(f"User {message.from_user.id} starting new task")
    
    # Очистить предыдущее состояние
    await state.clear()
    
    # Установить начальное состояние
    await state.set_state(ImageEditStates.waiting_for_image)
    
    await message.answer(
        "🖼 <b>Новая задача</b>\n\n"
        "Отправьте изображение для редактирования.\n\n"
        "💡 <i>Совет: отправьте как файл (📎) для сохранения "
        "оригинального качества</i>",
        parse_mode="HTML"
    )


@router.message(Command("status"))
async def cmd_status(message: Message, task_queue: TaskQueue):
    """Команда /status — статус очереди"""
    logger.debug(f"User {message.from_user.id} checking status")
    
    status = task_queue.get_status()
    
    processing_text = "🔄 Обработка: да" if status['current_task_id'] else "⏸ Обработка: нет"
    
    await message.answer(
        "📊 <b>Статус очереди</b>\n\n"
        f"📥 В очереди: {status['queue_size']}\n"
        f"{processing_text}\n"
        f"✅ Выполнено сегодня: {status['completed_today']}\n"
        f"📈 Всего выполнено: {status['total_completed']}\n"
        f"📉 Успешность: {status['success_rate']}%",
        parse_mode="HTML"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Команда /cancel — отменить текущую задачу"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("❌ Нет активной задачи для отмены")
        return
    
    await state.clear()
    logger.info(f"User {message.from_user.id} cancelled task (state: {current_state})")
    
    await message.answer(
        "🚫 <b>Задача отменена</b>\n\n"
        "Используйте /new чтобы начать заново.",
        parse_mode="HTML"
    )


@router.message(Command("skip"))
async def cmd_skip(message: Message, state: FSMContext, config: Config):
    """Команда /skip — пропустить negative prompt"""
    current_state = await state.get_state()
    
    if current_state != ImageEditStates.waiting_for_negative:
        await message.answer("❌ Эта команда доступна только при вводе negative prompt")
        return
    
    # Использовать дефолтный negative prompt из конфига
    data = await state.get_data()
    data['negative_prompt'] = config.workflow.defaults.negative_prompt
    await state.update_data(data)
    
    # Перейти к подтверждению
    await state.set_state(ImageEditStates.confirming)
    
    logger.debug(f"User {message.from_user.id} skipped negative prompt")
    
    await _show_confirmation(message, data, config)


# =============================================================================
# Обработка изображений
# =============================================================================

@router.message(ImageEditStates.waiting_for_image, F.photo)
async def handle_photo(message: Message, state: FSMContext, config: Config, 
                       file_manager: FileManager, bot: Bot):
    """Обработка фото (сжимается Telegram до 1280px)"""
    photo = message.photo[-1]  # Наилучшее качество
    
    logger.info(f"User {message.from_user.id} sent photo, file_id: {photo.file_id[:16]}...")
    
    try:
        # Скачать файл
        file_path = await file_manager.download_file(
            bot=bot,
            file_id=photo.file_id,
            user_id=message.from_user.id,
            extension="jpg"
        )
        
        # Сохранить в состояние
        await state.update_data(
            image_path=str(file_path),
            steps=config.workflow.defaults.steps,
            cfg=config.workflow.defaults.cfg,
            sampler=config.workflow.defaults.sampler,
            seed=config.workflow.defaults.seed,
            strength=config.workflow.defaults.strength
        )
        
        # Перейти к промпту
        await state.set_state(ImageEditStates.waiting_for_prompt)
        
        await message.answer(
            "✅ <b>Изображение получено</b>\n\n"
            "Теперь опишите, что нужно изменить.\n\n"
            "💡 <i>Пример: \"сделай небо закатным\", \"добавь снег\"</i>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Failed to download photo: {e}")
        await message.answer("❌ Не удалось загрузить изображение. Попробуйте ещё раз.")


@router.message(ImageEditStates.waiting_for_image, F.document)
async def handle_document(message: Message, state: FSMContext, config: Config,
                         file_manager: FileManager, bot: Bot):
    """Обработка документа (оригинальное качество)"""
    document = message.document
    
    # Проверить MIME тип
    allowed_mimes = ["image/jpeg", "image/png", "image/webp"]
    if document.mime_type not in allowed_mimes:
        await message.answer(
            "❌ <b>Неподдерживаемый формат</b>\n\n"
            "Отправьте изображение в формате JPG, PNG или WEBP.",
            parse_mode="HTML"
        )
        return
    
    # Проверить размер
    max_size_bytes = config.image.max_size_mb * 1024 * 1024
    if document.file_size and document.file_size > max_size_bytes:
        await message.answer(
            f"❌ <b>Файл слишком большой</b>\n\n"
            f"Максимальный размер: {config.image.max_size_mb} МБ",
            parse_mode="HTML"
        )
        return
    
    logger.info(
        f"User {message.from_user.id} sent document: "
        f"{document.file_name}, {document.mime_type}"
    )
    
    try:
        # Определить расширение
        extension = document.mime_type.split("/")[-1]
        if extension == "jpeg":
            extension = "jpg"
        
        # Скачать файл
        file_path = await file_manager.download_file(
            bot=bot,
            file_id=document.file_id,
            user_id=message.from_user.id,
            extension=extension
        )
        
        # Сохранить в состояние
        await state.update_data(
            image_path=str(file_path),
            steps=config.workflow.defaults.steps,
            cfg=config.workflow.defaults.cfg,
            sampler=config.workflow.defaults.sampler,
            seed=config.workflow.defaults.seed,
            strength=config.workflow.defaults.strength
        )
        
        # Перейти к промпту
        await state.set_state(ImageEditStates.waiting_for_prompt)
        
        await message.answer(
            "✅ <b>Изображение получено</b> (оригинальное качество)\n\n"
            "Теперь опишите, что нужно изменить.\n\n"
            "💡 <i>Пример: \"сделай небо закатным\", \"добавь снег\"</i>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Failed to download document: {e}")
        await message.answer("❌ Не удалось загрузить файл. Попробуйте ещё раз.")


# =============================================================================
# Обработка промптов
# =============================================================================

@router.message(ImageEditStates.waiting_for_prompt, F.text)
async def handle_prompt(message: Message, state: FSMContext):
    """Обработка positive prompt"""
    prompt = message.text.strip()
    
    if len(prompt) < 3:
        await message.answer("❌ Промпт слишком короткий. Опишите подробнее.")
        return
    
    if len(prompt) > 1000:
        await message.answer("❌ Промпт слишком длинный. Максимум 1000 символов.")
        return
    
    logger.debug(f"User {message.from_user.id} prompt: {prompt[:50]}...")
    
    await state.update_data(positive_prompt=prompt)
    await state.set_state(ImageEditStates.waiting_for_negative)
    
    await message.answer(
        "✅ <b>Промпт сохранён</b>\n\n"
        "Введите <b>negative prompt</b> (что НЕ должно быть на изображении) "
        "или нажмите /skip для пропуска.\n\n"
        "💡 <i>Пример: \"размытие, артефакты, низкое качество\"</i>",
        parse_mode="HTML",
        reply_markup=create_skip_keyboard()
    )


@router.message(ImageEditStates.waiting_for_negative, F.text)
async def handle_negative(message: Message, state: FSMContext, config: Config):
    """Обработка negative prompt"""
    negative = message.text.strip()
    
    if len(negative) > 500:
        await message.answer("❌ Negative prompt слишком длинный. Максимум 500 символов.")
        return
    
    logger.debug(f"User {message.from_user.id} negative: {negative[:50]}...")
    
    await state.update_data(negative_prompt=negative)
    await state.set_state(ImageEditStates.confirming)
    
    data = await state.get_data()
    await _show_confirmation(message, data, config)


@router.callback_query(F.data == "skip_negative")
async def callback_skip_negative(callback: CallbackQuery, state: FSMContext, config: Config):
    """Callback для пропуска negative prompt"""
    current_state = await state.get_state()
    
    if current_state != ImageEditStates.waiting_for_negative:
        await callback.answer("Эта кнопка больше не активна")
        return
    
    # Использовать дефолтный negative prompt
    data = await state.get_data()
    data['negative_prompt'] = config.workflow.defaults.negative_prompt
    await state.update_data(data)
    
    await state.set_state(ImageEditStates.confirming)
    
    logger.debug(f"User {callback.from_user.id} skipped negative prompt via callback")
    
    await callback.message.edit_text(
        "✅ <b>Negative prompt пропущен</b>",
        parse_mode="HTML"
    )
    
    await _show_confirmation(callback.message, data, config)
    await callback.answer()


# =============================================================================
# Callback handlers для подтверждения
# =============================================================================

@router.callback_query(F.data == "task_confirm")
async def callback_confirm(callback: CallbackQuery, state: FSMContext, 
                          task_queue: TaskQueue, config: Config):
    """Подтверждение и постановка задачи в очередь"""
    current_state = await state.get_state()
    
    if current_state != ImageEditStates.confirming:
        await callback.answer("Задача уже обработана или отменена")
        return
    
    data = await state.get_data()
    
    # Создать WorkflowParams
    workflow_params = WorkflowParams(
        input_image=data['image_path'],
        positive_prompt=data['positive_prompt'],
        negative_prompt=data.get('negative_prompt', ''),
        steps=data.get('steps', config.workflow.defaults.steps),
        cfg=data.get('cfg', config.workflow.defaults.cfg),
        sampler=data.get('sampler', config.workflow.defaults.sampler),
        seed=data.get('seed', config.workflow.defaults.seed),
        strength=data.get('strength', config.workflow.defaults.strength)
    )
    
    # Валидация
    try:
        workflow_params.validate(config.workflow.limits)
    except ValueError as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
        return
    
    # Создать задачу
    task = Task(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        image_path=Path(data['image_path']),
        workflow_params=workflow_params
    )
    
    try:
        position = await task_queue.add_task(task)
        
        logger.info(
            f"Task {task.id[:8]} created by user {callback.from_user.id}, "
            f"position: {position}"
        )
        
        # Очистить состояние
        await state.clear()
        
        await callback.message.edit_text(
            f"✅ <b>Задача добавлена в очередь</b>\n\n"
            f"🆔 ID: <code>{task.id[:8]}</code>\n"
            f"📍 Позиция: {position}\n\n"
            f"Ожидайте результат...",
            parse_mode="HTML"
        )
        
        await callback.answer("Задача добавлена!")
        
    except Exception as e:
        logger.error(f"Failed to add task: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "task_settings")
async def callback_settings(callback: CallbackQuery, state: FSMContext):
    """Открыть настройки параметров"""
    data = await state.get_data()
    
    await state.set_state(ImageEditStates.configuring_params)
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки параметров</b>\n\n"
        "Используйте кнопки для изменения значений:",
        parse_mode="HTML",
        reply_markup=create_settings_keyboard(data)
    )
    
    await callback.answer()


@router.callback_query(F.data == "task_cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена задачи"""
    await state.clear()
    
    logger.info(f"User {callback.from_user.id} cancelled task via callback")
    
    await callback.message.edit_text(
        "🚫 <b>Задача отменена</b>\n\n"
        "Используйте /new чтобы начать заново.",
        parse_mode="HTML"
    )
    
    await callback.answer("Задача отменена")


# =============================================================================
# Settings callbacks
# =============================================================================

@router.callback_query(F.data.startswith("steps_"))
async def callback_steps(callback: CallbackQuery, state: FSMContext, config: Config):
    """Изменение steps"""
    action = callback.data.split("_")[1]
    data = await state.get_data()
    
    current_steps = data.get('steps', config.workflow.defaults.steps)
    limits = config.workflow.limits
    
    if action == "inc":
        new_steps = min(current_steps + 1, limits.max_steps)
    elif action == "dec":
        new_steps = max(current_steps - 1, limits.min_steps)
    else:  # info
        await callback.answer(f"Steps: {limits.min_steps} - {limits.max_steps}")
        return
    
    if new_steps != current_steps:
        data['steps'] = new_steps
        await state.update_data(data)
        
        await callback.message.edit_reply_markup(
            reply_markup=create_settings_keyboard(data)
        )
    
    await callback.answer(f"Steps: {new_steps}")


@router.callback_query(F.data.startswith("cfg_"))
async def callback_cfg(callback: CallbackQuery, state: FSMContext, config: Config):
    """Изменение CFG"""
    action = callback.data.split("_")[1]
    data = await state.get_data()
    
    current_cfg = data.get('cfg', config.workflow.defaults.cfg)
    limits = config.workflow.limits
    
    if action == "inc":
        new_cfg = min(current_cfg + 0.5, limits.max_cfg)
    elif action == "dec":
        new_cfg = max(current_cfg - 0.5, limits.min_cfg)
    else:  # info
        await callback.answer(f"CFG: {limits.min_cfg} - {limits.max_cfg}")
        return
    
    if new_cfg != current_cfg:
        data['cfg'] = round(new_cfg, 1)
        await state.update_data(data)
        
        await callback.message.edit_reply_markup(
            reply_markup=create_settings_keyboard(data)
        )
    
    await callback.answer(f"CFG: {new_cfg:.1f}")


@router.callback_query(F.data.startswith("seed_"))
async def callback_seed(callback: CallbackQuery, state: FSMContext):
    """Настройка seed"""
    action = callback.data.split("_")[1]
    data = await state.get_data()
    
    if action == "random":
        # Переключить между random и текущим
        current_seed = data.get('seed', 0)
        if current_seed == 0:
            # Сгенерировать случайный seed
            import random
            new_seed = random.randint(1, 2**31 - 1)
        else:
            new_seed = 0  # Вернуть к random
        
        data['seed'] = new_seed
        await state.update_data(data)
        
        await callback.message.edit_reply_markup(
            reply_markup=create_settings_keyboard(data)
        )
        
        seed_text = str(new_seed) if new_seed > 0 else "random"
        await callback.answer(f"Seed: {seed_text}")
        
    elif action == "set":
        # TODO: Реализовать ввод seed через отдельное сообщение
        await callback.answer(
            "Для установки конкретного seed используйте кнопку 🎲 "
            "для переключения между random и фиксированным",
            show_alert=True
        )


@router.callback_query(F.data == "sampler_change")
async def callback_sampler_change(callback: CallbackQuery, state: FSMContext):
    """Открыть выбор sampler"""
    await callback.message.edit_text(
        "🔄 <b>Выберите sampler:</b>",
        parse_mode="HTML",
        reply_markup=create_sampler_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sampler_select_"))
async def callback_sampler_select(callback: CallbackQuery, state: FSMContext):
    """Выбор конкретного sampler"""
    sampler = callback.data.replace("sampler_select_", "")
    data = await state.get_data()
    
    data['sampler'] = sampler
    await state.update_data(data)
    
    logger.debug(f"User {callback.from_user.id} selected sampler: {sampler}")
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки параметров</b>\n\n"
        "Используйте кнопки для изменения значений:",
        parse_mode="HTML",
        reply_markup=create_settings_keyboard(data)
    )
    
    await callback.answer(f"Sampler: {sampler}")


@router.callback_query(F.data == "sampler_back")
async def callback_sampler_back(callback: CallbackQuery, state: FSMContext):
    """Вернуться из выбора sampler"""
    data = await state.get_data()
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки параметров</b>\n\n"
        "Используйте кнопки для изменения значений:",
        parse_mode="HTML",
        reply_markup=create_settings_keyboard(data)
    )
    
    await callback.answer()


@router.callback_query(F.data == "settings_apply")
async def callback_settings_apply(callback: CallbackQuery, state: FSMContext, config: Config):
    """Применить настройки и вернуться к подтверждению"""
    data = await state.get_data()
    
    await state.set_state(ImageEditStates.confirming)
    
    await _show_confirmation(callback.message, data, config, edit=True)
    await callback.answer("Настройки применены")


@router.callback_query(F.data == "settings_cancel")
async def callback_settings_cancel(callback: CallbackQuery, state: FSMContext, config: Config):
    """Отменить настройки и вернуться к подтверждению"""
    data = await state.get_data()
    
    # Восстановить дефолтные значения
    data['steps'] = config.workflow.defaults.steps
    data['cfg'] = config.workflow.defaults.cfg
    data['sampler'] = config.workflow.defaults.sampler
    data['seed'] = config.workflow.defaults.seed
    
    await state.update_data(data)
    await state.set_state(ImageEditStates.confirming)
    
    await _show_confirmation(callback.message, data, config, edit=True)
    await callback.answer("Настройки сброшены")


# =============================================================================
# Вспомогательные функции
# =============================================================================

async def _show_confirmation(message: Message, data: dict, config: Config, edit: bool = False):
    """Показать сообщение подтверждения с параметрами"""
    steps = data.get('steps', config.workflow.defaults.steps)
    cfg = data.get('cfg', config.workflow.defaults.cfg)
    sampler = data.get('sampler', config.workflow.defaults.sampler)
    seed = data.get('seed', 0)
    seed_text = str(seed) if seed > 0 else "random"
    
    text = (
        "📋 <b>Подтверждение задачи</b>\n\n"
        f"📝 <b>Промпт:</b> {data.get('positive_prompt', '')[:100]}...\n"
        f"🚫 <b>Negative:</b> {data.get('negative_prompt', '')[:50] or '(пусто)'}...\n\n"
        f"⚙️ <b>Параметры:</b>\n"
        f"• Steps: {steps}\n"
        f"• CFG: {cfg:.1f}\n"
        f"• Sampler: {sampler}\n"
        f"• Seed: {seed_text}\n\n"
        "Запустить генерацию?"
    )
    
    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=create_confirm_keyboard())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=create_confirm_keyboard())
