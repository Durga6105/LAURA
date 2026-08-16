"""
LAURA - Rule Book Service

Integrates the Rule Book pipeline:

Rule Book
    ↓
Parser
    ↓
Normalizer
    ↓
Validator
    ↓
Embeddings
    ↓
ChromaDB
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from embeddings.embedding_service import EmbeddingService
from ingestion.rulebook_parser import RuleBookParser
from rules.rule_normalizer import RuleNormalizer
from rules.rule_validator import RuleValidator
from utils.logger import get_logger
from vector_db.chroma_store import ChromaStore


logger = get_logger(__name__)


class RuleBookService:
    """Complete Rule Book ingestion and indexing service."""

    def __init__(
        self,
        parser: RuleBookParser | None = None,
        normalizer: RuleNormalizer | None = None,
        validator: RuleValidator | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: ChromaStore | None = None,
    ) -> None:

        self.parser = parser or RuleBookParser()
        self.normalizer = normalizer or RuleNormalizer()
        self.validator = validator or RuleValidator()
        self.embedding_service = (
            embedding_service or EmbeddingService()
        )
        self.vector_store = (
            vector_store or ChromaStore()
        )

    def ingest(
        self,
        file_path: str | Path,
    ) -> dict[str, Any]:
        """
        Process and index a Rule Book.

        Supports:
            .txt
            .xlsx
        """

        path = Path(file_path)

        logger.info(
            "Starting Rule Book ingestion: %s",
            path.name,
        )

        # ==================================================
        # 1. Parse Rule Book
        # ==================================================

        raw_data = self.parser.parse(path)

        logger.info(
            "Rule Book parsed successfully: %s",
            path.suffix.lower(),
        )

        # ==================================================
        # 2. Convert raw data into rule records
        # ==================================================

        if path.suffix.lower() == ".txt":

            raw_rules = self.normalizer.normalize_txt(
                raw_data,
                source=path.name,
            )

        else:

            raw_rules = raw_data

        logger.info(
            "Prepared %d raw rules",
            len(raw_rules),
        )

        # ==================================================
        # 3. Normalize into Rule objects
        # ==================================================

        rules = self.normalizer.normalize(
            raw_rules,
            source=path.name,
        )

        logger.info(
            "Normalized %d rules",
            len(rules),
        )

        # ==================================================
        # 4. Validate rules
        # ==================================================

        self.validator.validate_or_raise(rules)

        logger.info(
            "Rule Book validation successful",
        )

        # ==================================================
        # 5. Create embedding text
        # ==================================================

        embedding_texts = [
            self._rule_to_text(rule)
            for rule in rules
        ]

        # ==================================================
        # 6. Generate embeddings
        # ==================================================

        embeddings = (
            self.embedding_service.embed_texts(
                embedding_texts
            )
        )

        logger.info(
            "Generated %d embeddings",
            len(embeddings),
        )

        # ==================================================
        # 7. Prepare ChromaDB records
        # ==================================================

        chroma_records = []

        for rule, embedding, text in zip(
            rules,
            embeddings,
            embedding_texts,
        ):

            chroma_records.append(
                {
                    "id": rule.rule_id,
                    "text": text,
                    "embedding": embedding,
                    "metadata": {
                        "rule_id": rule.rule_id,
                        "category": rule.category,
                        "rule_name": rule.rule_name,
                        "description": rule.description,
                        "validation_criteria": (
                            rule.validation_criteria
                        ),
                        "severity": rule.severity.value,
                        "mandatory": rule.mandatory,
                        "correction_instruction": (
                            rule.correction_instruction
                        ),
                        "source": rule.source or "",
                    },
                }
            )

        # ==================================================
        # 8. Store in ChromaDB
        # ==================================================

        self.vector_store.add_rules(
            chroma_records
        )

        logger.info(
            "Indexed %d rules in ChromaDB",
            len(chroma_records),
        )

        # ==================================================
        # 9. Return result
        # ==================================================

        return {
            "status": "success",
            "source": path.name,
            "total_rules": len(rules),
            "indexed_rules": len(chroma_records),
            "rules": [
                self._rule_to_dict(rule)
                for rule in rules
            ],
        }

    @staticmethod
    def _rule_to_text(rule: Any) -> str:
        """Convert a Rule object into embedding text."""

        return (
            f"Rule ID: {rule.rule_id}\n"
            f"Category: {rule.category}\n"
            f"Rule Name: {rule.rule_name}\n"
            f"Description: {rule.description}\n"
            f"Validation Criteria: "
            f"{rule.validation_criteria}\n"
            f"Severity: {rule.severity.value}\n"
            f"Mandatory: {rule.mandatory}\n"
            f"Correction Instruction: "
            f"{rule.correction_instruction}"
        )

    @staticmethod
    def _rule_to_dict(rule: Any) -> dict[str, Any]:
        """Convert a Rule object to a dictionary."""

        return {
            "rule_id": rule.rule_id,
            "category": rule.category,
            "rule_name": rule.rule_name,
            "description": rule.description,
            "validation_criteria": (
                rule.validation_criteria
            ),
            "severity": rule.severity.value,
            "mandatory": rule.mandatory,
            "correction_instruction": (
                rule.correction_instruction
            ),
            "source": rule.source,
        }