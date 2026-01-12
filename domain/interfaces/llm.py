"""Интерфейс для работы с LLM."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMInterface(ABC):
    """Абстрактный интерфейс для работы с нейросетями."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Отправка запроса в LLM.

        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            tools: Список доступных инструментов (опционально)
            temperature: Температура генерации

        Returns:
            Ответ от LLM в формате словаря
        """
        pass

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Генерация эмбеддингов для текстов.

        Args:
            texts: Список текстов для эмбеддинга

        Returns:
            Список векторов эмбеддингов
        """
        pass
