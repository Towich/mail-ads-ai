"""Интерфейс для инструментов ИИ."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ToolInterface(ABC):
    """Абстрактный интерфейс для инструментов ИИ."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Название инструмента."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Описание функциональности инструмента."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        Схема параметров для вызова инструмента (JSON Schema).

        Returns:
            Словарь с описанием параметров в формате JSON Schema
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Выполнение инструмента.

        Args:
            **kwargs: Параметры для выполнения инструмента

        Returns:
            Результат выполнения инструмента
        """
        pass
