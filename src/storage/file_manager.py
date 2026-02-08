"""Управление файлами бота"""

import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from aiogram import Bot


class FileManager:
    """Управление файлами бота"""
    
    def __init__(self, data_dir: Path):
        """
        Args:
            data_dir: Базовая директория для данных (из config.data_dir)
        """
        self.data_dir = data_dir
        self.input_dir = data_dir / "input"
        self.output_dir = data_dir / "output"
        self.temp_dir = data_dir / "temp"
        
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Создать директории если не существуют
        for dir_path in [self.input_dir, self.output_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"FileManager initialized with data_dir: {data_dir}")
    
    async def download_file(self, bot: Bot, file_id: str, 
                           user_id: int, extension: str = "jpg") -> Path:
        """
        Скачивание файла из Telegram
        
        Args:
            bot: Telegram Bot instance
            file_id: ID файла в Telegram
            user_id: ID пользователя
            extension: Расширение файла
            
        Returns:
            Путь к скачанному файлу
        """
        file = await bot.get_file(file_id)
        
        # Уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{timestamp}_{file_id[:8]}.{extension}"
        file_path = self.input_dir / filename
        
        # Скачать
        await bot.download_file(file.file_path, file_path)
        logger.debug(f"Downloaded file: {file_path}")
        
        return file_path
    
    def get_output_path(self, task_id: str, extension: str = "png") -> Path:
        """
        Получить путь для сохранения результата
        
        Args:
            task_id: ID задачи
            extension: Расширение файла
            
        Returns:
            Путь для сохранения результата
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_id[:8]}_{timestamp}.{extension}"
        return self.output_dir / filename
    
    async def cleanup_old_files(self, max_age_hours: int = 24, 
                               keep_results: bool = True):
        """
        Очистка старых файлов
        
        Args:
            max_age_hours: Максимальный возраст файла в часах (из config.storage.cleanup_after_hours)
            keep_results: Сохранять результаты (из config.storage.keep_results)
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        total_removed = 0
        
        # Очистить input и temp
        for directory in [self.input_dir, self.temp_dir]:
            removed = await self._cleanup_directory(directory, cutoff_time)
            total_removed += removed
        
        # Очистить output если keep_results=False
        if not keep_results:
            removed = await self._cleanup_directory(self.output_dir, cutoff_time)
            total_removed += removed
        
        if total_removed > 0:
            logger.info(f"Cleaned up {total_removed} old files")
    
    async def _cleanup_directory(self, directory: Path, cutoff_time: datetime) -> int:
        """
        Очистка одной директории
        
        Args:
            directory: Путь к директории
            cutoff_time: Время отсечки (файлы старше удаляются)
            
        Returns:
            Количество удаленных файлов
        """
        removed_count = 0
        
        if not directory.exists():
            return 0
        
        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue
            
            # Проверить возраст файла
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    file_path.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")
        
        return removed_count
    
    async def start_cleanup_task(self, interval_hours: int = 1, 
                                 max_age_hours: int = 24, 
                                 keep_results: bool = True):
        """
        Запуск периодической очистки файлов
        
        Args:
            interval_hours: Интервал проверки в часах
            max_age_hours: Максимальный возраст файлов
            keep_results: Сохранять результаты
        """
        logger.info(
            f"Starting file cleanup task "
            f"(interval: {interval_hours}h, max_age: {max_age_hours}h, keep_results: {keep_results})"
        )
        
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_hours * 3600)
                try:
                    await self.cleanup_old_files(max_age_hours, keep_results)
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    def stop_cleanup_task(self):
        """Остановка периодической очистки"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("File cleanup task stopped")
    
    async def get_storage_stats(self) -> dict:
        """
        Получить статистику использования хранилища
        
        Returns:
            Dict со статистикой по директориям
        """
        stats = {}
        
        for name, directory in [
            ("input", self.input_dir),
            ("output", self.output_dir),
            ("temp", self.temp_dir)
        ]:
            if not directory.exists():
                stats[name] = {"files": 0, "size_mb": 0}
                continue
            
            files = list(directory.iterdir())
            file_count = len([f for f in files if f.is_file()])
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            stats[name] = {
                "files": file_count,
                "size_mb": round(total_size / (1024 * 1024), 2)
            }
        
        return stats
