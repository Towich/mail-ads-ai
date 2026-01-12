"""Git инструменты для работы с репозиторием."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from git import Repo, GitCommandError
from infrastructure.tools.base import BaseTool

logger = None  # Будет инициализирован при первом использовании


def get_logger():
    """Ленивая инициализация логгера."""
    global logger
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    return logger


class GitSearchFileTool(BaseTool):
    """Поиск файла по названию в репозитории."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_search_file",
            description="Поиск файла по названию в git-репозитории",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Название файла для поиска (можно использовать частичное совпадение)",
                    }
                },
                "required": ["filename"],
            },
        )
        self.repo_path = repo_path

    async def execute(self, filename: str) -> Dict[str, Any]:
        """
        Поиск файла.

        Args:
            filename: Название файла

        Returns:
            Результат поиска
        """
        try:
            repo = Repo(self.repo_path)
            found_files = []
            for root, dirs, files in os.walk(self.repo_path):
                # Пропускаем .git и другие служебные директории
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for file in files:
                    if filename.lower() in file.lower():
                        rel_path = os.path.relpath(
                            os.path.join(root, file), self.repo_path
                        )
                        found_files.append(rel_path)

            return {
                "success": True,
                "files": found_files,
                "count": len(found_files),
            }
        except Exception as e:
            get_logger().error(f"Error searching file: {e}")
            return {"success": False, "error": str(e)}


class GitListFilesTool(BaseTool):
    """Получение списка файлов в директории."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_list_files",
            description="Получение списка файлов в директории или репозитории",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Путь к директории (относительно корня репозитория). Если не указан, возвращает файлы корня.",
                    }
                },
                "required": [],
            },
        )
        self.repo_path = repo_path

    async def execute(self, directory: str = ".") -> Dict[str, Any]:
        """
        Получение списка файлов.

        Args:
            directory: Путь к директории

        Returns:
            Список файлов
        """
        try:
            full_path = os.path.join(self.repo_path, directory)
            if not os.path.exists(full_path):
                return {"success": False, "error": f"Directory not found: {directory}"}

            files = []
            dirs = []
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
                elif os.path.isdir(item_path) and not item.startswith("."):
                    dirs.append(item)

            return {
                "success": True,
                "files": sorted(files),
                "directories": sorted(dirs),
                "path": directory,
            }
        except Exception as e:
            get_logger().error(f"Error listing files: {e}")
            return {"success": False, "error": str(e)}


class GitReadFileTool(BaseTool):
    """Чтение содержимого файла."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_read_file",
            description="Чтение содержимого файла из репозитория",
            parameters={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Путь к файлу относительно корня репозитория",
                    }
                },
                "required": ["filepath"],
            },
        )
        self.repo_path = repo_path

    async def execute(self, filepath: str) -> Dict[str, Any]:
        """
        Чтение файла.

        Args:
            filepath: Путь к файлу

        Returns:
            Содержимое файла
        """
        try:
            full_path = os.path.join(self.repo_path, filepath)
            if not os.path.exists(full_path):
                return {"success": False, "error": f"File not found: {filepath}"}

            if not os.path.isfile(full_path):
                return {"success": False, "error": f"Path is not a file: {filepath}"}

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {
                "success": True,
                "content": content,
                "filepath": filepath,
            }
        except Exception as e:
            get_logger().error(f"Error reading file: {e}")
            return {"success": False, "error": str(e)}


