"""Сервис для работы с ИИ-агентом."""

import logging
import json
from typing import List, Dict, Any, Optional
from domain.interfaces.llm import LLMInterface
from domain.interfaces.rag import RAGInterface
from infrastructure.tools.base import BaseTool
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
    
    def _get_system_prompt_tools_description(self) -> str:
        """
        Формирование описания инструментов для системного промпта.
        
        Returns:
            Строка с описанием доступных инструментов
        """
        tools_desc = """У тебя есть доступ к следующим инструментам:
- **rag_search** - семантический поиск по документации проекта. Используй его, когда нужно найти информацию в документации, README, или когда пользователь спрашивает о проекте, его структуре, архитектуре, или как что-то работает.
- **git_search_file** - поиск файла по названию в репозитории
- **git_list_files** - список файлов в директории
- **git_read_file** - чтение содержимого файла
- **git_current_branch** - текущая ветка git
- **git_current_changes** - список измененных файлов
- **git_diff** - diff для файла или коммита
- **git_log** - история коммитов
- **git_file_history** - история изменений файла"""
        
        # Проверяем наличие Figma инструментов
        figma_tools = [name for name in self.tools.keys() if name.startswith("figma_")]
        if figma_tools:
            tools_desc += "\n\n### Figma инструменты:"
            for tool_name in figma_tools:
                tool = self.tools[tool_name]
                # Используем свойство description из BaseTool
                description = tool.description
                tools_desc += f"\n- **{tool_name}** - {description}"
        
        return tools_desc

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
        tools_description = self._get_system_prompt_tools_description()
        system_prompt = f"""Ты полезный ИИ-ассистент для разработчиков. 
Ты помогаешь работать с проектом, отвечаешь на вопросы о коде и документации.

{tools_description}

Используй инструменты когда нужно найти файлы, прочитать код, получить информацию о репозитории, найти информацию в документации проекта или работать с Figma дизайнами."""
        
        messages.append({
            "role": "system",
            "content": system_prompt,
        })

        # Добавляем историю разговора
        messages.extend(self.conversation_history[-5:])  # Последние 5 сообщений

        # Получаем ответ от LLM в цикле до получения финального ответа
        try:
            tools = self._get_tools_for_llm()
            max_iterations = 25  # Защита от бесконечного цикла
            iteration = 0
            content = ""
            
            while iteration < max_iterations:
                iteration += 1
                tools_text = " (с инструментами)" if tools else ""
                logger.info(f"LLM запрос: {len(messages)} сообщений{tools_text}")
                logger.debug(f"Сообщения в LLM: {json.dumps(messages, ensure_ascii=False, indent=2)}")
                if tools:
                    logger.debug(f"Доступно инструментов: {len(tools)}")
                
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

    async def process_review(self, query: str) -> str:
        """
        Обработка запроса для ревью кода с кастомным системным промптом.

        Args:
            query: Запрос с изменениями кода для ревью

        Returns:
            Ответ агента-ревьювера
        """
        # Формируем сообщения для LLM
        messages = []
        
        # Системный промпт для ревью
        tools_description = self._get_system_prompt_tools_description()
        system_prompt = f"""Ты - агент-ревьювер кода. Твоя задача - проводить детальный анализ изменений в коде, 
выявлять потенциальные проблемы, давать конструктивные рекомендации по улучшению кода.

Ты должен обращать внимание на:
- Качество кода и соответствие best practices
- Потенциальные баги и ошибки
- Производительность и оптимизацию
- Читаемость и поддерживаемость кода
- Соответствие архитектурным принципам проекта (SOLID, Clean Architecture)
- Безопасность
- Тестируемость
- Соответствие стилю кодирования проекта

{tools_description}

Используй инструменты для получения дополнительного контекста о проекте, связанных файлах и стандартах кодирования, 
чтобы дать более точные и релевантные рекомендации."""
        
        messages.append({
            "role": "system",
            "content": system_prompt,
        })

        # Добавляем запрос пользователя (с изменениями кода)
        messages.append({
            "role": "user",
            "content": query,
        })

        # Получаем ответ от LLM в цикле до получения финального ответа
        try:
            tools = self._get_tools_for_llm()
            max_iterations = 25  # Защита от бесконечного цикла
            iteration = 0
            content = ""
            
            while iteration < max_iterations:
                iteration += 1
                tools_text = " (с инструментами)" if tools else ""
                logger.info(f"LLM запрос: {len(messages)} сообщений{tools_text}")
                logger.debug(f"Сообщения в LLM: {json.dumps(messages, ensure_ascii=False, indent=2)}")
                if tools:
                    logger.debug(f"Доступно инструментов: {len(tools)}")
                
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
                    logger.info("✅ Получен финальный ответ ревью без вызовов инструментов")
                    break
                
                # Есть вызовы инструментов - выполняем их и продолжаем цикл
                logger.info(f"🔧 LLM запросил выполнение {len(tool_calls)} инструментов для ревью (итерация {iteration})")
                
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
                
                logger.info(f"🔄 Продолжаю ревью с результатами инструментов (итерация {iteration})")
            
            if iteration >= max_iterations:
                logger.warning(f"⚠️  Достигнут лимит итераций ({max_iterations}), возвращаю последний ответ")
            
            return content

        except Exception as e:
            logger.error(f"Error processing review: {e}", exc_info=True)
            return f"Ошибка при обработке ревью: {str(e)}"

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
            logger.debug(f"Сообщения в LLM: {json.dumps(messages, ensure_ascii=False, indent=2)}")
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
                    logger.info(f"Вызов инструмента: {tool_name}")
                    logger.debug(f"Аргументы: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
                    
                    result = await self.tools[tool_name].execute(**arguments)
                    
                    # Логируем результат
                    logger.info(f"Результат инструмента {tool_name}: {json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, (dict, list)) else str(result)}")
                    
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    results.append({"error": str(e)})
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                results.append({"error": f"Unknown tool: {tool_name}"})

        return results
