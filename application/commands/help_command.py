"""Команда /help для получения помощи по проекту."""

import logging
from typing import Optional
from application.services.agent_service import AgentService

logger = logging.getLogger(__name__)


class HelpCommand:
    """Команда /help для получения помощи."""

    def __init__(self, agent_service: AgentService):
        """
        Инициализация команды.

        Args:
            agent_service: Сервис агента с доступом к RAG
        """
        self.agent_service = agent_service

    async def execute(self, query: Optional[str] = None) -> str:
        """
        Выполнение команды /help.

        Args:
            query: Поисковый запрос (опционально)

        Returns:
            Результат выполнения команды
        """
        if not query:
            return self._get_general_help()

        # Просто передаем запрос агенту - он сам решит, использовать ли RAG инструмент
        try:
            response = await self.agent_service.process_query(query)
            return response
        except Exception as e:
            logger.error(f"Error in help command: {e}", exc_info=True)
            return f"Ошибка при обработке запроса: {str(e)}"

    def _get_general_help(self) -> str:
        """Получение общей справки."""
        return """
# Справка по проекту

Этот ИИ-агент помогает работать с проектом. Доступные возможности:

## Команды

- `/help [запрос]` - получить помощь по конкретному вопросу
- `/search [запрос]` - поиск по документации проекта
- `/review` - анализ изменений в git репозитории (код-ревью)
- `/exit` или `/quit` - выход

## Возможности

- **RAG-поиск**: Агент может искать информацию в документации проекта (.md файлы)
- **Git инструменты**: Агент может работать с git-репозиторием
- **Интерактивный режим**: Просто задавайте вопросы, агент ответит

## Примеры запросов

- "Как работает RAG система?"
- "Покажи структуру проекта"
- "Какие инструменты доступны для работы с git?"

Просто введите ваш вопрос после команды `/help` или напрямую в интерактивном режиме.
        """
