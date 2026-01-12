"""RAG система для семантического поиска по документации."""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from domain.interfaces.rag import RAGInterface
from infrastructure.logging.rich_logger import RichLogger

logger = logging.getLogger(__name__)


class RAGSystem(RAGInterface):
    """RAG система с использованием ChromaDB и Sentence Transformers."""

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        vector_db_path: str = "./data/vector_db",
        index_path: str = "./data/index",
        ollama_llm=None,
    ):
        """
        Инициализация RAG системы.

        Args:
            embedding_model: Название модели для эмбеддингов
            vector_db_path: Путь к векторной БД
            index_path: Путь для сохранения индекса
            ollama_llm: Экземпляр Ollama LLM (опционально, для генерации эмбеддингов)
        """
        self.embedding_model_name = embedding_model
        self.vector_db_path = vector_db_path
        self.index_path = index_path
        self.ollama_llm = ollama_llm

        # Инициализация модели эмбеддингов
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # Инициализация ChromaDB
        os.makedirs(vector_db_path, exist_ok=True)
        os.makedirs(index_path, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=vector_db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )

        # Загрузка индекса метаданных
        self.metadata_index = self._load_metadata_index()

    def _load_metadata_index(self) -> Dict[str, Dict[str, Any]]:
        """Загрузка индекса метаданных."""
        index_file = os.path.join(self.index_path, "metadata.json")
        if os.path.exists(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_metadata_index(self):
        """Сохранение индекса метаданных."""
        index_file = os.path.join(self.index_path, "metadata.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata_index, f, ensure_ascii=False, indent=2)

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Генерация эмбеддингов для текстов.

        Args:
            texts: Список текстов

        Returns:
            Список векторов эмбеддингов
        """
        if self.ollama_llm:
            # Используем Ollama если доступен
            return await self.ollama_llm.generate_embeddings(texts)
        else:
            # Используем Sentence Transformers (синхронный вызов)
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
            return embeddings.tolist()

    def _split_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Разбиение текста на чанки.

        Args:
            text: Текст для разбиения
            chunk_size: Размер чанка
            overlap: Перекрытие между чанками

        Returns:
            Список чанков
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 для пробела
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Перекрытие
                overlap_words = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_words + [word]
                current_length = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    async def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Индексация документов.

        Args:
            documents: Список документов с полями: content, filepath, metadata
        """
        all_chunks = []
        all_embeddings = []
        all_ids = []
        all_metadatas = []

        for doc_idx, doc in enumerate(documents):
            content = doc.get("content", "")
            filepath = doc.get("filepath", f"doc_{doc_idx}")
            metadata = doc.get("metadata", {})

            # Разбиваем на чанки
            chunks = self._split_text(content)

            for chunk_idx, chunk in enumerate(chunks):
                chunk_id = f"{filepath}_{chunk_idx}"
                all_chunks.append(chunk)
                all_ids.append(chunk_id)
                all_metadatas.append({
                    "filepath": filepath,
                    "chunk_index": chunk_idx,
                    **metadata,
                })

        # Генерируем эмбеддинги
        logger.info(f"📊 Генерация эмбеддингов для {len(all_chunks)} фрагментов...")
        all_embeddings = await self._generate_embeddings(all_chunks)
        logger.info("✅ Эмбеддинги сгенерированы")

        # Добавляем в ChromaDB
        self.collection.add(
            embeddings=all_embeddings,
            documents=all_chunks,
            ids=all_ids,
            metadatas=all_metadatas,
        )

        # Сохраняем метаданные
        for doc in documents:
            filepath = doc.get("filepath", "")
            self.metadata_index[filepath] = {
                "filepath": filepath,
                "metadata": doc.get("metadata", {}),
            }

        self._save_metadata_index()
        logger.info(f"✅ Проиндексировано {len(documents)} документов ({len(all_chunks)} фрагментов)")

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Семантический поиск по документам.

        Args:
            query: Поисковый запрос
            top_k: Количество результатов

        Returns:
            Список релевантных документов
        """
        logger.info(f"🔍 Выполняю RAG поиск: '{query}' (top_k={top_k})")
        
        # Генерируем эмбеддинг для запроса
        query_embeddings = await self._generate_embeddings([query])
        query_embedding = query_embeddings[0]

        # Поиск в ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        # Формируем результат
        documents = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                documents.append({
                    "content": results["documents"][0][i],
                    "filepath": results["metadatas"][0][i].get("filepath", ""),
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                })
            
            # Красивый вывод результатов
            RichLogger.log_rag_search(query, documents, top_k)
            logger.info(f"✅ Найдено {len(documents)} релевантных документов")
        else:
            logger.warning("⚠️  RAG поиск не вернул результатов")

        return documents

    async def get_context(self, query: str, top_k: int = 5) -> str:
        """
        Получение контекста для запроса.

        Args:
            query: Поисковый запрос
            top_k: Количество документов

        Returns:
            Строка с контекстом
        """
        documents = await self.search(query, top_k)
        if not documents:
            return ""

        context_parts = []
        for doc in documents:
            filepath = doc.get("filepath", "unknown")
            content = doc.get("content", "")
            context_parts.append(f"Файл: {filepath}\n{content}\n")

        return "\n---\n".join(context_parts)


class DocumentIndexer:
    """Индексатор для обработки .md файлов проекта."""

    def __init__(self, project_root: str = "."):
        """
        Инициализация индексатора.

        Args:
            project_root: Корневая директория проекта
        """
        self.project_root = Path(project_root)

    def find_markdown_files(self) -> List[Path]:
        """
        Поиск всех .md файлов в проекте.

        Returns:
            Список путей к .md файлам
        """
        md_files = []
        for md_file in self.project_root.rglob("*.md"):
            # Пропускаем файлы в служебных директориях
            if any(part.startswith(".") for part in md_file.parts):
                continue
            md_files.append(md_file)
        return md_files

    def index_project(self) -> List[Dict[str, Any]]:
        """
        Индексация всех .md файлов проекта.

        Returns:
            Список документов для индексации
        """
        md_files = self.find_markdown_files()
        logger.info(f"📚 Найдено {len(md_files)} .md файлов для индексации")
        documents = []

        for idx, md_file in enumerate(md_files, 1):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                rel_path = md_file.relative_to(self.project_root)
                RichLogger.log_indexing_progress(idx, len(md_files), str(rel_path))
                
                documents.append({
                    "content": content,
                    "filepath": str(rel_path),
                    "metadata": {
                        "type": "markdown",
                        "size": len(content),
                    },
                })
            except Exception as e:
                logger.error(f"Error reading {md_file}: {e}")

        return documents
