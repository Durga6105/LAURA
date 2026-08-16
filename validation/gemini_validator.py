"""
LAURA - Gemini Validator

Uses Gemini to validate NDA clauses against
Rule Book rules retrieved through RAG.

Supports:
- single-clause validation
- batched multi-clause validation
"""

from __future__ import annotations

from typing import Any

from llm.gemini_client import GeminiClient
from llm.validation_prompts import (
    VALIDATION_SYSTEM_PROMPT,
    build_validation_prompt,
)
from rag.context_builder import ContextBuilder
from utils.json_parser import parse_json_response
from validation.validation_engine import ValidationResult


class GeminiValidator:
    """Perform rule-level NDA validation using Gemini."""

    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule_id": {
                            "type": "string",
                        },
                        "clause_id": {
                            "type": "string",
                        },
                        "status": {
                            "type": "string",
                            "enum": [
                                "PASS",
                                "FAIL",
                                "NOT_FOUND",
                                "UNCERTAIN",
                            ],
                        },
                        "risk": {
                            "type": "string",
                            "enum": [
                                "LOW",
                                "MEDIUM",
                                "HIGH",
                            ],
                        },
                        "mandatory": {
                            "type": "boolean",
                        },
                        "nda_section": {
                            "type": "string",
                        },
                        "page_number": {
                            "type": "integer",
                        },
                        "evidence": {
                            "type": "string",
                        },
                        "reason": {
                            "type": "string",
                        },
                        "required_change": {
                            "type": "string",
                        },
                        "confidence": {
                            "type": "number",
                        },
                    },
                    "required": [
                        "rule_id",
                        "clause_id",
                        "status",
                        "risk",
                        "mandatory",
                        "nda_section",
                        "page_number",
                        "evidence",
                        "reason",
                        "required_change",
                        "confidence",
                    ],
                },
            },
        },
        "required": [
            "results",
        ],
    }

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:

        self.gemini_client = (
            gemini_client or GeminiClient()
        )

        self.context_builder = (
            context_builder or ContextBuilder()
        )

    # ======================================================
    # SINGLE CLAUSE VALIDATION
    # ======================================================

    def validate(
        self,
        clause: dict[str, Any],
        retrieved_rules: list[dict[str, Any]],
    ) -> list[ValidationResult]:
        """
        Validate one NDA clause against retrieved rules.

        Kept for compatibility with existing code.
        """

        if not clause.get(
            "text",
            "",
        ).strip():
            return []

        if not retrieved_rules:
            return []

        context = (
            self.context_builder.build_prompt_context(
                clause=clause,
                retrieved_rules=retrieved_rules,
            )
        )

        response = self._generate(
            context
        )

        data = parse_json_response(
            response
        )

        if not isinstance(data, dict):
            raise ValueError(
                "Gemini validation response "
                "must be an object."
            )

        raw_results = data.get(
            "results",
            [],
        )

        if not isinstance(
            raw_results,
            list,
        ):
            raise ValueError(
                "Gemini validation 'results' "
                "must be a list."
            )

        return [
            self._to_validation_result(
                item=item,
                clause=clause,
                retrieved_rules=retrieved_rules,
            )
            for item in raw_results
        ]

    # ======================================================
    # BATCH VALIDATION
    # ======================================================

    def validate_clauses(
        self,
        clauses_with_rules: list[dict[str, Any]],
    ) -> list[ValidationResult]:
        """
        Validate multiple NDA clauses using ONE Gemini request.

        Args:
            clauses_with_rules:
                List containing:

                {
                    "clause": {...},
                    "retrieved_rules": [...]
                }

        Returns:
            Validation results for all returned rules.
        """

        if not clauses_with_rules:
            return []

        contexts: list[str] = []

        # --------------------------------------------------
        # Lookups used after Gemini responds.
        # --------------------------------------------------

        rule_lookup: dict[
            str,
            dict[str, Any],
        ] = {}

        clause_lookup: dict[
            str,
            dict[str, Any],
        ] = {}

        # --------------------------------------------------
        # Build context for every clause.
        # --------------------------------------------------

        for item in clauses_with_rules:

            clause = item.get(
                "clause",
                {},
            )

            retrieved_rules = item.get(
                "retrieved_rules",
                [],
            )

            if not clause.get(
                "text",
                "",
            ).strip():
                continue

            if not retrieved_rules:
                continue

            clause_id = str(
                clause.get(
                    "clause_id",
                    "",
                )
            ).strip()

            if not clause_id:
                raise ValueError(
                    "NDA clause is missing clause_id."
                )

            clause_lookup[
                clause_id
            ] = clause

            # --------------------------------------------------
            # Store Rule Book metadata.
            # --------------------------------------------------

            for rule in retrieved_rules:

                metadata = rule.get(
                    "metadata",
                    {},
                )

                rule_id = str(
                    metadata.get(
                        "rule_id",
                        rule.get(
                            "id",
                            "",
                        ),
                    )
                ).strip()

                if rule_id:
                    rule_lookup[
                        rule_id
                    ] = rule

            # --------------------------------------------------
            # Build readable Gemini context.
            # --------------------------------------------------

            context = (
                self.context_builder.build_prompt_context(
                    clause=clause,
                    retrieved_rules=retrieved_rules,
                )
            )

            contexts.append(
                context
            )

        if not contexts:
            return []

        # --------------------------------------------------
        # Combine all clauses into ONE prompt.
        # --------------------------------------------------

        combined_context = (
            "\n\n".join(
                [
                    (
                        f"========== NDA CLAUSE GROUP "
                        f"{index} ==========\n"
                        f"{context}"
                    )
                    for index, context in enumerate(
                        contexts,
                        start=1,
                    )
                ]
            )
        )

        # --------------------------------------------------
        # ONE Gemini request.
        # --------------------------------------------------

        response = self._generate(
            combined_context
        )

        data = parse_json_response(
            response
        )

        if not isinstance(data, dict):
            raise ValueError(
                "Gemini validation response "
                "must be an object."
            )

        raw_results = data.get(
            "results",
            [],
        )

        if not isinstance(
            raw_results,
            list,
        ):
            raise ValueError(
                "Gemini validation 'results' "
                "must be a list."
            )

        results: list[
            ValidationResult
        ] = []

        # --------------------------------------------------
        # Convert Gemini results.
        # --------------------------------------------------

        for item in raw_results:

            rule_id = str(
                item.get(
                    "rule_id",
                    "",
                )
            ).strip()

            if not rule_id:
                raise ValueError(
                    "Gemini returned an empty rule_id."
                )

            if rule_id not in rule_lookup:
                raise ValueError(
                    "Gemini returned unknown "
                    f"rule_id: {rule_id}"
                )

            clause_id = str(
                item.get(
                    "clause_id",
                    "",
                )
            ).strip()

            if not clause_id:
                raise ValueError(
                    "Gemini returned no clause_id "
                    f"for rule: {rule_id}"
                )

            if clause_id not in clause_lookup:
                raise ValueError(
                    "Gemini returned unknown "
                    f"clause_id: {clause_id}"
                )

            clause = clause_lookup[
                clause_id
            ]

            matching_rule = rule_lookup[
                rule_id
            ]

            results.append(
                self._to_validation_result(
                    item=item,
                    clause=clause,
                    retrieved_rules=[
                        matching_rule
                    ],
                )
            )

        return results

    # ======================================================
    # GEMINI REQUEST
    # ======================================================

    def _generate(
        self,
        context: str,
    ) -> str:
        """Send one validation request to Gemini."""

        prompt = build_validation_prompt(
            context
        )

        return self.gemini_client.generate_json(
            prompt=prompt,
            response_schema=self.RESPONSE_SCHEMA,
            system_instruction=(
                VALIDATION_SYSTEM_PROMPT
            ),
        )

    # ======================================================
    # VALIDATION RESULT CONVERSION
    # ======================================================

    @staticmethod
    def _to_validation_result(
        item: dict[str, Any],
        clause: dict[str, Any],
        retrieved_rules: list[dict[str, Any]],
    ) -> ValidationResult:
        """
        Convert Gemini output into ValidationResult.

        Rule Book remains authoritative for:

        - risk
        - mandatory status

        Gemini provides:

        - status
        - evidence
        - reason
        - required change
        - confidence
        """

        rule_id = str(
            item.get(
                "rule_id",
                "",
            )
        ).strip()

        if not rule_id:
            raise ValueError(
                "Gemini returned an empty rule_id."
            )

        # --------------------------------------------------
        # Find Rule Book rule.
        # --------------------------------------------------

        matching_rule = None

        for rule in retrieved_rules:

            metadata = rule.get(
                "metadata",
                {},
            )

            stored_rule_id = str(
                metadata.get(
                    "rule_id",
                    rule.get(
                        "id",
                        "",
                    ),
                )
            ).strip()

            if stored_rule_id == rule_id:
                matching_rule = rule
                break

        if matching_rule is None:
            raise ValueError(
                f"Gemini returned unknown "
                f"rule_id: {rule_id}"
            )

        metadata = matching_rule.get(
            "metadata",
            {},
        )

        # --------------------------------------------------
        # Rule Book is authoritative.
        # --------------------------------------------------

        risk = metadata.get(
            "severity",
            "MEDIUM",
        )

        mandatory = metadata.get(
            "mandatory",
            True,
        )

        # --------------------------------------------------
        # Gemini analysis.
        # --------------------------------------------------

        status = item.get(
            "status",
            "UNCERTAIN",
        )

        evidence = item.get(
            "evidence",
            "",
        )

        reason = item.get(
            "reason",
            "",
        )

        required_change = item.get(
            "required_change",
            "",
        )

        confidence = item.get(
            "confidence",
            None,
        )

        # --------------------------------------------------
        # Clause metadata comes from the actual NDA clause.
        # --------------------------------------------------

        return ValidationResult(
            rule_id=rule_id,
            status=status,
            risk=risk,
            mandatory=mandatory,
            nda_section=clause.get(
                "section"
            ),
            page_number=clause.get(
                "page_number"
            ),
            evidence=evidence,
            reason=reason,
            required_change=required_change,
            confidence=confidence,
        )