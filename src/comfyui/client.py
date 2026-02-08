"""ComfyUI REST API клиент"""

from typing import Dict, Optional
from pathlib import Path
import uuid
import asyncio

import aiohttp
from loguru import logger


class ComfyUIClient:
    """Клиент для взаимодействия с ComfyUI REST API"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        """
        Инициализация клиента
        
        Args:
            host: Хост ComfyUI сервера
            port: Порт ComfyUI сервера
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.client_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self):
        """
        Открыть HTTP сессию (для долгоживущих приложений)
        
        Используйте для приложений, которые должны поддерживать сессию
        на протяжении всего жизненного цикла.
        """
        if self.session and not self.session.closed:
            logger.warning("Session already open")
            return
            
        self.session = aiohttp.ClientSession()
        self.client_id = str(uuid.uuid4())
        logger.info(f"ComfyUI client connected (client_id={self.client_id})")
    
    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("ComfyUI client session closed")
        
    async def __aenter__(self):
        """Контекстный менеджер - вход"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        await self.close()
    
    async def check_health(self) -> bool:
        """
        Проверка доступности ComfyUI сервера
        
        Returns:
            True если сервер доступен, False иначе
        """
        try:
            async with self.session.get(f"{self.base_url}/system_stats", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    stats = await response.json()
                    logger.debug(f"ComfyUI health check OK: {stats}")
                    return True
                else:
                    logger.warning(f"ComfyUI health check failed: status {response.status}")
                    return False
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"ComfyUI health check failed: {e}")
            return False
    
    async def wait_for_ready(self, max_attempts: int = 60, delay: int = 5) -> bool:
        """
        Ожидание запуска ComfyUI с retry логикой
        
        ComfyUI требует времени на загрузку моделей (~30-60 сек)
        
        Args:
            max_attempts: Максимальное количество попыток
            delay: Задержка между попытками в секундах
            
        Returns:
            True если сервер готов, False если timeout
        """
        logger.info(f"Waiting for ComfyUI to be ready (max {max_attempts * delay}s)...")
        
        for attempt in range(1, max_attempts + 1):
            if await self.check_health():
                logger.success(f"✅ ComfyUI is ready (attempt {attempt}/{max_attempts})")
                return True
            
            logger.warning(f"ComfyUI not ready, attempt {attempt}/{max_attempts}, retrying in {delay}s...")
            await asyncio.sleep(delay)
        
        logger.error(f"❌ ComfyUI failed to become ready after {max_attempts} attempts")
        return False
    
    async def upload_image(self, image_path: Path, subfolder: str = "") -> Dict:
        """
        Загрузка изображения на ComfyUI сервер
        
        Args:
            image_path: Путь к изображению
            subfolder: Подпапка для сохранения (опционально)
            
        Returns:
            {"name": "uploaded_filename.png", "subfolder": "", "type": "input"}
            
        Raises:
            aiohttp.ClientError: Ошибка при загрузке
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        logger.info(f"Uploading image: {image_path.name}")
        
        # Multipart form data
        data = aiohttp.FormData()
        data.add_field('image', 
                      open(image_path, 'rb'),
                      filename=image_path.name,
                      content_type='image/jpeg')
        
        if subfolder:
            data.add_field('subfolder', subfolder)
        
        try:
            async with self.session.post(
                f"{self.base_url}/upload/image",
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                logger.success(f"✅ Image uploaded: {result}")
                return result
        except aiohttp.ClientError as e:
            logger.error(f"Failed to upload image: {e}")
            raise
    
    async def queue_prompt(self, workflow: Dict) -> str:
        """
        Постановка workflow в очередь выполнения
        
        Args:
            workflow: Модифицированный workflow JSON
            
        Returns:
            prompt_id: Уникальный ID задачи
            
        Raises:
            aiohttp.ClientError: Ошибка при постановке в очередь
        """
        logger.info("Queueing prompt to ComfyUI...")
        
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                prompt_id = result["prompt_id"]
                logger.success(f"✅ Prompt queued: {prompt_id}")
                return prompt_id
        except aiohttp.ClientError as e:
            logger.error(f"Failed to queue prompt: {e}")
            raise
    
    async def get_history(self, prompt_id: str) -> Dict:
        """
        Получение истории выполнения задачи
        
        Args:
            prompt_id: ID задачи
            
        Returns:
            История выполнения с результатами
            
        Raises:
            aiohttp.ClientError: Ошибка при получении истории
        """
        logger.debug(f"Fetching history for prompt_id={prompt_id}")
        
        try:
            async with self.session.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                logger.debug(f"History retrieved: {len(result)} entries")
                return result
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get history: {e}")
            raise
    
    async def get_image(
        self, 
        filename: str, 
        subfolder: str = "", 
        folder_type: str = "output"
    ) -> bytes:
        """
        Скачивание результирующего изображения
        
        Args:
            filename: Имя файла
            subfolder: Подпапка в которой находится файл
            folder_type: Тип папки (output/input/temp)
            
        Returns:
            Бинарные данные изображения
            
        Raises:
            aiohttp.ClientError: Ошибка при скачивании
        """
        logger.info(f"Downloading image: {filename}")
        
        params = {
            "filename": filename,
            "type": folder_type
        }
        
        if subfolder:
            params["subfolder"] = subfolder
        
        try:
            async with self.session.get(
                f"{self.base_url}/view",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                image_data = await response.read()
                logger.success(f"✅ Image downloaded: {len(image_data)} bytes")
                return image_data
        except aiohttp.ClientError as e:
            logger.error(f"Failed to download image: {e}")
            raise
    
    async def get_system_stats(self) -> Dict:
        """
        Получение статистики системы
        
        Returns:
            Статистика ComfyUI сервера
        """
        try:
            async with self.session.get(
                f"{self.base_url}/system_stats",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response.raise_for_status()
                stats = await response.json()
                return stats
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get system stats: {e}")
            raise
