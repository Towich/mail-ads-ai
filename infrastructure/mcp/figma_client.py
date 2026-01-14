"""MCP клиент для Figma сервера."""

import logging
import os
import shutil
from typing import Dict, Any, Optional, List, Callable, Awaitable
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class FigmaMCPClient:
    """Клиент для взаимодействия с Figma MCP сервером."""

    def __init__(self, figma_api_key: str):
        """
        Инициализация Figma MCP клиента.

        Args:
            figma_api_key: API ключ для Figma
        """
        self.figma_api_key = figma_api_key
        self._server_params: Optional[StdioServerParameters] = None

    def _get_server_params(self) -> StdioServerParameters:
        """Получение параметров сервера."""
        if self._server_params is None:
            # Проверяем наличие Node.js и npx
            if not shutil.which("node"):
                raise RuntimeError("Node.js не установлен. Установите Node.js для работы с Figma MCP сервером.")
            
            if not shutil.which("npx"):
                raise RuntimeError("npx не найден. Убедитесь, что Node.js установлен корректно.")

            # Параметры для запуска Figma MCP сервера
            # Используем npx для запуска figma-developer-mcp пакета
            self._server_params = StdioServerParameters(
                command="npx",
                args=["-y", "figma-developer-mcp", f"--figma-api-key={self.figma_api_key}", "--stdio"],
                env=os.environ.copy(),
            )
        return self._server_params

    @asynccontextmanager
    async def _session(self):
        """
        Context manager для работы с MCP сессией.
        
        Использование:
            async with figma_client._session() as session:
                # работа с session
        """
        server_params = self._get_server_params()
        logger.info("🔌 Подключение к Figma MCP серверу...")
        
        try:
            # Создаем stdio клиент как context manager
            async with stdio_client(server_params) as (read, write):
                # Создаем сессию как context manager
                async with ClientSession(read, write) as session:
                    # Инициализируем соединение
                    await session.initialize()
                    
                    logger.info("✅ Подключение к Figma MCP серверу установлено")
                    
                    try:
                        yield session
                    finally:
                        logger.info("Отключение от Figma MCP сервера")
        except Exception as e:
            logger.error(f"Ошибка при работе с Figma MCP сервером: {e}", exc_info=True)
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
