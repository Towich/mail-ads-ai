"""Инструменты для работы с Atlassian (Jira, Confluence) через MCP."""

import logging
from typing import Dict, Any, Optional
from infrastructure.tools.base import BaseTool
from infrastructure.mcp.atlassian_client import AtlassianMCPClient

logger = logging.getLogger(__name__)


class JiraSearchTool(BaseTool):
    """Инструмент для поиска задач в Jira с использованием JQL."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="jira_search",
            description=(
                "Поиск задач в Jira с использованием JQL (Jira Query Language). "
                "Используй этот инструмент для поиска задач по различным критериям: "
                "по проекту, статусу, назначенному пользователю, дате и т.д. "
                "Примеры JQL: 'project = PROJ', 'assignee = currentUser()', "
                "'status = Open', 'project = PROJ AND assignee = currentUser()'"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "jql": {
                        "type": "string",
                        "description": "JQL запрос для поиска задач (например: 'project = PROJ AND status = Open')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Максимальное количество результатов (не используется MCP сервером, оставлено для совместимости)",
                        "default": 50,
                    },
                },
                "required": ["jql"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self, jql: str, max_results: int = 50) -> Dict[str, Any]:
        """
        Поиск задач в Jira.

        Args:
            jql: JQL запрос
            max_results: Максимальное количество результатов (не используется, оставлено для совместимости)

        Returns:
            Результаты поиска
        """
        try:
            # MCP сервер mcp-atlassian принимает только jql параметр
            result = await self.atlassian_client.call_tool(
                "jira_search",
                arguments={
                    "jql": jql,
                }
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "jql": jql,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "jql": jql,
                }
        except Exception as e:
            logger.error(f"Ошибка при поиске задач в Jira: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "jql": jql,
            }


class JiraGetIssueTool(BaseTool):
    """Инструмент для получения информации о задаче в Jira."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="jira_get_issue",
            description=(
                "Получение детальной информации о задаче в Jira по её ключу. "
                "Используй этот инструмент для получения полной информации о задаче: "
                "описание, статус, приоритет, назначенный пользователь, комментарии и т.д. "
                "Примеры ключей: 'PROJ-123', 'TASK-456'"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Ключ задачи в Jira (например: PROJ-123)",
                    },
                },
                "required": ["issue_key"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self, issue_key: str) -> Dict[str, Any]:
        """
        Получение информации о задаче.

        Args:
            issue_key: Ключ задачи

        Returns:
            Информация о задаче
        """
        try:
            result = await self.atlassian_client.call_tool(
                "jira_get_issue",
                arguments={
                    "issue_key": issue_key,
                }
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "issue_key": issue_key,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "issue_key": issue_key,
                }
        except Exception as e:
            logger.error(f"Ошибка при получении задачи {issue_key}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "issue_key": issue_key,
            }


