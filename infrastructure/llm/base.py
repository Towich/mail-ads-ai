"""Базовый класс для LLM."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from domain.interfaces.llm import LLMInterface


class BaseLLM(LLMInterface, ABC):
    """Базовый класс для работы с нейросетями."""

    def __init__(self, api_key: str, base_url: str):
        """
        Инициализация базового LLM.

        Args:
            api_key: API ключ
            base_url: Базовый URL API
        """
        self.api_key = api_key
        self.base_url = base_url

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Отправка запроса в LLM.

        Args:
            messages: Список сообщений
            tools: Список доступных инструментов
            temperature: Температура генерации

        Returns:
            Ответ от LLM
        """
        return await self._send_request(messages, tools, temperature)

    @abstractmethod
    async def _send_request(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Внутренний метод для отправки запроса.

        Args:
            messages: Список сообщений
            tools: Список инструментов
            temperature: Температура

        Returns:
            Ответ от API
        """
        pass

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Генерация эмбеддингов.

        Args:
            texts: Список текстов

        Returns:
            Список векторов эмбеддингов
        """
        pass
