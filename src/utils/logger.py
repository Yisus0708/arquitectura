"""
Logging utility for the School Grades Data Pipeline.
Configures structured timestamped logging to both stdout and logs/pipeline.log.
"""
import logging
import sys
from pathlib import Path
from src.utils.config import LOGS_DIR, LOG_LEVEL

def get_logger(name: str = "pipeline") -> logging.Logger:
    """
    Returns a configured logger with console and file handlers.
    Avoids duplicate handlers if already attached.
    """
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOGS_DIR / "pipeline.log", encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
