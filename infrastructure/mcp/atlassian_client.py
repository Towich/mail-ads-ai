"""MCP клиент для Atlassian сервера (Jira, Confluence)."""

import logging
import os
import shutil
from typing import Dict, Any, Optional, List, Callable, Awaitable
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class AtlassianMCPClient:
    """Клиент для взаимодействия с Atlassian MCP сервером (Jira, Confluence)."""

    def __init__(
        self,
        jira_url: str,
        jira_personal_token: Optional[str] = None,
        jira_username: Optional[str] = None,
        jira_api_token: Optional[str] = None,
        confluence_url: Optional[str] = None,
        confluence_username: Optional[str] = None,
        confluence_api_token: Optional[str] = None,
        confluence_personal_token: Optional[str] = None,
    ):
        """
        Инициализация Atlassian MCP клиента.

        Args:
            jira_url: URL Jira сервера (например: https://jira.vk.team)
            jira_personal_token: Personal Access Token для Jira (для Server/Data Center)
            jira_username: Username для Jira (для Cloud)
            jira_api_token: API Token для Jira (для Cloud)
            confluence_url: URL Confluence сервера (опционально)
            confluence_username: Username для Confluence (для Cloud)
            confluence_api_token: API Token для Confluence (для Cloud)
            confluence_personal_token: Personal Access Token для Confluence (для Server/Data Center)
        """
        self.jira_url = jira_url
        self.jira_personal_token = jira_personal_token
        self.jira_username = jira_username
        self.jira_api_token = jira_api_token
        self.confluence_url = confluence_url
        self.confluence_username = confluence_username
        self.confluence_api_token = confluence_api_token
        self.confluence_personal_token = confluence_personal_token
        self._server_params: Optional[StdioServerParameters] = None

    def _get_server_params(self) -> StdioServerParameters:
        """Получение параметров сервера."""
        if self._server_params is None:
            # Проверяем наличие uvx (через uv)
            if not shutil.which("uvx") and not shutil.which("uv"):
                raise RuntimeError(
                    "uvx не найден. Установите uv для работы с Atlassian MCP сервером: "
                    "https://github.com/astral-sh/uv"
                )

            # Подготавливаем переменные окружения
            env = os.environ.copy()
            env["JIRA_URL"] = self.jira_url

            # Для Server/Data Center используем Personal Access Token
            if self.jira_personal_token:
                env["JIRA_PERSONAL_TOKEN"] = self.jira_personal_token
            # Для Cloud используем username + API token
            elif self.jira_username and self.jira_api_token:
                env["JIRA_USERNAME"] = self.jira_username
                env["JIRA_API_TOKEN"] = self.jira_api_token
            else:
                raise ValueError(
                    "Необходимо указать либо jira_personal_token (для Server/Data Center), "
                    "либо jira_username + jira_api_token (для Cloud)"
                )

            # Настройки Confluence (опционально)
            if self.confluence_url:
                env["CONFLUENCE_URL"] = self.confluence_url
                if self.confluence_personal_token:
                    env["CONFLUENCE_PERSONAL_TOKEN"] = self.confluence_personal_token
                elif self.confluence_username and self.confluence_api_token:
                    env["CONFLUENCE_USERNAME"] = self.confluence_username
                    env["CONFLUENCE_API_TOKEN"] = self.confluence_api_token

            # Параметры для запуска Atlassian MCP сервера
            # Используем uvx для запуска mcp-atlassian пакета
            command = "uvx"
            args = ["mcp-atlassian"]
            
            # Если Python 3.14 не поддерживается, можно указать версию
            # args = ["--python=3.12", "mcp-atlassian"]

            self._server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env,
            )
        return self._server_params

    @asynccontextmanager
    async def _session(self):
        """
        Context manager для работы с MCP сессией.
        
        Использование:
            async with atlassian_client._session() as session:
                # работа с session
        """
        server_params = self._get_server_params()
        logger.info("🔌 Подключение к Atlassian MCP серверу...")
        
        try:
            # Создаем stdio клиент как context manager
            async with stdio_client(server_params) as (read, write):
                # Создаем сессию как context manager
                async with ClientSession(read, write) as session:
                    # Инициализируем соединение
                    await session.initialize()
                    
                    logger.info("✅ Подключение к Atlassian MCP серверу установлено")
                    
                    try:
                        yield session
                    finally:
                        logger.info("Отключение от Atlassian MCP сервера")
        except Exception as e:
            logger.error(f"Ошибка при работе с Atlassian MCP сервером: {e}", exc_info=True)
            raise

    async def _execute_with_session(self, func: Callable[[ClientSession], Awaitable[Any]]) -> Any:
        """
        Выполнение функции с активной сессией.

        Args:
            func: Асинхронная функция, принимающая сессию

        Returns:
            Результат выполнения функции
        """
        async with self._session() as session:
            return await func(session)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Получение списка доступных инструментов.

        Returns:
            Список инструментов
        """
        async def _list(session: ClientSession):
            result = await session.list_tools()
            tools = []
            for tool in (result.tools if hasattr(result, 'tools') else []):
                if hasattr(tool, 'name'):
                    tools.append({
                        "name": tool.name,
                        "description": getattr(tool, 'description', ''),
                    })
                else:
                    tools.append(tool)
            return tools
        
        try:
            return await self._execute_with_session(_list)
        except Exception as e:
            logger.error(f"Ошибка при получении списка инструментов: {e}", exc_info=True)
            raise

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Вызов инструмента MCP сервера.

        Args:
            name: Название инструмента
            arguments: Аргументы для инструмента

        Returns:
            Результат выполнения инструмента
        """
        async def _call(session: ClientSession):
            result = await session.call_tool(name, arguments)
            # Преобразуем результат в словарь
            if hasattr(result, 'content'):
                # MCP возвращает результат с content
                content_items = result.content
                if content_items:
                    # Берем первый элемент content
                    first_item = content_items[0]
                    if hasattr(first_item, 'text'):
                        return {"success": True, "result": first_item.text}
                    elif hasattr(first_item, 'data'):
                        return {"success": True, "result": first_item.data}
                return {"success": True, "result": str(result)}
            return {"success": True, "result": str(result)}
        
        try:
            return await self._execute_with_session(_call)
        except Exception as e:
            logger.error(f"Ошибка при вызове инструмента {name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        Получение списка доступных ресурсов.

        Returns:
            Список ресурсов
        """
        async def _list(session: ClientSession):
            result = await session.list_resources()
            return result.resources if hasattr(result, 'resources') else []
        
        try:
            return await self._execute_with_session(_list)
        except Exception as e:
            logger.error(f"Ошибка при получении списка ресурсов: {e}", exc_info=True)
            raise

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Чтение ресурса.

        Args:
            uri: URI ресурса

        Returns:
            Содержимое ресурса
        """
        async def _read(session: ClientSession):
            result = await session.read_resource(uri)
            if hasattr(result, 'contents'):
                contents = result.contents
                if contents:
                    first_item = contents[0]
                    if hasattr(first_item, 'text'):
                        return {"success": True, "content": first_item.text}
                    elif hasattr(first_item, 'data'):
                        return {"success": True, "content": first_item.data}
            return {"success": True, "content": str(result)}
        
        try:
            return await self._execute_with_session(_read)
        except Exception as e:
            logger.error(f"Ошибка при чтении ресурса {uri}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
