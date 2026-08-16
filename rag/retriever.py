"""
LAURA - RAG Retriever

Retrieves relevant Rule Book rules for NDA clauses
using semantic vector search.
"""

from __future__ import annotations

from typing import Any

from embeddings.embedding_service import EmbeddingService
from vector_db.chroma_store import ChromaStore


class RAGRetriever:
    """Retrieve relevant Rule Book rules for NDA content."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: ChromaStore | None = None,
    ) -> None:

        self.embedding_service = (
            embedding_service or EmbeddingService()
        )

        self.vector_store = (
            vector_store or ChromaStore()
        )

    def retrieve_rules(
        self,
        clause_text: str,
        n_results: int = 5,
        max_distance: float = 1.0,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant Rule Book rules for an NDA clause.

        Rules whose semantic distance is greater than
        max_distance are filtered out.
        """

        if not clause_text.strip():
            return []

        query_embedding = self.embedding_service.embed_text(
            clause_text
        )

        results = self.vector_store.search_rules(
            query_embedding=query_embedding,
            n_results=n_results,
        )

        # --------------------------------------------------
        # Filter semantically weak matches.
        #
        # Lower Chroma distance = more similar.
        # --------------------------------------------------

        relevant_rules = []

        for rule in results:

            distance = rule.get("distance")

            if distance is None:
                relevant_rules.append(rule)
                continue

            if distance <= max_distance:
                relevant_rules.append(rule)

        return relevant_rules

    def retrieve_for_clause(
        self,
        clause: dict[str, Any],
        n_results: int = 5,
        max_distance: float = 1.0,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant rules for a structured NDA clause.
        """

        clause_text = clause.get(
            "text",
            "",
        ).strip()

        if not clause_text:
            return []

        return self.retrieve_rules(
            clause_text=clause_text,
            n_results=n_results,
            max_distance=max_distance,
        )