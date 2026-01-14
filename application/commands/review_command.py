"""Команда /review для анализа изменений в git репозитории."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from git import Repo
from application.services.agent_service import AgentService

logger = logging.getLogger(__name__)


class ReviewCommand:
    """Команда /review для анализа изменений кода."""

    def __init__(self, agent_service: AgentService, repo_path: str = "."):
        """
        Инициализация команды.

        Args:
            agent_service: Сервис агента с доступом к RAG
            repo_path: Путь к git репозиторию
        """
        self.agent_service = agent_service
        self.repo_path = os.path.abspath(repo_path)

    async def execute(self) -> str:
        """
        Выполнение команды /review.

        Returns:
            Результат выполнения команды
        """
        try:
            # Проверяем, что это git репозиторий
            if not os.path.exists(os.path.join(self.repo_path, ".git")):
                return f"Ошибка: {self.repo_path} не является git репозиторием."
            
            # Получаем git diff измененных файлов
            diff_text = self._get_git_diff()
            
            if not diff_text:
                return "Нет изменений для анализа. Рабочая директория чиста."

            # Формируем промпт для ревью
            review_prompt = f"""Проанализируй следующие изменения в коде:

{diff_text}

Проведи детальный код-ревью, обращая внимание на:
- Качество кода и соответствие best practices
- Потенциальные баги и ошибки
- Производительность и оптимизацию
- Читаемость и поддерживаемость кода
- Соответствие архитектурным принципам проекта
- Безопасность
- Тестируемость

Предоставь конструктивную обратную связь с конкретными рекомендациями."""

            # Вызываем агента с кастомным системным промптом для ревью
            response = await self.agent_service.process_review(review_prompt)

            # Сохраняем результат в md-файл
            output_file = self._save_review_to_file(response, diff_text)

            return f"""✅ Ревью завершено!

📄 Результат сохранен в файл: {output_file}

{response}"""

        except Exception as e:
            logger.error(f"Error in review command: {e}", exc_info=True)
            return f"Ошибка при выполнении ревью: {str(e)}"

    def _get_git_diff(self) -> str:
        """
        Получение git diff для измененных файлов.

        Returns:
            Текст diff или пустая строка
        """
        try:
            # Проверяем, что это git репозиторий
            if not os.path.exists(os.path.join(self.repo_path, ".git")):
                logger.warning(f"Directory {self.repo_path} is not a git repository")
                return ""
            
            repo = Repo(self.repo_path)
            
            # Получаем измененные файлы (unstaged)
            unstaged_diff = repo.index.diff(None)
            
            # Получаем staged файлы
            staged_diff = repo.index.diff("HEAD")
            
            # Получаем неотслеживаемые файлы
            untracked_files = repo.untracked_files
            
            diff_parts = []
            
            # Добавляем staged изменения
            if staged_diff:
                diff_parts.append("=== STAGED CHANGES ===")
                for item in staged_diff:
                    diff_parts.append(f"\n--- File: {item.a_path} ---")
                    try:
                        # item.diff может быть как bytes, так и str в зависимости от версии GitPython
                        if isinstance(item.diff, bytes):
                            diff_text = item.diff.decode("utf-8", errors="ignore")
                        else:
                            diff_text = str(item.diff)
                        diff_parts.append(diff_text)
                    except Exception as e:
                        logger.warning(f"Error reading diff for {item.a_path}: {e}")
                        diff_parts.append(f"[Error reading diff: {str(e)}]")
            
            # Добавляем unstaged изменения
            if unstaged_diff:
                diff_parts.append("\n=== UNSTAGED CHANGES ===")
                for item in unstaged_diff:
                    diff_parts.append(f"\n--- File: {item.a_path} ---")
                    try:
                        # item.diff может быть как bytes, так и str в зависимости от версии GitPython
                        if isinstance(item.diff, bytes):
                            diff_text = item.diff.decode("utf-8", errors="ignore")
                        else:
                            diff_text = str(item.diff)
                        diff_parts.append(diff_text)
                    except Exception as e:
                        logger.warning(f"Error reading diff for {item.a_path}: {e}")
                        diff_parts.append(f"[Error reading diff: {str(e)}]")
            
            # Добавляем неотслеживаемые файлы (полный контент)
            if untracked_files:
                diff_parts.append("\n=== UNTRACKED FILES ===")
                for filepath in untracked_files:
                    full_path = os.path.join(self.repo_path, filepath)
                    if os.path.isfile(full_path):
                        diff_parts.append(f"\n--- New File: {filepath} ---")
                        try:
                            with open(full_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                diff_parts.append(content)
                        except Exception as e:
                            logger.warning(f"Error reading untracked file {filepath}: {e}")
                            diff_parts.append(f"[Error reading file: {str(e)}]")
            
            return "\n".join(diff_parts) if diff_parts else ""
            
        except Exception as e:
            logger.error(f"Error getting git diff: {e}", exc_info=True)
            return ""

    def _save_review_to_file(self, review_content: str, diff_text: str) -> str:
        """
        Сохранение результата ревью в md-файл.

        Args:
            review_content: Содержимое ревью
            diff_text: Исходный diff

        Returns:
            Путь к сохраненному файлу
        """
        # Создаем директорию для ревью, если её нет
        reviews_dir = Path(self.repo_path) / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        
        # Генерируем уникальное имя файла с timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_{timestamp}.md"
        filepath = reviews_dir / filename
        
        # Формируем полное содержимое файла
        full_content = f"""# Code Review

**Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Изменения

```diff
{diff_text}
```

## Ревью

{review_content}
"""
        
        # Сохраняем файл
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        logger.info(f"Review saved to {filepath}")
        return str(filepath)
