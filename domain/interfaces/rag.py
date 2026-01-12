"""Интерфейс для RAG-системы."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class RAGInterface(ABC):
    """Абстрактный интерфейс для RAG-системы."""

    @abstractmethod
    async def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Индексация документов.

        Args:
            documents: Список документов для индексации
        """
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Семантический поиск по документам.

        Args:
            query: Поисковый запрос
            top_k: Количество результатов для возврата

        Returns:
            Список релевантных документов с метаданными
        """
        pass

    @abstractmethod
    async def get_context(self, query: str, top_k: int = 5) -> str:
        """
        Получение контекста для запроса на основе найденных документов.

        Args:
            query: Поисковый запрос
            top_k: Количество документов для включения в контекст

        Returns:
            Строка с контекстом из найденных документов
        """
        pass
