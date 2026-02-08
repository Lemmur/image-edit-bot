from pathlib import Path
import yaml
from dotenv import load_dotenv
import os
from src.models.config import Config

def load_config() -> Config:
    """Загрузка конфигурации из .env и config.yaml"""
    # Загрузка .env
    load_dotenv()
    
    # Загрузка config.yaml
    config_path = Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found")
    
    with open(config_path) as f:
        yaml_config = yaml.safe_load(f)
    
    # Объединение с env переменными
    config_data = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "admin_user_ids": [
            int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()
        ],
        "comfyui_host": os.getenv("COMFYUI_HOST", "127.0.0.1"),
        "comfyui_port": int(os.getenv("COMFYUI_PORT", "8188")),
        "data_dir": Path(os.getenv("DATA_DIR", "data")),
        "logs_dir": Path(os.getenv("LOGS_DIR", "logs")),
        **yaml_config
    }
    
    return Config(**config_data)
