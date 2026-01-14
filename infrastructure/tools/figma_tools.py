"""Инструменты для работы с Figma через MCP."""

import logging
import re
from typing import Dict, Any, Optional
from infrastructure.tools.base import BaseTool
from infrastructure.mcp.figma_client import FigmaMCPClient

logger = logging.getLogger(__name__)


class FigmaGetFileTool(BaseTool):
    """Инструмент для получения информации о Figma файле."""

    def __init__(self, figma_client: FigmaMCPClient):
        """
        Инициализация инструмента.

        Args:
            figma_client: Клиент для работы с Figma MCP сервером
        """
        super().__init__(
            name="figma_get_file",
            description="Получение информации о Figma файле, фрейме или группе по ссылке. Используй этот инструмент для получения layout информации, стилей и структуры дизайна из Figma.",
            parameters={
                "type": "object",
                "properties": {
                    "figma_url": {
                        "type": "string",
                        "description": "Ссылка на Figma файл, фрейм или группу (например: https://www.figma.com/file/xxx или https://www.figma.com/design/xxx)",
                    },
                },
                "required": ["figma_url"],
            },
        )
        self.figma_client = figma_client

    def _extract_file_key(self, figma_url: str) -> str:
        """
        Извлечение fileKey из Figma URL или возврат как есть, если это уже fileKey.
        
        Args:
            figma_url: URL Figma файла или fileKey
            
        Returns:
            fileKey
        """
        # Если это уже похоже на fileKey (не URL), возвращаем как есть
        if not figma_url.startswith("http"):
            return figma_url
        
        # Пытаемся извлечь fileKey из URL
        # Форматы: https://www.figma.com/file/KEY/name или https://www.figma.com/design/KEY/name
        patterns = [
            r"figma\.com/file/([A-Za-z0-9]+)",
            r"figma\.com/design/([A-Za-z0-9]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, figma_url)
            if match:
                return match.group(1)
        
        # Если не удалось извлечь, возвращаем как есть
        return figma_url

    async def execute(self, figma_url: str) -> Dict[str, Any]:
        """
        Получение информации о Figma файле.

        Args:
            figma_url: Ссылка на Figma файл, фрейм или группу (или fileKey)

        Returns:
            Информация о файле
        """
        try:
            # Извлекаем fileKey из URL
            file_key = self._extract_file_key(figma_url)
            
            # Получаем список доступных инструментов
            tools = await self.figma_client.list_tools()
            
            # Пытаемся найти подходящий инструмент для работы с Figma
            # MCP инструмент get_figma_data требует параметр fileKey
            tool_names_to_try = ["get_figma_data", "get_figma_file", "get_file", "fetch_figma", "get_figma_context", "figma_get_file"]
            
            # Сначала пробуем известные названия
            result = None
            for tool_name in tool_names_to_try:
                # Проверяем, есть ли такой инструмент в списке
                tool_found = any(
                    (t.get('name') if isinstance(t, dict) else getattr(t, 'name', '')) == tool_name
                    for t in tools
                )
                if tool_found:
                    try:
                        # Для get_figma_data используем fileKey
                        if tool_name == "get_figma_data":
                            result = await self.figma_client.call_tool(
                                tool_name,
                                arguments={"fileKey": file_key}
                            )
                        else:
                            # Для других инструментов пробуем разные варианты
                            for arg_name in ["fileKey", "url", "figma_url", "file_url", "link"]:
                                try:
                                    result = await self.figma_client.call_tool(
                                        tool_name,
                                        arguments={arg_name: file_key if arg_name == "fileKey" else figma_url}
                                    )
                                    if result.get("success"):
                                        break
                                except:
                                    continue
                        if result and result.get("success"):
                            break
                    except Exception as e:
                        logger.debug(f"Ошибка при вызове {tool_name}: {e}")
                        continue
            
            # Если не нашли, пробуем все доступные инструменты
            if not result or not result.get("success"):
                for tool in tools:
                    tool_name = tool.get('name') if isinstance(tool, dict) else getattr(tool, 'name', '')
                    if tool_name and tool_name not in tool_names_to_try:
                        try:
                            # Пробуем с разными вариантами аргументов
                            for arg_name in ["fileKey", "url", "figma_url", "file_url", "link"]:
                                try:
                                    result = await self.figma_client.call_tool(
                                        tool_name,
                                        arguments={arg_name: file_key if arg_name == "fileKey" else figma_url}
                                    )
                                    if result.get("success"):
                                        break
                                except:
                                    continue
                            if result and result.get("success"):
                                break
                        except Exception as e:
                            logger.debug(f"Ошибка при вызове {tool_name}: {e}")
                            continue
            
            if result and result.get("success"):
                return {
                    "success": True,
                    "figma_url": figma_url,
                    "data": result.get("result", result),
                }
            else:
                return {
                    "success": False,
                    "error": "Не удалось получить информацию о Figma файле. Убедитесь, что ссылка корректна и у вас есть доступ к файлу.",
                    "figma_url": figma_url,
                }
                
        except Exception as e:
            logger.error(f"Ошибка при получении информации о Figma файле: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "figma_url": figma_url,
            }


class FigmaListToolsTool(BaseTool):
    """Инструмент для получения списка доступных Figma инструментов."""

    def __init__(self, figma_client: FigmaMCPClient):
        """
        Инициализация инструмента.

        Args:
            figma_client: Клиент для работы с Figma MCP сервером
        """
        super().__init__(
            name="figma_list_tools",
            description="Получение списка доступных инструментов Figma MCP сервера. Используй для отладки и понимания доступных возможностей.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )
        self.figma_client = figma_client

    async def execute(self) -> Dict[str, Any]:
        """
        Получение списка инструментов.

        Returns:
            Список доступных инструментов
        """
        try:
            tools = await self.figma_client.list_tools()
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
