"""
LAURA - Rule Validator

Validates normalized Rule objects before they enter
the RAG and validation pipeline.
"""

from rules.rule_models import Rule


class RuleValidationError(ValueError):
    """Raised when a Rule Book contains invalid rules."""


class RuleValidator:
    """Validate normalized Rule objects."""

    def validate(self, rules: list[Rule]) -> list[str]:
        """
        Validate a list of rules.

        Returns:
            List of validation errors.
        """

        errors: list[str] = []

        if not rules:
            errors.append("Rule Book contains no valid rules.")
            return errors

        seen_rule_ids: set[str] = set()

        for index, rule in enumerate(rules, start=1):

            if rule.rule_id in seen_rule_ids:
                errors.append(
                    f"Duplicate rule ID: {rule.rule_id}"
                )

            seen_rule_ids.add(rule.rule_id)

            if not rule.description.strip():
                errors.append(
                    f"{rule.rule_id}: Missing description."
                )

            if not rule.validation_criteria.strip():
                errors.append(
                    f"{rule.rule_id}: Missing validation criteria."
                )

            if not rule.correction_instruction.strip():
                errors.append(
                    f"{rule.rule_id}: Missing correction instruction."
                )

            if not rule.category.strip():
                errors.append(
                    f"{rule.rule_id}: Missing category."
                )

            if not rule.rule_name.strip():
                errors.append(
                    f"{rule.rule_id}: Missing rule name."
                )

        return errors

    def validate_or_raise(self, rules: list[Rule]) -> None:
        """Validate rules and raise an exception if invalid."""

        errors = self.validate(rules)

        if errors:
            raise RuleValidationError(
                "Invalid Rule Book:\n"
                + "\n".join(f"- {error}" for error in errors)
            )