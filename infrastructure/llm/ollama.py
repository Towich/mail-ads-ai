"""Реализация Ollama LLM для эмбеддингов и генерации."""

import aiohttp
import logging
from typing import List, Dict, Any, Optional
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """Реализация Ollama для работы с локальной моделью."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        """
        Инициализация Ollama.

        Args:
            base_url: URL Ollama сервера
            model: Название модели
        """
        super().__init__("", base_url)  # Ollama не требует API ключ
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
        Отправка запроса в Ollama.

        Args:
            messages: Список сообщений
            tools: Список инструментов (Ollama может не поддерживать)
            temperature: Температура генерации

        Returns:
            Ответ от Ollama
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/chat"

        # Преобразуем сообщения в формат Ollama
        prompt = self._messages_to_prompt(messages)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": result.get("message", {}).get("content", ""),
                                }
                            }
                        ]
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    response.raise_for_status()
        except aiohttp.ClientError as e:
            logger.error(f"Request error: {e}")
            raise

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Преобразование сообщений в промпт."""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        return "\n".join(prompt_parts)

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Генерация эмбеддингов через Ollama.

        Args:
            texts: Список текстов

        Returns:
            Список векторов эмбеддингов
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/embeddings"

        embeddings = []
        for text in texts:
            payload = {
                "model": self.model,
                "prompt": text,
            }

            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        embeddings.append(result.get("embedding", []))
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama embeddings error: {response.status} - {error_text}")
                        raise Exception(f"Failed to generate embeddings: {error_text}")
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {e}")
                raise

        return embeddings

    async def close(self):
        """Закрытие сессии."""
        if self.session and not self.session.closed:
            await self.session.close()
