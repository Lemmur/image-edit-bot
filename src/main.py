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

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger
from src.bot.handlers import router
from src.bot.filters import WhitelistFilter, RateLimitFilter
from src.comfyui.client import ComfyUIClient
from src.comfyui.workflow import WorkflowManager
from src.queue.task_queue import TaskQueue
from src.queue.processor import TaskProcessor
from src.storage.file_manager import FileManager


class Application:
    """Главное приложение бота"""
    
    def __init__(self):
        """Инициализация приложения"""
        self.config = None
        self.bot = None
        self.dp = None
        self.comfyui_client = None
        self.workflow_manager = None
        self.task_queue = None
        self.task_processor = None
        self.file_manager = None
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
        
        # 4. Dispatcher с роутером
        self.dp = Dispatcher()
        self.dp.include_router(router)
        
        # 5. Фильтры (опционально)
        if self.config.admin_user_ids:
            logger.info(f"Whitelist enabled: {len(self.config.admin_user_ids)} users")
            # Whitelist применяется в handlers.py через dependency injection
        
        # 6. ComfyUI клиент
        logger.info("Initializing ComfyUI client...")
        self.comfyui_client = ComfyUIClient(
            host=self.config.comfyui_host,
            port=self.config.comfyui_port
        )
        
        # Открыть сессию для долгоживущего соединения
        await self.comfyui_client.connect()
        
        # Проверка доступности ComfyUI с retry
        if not await self.comfyui_client.wait_for_ready(max_attempts=60, delay=5):
            logger.error("ComfyUI is not available after 5 minutes!")
            await self.comfyui_client.close()
            raise RuntimeError("ComfyUI connection failed")
        
        logger.success("ComfyUI is ready")
        
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
        
        # 5. Закрыть ComfyUI клиент
        if self.comfyui_client:
            await self.comfyui_client.close()
        logger.info("ComfyUI client closed")
        
        # 6. Закрыть bot session
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
