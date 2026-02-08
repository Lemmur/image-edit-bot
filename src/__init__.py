"""
Qwen Image Edit Bot

Telegram бот для редактирования изображений через ComfyUI с использованием Qwen Image Edit модели.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__description__ = "Telegram bot for image editing via ComfyUI Qwen Image Edit"

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger

__all__ = [
    "load_config",
    "setup_logger",
]
