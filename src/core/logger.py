import sys
from loguru import logger
from src.core.config import settings

logger.remove()

logger.add(
    sys.stdout,
    colorize=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    level="DEBUG" if settings.app_env == "development" else "INFO",
)

logger.add(
    "logs/sas_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
    level="INFO",
    enqueue=True,
)

__all__ = ["logger"]