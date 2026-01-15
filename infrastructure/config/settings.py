"""Настройки приложения."""

import os
from pathlib import Path
from typing import Optional, Any
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file="local.properties",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # VK AI
    vkai_api_key: str = ""
    vkai_base_url: str = "https://llm-proxy.vkteam.ru"
    vkai_model: str = "deepseek-chat"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # RAG
    rag_embedding_model: str = "all-minilm-l6-v2"
    rag_vector_db_path: str = "./data/vector_db"
    rag_index_path: str = "./data/index"

    # Figma
    figma_api_key: str = ""  # API ключ для Figma (опционально)

    # Atlassian Jira
    jira_url: str = ""  # URL Jira сервера (например: https://jira.vk.team)
    jira_personal_token: str = ""  # Personal Access Token для Jira Server/Data Center
    jira_username: str = ""  # Username для Jira Cloud (опционально)
    jira_api_token: str = ""  # API Token для Jira Cloud (опционально)

    # Atlassian Confluence (опционально, для будущего использования)
    confluence_url: str = ""  # URL Confluence сервера
    confluence_personal_token: str = ""  # Personal Access Token для Confluence Server/Data Center
    confluence_username: str = ""  # Username для Confluence Cloud (опционально)
    confluence_api_token: str = ""  # API Token для Confluence Cloud (опционально)

    # Application
    app_log_level: str = "INFO"
    app_data_dir: str = "./data"
    app_work_dir: str = "."  # Рабочая директория для работы с проектом

    def __init__(self, **kwargs):
        """Инициализация настроек с загрузкой из local.properties."""
        # Загружаем из local.properties если файл существует
        props_file = Path("local.properties")
        if props_file.exists():
            env_vars = {}
            with open(props_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            # Преобразуем формат vkai.api_key -> vkai_api_key
                            key = key.replace(".", "_")
                            # Устанавливаем как переменную окружения для pydantic
                            os.environ[key.upper()] = value
                            env_vars[key] = value
        super().__init__(**kwargs)


def get_settings() -> Settings:
    """Получение экземпляра настроек."""
    return Settings()
