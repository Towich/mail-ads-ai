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


class ConfluenceSearchTool(BaseTool):
    """Инструмент для поиска страниц в Confluence с использованием CQL."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="confluence_search",
            description=(
                "Поиск страниц в Confluence с использованием CQL (Confluence Query Language). "
                "Используй этот инструмент для поиска страниц по различным критериям: "
                "по пространству, заголовку, содержимому, автору и т.д. "
                "Примеры CQL: 'space = SPACE', 'title ~ \"test\"', "
                "'text ~ \"documentation\" AND space = DOCS'"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "cql": {
                        "type": "string",
                        "description": "CQL запрос для поиска страниц (например: 'space = SPACE AND title ~ \"test\"')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Максимальное количество результатов",
                        "default": 25,
                    },
                },
                "required": ["cql"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self, cql: str, limit: int = 25) -> Dict[str, Any]:
        """
        Поиск страниц в Confluence.

        Args:
            cql: CQL запрос
            limit: Максимальное количество результатов

        Returns:
            Результаты поиска
        """
        try:
            result = await self.atlassian_client.call_tool(
                "confluence_search",
                arguments={
                    "cql": cql,
                    "limit": limit,
                }
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "cql": cql,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "cql": cql,
                }
        except Exception as e:
            logger.error(f"Ошибка при поиске страниц в Confluence: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "cql": cql,
            }


class ConfluenceGetPageTool(BaseTool):
    """Инструмент для получения информации о странице в Confluence."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="confluence_get_page",
            description=(
                "Получение детальной информации о странице в Confluence по её ID. "
                "Используй этот инструмент для получения полной информации о странице: "
                "заголовок, содержимое, автор, дата создания, версия и т.д."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "ID страницы в Confluence",
                    },
                },
                "required": ["page_id"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self, page_id: str) -> Dict[str, Any]:
        """
        Получение информации о странице.

        Args:
            page_id: ID страницы

        Returns:
            Информация о странице
        """
        try:
            result = await self.atlassian_client.call_tool(
                "confluence_get_page",
                arguments={
                    "page_id": page_id,
                }
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "page_id": page_id,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "page_id": page_id,
                }
        except Exception as e:
            logger.error(f"Ошибка при получении страницы {page_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "page_id": page_id,
            }


class ConfluenceCreatePageTool(BaseTool):
    """Инструмент для создания новой страницы в Confluence."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="confluence_create_page",
            description=(
                "Создание новой страницы в Confluence. Используй этот инструмент для создания "
                "документации, заметок, инструкций и других страниц в Confluence. "
                "Необходимо указать пространство, заголовок и содержимое."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "space_key": {
                        "type": "string",
                        "description": "Ключ пространства (например: DOCS, TEAM)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Заголовок страницы",
                    },
                    "content": {
                        "type": "string",
                        "description": "Содержимое страницы (в формате Confluence Storage Format или Markdown)",
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "ID родительской страницы (опционально, для создания подстраницы)",
                    },
                },
                "required": ["space_key", "title", "content"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(
        self,
        space_key: str,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создание страницы в Confluence.

        Args:
            space_key: Ключ пространства
            title: Заголовок
            content: Содержимое
            parent_id: ID родительской страницы

        Returns:
            Информация о созданной странице
        """
        try:
            arguments = {
                "space_key": space_key,
                "title": title,
                "content": content,
            }
            
            if parent_id:
                arguments["parent_id"] = parent_id
            
            result = await self.atlassian_client.call_tool(
                "confluence_create_page",
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
            logger.error(f"Ошибка при создании страницы в Confluence: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }


class ConfluenceUpdatePageTool(BaseTool):
    """Инструмент для обновления страницы в Confluence."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="confluence_update_page",
            description=(
                "Обновление существующей страницы в Confluence. Используй этот инструмент для "
                "изменения заголовка, содержимого и других полей страницы."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "ID страницы",
                    },
                    "title": {
                        "type": "string",
                        "description": "Новый заголовок страницы (опционально)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Новое содержимое страницы (опционально)",
                    },
                    "version": {
                        "type": "integer",
                        "description": "Версия страницы (необходимо для обновления, обычно получается из get_page)",
                    },
                },
                "required": ["page_id"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(
        self,
        page_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Обновление страницы в Confluence.

        Args:
            page_id: ID страницы
            title: Новый заголовок
            content: Новое содержимое
            version: Версия страницы

        Returns:
            Результат обновления
        """
        try:
            arguments = {"page_id": page_id}
            
            if title:
                arguments["title"] = title
            if content:
                arguments["content"] = content
            if version:
                arguments["version"] = version
            
            result = await self.atlassian_client.call_tool(
                "confluence_update_page",
                arguments=arguments
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "page_id": page_id,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "page_id": page_id,
                }
        except Exception as e:
            logger.error(f"Ошибка при обновлении страницы {page_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "page_id": page_id,
            }


class ConfluenceDeletePageTool(BaseTool):
    """Инструмент для удаления страницы в Confluence."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="confluence_delete_page",
            description=(
                "Удаление страницы в Confluence. Используй этот инструмент для удаления "
                "ненужных страниц. Внимание: операция необратима!"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "ID страницы для удаления",
                    },
                },
                "required": ["page_id"],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self, page_id: str) -> Dict[str, Any]:
        """
        Удаление страницы в Confluence.

        Args:
            page_id: ID страницы

        Returns:
            Результат удаления
        """
        try:
            result = await self.atlassian_client.call_tool(
                "confluence_delete_page",
                arguments={
                    "page_id": page_id,
                }
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "page_id": page_id,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Неизвестная ошибка"),
                    "page_id": page_id,
                }
        except Exception as e:
            logger.error(f"Ошибка при удалении страницы {page_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "page_id": page_id,
            }


class ConfluenceGetSpacesTool(BaseTool):
    """Инструмент для получения списка пространств в Confluence."""

    def __init__(self, atlassian_client: AtlassianMCPClient):
        """
        Инициализация инструмента.

        Args:
            atlassian_client: Клиент для работы с Atlassian MCP сервером
        """
        super().__init__(
            name="confluence_get_spaces",
            description=(
                "Получение списка доступных пространств в Confluence. "
                "Используй этот инструмент для получения информации о пространствах: "
                "их ключи, названия, описания и т.д."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Максимальное количество результатов",
                        "default": 25,
                    },
                },
                "required": [],
            },
        )
        self.atlassian_client = atlassian_client

    async def execute(self, limit: int = 25) -> Dict[str, Any]:
        """
        Получение списка пространств.

        Args:
            limit: Максимальное количество результатов

        Returns:
            Список пространств
        """
        try:
            result = await self.atlassian_client.call_tool(
                "confluence_get_spaces",
                arguments={
                    "limit": limit,
                }
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
            logger.error(f"Ошибка при получении списка пространств: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
