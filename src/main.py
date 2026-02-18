#!/usr/bin/env python3
"""
Qwen Image Edit Bot - Telegram бот для редактирования изображений через ComfyUI
"""

import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger
from src.bot.handlers import router
from src.bot.filters import WhitelistFilter, RateLimitFilter
from src.comfyui.client import ComfyUIClient
from src.comfyui.launcher import ComfyUILauncher
from src.comfyui.workflow import WorkflowManager
from src.queue.task_queue import TaskQueue
from src.queue.processor import TaskProcessor
from src.storage.file_manager import FileManager
from src.storage.user_settings import UserSettingsManager


class Application:
    """Главное приложение бота"""
    
    def __init__(self):
        """Инициализация приложения"""
        self.config = None
        self.bot = None
        self.dp = None
        self.comfyui_client = None
        self.comfyui_launcher = None
        self.workflow_manager = None
        self.task_queue = None
        self.task_processor = None
        self.file_manager = None
        self.user_settings_manager = None
        self.processor_task = None
        self.cleanup_task = None
        self.shutdown_event = asyncio.Event()
        
    async def setup(self):
        """Настройка всех компонентов"""
        # 1. Загрузка конфигурации
        logger.info("Loading configuration...")
        self.config = load_config()
        
        # 2. Настройка логирования
        setup_logger(self.config.logs_dir, self.config.logging.level)
        logger.info("Configuration loaded successfully")
        
        # 3. Инициализация Telegram бота
        logger.info("Initializing Telegram bot...")
        self.bot = Bot(
            token=self.config.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # 3.1. Установка меню команд
        commands = [
            BotCommand(command="start", description="🚀 Начать работу"),
            BotCommand(command="new", description="✨ Новая задача"),
            BotCommand(command="settings", description="⚙️ Настройки"),
            BotCommand(command="status", description="📊 Статус очереди"),
            BotCommand(command="cancel", description="❌ Отменить задачу"),
            BotCommand(command="help", description="ℹ️ Справка")
        ]
        await self.bot.set_my_commands(commands)
        logger.info("Bot commands menu set")
        
        # 4. Dispatcher с роутером
        self.dp = Dispatcher()
        self.dp.include_router(router)
        
        # 5. Фильтры (опционально)
        if self.config.admin_user_ids:
            logger.info(f"Whitelist enabled: {len(self.config.admin_user_ids)} users")
            # Whitelist применяется в handlers.py через dependency injection
        
        # 6. ComfyUI - инициализация и запуск
        await self._setup_comfyui()
        
    async def _setup_comfyui(self):
        """Настройка и запуск ComfyUI"""
        comfyui_config = self.config.comfyui
        host = comfyui_config.host
        port = comfyui_config.port
        
        # Инициализация клиента
        logger.info("Initializing ComfyUI client...")
        self.comfyui_client = ComfyUIClient(host=host, port=port)
        await self.comfyui_client.connect()
        
        # Проверяем, запущен ли уже ComfyUI
        if await self.comfyui_client.check_health():
            logger.success("✅ ComfyUI is already running")
            return
        
        # ComfyUI не запущен - проверяем, нужно ли его запускать
        if not comfyui_config.auto_start:
            logger.error("ComfyUI is not running and auto_start is disabled!")
            await self.comfyui_client.close()
            raise RuntimeError("ComfyUI is not available")
        
        # Проверяем, указан ли путь к ComfyUI
        if not comfyui_config.dir:
            logger.error("ComfyUI is not running and COMFYUI_DIR is not set!")
            logger.error("Please either:")
            logger.error("  1. Start ComfyUI manually, or")
            logger.error("  2. Set COMFYUI_DIR in .env to auto-start")
            await self.comfyui_client.close()
            raise RuntimeError("ComfyUI path not configured")
        
        # Запускаем ComfyUI
        logger.info(f"ComfyUI not running, starting from {comfyui_config.dir}...")
        self.comfyui_launcher = ComfyUILauncher(
            comfyui_dir=comfyui_config.dir,
            host=host,
            port=port,
            venv_path=comfyui_config.venv,
            extra_args=comfyui_config.args
        )
        
        if not await self.comfyui_launcher.start():
            logger.error("Failed to start ComfyUI!")
            await self.comfyui_client.close()
            raise RuntimeError("Failed to start ComfyUI")
        
        # Ожидание готовности ComfyUI
        max_attempts = comfyui_config.startup_timeout // 5
        if not await self.comfyui_client.wait_for_ready(max_attempts=max_attempts, delay=5):
            logger.error(f"ComfyUI failed to start within {comfyui_config.startup_timeout}s!")
            await self.comfyui_launcher.stop()
            await self.comfyui_client.close()
            raise RuntimeError("ComfyUI startup timeout")
        
        logger.success("✅ ComfyUI started and ready")
        
        # 7. Workflow manager
        workflow_path = self.config.workflows_dir / self.config.workflow.default_file
        ui_workflow_path = Path("Qwen Image Edit Rapid.json")  # UI формат для extra_pnginfo
        self.workflow_manager = WorkflowManager(workflow_path, ui_workflow_path)
        logger.info(f"Workflow loaded: {workflow_path}")
        
        # 8. Task queue
        self.task_queue = TaskQueue(max_size=self.config.queue.max_size)
        logger.info(f"Task queue initialized (max_size: {self.config.queue.max_size})")
        
        # 9. File manager
        self.file_manager = FileManager(self.config.data_dir)
        logger.info("File manager initialized")
        
        # 9.1. User settings manager
        self.user_settings_manager = UserSettingsManager(self.config.data_dir)
        logger.info("User settings manager initialized")
        
        # 10. Task processor
        self.task_processor = TaskProcessor(
            task_queue=self.task_queue,
            comfyui_client=self.comfyui_client,
            workflow_manager=self.workflow_manager,
            bot=self.bot,
            timeout=self.config.queue.timeout_seconds
        )
        logger.info("Task processor initialized")
        
        # 11. Передача зависимостей в handlers через middleware
        self.dp["task_queue"] = self.task_queue
        self.dp["comfyui_client"] = self.comfyui_client
        self.dp["config"] = self.config
        self.dp["file_manager"] = self.file_manager
        self.dp["user_settings_manager"] = self.user_settings_manager
        
        logger.success("All components initialized successfully")
        
    async def start(self):
        """Запуск приложения"""
        logger.info("Starting application...")
        
        # Запуск processor в фоне
        self.processor_task = asyncio.create_task(self.task_processor.start())
        logger.info("Task processor started")
        
        # Запуск cleanup task в фоне
        self.cleanup_task = asyncio.create_task(
            self.file_manager.start_cleanup_task(
                interval_hours=1,
                max_age_hours=self.config.storage.cleanup_after_hours,
                keep_results=self.config.storage.keep_results
            )
        )
        logger.info("File cleanup task started")
        
        # Запуск polling
        logger.success("🚀 Bot started successfully!")
        logger.info("Press Ctrl+C to stop")
        
        try:
            await self.dp.start_polling(
                self.bot,
                allowed_updates=self.dp.resolve_used_update_types()
            )
        except asyncio.CancelledError:
            logger.info("Polling cancelled")
            
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down application...")
        
        # 1. Остановить polling
        await self.dp.stop_polling()
        logger.info("Polling stopped")
        
        # 2. Остановить processor (ждёт текущую задачу до 60 сек)
        await self.task_processor.stop()
        
        # 3. Отменить processor task
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Task processor stopped")
        
        # 4. Отменить cleanup task
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup task stopped")
        
        # 5. Остановить ComfyUI (если запускали)
        if self.comfyui_launcher:
            logger.info("Stopping ComfyUI...")
            await self.comfyui_launcher.stop(timeout=30)
        logger.info("ComfyUI stopped")
        
        # 6. Закрыть ComfyUI клиент
        if self.comfyui_client:
            await self.comfyui_client.close()
        logger.info("ComfyUI client closed")
        
        # 7. Закрыть bot session
        if self.bot:
            await self.bot.session.close()
        logger.info("Bot session closed")
        
        logger.success("Application stopped gracefully")


async def main():
    """Главная функция"""
    app = Application()
    
    # Обработка сигналов для graceful shutdown
    def signal_handler(sig):
        """Обработчик SIGINT/SIGTERM"""
        logger.warning(f"Received signal {signal.Signals(sig).name}, initiating shutdown...")
        app.shutdown_event.set()
    
    # Регистрация обработчиков сигналов
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    
    try:
        # Настройка компонентов
        await app.setup()
        
        # Запуск приложения
        start_task = asyncio.create_task(app.start())
        
        # Ожидание shutdown event или завершения start_task
        done, pending = await asyncio.wait(
            [start_task, asyncio.create_task(app.shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Если получен сигнал shutdown
        if app.shutdown_event.is_set():
            # Отменить start_task
            for task in pending:
                task.cancel()
            
            # Graceful shutdown
            await app.shutdown()
        else:
            # start_task завершился (ошибка или нормальное завершение)
            await app.shutdown()
            
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received")
        await app.shutdown()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        await app.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.critical(f"Application crashed: {e}")
        sys.exit(1)
