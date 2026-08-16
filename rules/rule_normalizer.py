"""
LAURA - Rule Normalizer

Converts raw Rule Book data into normalized Rule objects.
"""

from typing import Any

from rules.rule_models import RiskLevel, Rule


class RuleNormalizer:
    """Normalize raw Rule Book records."""

    FIELD_ALIASES = {
        "rule_id": [
            "rule_id",
            "ruleid",
            "rule",
            "id",
        ],
        "category": [
            "category",
            "type",
        ],
        "rule_name": [
            "rule_name",
            "rulename",
            "name",
        ],
        "description": [
            "description",
            "rule_description",
        ],
        "validation_criteria": [
            "validation_criteria",
            "validationcriteria",
            "criteria",
        ],
        "severity": [
            "severity",
            "risk",
            "risk_level",
        ],
        "mandatory": [
            "mandatory",
            "required",
        ],
        "correction_instruction": [
            "correction_instruction",
            "correctioninstruction",
            "correction",
            "recommendation",
        ],
    }

    def normalize(
        self,
        raw_rules: list[dict[str, Any]],
        source: str | None = None,
    ) -> list[Rule]:
        """
        Normalize raw Rule Book records.

        Args:
            raw_rules: Raw records from the Rule Book.
            source: Source Rule Book filename.

        Returns:
            List of normalized Rule objects.
        """

        normalized_rules = []

        for index, raw_rule in enumerate(raw_rules, start=1):

            normalized = self._normalize_record(raw_rule)

            normalized.setdefault(
                "rule_id",
                f"RULE-{index:04d}",
            )

            normalized.setdefault(
                "category",
                "General",
            )

            normalized.setdefault(
                "rule_name",
                normalized["rule_id"],
            )

            normalized.setdefault(
                "description",
                "",
            )

            normalized.setdefault(
                "validation_criteria",
                normalized["description"],
            )

            normalized.setdefault(
                "severity",
                "MEDIUM",
            )

            normalized.setdefault(
                "mandatory",
                True,
            )

            normalized.setdefault(
                "correction_instruction",
                "Review and modify the clause to satisfy the rule.",
            )

            normalized["severity"] = self._normalize_severity(
                normalized["severity"]
            )

            normalized["mandatory"] = self._normalize_boolean(
                normalized["mandatory"]
            )

            normalized["source"] = source

            normalized_rules.append(
                Rule(**normalized)
            )

        return normalized_rules

    def normalize_txt(
        self,
        text: str,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Prepare TXT content for rule normalization.

        TXT rule extraction will initially treat separated
        non-empty blocks as individual raw rules.

        More advanced natural-language extraction can be
        added later using Gemini.
        """

        blocks = [
            block.strip()
            for block in text.split("\n\n")
            if block.strip()
        ]

        return [
            {
                "rule_id": f"RULE-{index:04d}",
                "category": "General",
                "rule_name": f"Rule {index}",
                "description": block,
                "validation_criteria": block,
                "severity": "MEDIUM",
                "mandatory": True,
                "correction_instruction": (
                    "Modify the NDA clause to satisfy this rule."
                ),
            }
            for index, block in enumerate(blocks, start=1)
        ]

    def _normalize_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize field names."""

        normalized = {}

        cleaned_record = {
            str(key).strip().lower().replace(" ", "_"): value
            for key, value in record.items()
        }

        for target_field, aliases in self.FIELD_ALIASES.items():

            for alias in aliases:

                if alias in cleaned_record:
                    value = cleaned_record[alias]

                    if value is not None and str(value).strip():
                        normalized[target_field] = value
                        break

        return normalized

    @staticmethod
    def _normalize_severity(value: Any) -> RiskLevel:
        """Normalize severity values."""

        if value is None:
            return RiskLevel.MEDIUM

        value = str(value).strip().upper()

        if value in {"HIGH", "CRITICAL", "SEVERE"}:
            return RiskLevel.HIGH

        if value in {"LOW", "MINOR"}:
            return RiskLevel.LOW

        return RiskLevel.MEDIUM

    @staticmethod
    def _normalize_boolean(value: Any) -> bool:
        """Normalize boolean values."""

        if isinstance(value, bool):
            return value

        value = str(value).strip().lower()

        return value in {
            "true",
            "yes",
            "y",
            "1",
            "mandatory",
            "required",
        }