"""Точка входа в приложение."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from infrastructure.config.settings import get_settings
from infrastructure.llm.vkai import VKAI
from infrastructure.llm.ollama import OllamaLLM
from infrastructure.rag.rag_system import RAGSystem, DocumentIndexer
from infrastructure.tools.git_tools import (
    GitSearchFileTool,
    GitListFilesTool,
    GitReadFileTool,
    GitCurrentBranchTool,
    GitCurrentChangesTool,
    GitDiffTool,
    GitLogTool,
    GitFileHistoryTool,
)
from infrastructure.tools.rag_tool import RAGSearchTool
from infrastructure.logging.rich_logger import setup_rich_logging, RichLogger
from application.services.agent_service import AgentService
from application.cli.cli import CLI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


async def initialize_rag(settings, ollama_llm=None) -> RAGSystem:
    """
    Инициализация RAG системы.

    Args:
        settings: Настройки приложения
        ollama_llm: Экземпляр Ollama LLM (опционально)

    Returns:
        Инициализированная RAG система
    """
    rag = RAGSystem(
        embedding_model=settings.rag_embedding_model,
        vector_db_path=settings.rag_vector_db_path,
        index_path=settings.rag_index_path,
        ollama_llm=ollama_llm,
    )

    # Индексируем .md файлы проекта если еще не проиндексированы
    # Проверяем, есть ли уже документы в индексе
    metadata_file = os.path.join(settings.rag_index_path, "metadata.json")
    
    if not os.path.exists(metadata_file) or os.path.getsize(metadata_file) == 0:
        # Используем рабочую директорию из настроек
        work_dir = os.path.abspath(settings.app_work_dir)
        indexer = DocumentIndexer(project_root=work_dir)
        documents = indexer.index_project()
        
        if documents:
            logger = logging.getLogger(__name__)
            logger.info(f"📚 Начинаю индексацию {len(documents)} markdown файлов...")
            await rag.index_documents(documents)
            logger.info("✅ Индексация завершена")
    else:
        logger = logging.getLogger(__name__)
        logger.info("Documents already indexed, skipping indexing")

    return rag


async def main():
    """Главная функция приложения."""
    # Загрузка настроек
    settings = get_settings()

    # Настройка красивого логирования
    setup_rich_logging(settings.app_log_level)
    logger = logging.getLogger(__name__)

    # Красивый вывод при старте
    console.print()
    console.print(Panel(
        Text("🚀 ИИ-агент CLI запускается...", style="bold green"),
        border_style="green",
        padding=(1, 2),
    ))
    console.print()

    try:
        # Инициализация Ollama для эмбеддингов
        logger.info(f"🔌 Подключение к Ollama: {settings.ollama_base_url} (модель: {settings.ollama_model})")
        ollama_llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

        # Инициализация RAG системы
        console.print("[cyan]📚 Инициализация RAG системы...[/cyan]")
        rag = await initialize_rag(settings, ollama_llm)

        # Инициализация LLM
        if settings.vkai_api_key:
            console.print(f"[green]✅ Используется VK AI (модель: {settings.vkai_model})[/green]")
            llm = VKAI(
                api_key=settings.vkai_api_key,
                base_url=settings.vkai_base_url,
                model=settings.vkai_model,
            )
        else:
            console.print(f"[yellow]✅ Используется Ollama (модель: {settings.ollama_model})[/yellow]")
            llm = ollama_llm

        # Инициализация инструментов
        console.print("[cyan]🔧 Инициализация инструментов...[/cyan]")
        # Используем рабочую директорию из настроек
        work_dir = os.path.abspath(settings.app_work_dir)
        console.print(f"[dim]📁 Рабочая директория: {work_dir}[/dim]")
        
        # Создаем список всех инструментов
        tools = [
            # RAG инструмент для поиска по документации
            RAGSearchTool(rag=rag),
            # Git инструменты
            GitSearchFileTool(repo_path=work_dir),
            GitListFilesTool(repo_path=work_dir),
            GitReadFileTool(repo_path=work_dir),
            GitCurrentBranchTool(repo_path=work_dir),
            GitCurrentChangesTool(repo_path=work_dir),
            GitDiffTool(repo_path=work_dir),
            GitLogTool(repo_path=work_dir),
            GitFileHistoryTool(repo_path=work_dir),
        ]
        
        console.print(f"[green]✅ Загружено {len(tools)} инструментов[/green]")

        # Инициализация сервиса агента
        agent_service = AgentService(
            llm=llm,
            rag=rag,
            tools=tools,
        )

        # Запуск CLI
        cli = CLI(agent_service)
        await cli.run()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Закрытие соединений
        if "ollama_llm" in locals():
            await ollama_llm.close()
        if "llm" in locals() and hasattr(llm, "close"):
            await llm.close()


if __name__ == "__main__":
    asyncio.run(main())
