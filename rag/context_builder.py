"""
LAURA - RAG Context Builder

Builds structured context from NDA clauses and
retrieved Rule Book rules for Gemini.
"""

from __future__ import annotations

from typing import Any


class ContextBuilder:
    """Build LLM-ready validation context."""

    def build_validation_context(
        self,
        clause: dict[str, Any],
        retrieved_rules: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build context for validating an NDA clause.
        """

        return {
            "nda_clause": {
                "clause_id": clause.get("clause_id"),
                "section": clause.get("section"),
                "page_number": clause.get("page_number"),
                "paragraph_number": clause.get(
                    "paragraph_number"
                ),
                "text": clause.get("text", ""),
            },
            "rules": [
                self._format_rule(rule)
                for rule in retrieved_rules
            ],
        }

    def build_prompt_context(
        self,
        clause: dict[str, Any],
        retrieved_rules: list[dict[str, Any]],
    ) -> str:
        """
        Build a readable text context for Gemini.
        """

        context = self.build_validation_context(
            clause,
            retrieved_rules,
        )

        clause_data = context["nda_clause"]

        lines = [
            "NDA CLAUSE",
            "==========",
            f"Clause ID: {clause_data['clause_id']}",
            f"Section: {clause_data['section']}",
            f"Page: {clause_data['page_number']}",
            "",
            "Clause Text:",
            clause_data["text"],
            "",
            "RELEVANT RULE BOOK RULES",
            "=========================",
        ]

        if not context["rules"]:
            lines.append(
                "No relevant Rule Book rules were retrieved."
            )
        else:
            for index, rule in enumerate(
                context["rules"],
                start=1,
            ):
                lines.extend(
                    [
                        "",
                        f"Rule {index}",
                        f"Rule ID: {rule['rule_id']}",
                        f"Category: {rule['category']}",
                        f"Rule Name: {rule['rule_name']}",
                        f"Description: {rule['description']}",
                        (
                            "Validation Criteria: "
                            f"{rule['validation_criteria']}"
                        ),
                        f"Risk: {rule['severity']}",
                        f"Mandatory: {rule['mandatory']}",
                        (
                            "Correction Instruction: "
                            f"{rule['correction_instruction']}"
                        ),
                    ]
                )

        return "\n".join(lines)

    @staticmethod
    def _format_rule(
        rule: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize a retrieved Chroma rule."""

        metadata = rule.get("metadata", {})

        return {
            "rule_id": metadata.get(
                "rule_id",
                rule.get("id"),
            ),
            "category": metadata.get(
                "category",
                "",
            ),
            "rule_name": metadata.get(
                "rule_name",
                "",
            ),
            "description": metadata.get(
                "description",
                rule.get("text", ""),
            ),
            "validation_criteria": metadata.get(
                "validation_criteria",
                "",
            ),
            "severity": metadata.get(
                "severity",
                "MEDIUM",
            ),
            "mandatory": metadata.get(
                "mandatory",
                True,
            ),
            "correction_instruction": metadata.get(
                "correction_instruction",
                "",
            ),
            "similarity_distance": rule.get(
                "distance"
            ),
        }