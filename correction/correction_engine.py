"""
LAURA - Correction Engine

Generates clause-level corrections for NDA rules that
failed validation.
"""

from __future__ import annotations

import json
from typing import Any

from llm.correction_prompts import (
    CORRECTION_SYSTEM_PROMPT,
    build_correction_prompt,
)
from llm.gemini_client import GeminiClient
from utils.json_parser import parse_json_response
from validation.validation_engine import (
    ValidationResult,
    ValidationStatus,
)


class CorrectionEngine:
    """Generate corrections for failed NDA clauses."""

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.gemini_client = (
            gemini_client or GeminiClient()
        )

    def find_failed_rules(
        self,
        results: list[ValidationResult],
    ) -> list[ValidationResult]:
        """Return rules that require correction."""

        return [
            result
            for result in results
            if result.status
            in {
                ValidationStatus.FAIL,
                ValidationStatus.NOT_FOUND,
                ValidationStatus.UNCERTAIN,
            }
            and result.mandatory
        ]

    def generate_correction(
        self,
        validation_result: ValidationResult,
        original_clause: str,
        rule_context: str,
    ) -> dict[str, Any]:
        """
        Ask Gemini to generate a correction for one
        failed NDA clause.
        """

        if not original_clause.strip():
            raise ValueError(
                "Original NDA clause cannot be empty."
            )

        prompt = build_correction_prompt(
            original_clause=original_clause,
            rule_context=rule_context,
        )

        response = self.gemini_client.generate_text(
            prompt=(
                CORRECTION_SYSTEM_PROMPT
                + "\n\n"
                + prompt
            )
        )

        correction = parse_json_response(response)

        if not isinstance(correction, dict):
            raise ValueError(
                "Gemini correction response must be a JSON object."
            )

        return {
            "rule_id": validation_result.rule_id,
            "original_text": correction.get(
                "original_text",
                original_clause,
            ),
            "modified_text": correction.get(
                "modified_text",
                "",
            ),
            "reason": correction.get(
                "reason",
                validation_result.reason,
            ),
            "modification_type": correction.get(
                "modification_type",
                "CLAUSE_MODIFICATION",
            ),
            "nda_section": validation_result.nda_section,
            "page_number": validation_result.page_number,
        }

    def generate_corrections(
        self,
        failed_results: list[ValidationResult],
        clauses: dict[str, str],
        rule_contexts: dict[str, str],
    ) -> list[dict[str, Any]]:
        """
        Generate corrections for multiple failed rules.

        Args:
            failed_results:
                Failed mandatory validation results.

            clauses:
                Mapping of rule_id to original clause text.

            rule_contexts:
                Mapping of rule_id to Rule Book context.
        """

        corrections = []

        for result in failed_results:

            original_clause = clauses.get(
                result.rule_id,
                result.evidence,
            )

            rule_context = rule_contexts.get(
                result.rule_id,
                result.required_change,
            )

            correction = self.generate_correction(
                validation_result=result,
                original_clause=original_clause,
                rule_context=rule_context,
            )

            corrections.append(correction)

        return corrections