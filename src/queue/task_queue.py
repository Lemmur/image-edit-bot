import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from src.models.task import Task, TaskStatus


class TaskQueue:
    """FIFO очередь задач с async support"""
    
    def __init__(self, max_size: int = 100):
        """
        Инициализация очереди
        
        Args:
            max_size: Максимальный размер очереди (из config.queue.max_size)
        """
        self.queue: asyncio.Queue[Task] = asyncio.Queue(maxsize=max_size)
        self.current_task: Optional[Task] = None
        self.completed_tasks: List[Task] = []
        self._lock = asyncio.Lock()
        
    async def add_task(self, task: Task) -> int:
        """
        Добавление задачи в очередь
        
        Args:
            task: Задача для добавления
            
        Returns:
            Позиция в очереди (1-indexed)
            
        Raises:
            asyncio.QueueFull: Если очередь переполнена
        """
        await self.queue.put(task)
        position = self.queue.qsize()
        logger.info(f"Task {task.id[:8]} added to queue, position: {position}")
        return position
        
    async def get_task(self) -> Task:
        """
        Получение следующей задачи (блокирующая операция)
        
        Returns:
            Следующая задача из очереди
        """
        task = await self.queue.get()
        async with self._lock:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now()
            self.current_task = task
        logger.info(f"Task {task.id[:8]} started processing")
        return task
        
    async def task_done(self, task: Task, success: bool = True, 
                       result_path: Optional[Path] = None, error: Optional[str] = None):
        """
        Завершение обработки задачи
        
        Args:
            task: Завершенная задача
            success: Успешно ли завершена
            result_path: Путь к результату (если успешно)
            error: Сообщение об ошибке (если неудачно)
        """
        async with self._lock:
            task.completed_at = datetime.now()
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.result_path = result_path
            task.error = error
            
            self.completed_tasks.append(task)
            self.current_task = None
            self.queue.task_done()
            
        if success:
            logger.success(f"Task {task.id[:8]} completed successfully")
        else:
            logger.error(f"Task {task.id[:8]} failed: {error}")
            
    def get_status(self) -> Dict:
        """
        Получение статуса очереди
        
        Returns:
            Dict с информацией о состоянии очереди
        """
        return {
            "queue_size": self.queue.qsize(),
            "current_task_id": self.current_task.id[:8] if self.current_task else None,
            "completed_today": len([
                t for t in self.completed_tasks 
                if t.completed_at and t.completed_at.date() == datetime.now().date()
            ]),
            "total_completed": len(self.completed_tasks),
            "success_rate": self._calculate_success_rate()
        }
        
    def _calculate_success_rate(self) -> float:
        """Рассчитать процент успешных задач"""
        if not self.completed_tasks:
            return 0.0
        successful = sum(1 for t in self.completed_tasks if t.status == TaskStatus.COMPLETED)
        return (successful / len(self.completed_tasks)) * 100
        
    async def clear_old_completed(self, max_age_hours: int = 24):
        """
        Очистка старых завершенных задач из памяти
        
        Args:
            max_age_hours: Максимальный возраст задачи в часах
        """
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            before_count = len(self.completed_tasks)
            self.completed_tasks = [
                t for t in self.completed_tasks 
                if t.completed_at and t.completed_at > cutoff_time
            ]
            removed = before_count - len(self.completed_tasks)
            if removed > 0:
                logger.info(f"Cleared {removed} old completed tasks from memory")
