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
from infrastructure.mcp.figma_client import FigmaMCPClient
from infrastructure.tools.figma_tools import FigmaGetFileTool, FigmaListToolsTool
from infrastructure.logging.rich_logger import setup_logging
from application.services.agent_service import AgentService
from application.cli.cli import CLI


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

    # Настройка логирования
    setup_logging(settings.app_log_level)
    logger = logging.getLogger(__name__)

    logger.info("🚀 ИИ-агент CLI запускается...")

    try:
        # Инициализация Ollama для эмбеддингов
        logger.info(f"🔌 Подключение к Ollama: {settings.ollama_base_url} (модель: {settings.ollama_model})")
        ollama_llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

        # Инициализация RAG системы
        logger.info("📚 Инициализация RAG системы...")
        rag = await initialize_rag(settings, ollama_llm)

        # Инициализация LLM
        if settings.vkai_api_key:
            logger.info(f"✅ Используется VK AI (модель: {settings.vkai_model})")
            llm = VKAI(
                api_key=settings.vkai_api_key,
                base_url=settings.vkai_base_url,
                model=settings.vkai_model,
            )
        else:
            logger.info(f"✅ Используется Ollama (модель: {settings.ollama_model})")
            llm = ollama_llm

        # Инициализация инструментов
        logger.info("🔧 Инициализация инструментов...")
        # Используем рабочую директорию из настроек
        work_dir = os.path.abspath(settings.app_work_dir)
        logger.info(f"📁 Рабочая директория: {work_dir}")
        
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
        
        # Инициализация Figma MCP клиента и инструментов (если API ключ указан)
        figma_client = None
        if settings.figma_api_key:
            try:
                logger.info("🎨 Инициализация Figma MCP клиента...")
                figma_client = FigmaMCPClient(figma_api_key=settings.figma_api_key)
                # Добавляем Figma инструменты
                tools.extend([
                    FigmaGetFileTool(figma_client=figma_client),
                    FigmaListToolsTool(figma_client=figma_client),
                ])
                logger.info("✅ Figma инструменты загружены")
            except Exception as e:
                logger.warning(f"Не удалось инициализировать Figma MCP клиент: {e}")
                logger.warning(f"⚠️  Figma инструменты недоступны: {e}")
        else:
            logger.info("Figma API ключ не указан, Figma инструменты не загружены")
        
        logger.info(f"✅ Загружено {len(tools)} инструментов")

        # Инициализация сервиса агента
        agent_service = AgentService(
            llm=llm,
            rag=rag,
            tools=tools,
        )

        # Запуск CLI
        cli = CLI(agent_service, repo_path=work_dir)
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
