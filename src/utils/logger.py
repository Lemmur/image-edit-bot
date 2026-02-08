from loguru import logger
import sys
from pathlib import Path

def setup_logger(logs_dir: Path = Path("logs"), level: str = "INFO") -> logger:
    """Настройка логирования с loguru"""
    
    logs_dir.mkdir(exist_ok=True)
    
    # Удаление стандартного handler
    logger.remove()
    
    # Console handler (цветной вывод)
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # File handler - общий лог
    logger.add(
        logs_dir / "bot.log",
        rotation="100 MB",
        retention="7 days",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=True
    )
    
    # File handler - только ошибки
    logger.add(
        logs_dir / "errors.log",
        rotation="50 MB",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Logger initialized")
    return logger
