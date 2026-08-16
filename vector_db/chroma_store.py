"""
LAURA - ChromaDB Store

Handles persistent vector storage and semantic search
using ChromaDB.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from config.settings import settings


class ChromaStore:
    """Persistent ChromaDB storage for LAURA."""

    RULES_COLLECTION = "laura_rules"
    NDA_COLLECTION = "laura_nda"

    def __init__(
        self,
        persist_directory: str | None = None,
    ) -> None:
        """
        Initialize ChromaDB.

        Args:
            persist_directory: Directory where ChromaDB stores data.
        """

        self.persist_directory = Path(
            persist_directory
            or settings.chroma_persist_directory
        )

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )

        self.rules_collection = self.client.get_or_create_collection(
            name=self.RULES_COLLECTION,
            metadata={
                "description": (
                    "LAURA Rule Book embeddings"
                )
            },
        )

        self.nda_collection = self.client.get_or_create_collection(
            name=self.NDA_COLLECTION,
            metadata={
                "description": (
                    "LAURA NDA document embeddings"
                )
            },
        )

    # =========================================================
    # RULES
    # =========================================================

    def add_rules(
        self,
        rules: list[dict[str, Any]],
    ) -> None:
        """
        Add normalized Rule Book rules.

        Expected rule format:

        {
            "id": "...",
            "text": "...",
            "embedding": [...],
            "metadata": {...}
        }
        """

        if not rules:
            return

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for rule in rules:
            ids.append(str(rule["id"]))
            documents.append(rule["text"])
            embeddings.append(rule["embedding"])

            metadata = self._sanitize_metadata(
                rule.get("metadata", {})
            )

            metadatas.append(metadata)

        self.rules_collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search_rules(
        self,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant Rule Book rules.
        """

        if not query_embedding:
            return []

        results = self.rules_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        return self._format_results(results)

    def delete_rule_book(
        self,
        rule_ids: list[str],
    ) -> None:
        """Delete specific Rule Book rules."""

        if not rule_ids:
            return

        self.rules_collection.delete(
            ids=[str(rule_id) for rule_id in rule_ids]
        )

    def clear_rules(self) -> None:
        """Delete all stored Rule Book rules."""

        self.client.delete_collection(
            self.RULES_COLLECTION
        )

        self.rules_collection = (
            self.client.get_or_create_collection(
                name=self.RULES_COLLECTION,
                metadata={
                    "description": (
                        "LAURA Rule Book embeddings"
                    )
                },
            )
        )

    # =========================================================
    # NDA
    # =========================================================

    def add_nda_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> None:
        """
        Store NDA chunks and their embeddings.

        Expected format:

        {
            "id": "...",
            "text": "...",
            "embedding": [...],
            "metadata": {...}
        }
        """

        if not chunks:
            return

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for chunk in chunks:
            ids.append(str(chunk["id"]))
            documents.append(chunk["text"])
            embeddings.append(chunk["embedding"])

            metadata = self._sanitize_metadata(
                chunk.get("metadata", {})
            )

            metadatas.append(metadata)

        self.nda_collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search_nda(
        self,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant NDA chunks."""

        if not query_embedding:
            return []

        results = self.nda_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        return self._format_results(results)

    def delete_nda(
        self,
        chunk_ids: list[str],
    ) -> None:
        """Delete specific NDA chunks."""

        if not chunk_ids:
            return

        self.nda_collection.delete(
            ids=[str(chunk_id) for chunk_id in chunk_ids]
        )

    def clear_nda(self) -> None:
        """Delete all stored NDA chunks."""

        self.client.delete_collection(
            self.NDA_COLLECTION
        )

        self.nda_collection = (
            self.client.get_or_create_collection(
                name=self.NDA_COLLECTION,
                metadata={
                    "description": (
                        "LAURA NDA document embeddings"
                    )
                },
            )
        )

    # =========================================================
    # GENERAL
    # =========================================================

    def count_rules(self) -> int:
        """Return number of stored rules."""

        return self.rules_collection.count()

    def count_nda_chunks(self) -> int:
        """Return number of stored NDA chunks."""

        return self.nda_collection.count()

    def reset(self) -> None:
        """Clear both collections."""

        self.clear_rules()
        self.clear_nda()

    @staticmethod
    def _format_results(
        results: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Convert ChromaDB query output into a simpler format.
        """

        if not results:
            return []

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        formatted = []

        for index, item_id in enumerate(ids):

            formatted.append(
                {
                    "id": item_id,
                    "text": documents[index]
                    if index < len(documents)
                    else "",

                    "metadata": metadatas[index]
                    if index < len(metadatas)
                    else {},

                    "distance": distances[index]
                    if index < len(distances)
                    else None,
                }
            )

        return formatted

    @staticmethod
    def _sanitize_metadata(
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        ChromaDB metadata supports primitive values.
        Convert unsupported values to strings.
        """

        sanitized = {}

        for key, value in metadata.items():

            if value is None:
                continue

            if isinstance(
                value,
                (str, int, float, bool),
            ):
                sanitized[str(key)] = value
            else:
                sanitized[str(key)] = str(value)

        return sanitized