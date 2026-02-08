"""Хранение пользовательских настроек"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class UserSettings:
    """Настройки пользователя"""
    user_id: int
    default_prompt: str = ""
    auto_confirm: bool = False  # Автоматический запуск без подтверждения
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSettings':
        """Создать из словаря"""
        return cls(**data)


class UserSettingsManager:
    """Менеджер пользовательских настроек"""
    
    def __init__(self, storage_path: Path):
        """
        Args:
            storage_path: Путь к директории для хранения настроек
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.storage_path / "user_settings.json"
        
        # Загрузить существующие настройки
        self._settings_cache: Dict[int, UserSettings] = {}
        self._load_all()
    
    def _load_all(self):
        """Загрузить все настройки из файла"""
        if not self.settings_file.exists():
            logger.info("User settings file not found, creating new one")
            self._save_all()
            return
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for user_id_str, settings_dict in data.items():
                user_id = int(user_id_str)
                self._settings_cache[user_id] = UserSettings.from_dict(settings_dict)
            
            logger.info(f"Loaded settings for {len(self._settings_cache)} users")
            
        except Exception as e:
            logger.error(f"Failed to load user settings: {e}")
            self._settings_cache = {}
    
    def _save_all(self):
        """Сохранить все настройки в файл"""
        try:
            data = {
                str(user_id): settings.to_dict()
                for user_id, settings in self._settings_cache.items()
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved settings for {len(self._settings_cache)} users")
            
        except Exception as e:
            logger.error(f"Failed to save user settings: {e}")
    
    def get_settings(self, user_id: int) -> UserSettings:
        """
        Получить настройки пользователя (создаёт новые если не существуют)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            UserSettings для данного пользователя
        """
        if user_id not in self._settings_cache:
            self._settings_cache[user_id] = UserSettings(user_id=user_id)
            self._save_all()
            logger.info(f"Created default settings for user {user_id}")
        
        return self._settings_cache[user_id]
    
    def update_settings(self, user_id: int, **kwargs):
        """
        Обновить настройки пользователя
        
        Args:
            user_id: ID пользователя
            **kwargs: Параметры для обновления (default_prompt, auto_confirm)
        """
        settings = self.get_settings(user_id)
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
                logger.debug(f"Updated {key} for user {user_id}: {value}")
        
        self._settings_cache[user_id] = settings
        self._save_all()
    
    def has_default_prompt(self, user_id: int) -> bool:
        """
        Проверить, установлен ли промпт по умолчанию
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если промпт установлен и не пустой
        """
        settings = self.get_settings(user_id)
        return bool(settings.default_prompt.strip())
    
    def get_default_prompt(self, user_id: int) -> str:
        """
        Получить промпт по умолчанию
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Промпт по умолчанию или пустая строка
        """
        settings = self.get_settings(user_id)
        return settings.default_prompt.strip()
    
    def is_auto_confirm_enabled(self, user_id: int) -> bool:
        """
        Проверить, включено ли автоподтверждение
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если автоподтверждение включено
        """
        settings = self.get_settings(user_id)
        return settings.auto_confirm
