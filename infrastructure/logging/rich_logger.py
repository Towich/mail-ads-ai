"""Rich logger для красивого вывода логов."""

import logging
import sys
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# Устанавливаем rich traceback для красивых ошибок
install(show_locals=True)

console = Console()


class RichLogger:
    """Обертка для красивого логирования с Rich."""

    def __init__(self, name: str, level: str = "INFO"):
        """
        Инициализация логгера.

        Args:
            name: Имя логгера
            level: Уровень логирования
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Удаляем существующие handlers
        self.logger.handlers.clear()
        
        # Создаем Rich handler
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        
        # Форматирование
        formatter = logging.Formatter(
            "%(message)s",
            datefmt="[%X]"
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)

    def get_logger(self) -> logging.Logger:
        """Получение логгера."""
        return self.logger

    @staticmethod
    def log_tool_call(tool_name: str, arguments: dict, result: any = None):
        """
        Логирование вызова инструмента.

        Args:
            tool_name: Название инструмента
            arguments: Аргументы вызова
            result: Результат выполнения (опционально)
        """
        table = Table(show_header=False, box=box.ROUNDED, padding=(0, 1))
        table.add_column("Параметр", style="cyan", width=20)
        table.add_column("Значение", style="white")
        
        table.add_row("🔧 Инструмент", f"[bold green]{tool_name}[/bold green]")
        
        if arguments:
            for key, value in arguments.items():
                # Обрезаем длинные значения
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                table.add_row(f"  {key}", value_str)
        
        if result is not None:
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            table.add_row("✅ Результат", f"[green]{result_str}[/green]")
        
        console.print(Panel(table, title="[bold blue]Вызов инструмента[/bold blue]", border_style="blue"))

    @staticmethod
    def log_rag_search(query: str, results: list, top_k: int = 5):
        """
        Логирование RAG поиска.

        Args:
            query: Поисковый запрос
            results: Результаты поиска
            top_k: Количество результатов
        """
        table = Table(show_header=True, box=box.ROUNDED, padding=(0, 1))
        table.add_column("№", style="cyan", width=3)
        table.add_column("Файл", style="yellow", width=30)
        table.add_column("Релевантность", style="green", width=12)
        table.add_column("Фрагмент", style="white", width=50)
        
        for i, doc in enumerate(results[:top_k], 1):
            filepath = doc.get("filepath", "unknown")
            distance = doc.get("distance")
            content = doc.get("content", "")
            
            # Форматируем релевантность
            if distance is not None:
                relevance = f"{1 - distance:.2%}"
            else:
                relevance = "N/A"
            
            # Обрезаем контент
            if len(content) > 100:
                content = content[:100] + "..."
            
            table.add_row(
                str(i),
                filepath,
                relevance,
                content
            )
        
        console.print(Panel(
            table,
            title=f"[bold magenta]🔍 RAG Поиск:[/bold magenta] [white]{query}[/white]",
            border_style="magenta"
        ))

    @staticmethod
    def log_indexing_progress(current: int, total: int, filename: str = ""):
        """
        Логирование прогресса индексации.

        Args:
            current: Текущий номер
            total: Всего файлов
            filename: Имя текущего файла
        """
        progress_text = f"[{current}/{total}]"
        if filename:
            progress_text += f" {filename}"
        console.print(f"[cyan]📚 Индексация:[/cyan] {progress_text}")

    @staticmethod
    def log_llm_request(messages_count: int, has_tools: bool = False):
        """
        Логирование запроса к LLM.

        Args:
            messages_count: Количество сообщений
            has_tools: Есть ли инструменты
        """
        tools_text = " [yellow](с инструментами)[/yellow]" if has_tools else ""
        console.print(f"[bold blue]🤖 LLM запрос:[/bold blue] {messages_count} сообщений{tools_text}")

    @staticmethod
    def log_llm_messages(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None):
        """
        Логирование сообщений, отправляемых в LLM.

        Args:
            messages: Список сообщений
            tools: Список инструментов (опционально)
        """
        from rich.syntax import Syntax
        
        # Сначала логируем системный промпт полностью
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        if system_messages:
            for i, msg in enumerate(system_messages):
                content = msg.get("content", "")
                title = f"[bold yellow]📋 Системный промпт[/bold yellow]"
                if len(system_messages) > 1:
                    title += f" [dim]({i + 1}/{len(system_messages)})[/dim]"
                
                console.print(Panel(
                    content,
                    title=title,
                    border_style="yellow",
                    expand=False
                ))
        
        # Создаем таблицу для остальных сообщений
        other_messages = [msg for msg in messages if msg.get("role") != "system"]
        if other_messages:
            table = Table(show_header=True, box=box.ROUNDED, padding=(0, 1))
            table.add_column("Роль", style="cyan", width=12)
            table.add_column("Содержимое", style="white", width=60)
            table.add_column("Доп. инфо", style="dim", width=20)
            
            for msg in other_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")
                tool_call_id = msg.get("tool_call_id")
                name = msg.get("name")
                
                # Обрезаем длинный контент (не для system, он уже показан)
                max_length = 200
                content_preview = content
                is_truncated = False
                if len(content) > max_length:
                    content_preview = content[:max_length] + "..."
                    is_truncated = True
                
                # Форматируем роль
                role_style = {
                    "user": "[bold green]user[/bold green]",
                    "assistant": "[bold blue]assistant[/bold blue]",
                    "tool": "[bold magenta]tool[/bold magenta]",
                }.get(role, role)
                
                # Добавляем индикатор обрезки
                if is_truncated:
                    content_preview += f" [dim]({len(content)} символов)[/dim]"
                
                # Дополнительная информация
                extra_info = ""
                if tool_calls:
                    tool_names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
                    extra_info = f"[yellow]{len(tool_calls)} calls: {', '.join(tool_names[:3])}[/yellow]"
                    if len(tool_calls) > 3:
                        extra_info += f" [dim]+{len(tool_calls) - 3}[/dim]"
                elif tool_call_id:
                    extra_info = f"[dim]id: {tool_call_id[:12]}...[/dim]"
                elif name:
                    extra_info = f"[dim]name: {name}[/dim]"
                
                table.add_row(role_style, content_preview, extra_info)
            
            console.print(Panel(
                table,
                title="[bold blue]📤 Сообщения в LLM[/bold blue]",
                border_style="blue"
            ))
        
        # Информация об инструментах
        tools_info = ""
        if tools:
            tools_info = f"\n[dim]Доступно инструментов: {len(tools)}[/dim]"
            if len(tools) <= 5:
                tool_names = ", ".join([t.get("function", {}).get("name", "unknown") for t in tools])
                tools_info += f"\n[dim]Инструменты: {tool_names}[/dim]"
        
        if tools_info:
            console.print(tools_info)

    @staticmethod
    def log_info(message: str, title: Optional[str] = None):
        """
        Красивый вывод информации.

        Args:
            message: Сообщение
            title: Заголовок (опционально)
        """
        if title:
            console.print(Panel(message, title=f"[bold green]{title}[/bold green]", border_style="green"))
        else:
            console.print(f"[green]ℹ️  {message}[/green]")

    @staticmethod
    def log_warning(message: str):
        """Логирование предупреждения."""
        console.print(f"[yellow]⚠️  {message}[/yellow]")

    @staticmethod
    def log_error(message: str):
        """Логирование ошибки."""
        console.print(f"[red]❌ {message}[/red]")


def setup_rich_logging(level: str = "INFO") -> None:
    """
    Настройка Rich логирования для всего приложения.

    Args:
        level: Уровень логирования
    """
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers.clear()
    
    # Добавляем Rich handler
    handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )
    
    formatter = logging.Formatter("%(message)s", datefmt="[%X]")
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
