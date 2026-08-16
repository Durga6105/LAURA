"""
LAURA - Document Chunker

Creates retrieval-friendly chunks from NDA clauses.
"""

from typing import Any


class Chunker:
    """Create chunks from NDA clauses."""

    def __init__(self, max_characters: int = 1500):
        self.max_characters = max_characters

    def chunk(self, clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create chunks from clauses."""

        chunks = []

        for clause in clauses:
            text = clause.get("text", "").strip()

            if not text:
                continue

            parts = self._split_text(text)

            for index, part in enumerate(parts, start=1):
                chunks.append(
                    {
                        "chunk_id": (
                            f"{clause['clause_id']}-"
                            f"CHUNK-{index:03d}"
                        ),
                        "clause_id": clause["clause_id"],
                        "section": clause.get("section"),
                        "page_number": clause.get("page_number"),
                        "paragraph_number": clause.get("paragraph_number"),
                        "text": part,
                    }
                )

        return chunks

    def _split_text(self, text: str) -> list[str]:
        """Split long text into smaller chunks."""

        if len(text) <= self.max_characters:
            return [text]

        return [
            text[index:index + self.max_characters]
            for index in range(0, len(text), self.max_characters)
        ]