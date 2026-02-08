# 🔧 Технические спецификации компонентов

## 1. ComfyUI Client (`src/comfyui/client.py`)

### Интерфейс класса

```python
from typing import Dict, Optional, List
from pathlib import Path
import aiohttp
import asyncio

class ComfyUIClient:
    """Клиент для взаимодействия с ComfyUI API"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.client_id = None
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Контекстный менеджер для session"""
        self.session = aiohttp.ClientSession()
        self.client_id = str(uuid.uuid4())
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> bool:
        """Проверка доступности ComfyUI"""
        ...
    
    async def upload_image(self, image_path: Path, subfolder: str = "") -> Dict:
        """Загрузка изображения на ComfyUI сервер
        
        Args:
            image_path: Путь к изображению
            subfolder: Подпапка для сохранения
            
        Returns:
            {"name": "uploaded_filename.png", "subfolder": "", "type": "input"}
        """
        ...
    
    async def queue_prompt(self, workflow: Dict) -> str:
        """Постановка workflow в очередь
        
        Args:
            workflow: Модифицированный workflow JSON
            
        Returns:
            prompt_id: Уникальный ID задачи
        """
        ...
    
    async def get_history(self, prompt_id: str) -> Dict:
        """Получение истории выполнения
        
        Args:
            prompt_id: ID задачи
            
        Returns:
            История выполнения с результатами
        """
        ...
    
    async def get_image(self, filename: str, subfolder: str = "", 
                       folder_type: str = "output") -> bytes:
        """Скачивание результирующего изображения
        
        Args:
            filename: Имя файла
            subfolder: Подпапка
            folder_type: Тип папки (output/input/temp)
            
        Returns:
            Бинарные данные изображения
        """
        ...
    
    async def track_progress(self, prompt_id: str, 
                           callback: Optional[callable] = None) -> Dict:
        """Отслеживание прогресса через WebSocket
        
        Args:
            prompt_id: ID задачи
            callback: Функция для обновления прогресса
            
        Returns:
            Финальный результат выполнения
        """
        ...
```

### REST API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/system_stats` | Статистика системы |
| `GET` | `/prompt` | Текущая очередь |
| `POST` | `/prompt` | Добавить задачу |
| `POST` | `/upload/image` | Загрузить изображение |
| `GET` | `/view` | Просмотр изображения |
| `GET` | `/history/{prompt_id}` | История задачи |
| `WS` | `/ws?clientId={id}` | WebSocket для прогресса |

### WebSocket Messages

```python
# Типы сообщений
{
    "type": "status",
    "data": {
        "status": {
            "exec_info": {
                "queue_remaining": 0
            }
        }
    }
}

{
    "type": "progress",
    "data": {
        "value": 5,    # Текущий шаг
        "max": 8       # Всего шагов
    }
}

{
    "type": "executing",
    "data": {
        "node": "121",  # ID узла
        "prompt_id": "abc-123"
    }
}

{
    "type": "execution_cached",
    "data": {
        "nodes": ["78", "118"],
        "prompt_id": "abc-123"
    }
}

{
    "type": "executed",
    "data": {
        "node": "102",
        "output": {
            "images": [{
                "filename": "result_001.webp",
                "subfolder": "qwen_edit/2026-02-08",
                "type": "output"
            }]
        }
    }
}
```

---

## 2. Workflow Manager (`src/comfyui/workflow.py`)

### Интерфейс класса

```python
from typing import Dict, Any
from pathlib import Path
import json

class WorkflowManager:
    """Управление и модификация ComfyUI workflow"""
    
    def __init__(self, template_path: Path):
        self.template_path = template_path
        self.template = self._load_template()
        
    def _load_template(self) -> Dict:
        """Загрузка базового workflow шаблона"""
        ...
        
    def create_workflow(self, params: WorkflowParams) -> Dict:
        """Создание workflow с параметрами пользователя
        
        Args:
            params: Параметры для workflow
            
        Returns:
            Модифицированный workflow JSON
        """
        workflow = self.template.copy()
        
        # Модификация узлов
        self._set_input_image(workflow, params.input_image)
        self._set_prompts(workflow, params.positive_prompt, params.negative_prompt)
        self._set_sampling_params(workflow, params)
        self._set_seed(workflow, params.seed)
        
        return workflow
        
    def _set_input_image(self, workflow: Dict, image_name: str):
        """Установка входного изображения (Node 78)"""
        workflow["78"]["inputs"]["image"] = image_name
        
    def _set_prompts(self, workflow: Dict, positive: str, negative: str):
        """Установка промптов (Nodes 119, 77)"""
        workflow["119"]["inputs"]["prompt"] = positive
        workflow["77"]["inputs"]["prompt"] = negative
        
    def _set_sampling_params(self, workflow: Dict, params: WorkflowParams):
        """Установка параметров сэмплинга (Node 121)"""
        node_121 = workflow["121"]["inputs"]
        node_121["sampler_name"] = params.sampler
        node_121["scheduler"] = params.scheduler
        node_121["cfg"] = params.cfg
        node_121["eta"] = params.eta
        node_121["denoise"] = params.denoise
        
    def _set_seed(self, workflow: Dict, seed: int):
        """Установка seed (Node 117)"""
        if seed <= 0:
            seed = random.randint(0, 2**32 - 1)
        workflow["117"]["inputs"]["value"] = seed
        
    def _set_steps(self, workflow: Dict, steps: int):
        """Установка количества шагов (Node 115)"""
        workflow["115"]["inputs"]["value"] = steps
        workflow["121"]["inputs"]["steps"] = steps
```