class JiraCreateIssueTool(BaseTool):
    """Инструмент для создания новой задачи в Jira."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="jira_create_issue",
            description=(
                "Создание новой задачи в Jira. Используй этот инструмент для создания "
                "багов, задач, историй и других типов задач в Jira. "
                "Необходимо указать проект, тип задачи и заголовок."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "Ключ проекта (например: PROJ)",
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Тип задачи (Bug, Task, Story, Epic и т.д.)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Заголовок задачи",
                    },
                    "description": {
                        "type": "string",
                        "description": "Описание задачи (опционально)",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Имя пользователя для назначения задачи (опционально)",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Приоритет задачи (Highest, High, Medium, Low, Lowest) (опционально)",
                    },
                },
                "required": ["project_key", "issue_type", "summary"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создание задачи в Jira.

        Args:
            project_key: Ключ проекта
            issue_type: Тип задачи
            summary: Заголовок
            description: Описание
            assignee: Назначенный пользователь
            priority: Приоритет

        Returns:
            Информация о созданной задаче
        """
        try:
            arguments = {
                "project_key": project_key,
                "issue_type": issue_type,
                "summary": summary,
            }
            
            if description:
                arguments["description"] = description
            if assignee:
                arguments["assignee"] = assignee
            if priority:
                arguments["priority"] = priority
            
            result = await self.atlassian_client.call_tool(
                "jira_create_issue",
                arguments=arguments
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                }
        except Exception as e:
            logger.error(f"Ошибка при создании задачи в Jira: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }


class JiraUpdateIssueTool(BaseTool):
    """Инструмент для обновления задачи в Jira."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="jira_update_issue",
            description=(
                "Обновление существующей задачи в Jira. Используй этот инструмент для "
                "изменения полей задачи: заголовка, описания, приоритета, назначенного пользователя и т.д."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Ключ задачи (например: PROJ-123)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Новый заголовок задачи (опционально)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Новое описание задачи (опционально)",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Новый назначенный пользователь (опционально)",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Новый приоритет (опционально)",
                    },
                },
                "required": ["issue_key"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Обновление задачи в Jira.

        Args:
            issue_key: Ключ задачи
            summary: Новый заголовок
            description: Новое описание
            assignee: Новый назначенный пользователь
            priority: Новый приоритет

        Returns:
            Результат обновления
        """
        try:
            arguments = {"issue_key": issue_key}
            
            if summary:
                arguments["summary"] = summary
            if description:
                arguments["description"] = description
            if assignee:
                arguments["assignee"] = assignee
            if priority:
                arguments["priority"] = priority
            
            result = await self.atlassian_client.call_tool(
                "jira_update_issue",
                arguments=arguments
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "issue_key": issue_key,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "issue_key": issue_key,
                }
        except Exception as e:
            logger.error(f"Ошибка при обновлении задачи {issue_key}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "issue_key": issue_key,
            }


class JiraTransitionIssueTool(BaseTool):
    """Инструмент для изменения статуса задачи в Jira."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="jira_transition_issue",
            description=(
                "Изменение статуса задачи в Jira (переход по workflow). "
                "Используй этот инструмент для перевода задачи в другой статус: "
                "например, из 'Open' в 'In Progress', из 'In Progress' в 'Done' и т.д."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Ключ задачи (например: PROJ-123)",
                    },
                    "transition_name": {
                        "type": "string",
                        "description": "Название перехода (например: 'In Progress', 'Done', 'Resolve Issue')",
                    },
                },
                "required": ["issue_key", "transition_name"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self, issue_key: str, transition_name: str) -> Dict[str, Any]:
        """
        Изменение статуса задачи.

        Args:
            issue_key: Ключ задачи
            transition_name: Название перехода

        Returns:
            Результат изменения статуса
        """
        try:
            result = await self.atlassian_client.call_tool(
                "jira_transition_issue",
                arguments={
                    "issue_key": issue_key,
                    "transition_name": transition_name,
                }
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "issue_key": issue_key,
                    "transition_name": transition_name,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "issue_key": issue_key,
                    "transition_name": transition_name,
                }
        except Exception as e:
            logger.error(f"Ошибка при изменении статуса задачи {issue_key}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "issue_key": issue_key,
                "transition_name": transition_name,
            }


class AtlassianListToolsTool(BaseTool):
    """Инструмент для получения списка доступных Atlassian инструментов."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="atlassian_list_tools",
            description=(
                "Получение списка доступных инструментов Atlassian MCP сервера. "
                "Используй для отладки и понимания доступных возможностей."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self) -> Dict[str, Any]:
        """
        Получение списка инструментов.

        Returns:
            Список доступных инструментов
        """
        try:
            tools = await self.atlassian_client.list_tools()
            tools_list = []
            for tool in tools:
                if hasattr(tool, 'name'):
                    tool_info = {
                        "name": tool.name,
                        "description": getattr(tool, 'description', ''),
                    }
                else:
                    tool_info = {
                        "name": tool.get('name', ''),
                        "description": tool.get('description', ''),
                    }
                tools_list.append(tool_info)
            
            return {
                "success": True,
                "tools": tools_list,
                "count": len(tools_list),
            }
        except Exception as e:
            logger.error(f"Ошибка при получении списка инструментов: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
