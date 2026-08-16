"""
LAURA - Validation Loop

Controls the NDA validation -> correction -> re-validation
workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from config.settings import settings
from validation.validation_engine import (
    ValidationEngine,
    ValidationResult,
    ValidationSummary,
)


@dataclass
class ValidationIteration:
    """Stores one complete validation iteration."""

    iteration: int
    results: list[ValidationResult]
    summary: ValidationSummary

    modifications: list[dict[str, Any]] = field(
        default_factory=list
    )


@dataclass
class ValidationWorkflowResult:
    """Final result of the validation workflow."""

    success: bool
    final_summary: ValidationSummary

    iterations: list[ValidationIteration] = field(
        default_factory=list
    )

    final_document_path: str | None = None


class ValidationLoop:
    """
    Coordinate validation and future correction/re-validation.
    """

    def __init__(
        self,
        validation_engine: ValidationEngine | None = None,
        max_iterations: int | None = None,
    ) -> None:

        self.validation_engine = (
            validation_engine
            or ValidationEngine()
        )

        self.max_iterations = (
            max_iterations
            or settings.max_validation_iterations
        )

    def evaluate(
        self,
        results: list[ValidationResult],
        iteration: int = 1,
    ) -> ValidationIteration:
        """
        Evaluate one validation iteration.
        """

        summary = self.validation_engine.validate(
            results
        )

        return ValidationIteration(
            iteration=iteration,
            results=results,
            summary=summary,
        )

    def is_compliant(
        self,
        summary: ValidationSummary,
    ) -> bool:
        """
        Return True only when every mandatory rule passes.
        """

        return (
            summary.overall_status.value == "PASS"
            and summary.mandatory_failures == 0
            and summary.mandatory_not_found == 0
            and summary.mandatory_uncertain == 0
        )

    def can_continue(
        self,
        current_iteration: int,
    ) -> bool:
        """Check whether another correction iteration is allowed."""

        return current_iteration < self.max_iterations

    def run(
        self,
        initial_results: list[ValidationResult],
        correction_callback: Callable[
            [list[ValidationResult], int],
            list[ValidationResult],
        ] | None = None,
    ) -> ValidationWorkflowResult:
        """
        Run validation and optional correction/re-validation.

        The correction callback will be connected to the
        correction engine later.

        Args:
            initial_results:
                Validation results for the original NDA.

            correction_callback:
                Function that receives failed results and
                iteration number and returns results for
                the corrected NDA.
        """

        iterations: list[ValidationIteration] = []

        current_results = initial_results

        for iteration_number in range(
            1,
            self.max_iterations + 1,
        ):

            iteration = self.evaluate(
                results=current_results,
                iteration=iteration_number,
            )

            iterations.append(iteration)

            if self.is_compliant(
                iteration.summary
            ):
                return ValidationWorkflowResult(
                    success=True,
                    final_summary=iteration.summary,
                    iterations=iterations,
                )

            if not self.can_continue(
                iteration_number
            ):
                break

            if correction_callback is None:
                break

            current_results = correction_callback(
                current_results,
                iteration_number,
            )

        final_iteration = iterations[-1]

        return ValidationWorkflowResult(
            success=False,
            final_summary=final_iteration.summary,
            iterations=iterations,
        )