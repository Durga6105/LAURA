"""
LAURA - NDA Validator

Validates an entire NDA document against the Rule Book
using RAG retrieval and Gemini rule-level validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rag.retriever import RAGRetriever
from validation.gemini_validator import GeminiValidator
from validation.validation_engine import (
    ValidationEngine,
    ValidationResult,
    ValidationSummary,
)


@dataclass
class ClauseValidation:
    """Validation results for one NDA clause."""

    clause_id: str
    section: str | None
    page_number: int | None

    results: list[ValidationResult] = field(
        default_factory=list
    )


@dataclass
class NDAValidationResult:
    """Complete validation result for an NDA."""

    success: bool

    file_name: str | None

    summary: ValidationSummary

    clause_results: list[ClauseValidation] = field(
        default_factory=list
    )

    all_results: list[ValidationResult] = field(
        default_factory=list
    )


class NDAValidator:
    """
    Validate a complete NDA against the Rule Book.

    Pipeline:

        NDA clauses
            ↓
        RAG retrieval
            ↓
        ONE Gemini batch validation
            ↓
        ValidationEngine
            ↓
        Final NDA result
    """

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        gemini_validator: GeminiValidator | None = None,
        validation_engine: ValidationEngine | None = None,
        rules_per_clause: int = 5,
    ) -> None:

        self.retriever = (
            retriever
            or RAGRetriever()
        )

        self.gemini_validator = (
            gemini_validator
            or GeminiValidator()
        )

        self.validation_engine = (
            validation_engine
            or ValidationEngine()
        )

        self.rules_per_clause = (
            rules_per_clause
        )

    def validate(
        self,
        clauses: list[dict[str, Any]],
        file_name: str | None = None,
    ) -> NDAValidationResult:
        """
        Validate all NDA clauses.

        Rule retrieval happens for every clause first.
        Gemini is then called exactly once for the batch.
        """

        if not clauses:
            raise ValueError(
                "Cannot validate NDA with no clauses."
            )

        # --------------------------------------------------
        # Store clause metadata.
        # --------------------------------------------------

        clause_map: dict[
            str,
            ClauseValidation,
        ] = {}

        clauses_with_rules: list[
            dict[str, Any]
        ] = []

        # --------------------------------------------------
        # 1. Retrieve Rule Book rules.
        #
        # No Gemini request happens here.
        # --------------------------------------------------

        for clause in clauses:

            clause_id = str(
                clause.get(
                    "clause_id",
                    "",
                )
            ).strip()

            if not clause_id:
                continue

            clause_text = str(
                clause.get(
                    "text",
                    "",
                )
            ).strip()

            if not clause_text:
                continue

            clause_validation = (
                ClauseValidation(
                    clause_id=clause_id,
                    section=clause.get(
                        "section"
                    ),
                    page_number=clause.get(
                        "page_number"
                    ),
                    results=[],
                )
            )

            clause_map[
                clause_id
            ] = clause_validation

            retrieved_rules = (
                self.retriever.retrieve_for_clause(
                    clause=clause,
                    n_results=self.rules_per_clause,
                )
            )

            if not retrieved_rules:
                continue

            clauses_with_rules.append(
                {
                    "clause": clause,
                    "retrieved_rules": retrieved_rules,
                }
            )

        # --------------------------------------------------
        # 2. ONE Gemini batch request.
        # --------------------------------------------------

        all_results: list[
            ValidationResult
        ] = []

        if clauses_with_rules:

            all_results = (
                self.gemini_validator.validate_clauses(
                    clauses_with_rules
                )
            )

        # --------------------------------------------------
        # 3. Attach results to the correct clause.
        #
        # GeminiValidator uses clause_id internally to
        # select the correct clause before creating the
        # ValidationResult.
        #
        # We use section/page as a fallback because
        # ValidationResult intentionally does not expose
        # clause_id.
        # --------------------------------------------------

        for result in all_results:

            matched_clause = None

            for clause_validation in (
                clause_map.values()
            ):

                if (
                    clause_validation.section
                    == result.nda_section
                    and clause_validation.page_number
                    == result.page_number
                ):
                    matched_clause = (
                        clause_validation
                    )
                    break

            if matched_clause is not None:
                matched_clause.results.append(
                    result
                )

        # --------------------------------------------------
        # 4. Aggregate deterministic validation.
        # --------------------------------------------------

        summary = (
            self.validation_engine.validate(
                all_results
            )
        )

        success = self._is_compliant(
            summary
        )

        return NDAValidationResult(
            success=success,
            file_name=file_name,
            summary=summary,
            clause_results=list(
                clause_map.values()
            ),
            all_results=all_results,
        )

    @staticmethod
    def _is_compliant(
        summary: ValidationSummary,
    ) -> bool:
        """
        Determine whether the complete NDA is compliant.

        A document is compliant only when:

        - overall status is PASS
        - no mandatory failures
        - no mandatory NOT_FOUND results
        - no mandatory UNCERTAIN results
        """

        return (
            summary.overall_status.value
            == "PASS"
            and summary.mandatory_failures
            == 0
            and summary.mandatory_not_found
            == 0
            and summary.mandatory_uncertain
            == 0
        )