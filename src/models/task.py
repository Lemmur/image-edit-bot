from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from datetime import datetime
from enum import Enum
import uuid

class TaskStatus(str, Enum):
    """Статусы задачи"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkflowParams:
    """Параметры для генерации workflow"""
    
    # Обязательные
    input_image: str
    positive_prompt: str
    
    # Опциональные с defaults
    negative_prompt: str = ""
    steps: int = 8
    cfg: float = 1.0
    sampler: str = "linear/euler"
    scheduler: str = "simple"
    seed: int = 0  # 0 = random
    strength: float = 0.5
    eta: float = 0.5
    denoise: float = 1.0
    
    def validate(self, limits) -> None:
        """Валидация параметров против лимитов из конфига"""
        if not limits.min_steps <= self.steps <= limits.max_steps:
            raise ValueError(f"Steps must be between {limits.min_steps} and {limits.max_steps}")
        if not limits.min_cfg <= self.cfg <= limits.max_cfg:
            raise ValueError(f"CFG must be between {limits.min_cfg} and {limits.max_cfg}")
        if not limits.min_strength <= self.strength <= limits.max_strength:
            raise ValueError(f"Strength must be between {limits.min_strength} and {limits.max_strength}")

@dataclass
class Task:
    """Задача для обработки"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0
    chat_id: int = 0
    message_id: int = 0
    
    # Данные задачи
    image_path: Optional[Path] = None
    workflow_params: Optional[WorkflowParams] = None
    
    # Метаданные
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Статус
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None
    result_path: Optional[Path] = None
