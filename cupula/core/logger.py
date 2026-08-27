import logging
import sys

from cupula.config.settings import get_settings


def get_logger(name: str) -> logging.Logger:
    settings = get_settings()

    logger = logging.getLogger(f"cupula.{name}")

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(settings.LOG_FORMAT))
        logger.addHandler(console)

        filepath = settings.LOGS_DIR / f"{name}.log"
        file_h = logging.FileHandler(filepath, encoding="utf-8")
        file_h.setLevel(logging.DEBUG)
        file_h.setFormatter(logging.Formatter(settings.LOG_FORMAT))
        logger.addHandler(file_h)

    return logger
