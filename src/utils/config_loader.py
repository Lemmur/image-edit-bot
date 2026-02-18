from pathlib import Path
import yaml
from dotenv import load_dotenv
import os
from src.models.config import Config, ComfyUIConfig


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
    
    # Построение конфигурации ComfyUI с приоритетом env переменных
    comfyui_config = _build_comfyui_config(yaml_config.get("comfyui", {}))
    
    # Объединение с env переменными
    config_data = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "admin_user_ids": [
            int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()
        ],
        "comfyui": comfyui_config,
        # Legacy поля для обратной совместимости
        "comfyui_host": comfyui_config.host,
        "comfyui_port": comfyui_config.port,
        "data_dir": Path(os.getenv("DATA_DIR", "data")),
        "logs_dir": Path(os.getenv("LOGS_DIR", "logs")),
        **{k: v for k, v in yaml_config.items() if k != "comfyui"}
    }
    
    return Config(**config_data)


def _build_comfyui_config(yaml_comfyui: dict) -> ComfyUIConfig:
    """Построение конфигурации ComfyUI с приоритетом env переменных"""
    
    # Получаем значения из env с fallback на yaml
    comfyui_dir = os.getenv("COMFYUI_DIR") or yaml_comfyui.get("dir", "")
    comfyui_venv = os.getenv("COMFYUI_VENV") or yaml_comfyui.get("venv", "")
    auto_start_str = os.getenv("COMFYUI_AUTO_START") or str(yaml_comfyui.get("auto_start", True)).lower()
    comfyui_args = os.getenv("COMFYUI_ARGS") or yaml_comfyui.get("args", "")
    
    # Парсинг auto_start
    auto_start = auto_start_str.lower() in ("true", "1", "yes")
    
    return ComfyUIConfig(
        host=os.getenv("COMFYUI_HOST") or yaml_comfyui.get("host", "127.0.0.1"),
        port=int(os.getenv("COMFYUI_PORT") or yaml_comfyui.get("port", 8188)),
        dir=Path(comfyui_dir) if comfyui_dir else None,
        venv=Path(comfyui_venv) if comfyui_venv else None,
        auto_start=auto_start,
        args=comfyui_args,
        startup_timeout=int(yaml_comfyui.get("startup_timeout", 300))
    )
