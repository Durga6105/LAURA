"""
LAURA - DOCX Parser

Extracts paragraphs and basic structure from DOCX documents.
"""
from pathlib import Path
from typing import Any
from docx import Document
class DOCXParser:
    """Parse DOCX documents."""

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        """
        Extract paragraphs from a DOCX document.

        Args:
            file_path: Path to DOCX.

        Returns:
            Parsed document information.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"DOCX not found: {path}")

        document = Document(path)

        paragraphs = []

        for index, paragraph in enumerate(document.paragraphs, start=1):
            text = paragraph.text.strip()

            if not text:
                continue

            paragraphs.append(
                {
                    "paragraph_number": index,
                    "text": text,
                    "style": paragraph.style.name,
                }
            )

        return {
            "file_name": path.name,
            "file_type": "docx",
            "paragraphs": paragraphs,
        }