class GitCurrentBranchTool(BaseTool):
    """Получение текущей ветки."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_current_branch",
            description="Получение названия текущей ветки git",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )
        self.repo_path = repo_path

    async def execute(self) -> Dict[str, Any]:
        """
        Получение текущей ветки.

        Returns:
            Название ветки
        """
        try:
            repo = Repo(self.repo_path)
            branch = repo.active_branch.name
            return {
                "success": True,
                "branch": branch,
            }
        except Exception as e:
            get_logger().error(f"Error getting current branch: {e}")
            return {"success": False, "error": str(e)}


class GitCurrentChangesTool(BaseTool):
    """Получение списка измененных файлов."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_current_changes",
            description="Получение списка измененных файлов (git status)",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )
        self.repo_path = repo_path

    async def execute(self) -> Dict[str, Any]:
        """
        Получение изменений.

        Returns:
            Список измененных файлов
        """
        try:
            repo = Repo(self.repo_path)
            changed_files = [item.a_path for item in repo.index.diff(None)]
            untracked_files = repo.untracked_files
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]

            return {
                "success": True,
                "modified": changed_files,
                "untracked": untracked_files,
                "staged": staged_files,
            }
        except Exception as e:
            get_logger().error(f"Error getting changes: {e}")
            return {"success": False, "error": str(e)}


class GitDiffTool(BaseTool):
    """Получение diff для файла или коммита."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_diff",
            description="Получение diff для файла или коммита",
            parameters={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Путь к файлу (опционально)",
                    },
                    "commit": {
                        "type": "string",
                        "description": "Хеш коммита для получения diff (опционально)",
                    },
                },
                "required": [],
            },
        )
        self.repo_path = repo_path

    async def execute(self, filepath: Optional[str] = None, commit: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение diff.

        Args:
            filepath: Путь к файлу
            commit: Хеш коммита

        Returns:
            Diff
        """
        try:
            repo = Repo(self.repo_path)
            if commit:
                commit_obj = repo.commit(commit)
                diff = commit_obj.diff(commit_obj.parents[0] if commit_obj.parents else None)
                diff_text = "\n".join([d.diff.decode("utf-8", errors="ignore") for d in diff])
            elif filepath:
                diff = repo.index.diff(None, paths=[filepath])
                diff_text = "\n".join([d.diff.decode("utf-8", errors="ignore") for d in diff])
            else:
                diff = repo.index.diff(None)
                diff_text = "\n".join([d.diff.decode("utf-8", errors="ignore") for d in diff])

            return {
                "success": True,
                "diff": diff_text,
            }
        except Exception as e:
            get_logger().error(f"Error getting diff: {e}")
            return {"success": False, "error": str(e)}


class GitLogTool(BaseTool):
    """Получение истории коммитов."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_log",
            description="Получение истории коммитов",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Количество коммитов для возврата (по умолчанию 10)",
                    },
                },
                "required": [],
            },
        )
        self.repo_path = repo_path

    async def execute(self, limit: int = 10) -> Dict[str, Any]:
        """
        Получение истории.

        Args:
            limit: Количество коммитов

        Returns:
            История коммитов
        """
        try:
            repo = Repo(self.repo_path)
            commits = []
            for commit in repo.iter_commits(max_count=limit):
                commits.append({
                    "hash": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat(),
                })

            return {
                "success": True,
                "commits": commits,
                "count": len(commits),
            }
        except Exception as e:
            get_logger().error(f"Error getting log: {e}")
            return {"success": False, "error": str(e)}


class GitFileHistoryTool(BaseTool):
    """История изменений конкретного файла."""

    def __init__(self, repo_path: str = "."):
        """Инициализация инструмента."""
        super().__init__(
            name="git_file_history",
            description="История изменений конкретного файла",
            parameters={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Путь к файлу относительно корня репозитория",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Количество коммитов для возврата (по умолчанию 10)",
                    },
                },
                "required": ["filepath"],
            },
        )
        self.repo_path = repo_path

    async def execute(self, filepath: str, limit: int = 10) -> Dict[str, Any]:
        """
        Получение истории файла.

        Args:
            filepath: Путь к файлу
            limit: Количество коммитов

        Returns:
            История изменений файла
        """
        try:
            repo = Repo(self.repo_path)
            commits = []
            for commit in repo.iter_commits(paths=[filepath], max_count=limit):
                commits.append({
                    "hash": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat(),
                })

            return {
                "success": True,
                "filepath": filepath,
                "commits": commits,
                "count": len(commits),
            }
        except Exception as e:
            get_logger().error(f"Error getting file history: {e}")
            return {"success": False, "error": str(e)}
