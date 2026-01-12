"""RAG инструмент для поиска по документации."""

import logging
from typing import Dict, Any
from infrastructure.tools.base import BaseTool
from domain.interfaces.rag import RAGInterface
from infrastructure.logging.rich_logger import RichLogger

logger = logging.getLogger(__name__)


class RAGSearchTool(BaseTool):
    """Инструмент для семантического поиска по документации проекта."""

    def __init__(self, rag: RAGInterface):
        """
        Инициализация RAG инструмента.

        Args:
            rag: Интерфейс RAG системы
        """
        super().__init__(
            name="rag_search",
            description="Семантический поиск по документации проекта. Используй этот инструмент, когда нужно найти информацию в документации, README файлах, или когда пользователь спрашивает о проекте, его структуре, архитектуре, или как что-то работает.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос для поиска в документации проекта",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Количество результатов для возврата (по умолчанию 5, максимум 10)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["query"],
            },
        )
        self.rag = rag

    async def execute(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Выполнение RAG поиска.

        Args:
            query: Поисковый запрос
            top_k: Количество результатов

        Returns:
            Результаты поиска
        """
        try:
            # Ограничиваем top_k
            top_k = min(max(1, top_k), 10)
            
            # Выполняем поиск
            documents = await self.rag.search(query, top_k=top_k)
            
            # Форматируем результаты
            results = []
            for doc in documents:
                results.append({
                    "filepath": doc.get("filepath", "unknown"),
                    "content": doc.get("content", ""),
                    "relevance": 1 - doc.get("distance", 1.0) if doc.get("distance") is not None else None,
                })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"Error in RAG search: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query,
            }
