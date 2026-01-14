"""CLI интерфейс приложения."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from application.commands.help_command import HelpCommand
from application.commands.review_command import ReviewCommand
from application.services.agent_service import AgentService

console = Console()
logger = logging.getLogger(__name__)


class CLI:
    """Интерактивный CLI интерфейс."""

    def __init__(self, agent_service: AgentService, repo_path: str = "."):
        """
        Инициализация CLI.

        Args:
            agent_service: Сервис агента
            repo_path: Путь к git репозиторию
        """
        self.agent_service = agent_service
        self.help_command = HelpCommand(agent_service)
        self.review_command = ReviewCommand(agent_service, repo_path)
        self.running = True

    def print_welcome(self):
        """Вывод приветственного сообщения."""
        welcome_text = """
# ИИ-агент CLI

Добро пожаловать! Это интерактивный интерфейс для работы с ИИ-агентом.

**Доступные команды:**
- `/help [запрос]` - получить помощь по проекту
- `/search [запрос]` - поиск по документации
- `/review` - анализ изменений в git репозитории
- `/exit` или `/quit` - выход из приложения

Просто введите ваш запрос для общения с агентом.
        """
        console.print(Panel(Markdown(welcome_text), title="Добро пожаловать", border_style="green"))

    async def process_command(self, user_input: str) -> Optional[str]:
        """
        Обработка команды пользователя.

        Args:
            user_input: Ввод пользователя

        Returns:
            Результат выполнения команды или None
        """
        user_input = user_input.strip()

        if not user_input:
            return None

        # Команды с префиксом /
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if command == "/help":
                return await self.help_command.execute(args)
            elif command == "/search":
                return await self.help_command.execute(args)  # Используем тот же механизм
            elif command == "/review":
                return await self.review_command.execute()
            elif command in ["/exit", "/quit"]:
                self.running = False
                return "До свидания!"
            else:
                return f"Неизвестная команда: {command}. Используйте /help для справки."

        # Обычный запрос к агенту
        try:
            response = await self.agent_service.process_query(user_input)
            return response
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return f"Ошибка при обработке запроса: {str(e)}"

    async def run(self):
        """Запуск интерактивного режима."""
        self.print_welcome()

        while self.running:
            try:
                user_input = Prompt.ask("\n[bold cyan]Вы[/bold cyan]")
                if not user_input:
                    continue

                result = await self.process_command(user_input)
                if result:
                    console.print(Panel(
                        Markdown(result),
                        title="[bold green]Агент[/bold green]",
                        border_style="blue"
                    ))
            except KeyboardInterrupt:
                console.print("\n[yellow]Прервано пользователем[/yellow]")
                break
            except EOFError:
                console.print("\n[yellow]Выход...[/yellow]")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                console.print(f"[red]Ошибка: {str(e)}[/red]")

        console.print("[green]До свидания![/green]")
