import asyncio
from typing import Optional
from pathlib import Path
from loguru import logger
from aiogram import Bot
from aiogram.types import FSInputFile

from src.queue.task_queue import TaskQueue
from src.comfyui.client import ComfyUIClient
from src.comfyui.workflow import WorkflowManager
from src.comfyui.websocket import track_progress
from src.models.task import Task


class TaskProcessor:
    """Обработчик задач из очереди"""
    
    def __init__(
        self, 
        task_queue: TaskQueue, 
        comfyui_client: ComfyUIClient,
        workflow_manager: WorkflowManager, 
        bot: Bot,
        timeout: int = 300
    ):
        """
        Инициализация процессора
        
        Args:
            task_queue: Очередь задач
            comfyui_client: Клиент ComfyUI API
            workflow_manager: Менеджер workflow
            bot: Telegram bot instance
            timeout: Таймаут обработки задачи в секундах (из config.queue.timeout_seconds)
        """
        self.task_queue = task_queue
        self.comfyui = comfyui_client
        self.workflow_manager = workflow_manager
        self.bot = bot
        self.timeout = timeout
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Запуск обработчика (бесконечный цикл)"""
        self.is_running = True
        logger.info("Task processor started")
        
        while self.is_running:
            try:
                # Получаем задачу (блокирующая операция)
                # Используем wait_for для поддержки graceful shutdown
                task = await asyncio.wait_for(
                    self.task_queue.get_task(),
                    timeout=1.0  # Проверяем is_running каждую секунду
                )
                
                logger.info(f"Processing task {task.id[:8]}")
                
                # Обработка с таймаутом
                await asyncio.wait_for(
                    self.process_task(task),
                    timeout=self.timeout
                )
                
            except asyncio.TimeoutError:
                # Либо нет задач в очереди, либо задача зависла
                if self.task_queue.current_task:
                    logger.error(f"Task {self.task_queue.current_task.id[:8]} timed out after {self.timeout}s")
                    await self.task_queue.task_done(
                        self.task_queue.current_task,
                        success=False,
                        error=f"Processing timeout ({self.timeout}s)"
                    )
                continue
                
            except asyncio.CancelledError:
                logger.info("Task processor cancelled")
                break
                
            except Exception as e:
                logger.exception(f"Error in task processor: {e}")
                if self.task_queue.current_task:
                    await self.task_queue.task_done(
                        self.task_queue.current_task,
                        success=False,
                        error=str(e)
                    )
                await asyncio.sleep(5)  # Пауза перед повтором после ошибки
        
        logger.info("Task processor stopped")
        
    async def stop(self):
        """Остановка обработчика (graceful shutdown)"""
        logger.info("Stopping task processor...")
        self.is_running = False
        
        # Если есть текущая задача — ждем её завершения
        if self.task_queue.current_task:
            logger.info(f"Waiting for current task {self.task_queue.current_task.id[:8]} to complete...")
            # Даём до 60 сек на завершение текущей задачи
            for _ in range(60):
                if not self.task_queue.current_task:
                    break
                await asyncio.sleep(1)
        
        logger.info("Task processor stopped gracefully")
        
    async def process_task(self, task: Task):
        """
        Обработка одной задачи
        
        Args:
            task: Задача для обработки
        """
        try:
            # 1. Уведомление пользователя о начале
            await self.notify_user(task, "🔄 Обработка началась...")
            
            # 2. Загрузка изображения в ComfyUI
            logger.debug(f"Uploading image: {task.image_path}")
            upload_result = await self.comfyui.upload_image(task.image_path)
            
            # 3. Создание workflow с параметрами
            task.workflow_params.input_image = upload_result["name"]
            workflow, extra_pnginfo = self.workflow_manager.create_workflow(task.workflow_params)
            
            # 4. Постановка в очередь ComfyUI (с extra_pnginfo для custom нод)
            prompt_id = await self.comfyui.queue_prompt(workflow, extra_pnginfo)
            logger.info(f"Task {task.id[:8]} queued in ComfyUI: {prompt_id}")
            
            # 5. Отслеживание прогресса через WebSocket
            async def progress_callback(current: int, total: int):
                """Callback для обновления прогресса в Telegram"""
                percent = int((current / total) * 100)
                progress_bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
                await self.notify_user(
                    task, 
                    f"⏳ Генерация: [{progress_bar}] {percent}%\n"
                    f"Шаг {current}/{total}"
                )
            
            ws_url = f"ws://{self.comfyui.host}:{self.comfyui.port}/ws"
            base_url = f"http://{self.comfyui.host}:{self.comfyui.port}"
            result = await track_progress(
                ws_url=ws_url,
                client_id=self.comfyui.client_id,
                prompt_id=prompt_id,
                callback=progress_callback,
                timeout=self.timeout,
                base_url=base_url
            )
            
            # 6. Извлечение результата
            # Node 102 = Image Saver Simple
            if "102" not in result.get("outputs", {}):
                raise ValueError("No output from Image Saver node (102)")
            
            output_images = result["outputs"]["102"]["images"]
            if not output_images:
                raise ValueError("No images in output")
            
            result_image = output_images[0]
            
            # 7. Скачивание результата
            logger.debug(f"Downloading result: {result_image['filename']}")
            image_data = await self.comfyui.get_image(
                result_image["filename"],
                result_image.get("subfolder", ""),
                result_image.get("type", "output")
            )
            
            # 8. Сохранение локально
            result_path = Path(f"data/output/{task.id}_{result_image['filename']}")
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_bytes(image_data)
            
            # 9. Отправка пользователю
            caption = (
                f"✅ Готово!\n\n"
                f"🎨 Промпт: {task.workflow_params.positive_prompt}\n"
                f"🔢 Steps: {task.workflow_params.steps}\n"
                f"🎲 Seed: {task.workflow_params.seed}\n"
                f"⚙️ CFG: {task.workflow_params.cfg}"
            )
            
            await self.bot.send_photo(
                chat_id=task.chat_id,
                photo=FSInputFile(result_path),
                caption=caption
            )
            
            # 10. Завершение задачи
            await self.task_queue.task_done(task, success=True, result_path=result_path)
            
        except Exception as e:
            # Обработка ошибки
            logger.exception(f"Task {task.id[:8]} failed: {e}")
            await self.task_queue.task_done(task, success=False, error=str(e))
            
            # Уведомление пользователя
            await self.notify_user(
                task, 
                f"❌ Ошибка при обработке:\n{str(e)}\n\nПопробуйте еще раз."
            )
            
    async def notify_user(self, task: Task, text: str):
        """
        Отправка уведомления пользователю
        
        Args:
            task: Задача
            text: Текст сообщения
        """
        try:
            await self.bot.edit_message_text(
                chat_id=task.chat_id,
                message_id=task.message_id,
                text=text
            )
        except Exception as e:
            # Игнорируем ошибки обновления сообщения (например, сообщение не изменилось)
            logger.debug(f"Failed to notify user: {e}")
