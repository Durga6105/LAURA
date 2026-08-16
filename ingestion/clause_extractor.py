"""
LAURA - Clause Extractor

Extracts logical clauses/sections from parsed NDA content.
"""

from __future__ import annotations

import re
from typing import Any


class ClauseExtractor:
    """Extract logical NDA clauses from parsed documents."""

    SECTION_PATTERN = re.compile(
        r"^(?:"
        r"(?:section|article|clause)\s+[\w.-]+"
        r"|"
        r"\d+(?:\.\d+)*[.)]?"
        r")",
        re.IGNORECASE,
    )

    DOCUMENT_TITLES = {
        "NON DISCLOSURE AGREEMENT",
        "NDA",
    }

    def extract_from_pdf(
        self,
        parsed_document: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract logical clauses from a parsed PDF."""

        clauses: list[dict[str, Any]] = []

        for page in parsed_document.get("pages", []):

            page_number = page["page_number"]
            text = page["text"]

            if not text:
                continue

            clauses.extend(
                self._extract_from_text(
                    text=text,
                    page_number=page_number,
                )
            )

        return clauses

    def extract_from_docx(
        self,
        parsed_document: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract logical clauses from a DOCX.

        Section headings are stored as metadata and are
        not returned as independent clauses.

        Document titles are ignored.
        """

        clauses: list[dict[str, Any]] = []

        current_section: str | None = None

        for paragraph in parsed_document.get(
            "paragraphs",
            [],
        ):

            text = paragraph["text"].strip()

            if not text:
                continue

            paragraph_number = paragraph[
                "paragraph_number"
            ]

            # --------------------------------------------------
            # Skip document title
            # --------------------------------------------------

            if self._is_document_title(text):
                continue

            # --------------------------------------------------
            # Detect section heading
            # --------------------------------------------------

            if self.SECTION_PATTERN.match(text):

                current_section = text
                continue

            # --------------------------------------------------
            # Actual clause content
            # --------------------------------------------------

            clauses.append(
                {
                    "clause_id": (
                        f"CLAUSE-{len(clauses) + 1:04d}"
                    ),
                    "section": current_section,
                    "paragraph_number": paragraph_number,
                    "text": text,
                }
            )

        return clauses

    def _extract_from_text(
        self,
        text: str,
        page_number: int,
    ) -> list[dict[str, Any]]:
        """
        Extract logical clauses from PDF text.

        Section headings are stored as metadata and are
        not returned as independent clauses.

        Document titles are ignored.
        """

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        clauses: list[dict[str, Any]] = []

        current_section: str | None = None

        for line in lines:

            # --------------------------------------------------
            # Skip document title
            # --------------------------------------------------

            if self._is_document_title(line):
                continue

            # --------------------------------------------------
            # Detect section heading
            # --------------------------------------------------

            if self.SECTION_PATTERN.match(line):

                current_section = line
                continue

            # --------------------------------------------------
            # Actual clause content
            # --------------------------------------------------

            clauses.append(
                {
                    "clause_id": (
                        f"CLAUSE-{len(clauses) + 1:04d}"
                    ),
                    "section": current_section,
                    "page_number": page_number,
                    "text": line,
                }
            )

        return clauses

    @classmethod
    def _is_document_title(
        cls,
        text: str,
    ) -> bool:
        """
        Detect obvious NDA document titles.

        Examples:
            NON-DISCLOSURE AGREEMENT
            NON DISCLOSURE AGREEMENT
            NDA
        """

        normalized = re.sub(
            r"[^A-Z0-9]+",
            " ",
            text.upper(),
        ).strip()

        return normalized in cls.DOCUMENT_TITLES