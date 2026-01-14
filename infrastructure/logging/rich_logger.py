"""Простое логирование без Rich."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Настройка стандартного логирования для всего приложения.

    Args:
        level: Уровень логирования
    """
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers.clear()
    
    # Создаем простой handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Форматирование
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)


class RichLogger:
    """Обертка для обратной совместимости (заглушка)."""
    
    def __init__(self, name: str, level: str = "INFO"):
        """
        Инициализация логгера.

        Args:
            name: Имя логгера
            level: Уровень логирования
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

    def get_logger(self) -> logging.Logger:
        """Получение логгера."""
        return self.logger
