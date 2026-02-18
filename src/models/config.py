from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Optional


class ComfyUIConfig(BaseModel):
    """Конфигурация подключения к ComfyUI"""
    host: str = "127.0.0.1"
    port: int = 8188
    dir: Optional[Path] = None  # Путь к установленному ComfyUI
    venv: Optional[Path] = None  # Путь к venv (опционально)
    auto_start: bool = True  # Автозапуск ComfyUI если не запущен
    args: str = ""  # Дополнительные аргументы запуска
    startup_timeout: int = 300  # Таймаут запуска в секундах


class WorkflowDefaults(BaseModel):
    """Дефолтные параметры workflow"""
    steps: int = 8
    cfg: float = 1.0
    sampler: str = "linear/euler"
    scheduler: str = "simple"
    seed: int = 0
    strength: float = 0.5
    eta: float = 0.5
    denoise: float = 1.0
    negative_prompt: str = ""  # Важно: будет из config.yaml


class WorkflowLimits(BaseModel):
    """Лимиты параметров"""
    min_steps: int = 1
    max_steps: int = 50
    min_cfg: float = 0.1
    max_cfg: float = 20.0
    min_strength: float = 0.0
    max_strength: float = 1.0


class WorkflowConfig(BaseModel):
    """Конфигурация workflow"""
    default_file: str
    defaults: WorkflowDefaults
    limits: WorkflowLimits


class ImageConfig(BaseModel):
    """Конфигурация обработки изображений"""
    max_size_mb: int
    allowed_formats: List[str]
    scale_megapixels: float


class QueueConfig(BaseModel):
    """Конфигурация очереди"""
    max_size: int
    timeout_seconds: int


class StorageConfig(BaseModel):
    """Конфигурация хранилища"""
    cleanup_after_hours: int
    keep_results: bool


class LoggingConfig(BaseModel):
    """Конфигурация логирования"""
    level: str = "INFO"
    rotation: str = "100 MB"
    retention: str = "7 days"


class Config(BaseModel):
    """Полная конфигурация приложения"""
    # Telegram
    telegram_bot_token: str
    admin_user_ids: List[int] = []
    
    # ComfyUI
    comfyui: ComfyUIConfig = ComfyUIConfig()
    
    # Legacy поля для обратной совместимости (будут deprecated)
    comfyui_host: str = "127.0.0.1"
    comfyui_port: int = 8188
    
    # Пути
    data_dir: Path = Path("data")
    logs_dir: Path = Path("logs")
    workflows_dir: Path = Path("workflows")
    
    # Компоненты
    workflow: WorkflowConfig
    image: ImageConfig
    queue: QueueConfig
    storage: StorageConfig
    logging: LoggingConfig
    
    def get_comfyui_host(self) -> str:
        """Получить хост ComfyUI (приоритет comfyui.host)"""
        return self.comfyui.host or self.comfyui_host
    
    def get_comfyui_port(self) -> int:
        """Получить порт ComfyUI (приоритет comfyui.port)"""
        return self.comfyui.port or self.comfyui_port