### Dataclass для параметров

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class WorkflowParams:
    """Параметры для генерации workflow"""
    
    # Обязательные
    input_image: str
    positive_prompt: str
    
    # Опциональные (defaults из config)
    negative_prompt: str = ""
    steps: int = 8
    cfg: float = 1.0
    sampler: str = "linear/euler"
    scheduler: str = "simple"
    seed: int = 0  # 0 = random
    strength: float = 0.5
    eta: float = 0.5
    denoise: float = 1.0
    
    def validate(self):
        """Валидация параметров"""
        if not 1 <= self.steps <= 50:
            raise ValueError("Steps must be between 1 and 50")
        if not 0.1 <= self.cfg <= 20.0:
            raise ValueError("CFG must be between 0.1 and 20.0")
        # ... другие проверки
```

---

## 3. Task Queue (`src/queue/task_queue.py`)

### Интерфейс класса

```python
import asyncio
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class Task:
    """Задача для обработки"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0
    chat_id: int = 0
    message_id: int = 0
    
    # Данные задачи
    image_path: Path = None
    workflow_params: WorkflowParams = None
    
    # Метаданные
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Статус
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    result_path: Optional[Path] = None

class TaskQueue:
    """FIFO очередь задач с async support"""
    
    def __init__(self, max_size: int = 100):
        self.queue: asyncio.Queue[Task] = asyncio.Queue(maxsize=max_size)
        self.current_task: Optional[Task] = None
        self.completed_tasks: List[Task] = []
        
    async def add_task(self, task: Task) -> int:
        """Добавление задачи в очередь
        
        Returns:
            Позиция в очереди
        """
        await self.queue.put(task)
        return self.queue.qsize()
        
    async def get_task(self) -> Task:
        """Получение следующей задачи (блокирующая операция)"""
        task = await self.queue.get()
        task.status = "processing"
        task.started_at = datetime.now()
        self.current_task = task
        return task
        
    def task_done(self, task: Task, success: bool = True, 
                  result_path: Optional[Path] = None, error: Optional[str] = None):
        """Завершение обработки задачи"""
        task.completed_at = datetime.now()
        task.status = "completed" if success else "failed"
        task.result_path = result_path
        task.error = error
        
        self.completed_tasks.append(task)
        self.current_task = None
        self.queue.task_done()
        
    def get_status(self) -> Dict:
        """Получение статуса очереди"""
        return {
            "queue_size": self.queue.qsize(),
            "current_task": self.current_task.id if self.current_task else None,
            "completed_today": len([
                t for t in self.completed_tasks 
                if t.completed_at.date() == datetime.now().date()
            ])
        }
```

---

## 4. Telegram Bot Handlers (`src/bot/handlers.py`)

### FSM States

```python
from aiogram.fsm.state import State, StatesGroup

class ImageEditStates(StatesGroup):
    """Состояния для процесса редактирования"""
    waiting_for_image = State()
    waiting_for_prompt = State()
    waiting_for_negative = State()
    configuring_params = State()
    confirming = State()
```

### Handlers

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот для редактирования изображений.\n\n"
        "🎨 Отправьте /new чтобы начать\n"
        "⚙️ /settings - настройки параметров\n"
        "📊 /status - статус очереди\n"
        "❓ /help - помощь"
    )

@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    """Начало создания новой задачи"""
    await state.set_state(ImageEditStates.waiting_for_image)
    await message.answer(
        "📸 Отправьте изображение для редактирования\n"
        "Поддерживаемые форматы: JPG, PNG, WEBP\n"
        "Максимальный размер: 10 MB"
    )

@router.message(ImageEditStates.waiting_for_image, F.photo)
async def handle_image(message: Message, state: FSMContext):
    """Обработка полученного изображения"""
    # Получение файла с наилучшим качеством
    photo = message.photo[-1]
    
    # Скачивание
    file = await message.bot.get_file(photo.file_id)
    file_path = Path(f"data/input/{message.from_user.id}_{photo.file_id}.jpg")
    await message.bot.download_file(file.file_path, file_path)
    
    # Сохранение в state
    await state.update_data(image_path=str(file_path))
    await state.set_state(ImageEditStates.waiting_for_prompt)
    
    await message.answer(
        "✅ Изображение получено!\n\n"
        "✏️ Теперь отправьте промпт с описанием изменений\n"
        "Пример: 'remove background, make it professional portrait'"
    )

@router.message(ImageEditStates.waiting_for_prompt, F.text)
async def handle_prompt(message: Message, state: FSMContext):
    """Обработка промпта"""
    await state.update_data(positive_prompt=message.text)
    await state.set_state(ImageEditStates.waiting_for_negative)
    
    await message.answer(
        "📝 Промпт сохранен!\n\n"
        "❌ Отправьте negative промпт (что НЕ должно быть на изображении)\n"
        "Или отправьте /skip чтобы пропустить"
    )

@router.message(Command("skip"))
async def skip_negative(message: Message, state: FSMContext):
    """Пропуск negative промпта"""
    await state.update_data(negative_prompt="")
    await confirm_task(message, state)

@router.message(ImageEditStates.waiting_for_negative, F.text)
async def handle_negative(message: Message, state: FSMContext):
    """Обработка negative промпта"""
    await state.update_data(negative_prompt=message.text)
    await confirm_task(message, state)

async def confirm_task(message: Message, state: FSMContext):
    """Подтверждение задачи"""
    data = await state.get_data()
    
    # Создание inline клавиатуры
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Запустить", callback_data="task_confirm"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="task_settings")
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="task_cancel")]
    ])
    
    await message.answer(
        f"📋 Параметры задачи:\n\n"
        f"🎨 Промпт: {data['positive_prompt']}\n"
        f"❌ Negative: {data.get('negative_prompt', 'не указан')}\n"
        f"🔢 Steps: {data.get('steps', 8)}\n"
        f"🎲 Seed: {data.get('seed', 'random')}\n\n"
        f"Что дальше?",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "task_confirm")
async def callback_confirm(callback: CallbackQuery, state: FSMContext, 
                          task_queue: TaskQueue, comfyui_client: ComfyUIClient):
    """Подтверждение и постановка в очередь"""
    data = await state.get_data()
    
    # Создание задачи
    task = Task(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        image_path=Path(data['image_path']),
        workflow_params=WorkflowParams(
            input_image=Path(data['image_path']).name,
            positive_prompt=data['positive_prompt'],
            negative_prompt=data.get('negative_prompt', ''),
            steps=data.get('steps', 8),
            seed=data.get('seed', 0)
        )
    )
    
    # Добавление в очередь
    position = await task_queue.add_task(task)
    
    await callback.message.edit_text(
        f"✅ Задача добавлена в очередь!\n\n"
        f"🔢 Позиция: {position}\n"
        f"🆔 Task ID: {task.id[:8]}\n\n"
        f"⏳ Ожидайте, обработка начнется автоматически..."
    )
    
    await state.clear()

@router.callback_query(F.data == "task_settings")
async def callback_settings(callback: CallbackQuery, state: FSMContext):
    """Открытие настроек параметров"""
    data = await state.get_data()
    
    keyboard = create_settings_keyboard(data)
    
    await callback.message.edit_text(
        "⚙️ Настройки параметров генерации:",
        reply_markup=keyboard
    )
```

### Settings Keyboard

```python
def create_settings_keyboard(data: Dict) -> InlineKeyboardMarkup:
    """Создание клавиатуры для настроек"""
    steps = data.get('steps', 8)
    seed = data.get('seed', 0)
    cfg = data.get('cfg', 1.0)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⊖", callback_data="steps_dec"),
            InlineKeyboardButton(text=f"Steps: {steps}", callback_data="steps_info"),
            InlineKeyboardButton(text="⊕", callback_data="steps_inc")
        ],
        [
            InlineKeyboardButton(text="🎲 Random Seed", callback_data="seed_random"),
            InlineKeyboardButton(text=f"Seed: {seed if seed > 0 else 'random'}", 
                               callback_data="seed_set")
        ],
        [
            InlineKeyboardButton(text="⊖", callback_data="cfg_dec"),
            InlineKeyboardButton(text=f"CFG: {cfg:.1f}", callback_data="cfg_info"),
            InlineKeyboardButton(text="⊕", callback_data="cfg_inc")
        ],
        [
            InlineKeyboardButton(text="🔄 Sampler", callback_data="sampler_change")
        ],
        [
            InlineKeyboardButton(text="✅ Применить", callback_data="settings_apply"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="settings_cancel")
        ]
    ])
    
    return keyboard

@router.callback_query(F.data.startswith("steps_"))
async def callback_steps(callback: CallbackQuery, state: FSMContext):
    """Изменение количества шагов"""
    data = await state.get_data()
    current = data.get('steps', 8)
    
    if callback.data == "steps_inc":
        new_value = min(current + 1, 50)
    elif callback.data == "steps_dec":
        new_value = max(current - 1, 1)
    else:
        return
    
    await state.update_data(steps=new_value)
    
    # Обновление клавиатуры
    keyboard = create_settings_keyboard(await state.get_data())
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer(f"Steps: {new_value}")
```

---

## 5. Task Processor (`src/queue/processor.py`)

### Обработчик задач

```python
import asyncio
from typing import Optional
from pathlib import Path

class TaskProcessor:
    """Обработчик задач из очереди"""
    
    def __init__(self, task_queue: TaskQueue, comfyui_client: ComfyUIClient,
                 workflow_manager: WorkflowManager, bot):
        self.task_queue = task_queue
        self.comfyui = comfyui_client
        self.workflow_manager = workflow_manager
        self.bot = bot
        self.is_running = False
        
    async def start(self):
        """Запуск обработчика"""
        self.is_running = True
        logger.info("Task processor started")
        
        while self.is_running:
            try:
                # Получаем задачу (блокирующая операция)
                task = await self.task_queue.get_task()
                logger.info(f"Processing task {task.id}")
                
                # Обработка
                await self.process_task(task)
                
            except asyncio.CancelledError:
                logger.info("Task processor stopped")
                break
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                
    async def stop(self):
        """Остановка обработчика"""
        self.is_running = False
        
    async def process_task(self, task: Task):
        """Обработка одной задачи"""
        try:
            # 1. Отправка статуса в Telegram
            await self.notify_user(task, "🔄 Обработка началась...")
            
            # 2. Загрузка изображения в ComfyUI
            upload_result = await self.comfyui.upload_image(task.image_path)
            logger.debug(f"Image uploaded: {upload_result}")
            
            # 3. Создание workflow
            task.workflow_params.input_image = upload_result["name"]
            workflow = self.workflow_manager.create_workflow(task.workflow_params)
            
            # 4. Постановка в очередь ComfyUI
            prompt_id = await self.comfyui.queue_prompt(workflow)
            logger.info(f"Prompt queued: {prompt_id}")
            
            # 5. Отслеживание прогресса
            async def progress_callback(progress: int, total: int):
                percent = int((progress / total) * 100)
                await self.notify_user(task, f"⏳ Прогресс: {percent}% ({progress}/{total})")
            
            result = await self.comfyui.track_progress(prompt_id, progress_callback)
            
            # 6. Получение результата
            output_images = result["outputs"]["102"]["images"]
            result_image = output_images[0]
            
            # 7. Скачивание результата
            image_data = await self.comfyui.get_image(
                result_image["filename"],
                result_image["subfolder"]
            )
            
            # 8. Сохранение локально
            result_path = Path(f"data/output/{task.id}_{result_image['filename']}")
            result_path.write_bytes(image_data)
            
            # 9. Отправка пользователю
            await self.bot.send_photo(
                chat_id=task.chat_id,
                photo=FSInputFile(result_path),
                caption=f"✅ Готово!\n\n"
                        f"🎨 Промпт: {task.workflow_params.positive_prompt}\n"
                        f"🔢 Steps: {task.workflow_params.steps}\n"
                        f"🎲 Seed: {task.workflow_params.seed}"
            )
            
            # 10. Завершение задачи
            self.task_queue.task_done(task, success=True, result_path=result_path)
            logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            # Обработка ошибки
            logger.error(f"Task {task.id} failed: {e}")
            self.task_queue.task_done(task, success=False, error=str(e))
            
            await self.notify_user(
                task, 
                f"❌ Ошибка при обработке:\n{str(e)}\n\nПопробуйте еще раз."
            )
            
    async def notify_user(self, task: Task, text: str):
        """Отправка уведомления пользователю"""
        try:
            await self.bot.edit_message_text(
                chat_id=task.chat_id,
                message_id=task.message_id,
                text=text
            )
        except Exception as e:
            logger.warning(f"Failed to notify user: {e}")
```

---

## 6. Configuration Loader (`src/utils/config_loader.py`)

```python
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field

class WorkflowDefaults(BaseModel):
    steps: int = 8
    cfg: float = 1.0
    sampler: str = "linear/euler"
    scheduler: str = "simple"
    seed: int = 0
    strength: float = 0.5
    eta: float = 0.5
    denoise: float = 1.0

class WorkflowLimits(BaseModel):
    min_steps: int = 1
    max_steps: int = 50
    min_cfg: float = 0.1
    max_cfg: float = 20.0
    min_strength: float = 0.0
    max_strength: float = 1.0

class Config(BaseModel):
    """Полная конфигурация приложения"""
    
    # Telegram
    telegram_bot_token: str
    admin_user_ids: list[int] = []
    
    # ComfyUI
    comfyui_host: str = "127.0.0.1"
    comfyui_port: int = 8188
    
    # Paths
    data_dir: Path = Path("data")
    logs_dir: Path = Path("logs")
    workflows_dir: Path = Path("workflows")
    
    # Workflow
    workflow_defaults: WorkflowDefaults = WorkflowDefaults()
    workflow_limits: WorkflowLimits = WorkflowLimits()
    
    # Queue
    queue_max_size: int = 100
    queue_timeout: int = 300
    
    # Storage
    cleanup_after_hours: int = 24
    keep_results: bool = True
    
    @classmethod
    def load(cls) -> "Config":
        """Загрузка конфигурации из .env и config.yaml"""
        # Загрузка .env
        load_dotenv()
        
        # Загрузка config.yaml
        config_path = Path("config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                yaml_config = yaml.safe_load(f)
        else:
            yaml_config = {}
        
        # Объединение с env переменными
        config_data = {
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
            "admin_user_ids": [
                int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x
            ],
            "comfyui_host": os.getenv("COMFYUI_HOST", "127.0.0.1"),
            "comfyui_port": int(os.getenv("COMFYUI_PORT", 8188)),
            **yaml_config
        }
        
        return cls(**config_data)
```

---

## 7. Logger Setup (`src/utils/logger.py`)

```python
from loguru import logger
import sys
from pathlib import Path

def setup_logger(logs_dir: Path = Path("logs"), level: str = "INFO"):
    """Настройка логирования"""
    
    logs_dir.mkdir(exist_ok=True)
    
    # Удаление стандартного handler
    logger.remove()
    
    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level
    )
    
    # File handler - общий
    logger.add(
        logs_dir / "bot.log",
        rotation="100 MB",
        retention="7 days",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=True
    )
    
    # File handler - только ошибки
    logger.add(
        logs_dir / "errors.log",
        rotation="50 MB",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Logger initialized")
    return logger
```

---

## 8. Main Entry Point (`src/main.py`)

```python
import asyncio
from aiogram import Bot, Dispatcher
from pathlib import Path

from utils.config_loader import Config
from utils.logger import setup_logger
from bot.handlers import router
from comfyui.client import ComfyUIClient
from comfyui.workflow import WorkflowManager
from queue.task_queue import TaskQueue
from queue.processor import TaskProcessor

async def main():
    """Главная точка входа"""
    
    # Загрузка конфигурации
    config = Config.load()
    
    # Настройка логирования
    logger = setup_logger(config.logs_dir)
    
    # Инициализация компонентов
    bot = Bot(token=config.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    
    # ComfyUI клиент
    comfyui_client = ComfyUIClient(
        host=config.comfyui_host,
        port=config.comfyui_port
    )
    
    # Проверка доступности ComfyUI
    if not await comfyui_client.check_health():
        logger.error("ComfyUI is not available!")
        return
    
    # Workflow manager
    workflow_manager = WorkflowManager(
        template_path=config.workflows_dir / "qwen_image_edit.json"
    )
    
    # Task queue
    task_queue = TaskQueue(max_size=config.queue_max_size)
    
    # Task processor
    processor = TaskProcessor(
        task_queue=task_queue,
        comfyui_client=comfyui_client,
        workflow_manager=workflow_manager,
        bot=bot
    )
    
    # Передача зависимостей в handlers
    dp["task_queue"] = task_queue
    dp["comfyui_client"] = comfyui_client
    dp["config"] = config
    
    # Запуск processor в фоне
    processor_task = asyncio.create_task(processor.start())
    
    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown
        await processor.stop()
        await processor_task
        await bot.session.close()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

---

**Статус**: Технические спецификации готовы ✅  
**Следующий шаг**: Создание конфигурационных файлов и скриптов установки
