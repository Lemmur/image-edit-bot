"""Фильтры для Telegram бота"""

from typing import Union, List, Dict
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from loguru import logger
from datetime import datetime, timedelta
from collections import defaultdict


class WhitelistFilter(BaseFilter):
    """Фильтр для проверки пользователей в whitelist"""
    
    def __init__(self, allowed_user_ids: List[int]):
        """
        Args:
            allowed_user_ids: Список разрешенных user_id (из config.admin_user_ids)
        """
        self.allowed_user_ids = set(allowed_user_ids)
    
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        """
        Проверка user_id в whitelist
        
        Args:
            event: Message или CallbackQuery от пользователя
            
        Returns:
            True если пользователь разрешен, False иначе
        """
        # Если whitelist пустой — разрешаем всем
        if not self.allowed_user_ids:
            return True
        
        user_id = event.from_user.id
        is_allowed = user_id in self.allowed_user_ids
        
        if not is_allowed:
            logger.warning(f"Unauthorized access attempt from user {user_id}")
        
        return is_allowed


class RateLimitFilter(BaseFilter):
    """Фильтр для rate limiting (защита от спама)"""
    
    def __init__(self, rate: int = 5, per: int = 60):
        """
        Args:
            rate: Максимальное количество запросов
            per: За период времени в секундах
        """
        self.rate = rate
        self.per = per
        self.user_requests: Dict[int, List[datetime]] = defaultdict(list)
    
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        """
        Проверка rate limit для пользователя
        
        Args:
            event: Message или CallbackQuery от пользователя
            
        Returns:
            True если лимит не превышен, False иначе
        """
        user_id = event.from_user.id
        now = datetime.now()
        
        # Очистить старые запросы
        cutoff = now - timedelta(seconds=self.per)
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id] 
            if req_time > cutoff
        ]
        
        # Проверить лимит
        if len(self.user_requests[user_id]) >= self.rate:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        # Добавить текущий запрос
        self.user_requests[user_id].append(now)
        return True


class ImageFilter(BaseFilter):
    """Фильтр для проверки что сообщение содержит изображение"""
    
    def __init__(self, allowed_formats: List[str] = None):
        """
        Args:
            allowed_formats: Список разрешенных MIME типов
        """
        self.allowed_formats = allowed_formats or [
            "image/jpeg", 
            "image/png", 
            "image/webp"
        ]
    
    async def __call__(self, message: Message) -> bool:
        """
        Проверка что сообщение содержит валидное изображение
        
        Args:
            message: Сообщение от пользователя
            
        Returns:
            True если сообщение содержит изображение, False иначе
        """
        # Photo всегда валидно (Telegram сжимает)
        if message.photo:
            return True
        
        # Document — проверяем mime type
        if message.document:
            mime_type = message.document.mime_type
            if mime_type in self.allowed_formats:
                return True
            logger.debug(f"Invalid document mime type: {mime_type}")
            return False
        
        return False
