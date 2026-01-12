"""Базовый класс для инструментов."""

from abc import ABC
from typing import Dict, Any
from domain.interfaces.tool import ToolInterface


class BaseTool(ToolInterface, ABC):
    """Базовый класс для инструментов ИИ."""

    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        """
        Инициализация инструмента.

        Args:
            name: Название инструмента
            description: Описание функциональности
            parameters: Схема параметров (JSON Schema)
        """
        self._name = name
        self._description = description
        self._parameters = parameters

    @property
    def name(self) -> str:
        """Название инструмента."""
        return self._name

    @property
    def description(self) -> str:
        """Описание функциональности."""
        return self._description

    @property
    def parameters(self) -> Dict[str, Any]:
        """Схема параметров (JSON Schema)."""
        return self._parameters

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для передачи в LLM."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
