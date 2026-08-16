"""
LAURA - Follow-up Q&A Engine

Answers user questions using the current NDA analysis
context, Rule Book, validation results, and modification history.
"""

from __future__ import annotations

from typing import Any

from llm.gemini_client import GeminiClient
from llm.qa_prompts import (
    QA_SYSTEM_PROMPT,
    build_qa_prompt,
)


class QAEngine:
    """Handle grounded follow-up questions."""

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.gemini_client = (
            gemini_client or GeminiClient()
        )

    def answer(
        self,
        question: str,
        context: str,
    ) -> str:
        """
        Answer a user question using supplied analysis context.

        Args:
            question: User's follow-up question.
            context: Relevant analysis context.

        Returns:
            Grounded answer from Gemini.
        """

        if not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        if not context.strip():
            raise ValueError(
                "Q&A context cannot be empty."
            )

        prompt = build_qa_prompt(
            question=question,
            context=context,
        )

        return self.gemini_client.generate_text(
            prompt=prompt,
            system_instruction=QA_SYSTEM_PROMPT,
        )

    def build_analysis_context(
        self,
        rule_book_rules: list[dict[str, Any]] | None = None,
        original_clauses: list[dict[str, Any]] | None = None,
        final_clauses: list[dict[str, Any]] | None = None,
        validation_results: list[dict[str, Any]] | None = None,
        modification_history: list[dict[str, Any]] | None = None,
        validation_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Build a complete context string for follow-up questions.
        """

        sections: list[str] = []

        sections.append(
            self._format_rules(
                rule_book_rules or []
            )
        )

        sections.append(
            self._format_original_clauses(
                original_clauses or []
            )
        )

        sections.append(
            self._format_final_clauses(
                final_clauses or []
            )
        )

        sections.append(
            self._format_validation_results(
                validation_results or []
            )
        )

        sections.append(
            self._format_modifications(
                modification_history or []
            )
        )

        sections.append(
            self._format_validation_history(
                validation_history or []
            )
        )

        return "\n\n".join(
            section
            for section in sections
            if section.strip()
        )

    @staticmethod
    def _format_rules(
        rules: list[dict[str, Any]],
    ) -> str:
        """Format Rule Book rules."""

        if not rules:
            return ""

        lines = [
            "RULE BOOK",
            "=========",
        ]

        for rule in rules:
            lines.extend(
                [
                    "",
                    f"Rule ID: {rule.get('rule_id', '')}",
                    f"Category: {rule.get('category', '')}",
                    f"Rule Name: {rule.get('rule_name', '')}",
                    f"Description: {rule.get('description', '')}",
                    (
                        "Validation Criteria: "
                        f"{rule.get('validation_criteria', '')}"
                    ),
                    f"Risk: {rule.get('severity', '')}",
                    f"Mandatory: {rule.get('mandatory', '')}",
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _format_original_clauses(
        clauses: list[dict[str, Any]],
    ) -> str:
        """Format original NDA clauses."""

        if not clauses:
            return ""

        lines = [
            "ORIGINAL NDA",
            "============",
        ]

        for clause in clauses:
            lines.extend(
                [
                    "",
                    f"Clause ID: {clause.get('clause_id', '')}",
                    f"Section: {clause.get('section', '')}",
                    f"Page: {clause.get('page_number', '')}",
                    f"Text: {clause.get('text', '')}",
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _format_final_clauses(
        clauses: list[dict[str, Any]],
    ) -> str:
        """Format final NDA clauses."""

        if not clauses:
            return ""

        lines = [
            "FINAL NDA",
            "=========",
        ]

        for clause in clauses:
            lines.extend(
                [
                    "",
                    f"Clause ID: {clause.get('clause_id', '')}",
                    f"Section: {clause.get('section', '')}",
                    f"Page: {clause.get('page_number', '')}",
                    f"Text: {clause.get('text', '')}",
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _format_validation_results(
        results: list[dict[str, Any]],
    ) -> str:
        """Format validation results."""

        if not results:
            return ""

        lines = [
            "VALIDATION RESULTS",
            "==================",
        ]

        for result in results:
            lines.extend(
                [
                    "",
                    f"Rule ID: {result.get('rule_id', '')}",
                    f"Status: {result.get('status', '')}",
                    f"Risk: {result.get('risk', '')}",
                    f"Mandatory: {result.get('mandatory', '')}",
                    f"Section: {result.get('nda_section', '')}",
                    f"Page: {result.get('page_number', '')}",
                    f"Evidence: {result.get('evidence', '')}",
                    f"Reason: {result.get('reason', '')}",
                    (
                        "Required Change: "
                        f"{result.get('required_change', '')}"
                    ),
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _format_modifications(
        modifications: list[dict[str, Any]],
    ) -> str:
        """Format NDA modification history."""

        if not modifications:
            return ""

        lines = [
            "MODIFICATION HISTORY",
            "====================",
        ]

        for modification in modifications:
            lines.extend(
                [
                    "",
                    f"Rule ID: {modification.get('rule_id', '')}",
                    (
                        "Original Text: "
                        f"{modification.get('original_text', '')}"
                    ),
                    (
                        "Modified Text: "
                        f"{modification.get('modified_text', '')}"
                    ),
                    (
                        "Reason: "
                        f"{modification.get('reason', '')}"
                    ),
                    (
                        "Modification Type: "
                        f"{modification.get('modification_type', '')}"
                    ),
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _format_validation_history(
        history: list[dict[str, Any]],
    ) -> str:
        """Format previous validation iterations."""

        if not history:
            return ""

        lines = [
            "RE-VALIDATION HISTORY",
            "=====================",
        ]

        for item in history:
            lines.extend(
                [
                    "",
                    f"Iteration: {item.get('iteration', '')}",
                    f"Status: {item.get('status', '')}",
                    f"Risk: {item.get('risk', '')}",
                    (
                        "Passed Rules: "
                        f"{item.get('passed_rules', '')}"
                    ),
                    (
                        "Failed Rules: "
                        f"{item.get('failed_rules', '')}"
                    ),
                ]
            )

        return "\n".join(lines)