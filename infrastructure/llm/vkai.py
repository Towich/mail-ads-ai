"""Реализация VK AI LLM."""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class VKAI(BaseLLM):
    """Реализация VK AI API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://llm-proxy.vkteam.ru",
        model: str = "deepseek-chat",
    ):
        """
        Инициализация VK AI.

        Args:
            api_key: API ключ VK AI
            base_url: Базовый URL API
            model: Название модели для использования
        """
        super().__init__(api_key, base_url)
        self.model = model
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание сессии."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _send_request(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Отправка запроса в VK AI API.

        Args:
            messages: Список сообщений
            tools: Список инструментов
            temperature: Температура генерации

        Returns:
            Ответ от API
        """
        session = await self._get_session()
        url = f"{self.base_url}/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        # Rate limit - ждем и повторяем
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limit, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        error_text = await response.text()
                        logger.error(f"VK AI API error: {response.status} - {error_text}")
                        response.raise_for_status()
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise Exception("Failed to get response from VK AI after retries")

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Генерация эмбеддингов через VK AI API.

        Args:
            texts: Список текстов

        Returns:
            Список векторов эмбеддингов
        """
        # VK AI может не поддерживать эмбеддинги напрямую
        # В этом случае используем Ollama для эмбеддингов
        raise NotImplementedError(
            "VK AI embeddings not implemented. Use Ollama for embeddings."
        )

    async def close(self):
        """Закрытие сессии."""
        if self.session and not self.session.closed:
            await self.session.close()
