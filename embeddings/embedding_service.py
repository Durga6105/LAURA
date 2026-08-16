"""
LAURA - Embedding Service

Provides a reusable interface for generating text embeddings.
"""

from __future__ import annotations

from typing import Sequence

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Generate embeddings for rules, NDA chunks, and queries."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        """
        Initialize the embedding model.

        Args:
            model_name: SentenceTransformer model name.
        """
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding for a single text.

        Args:
            text: Input text.

        Returns:
            Embedding vector.
        """
        self._validate_text(text)

        embedding = self._model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: Input texts.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        for text in texts:
            self._validate_text(text)

        embeddings = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    def embed_rule(self, rule: object) -> list[float]:
        """
        Generate an embedding for a Rule object.

        The Rule object is converted into meaningful text
        before embedding.
        """
        text = self._rule_to_text(rule)

        return self.embed_text(text)

    def embed_clause(self, clause: dict) -> list[float]:
        """
        Generate an embedding for an NDA clause.
        """
        text = clause.get("text", "")

        return self.embed_text(text)

    @staticmethod
    def _rule_to_text(rule: object) -> str:
        """Convert a Rule object into embedding text."""

        return (
            f"Category: {getattr(rule, 'category', '')}\n"
            f"Rule Name: {getattr(rule, 'rule_name', '')}\n"
            f"Description: {getattr(rule, 'description', '')}\n"
            f"Validation Criteria: "
            f"{getattr(rule, 'validation_criteria', '')}\n"
            f"Correction Instruction: "
            f"{getattr(rule, 'correction_instruction', '')}"
        )

    @staticmethod
    def _validate_text(text: str) -> None:
        """Validate embedding input."""

        if not isinstance(text, str):
            raise TypeError("Embedding input must be a string.")

        if not text.strip():
            raise ValueError("Cannot generate embedding for empty text.")