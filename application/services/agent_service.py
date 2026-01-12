"""Сервис для работы с ИИ-агентом."""

import logging
import json
from typing import List, Dict, Any, Optional
from domain.interfaces.llm import LLMInterface
from domain.interfaces.rag import RAGInterface
from infrastructure.tools.base import BaseTool
from infrastructure.logging.rich_logger import RichLogger

logger = logging.getLogger(__name__)


class AgentService:
    """Сервис для управления ИИ-агентом."""

    def __init__(
        self,
        llm: LLMInterface,
        rag: RAGInterface,
        tools: List[BaseTool],
    ):
        """
        Инициализация сервиса агента.

        Args:
            llm: Интерфейс LLM
            rag: Интерфейс RAG системы
            tools: Список доступных инструментов
        """
        self.llm = llm
        self.rag = rag
        self.tools = {tool.name: tool for tool in tools}
        self.conversation_history: List[Dict[str, str]] = []

    def _get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Получение списка инструментов в формате для LLM."""
        return [tool.to_dict() for tool in self.tools.values()]

    async def process_query(self, query: str) -> str:
        """
        Обработка запроса пользователя.

        Args:
            query: Запрос пользователя

        Returns:
            Ответ агента
        """
        # Добавляем запрос в историю
        self.conversation_history.append({
            "role": "user",
            "content": query,
        })
        
        # Формируем сообщения для LLM
        messages = []
        
        # Системный промпт
        system_prompt = """Ты полезный ИИ-ассистент для разработчиков. 
Ты помогаешь работать с проектом, отвечаешь на вопросы о коде и документации.

У тебя есть доступ к следующим инструментам:
- **rag_search** - семантический поиск по документации проекта. Используй его, когда нужно найти информацию в документации, README, или когда пользователь спрашивает о проекте, его структуре, архитектуре, или как что-то работает.
- **git_search_file** - поиск файла по названию в репозитории
- **git_list_files** - список файлов в директории
- **git_read_file** - чтение содержимого файла
- **git_current_branch** - текущая ветка git
- **git_current_changes** - список измененных файлов
- **git_diff** - diff для файла или коммита
- **git_log** - история коммитов
- **git_file_history** - история изменений файла

Используй инструменты когда нужно найти файлы, прочитать код, получить информацию о репозитории или найти информацию в документации проекта."""
        
        messages.append({
            "role": "system",
            "content": system_prompt,
        })

        # Добавляем историю разговора
        messages.extend(self.conversation_history[-5:])  # Последние 5 сообщений

        # Получаем ответ от LLM в цикле до получения финального ответа
        try:
            tools = self._get_tools_for_llm()
            max_iterations = 100  # Защита от бесконечного цикла
            iteration = 0
            content = ""
            
            while iteration < max_iterations:
                iteration += 1
                RichLogger.log_llm_request(len(messages), has_tools=bool(tools))
                RichLogger.log_llm_messages(messages, tools)
                
                response = await self.llm.chat(messages, tools=tools)
                
                # Обрабатываем ответ
                if "choices" not in response or len(response["choices"]) == 0:
                    return "Не удалось получить ответ от LLM."
                
                choice = response["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                
                # Проверяем наличие tool_calls
                tool_calls = message.get("tool_calls", [])
                
                if not tool_calls:
                    # Финальный ответ без вызовов инструментов - выходим из цикла
                    logger.info("✅ Получен финальный ответ без вызовов инструментов")
                    break
                
                # Есть вызовы инструментов - выполняем их и продолжаем цикл
                logger.info(f"🔧 LLM запросил выполнение {len(tool_calls)} инструментов (итерация {iteration})")
                
                # Выполняем инструменты
                tool_results = await self._execute_tools(tool_calls)
                
                # Добавляем сообщение ассистента с tool_calls в контекст
                messages.append(message)
                
                # Связываем результаты с tool_call_id и добавляем в контекст
                for i, tool_call in enumerate(tool_calls):
                    tool_call_id = tool_call.get("id", "")
                    if not tool_call_id:
                        logger.warning(f"Tool call {i} не имеет id, пропускаю")
                        continue
                    
                    tool_result = tool_results[i] if i < len(tool_results) else {"error": "No result"}
                    
                    # Форматируем результат в JSON строку
                    if isinstance(tool_result, dict):
                        result_content = json.dumps(tool_result, ensure_ascii=False)
                    else:
                        result_content = str(tool_result)
                    
                    messages.append({
                        "role": "tool",
                        "content": result_content,
                        "tool_call_id": tool_call_id,
                    })
                
                logger.info(f"🔄 Продолжаю диалог с результатами инструментов (итерация {iteration})")
            
            if iteration >= max_iterations:
                logger.warning(f"⚠️  Достигнут лимит итераций ({max_iterations}), возвращаю последний ответ")
            
            # Добавляем финальный ответ в историю
            self.conversation_history.append({
                "role": "assistant",
                "content": content,
            })

            return content

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return f"Ошибка при обработке запроса: {str(e)}"

    async def process_query_with_context(self, query: str) -> str:
        """
        Обработка запроса с дополнительным контекстом.

        Args:
            query: Запрос с контекстом

        Returns:
            Ответ агента
        """
        messages = [{
            "role": "user",
            "content": query,
        }]

        try:
            RichLogger.log_llm_messages(messages)
            response = await self.llm.chat(messages)
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0].get("message", {}).get("content", "")
            return "Не удалось получить ответ."
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return f"Ошибка: {str(e)}"

    async def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Any]:
        """
        Выполнение инструментов.

        Args:
            tool_calls: Список вызовов инструментов

        Returns:
            Список результатов выполнения
        """
        results = []
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name", "")
            arguments = function.get("arguments", {})

            if tool_name in self.tools:
                try:
                    # Парсим аргументы если они строка
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)

                    # Логируем вызов инструмента
                    RichLogger.log_tool_call(tool_name, arguments)
                    
                    result = await self.tools[tool_name].execute(**arguments)
                    
                    # Логируем результат (обновляем с результатом)
                    RichLogger.log_tool_call(tool_name, arguments, result)
                    
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    results.append({"error": str(e)})
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                results.append({"error": f"Unknown tool: {tool_name}"})

        return results
