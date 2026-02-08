"""Inline клавиатуры для Telegram бота"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Any


def create_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения задачи
    
    Returns:
        InlineKeyboardMarkup с кнопками подтверждения/настроек/отмены
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Запустить", callback_data="task_confirm"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="task_settings")
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="task_cancel")]
    ])


def create_settings_keyboard(data: Dict[str, Any]) -> InlineKeyboardMarkup:
    """
    Клавиатура настроек параметров генерации
    
    Args:
        data: Словарь с текущими параметрами (steps, seed, cfg, sampler, etc.)
        
    Returns:
        InlineKeyboardMarkup с кнопками настроек
    """
    steps = data.get('steps', 8)
    seed = data.get('seed', 0)
    cfg = data.get('cfg', 1.0)
    sampler = data.get('sampler', 'linear/euler')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Steps
        [
            InlineKeyboardButton(text="⊖", callback_data="steps_dec"),
            InlineKeyboardButton(text=f"Steps: {steps}", callback_data="steps_info"),
            InlineKeyboardButton(text="⊕", callback_data="steps_inc")
        ],
        # Seed
        [
            InlineKeyboardButton(
                text=f"🎲 Seed: {seed if seed > 0 else 'random'}", 
                callback_data="seed_random"
            ),
            InlineKeyboardButton(text="🔢 Установить", callback_data="seed_set")
        ],
        # CFG
        [
            InlineKeyboardButton(text="⊖", callback_data="cfg_dec"),
            InlineKeyboardButton(text=f"CFG: {cfg:.1f}", callback_data="cfg_info"),
            InlineKeyboardButton(text="⊕", callback_data="cfg_inc")
        ],
        # Sampler
        [
            InlineKeyboardButton(
                text=f"🔄 Sampler: {sampler}", 
                callback_data="sampler_change"
            )
        ],
        # Действия
        [
            InlineKeyboardButton(text="✅ Применить", callback_data="settings_apply"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="settings_cancel")
        ]
    ])
    
    return keyboard


def create_sampler_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора sampler
    
    Returns:
        InlineKeyboardMarkup со списком доступных samplers
    """
    samplers = [
        "linear/euler",
        "linear/euler_ancestral", 
        "linear/heun",
        "linear/dpm_2",
        "linear/lms"
    ]
    
    buttons = [
        [InlineKeyboardButton(text=s, callback_data=f"sampler_select_{s}")]
        for s in samplers
    ]
    buttons.append([InlineKeyboardButton(text="◀ Назад", callback_data="sampler_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены
    
    Returns:
        InlineKeyboardMarkup с одной кнопкой отмены
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="task_cancel")]
    ])


def create_skip_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для пропуска negative prompt
    
    Returns:
        InlineKeyboardMarkup с кнопкой пропуска
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_negative")]
    ])


def create_user_settings_keyboard(default_prompt: str, auto_confirm: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура пользовательских настроек
    
    Args:
        default_prompt: Текущий промпт по умолчанию
        auto_confirm: Состояние автоподтверждения
        
    Returns:
        InlineKeyboardMarkup с настройками пользователя
    """
    # Статус промпта
    prompt_status = "✅ Установлен" if default_prompt else "❌ Не установлен"
    prompt_text = f"📝 Промпт: {prompt_status}"
    
    # Статус автоподтверждения
    auto_status = "✅ Вкл" if auto_confirm else "❌ Выкл"
    auto_text = f"⚡ Автозапуск: {auto_status}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=prompt_text, callback_data="user_set_prompt")],
        [InlineKeyboardButton(text=auto_text, callback_data="user_toggle_auto")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="user_settings_help")],
        [InlineKeyboardButton(text="◀️ Закрыть", callback_data="user_settings_close")]
    ])
