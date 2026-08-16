"""
LAURA - Validation Engine

Deterministic validation logic for NDA compliance.
Gemini provides rule-level analysis; this module determines
the application's final PASS/FAIL result.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from rules.rule_models import RiskLevel


class ValidationStatus(str, Enum):
    """Possible rule validation statuses."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_FOUND = "NOT_FOUND"
    UNCERTAIN = "UNCERTAIN"


class ValidationResult(BaseModel):
    """Validation result for a single Rule Book rule."""

    rule_id: str
    status: ValidationStatus

    risk: RiskLevel
    mandatory: bool

    nda_section: str | None = None
    page_number: int | None = None

    evidence: str = ""
    reason: str = ""
    required_change: str = ""

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class ValidationSummary(BaseModel):
    """Overall validation summary."""

    overall_status: ValidationStatus
    overall_risk: RiskLevel

    total_rules: int
    passed_rules: int
    failed_rules: int
    not_found_rules: int
    uncertain_rules: int

    high_risk_failures: int
    medium_risk_failures: int
    low_risk_failures: int

    mandatory_failures: int
    mandatory_not_found: int
    mandatory_uncertain: int


class ValidationEngine:
    """Determine deterministic NDA validation results."""

    def validate(
        self,
        results: list[ValidationResult],
    ) -> ValidationSummary:
        """
        Aggregate rule-level validation results.

        The overall status is determined by mandatory rules.
        """

        if not results:
            return ValidationSummary(
                overall_status=ValidationStatus.FAIL,
                overall_risk=RiskLevel.HIGH,
                total_rules=0,
                passed_rules=0,
                failed_rules=0,
                not_found_rules=0,
                uncertain_rules=0,
                high_risk_failures=0,
                medium_risk_failures=0,
                low_risk_failures=0,
                mandatory_failures=0,
                mandatory_not_found=0,
                mandatory_uncertain=0,
            )

        passed = sum(
            result.status == ValidationStatus.PASS
            for result in results
        )

        failed = sum(
            result.status == ValidationStatus.FAIL
            for result in results
        )

        not_found = sum(
            result.status == ValidationStatus.NOT_FOUND
            for result in results
        )

        uncertain = sum(
            result.status == ValidationStatus.UNCERTAIN
            for result in results
        )

        mandatory_failures = sum(
            result.mandatory
            and result.status == ValidationStatus.FAIL
            for result in results
        )

        mandatory_not_found = sum(
            result.mandatory
            and result.status == ValidationStatus.NOT_FOUND
            for result in results
        )

        mandatory_uncertain = sum(
            result.mandatory
            and result.status == ValidationStatus.UNCERTAIN
            for result in results
        )

        high_risk_failures = self._count_failures_by_risk(
            results,
            RiskLevel.HIGH,
        )

        medium_risk_failures = self._count_failures_by_risk(
            results,
            RiskLevel.MEDIUM,
        )

        low_risk_failures = self._count_failures_by_risk(
            results,
            RiskLevel.LOW,
        )

        overall_status = self._determine_overall_status(
            results
        )

        overall_risk = self._determine_overall_risk(
            results
        )

        return ValidationSummary(
            overall_status=overall_status,
            overall_risk=overall_risk,
            total_rules=len(results),
            passed_rules=passed,
            failed_rules=failed,
            not_found_rules=not_found,
            uncertain_rules=uncertain,
            high_risk_failures=high_risk_failures,
            medium_risk_failures=medium_risk_failures,
            low_risk_failures=low_risk_failures,
            mandatory_failures=mandatory_failures,
            mandatory_not_found=mandatory_not_found,
            mandatory_uncertain=mandatory_uncertain,
        )

    @staticmethod
    def _determine_overall_status(
        results: list[ValidationResult],
    ) -> ValidationStatus:
        """
        Determine overall NDA status.

        ALL mandatory rules must be PASS.
        """

        mandatory_results = [
            result
            for result in results
            if result.mandatory
        ]

        if not mandatory_results:
            return ValidationStatus.PASS

        if any(
            result.status != ValidationStatus.PASS
            for result in mandatory_results
        ):
            return ValidationStatus.FAIL

        return ValidationStatus.PASS

    @staticmethod
    def _determine_overall_risk(
        results: list[ValidationResult],
    ) -> RiskLevel:
        """
        Determine overall risk from unresolved rule results.

        HIGH takes precedence over MEDIUM, which takes
        precedence over LOW.
        """

        unresolved = [
            result
            for result in results
            if result.status
            in {
                ValidationStatus.FAIL,
                ValidationStatus.NOT_FOUND,
                ValidationStatus.UNCERTAIN,
            }
        ]

        if any(
            result.risk == RiskLevel.HIGH
            for result in unresolved
        ):
            return RiskLevel.HIGH

        if any(
            result.risk == RiskLevel.MEDIUM
            for result in unresolved
        ):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    @staticmethod
    def _count_failures_by_risk(
        results: list[ValidationResult],
        risk: RiskLevel,
    ) -> int:
        """Count failed rules for a specific risk level."""

        return sum(
            result.status == ValidationStatus.FAIL
            and result.risk == risk
            for result in results
        )