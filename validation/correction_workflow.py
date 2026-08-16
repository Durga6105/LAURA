"""
LAURA - Correction Workflow

Complete NDA workflow:

NDA
    ↓
Initial validation
    ↓
Failed rules
    ↓
Correction generation
    ↓
Corrected NDA
    ↓
Re-ingestion
    ↓
Re-validation
    ↓
PDF report
    ↓
Final result

The workflow does not permanently store NDA files.

The caller provides the output directory, which in
production will be a temporary directory managed by
the API layer.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from correction.correction_engine import CorrectionEngine
from correction.document_modifier import DocumentModifier
from ingestion.nda_service import NDAIngestionService
from reporting.report_generator import ReportGenerator
from validation.nda_validator import (
    NDAValidator,
    NDAValidationResult,
)
from validation.validation_engine import (
    ValidationResult,
)


@dataclass
class CorrectionWorkflowResult:
    """Complete correction, validation and reporting result."""

    original_file: str
    corrected_file: str | None
    report_file: str | None

    original_validation: NDAValidationResult
    final_validation: NDAValidationResult

    corrections: list[dict[str, Any]]

    success: bool


class CorrectionWorkflow:
    """Complete NDA correction workflow."""

    def __init__(
        self,
        ingestion_service: NDAIngestionService | None = None,
        validator: NDAValidator | None = None,
        correction_engine: CorrectionEngine | None = None,
        document_modifier: DocumentModifier | None = None,
        report_generator: ReportGenerator | None = None,
        output_directory: str | Path | None = None,
    ) -> None:

        self.ingestion_service = (
            ingestion_service
            or NDAIngestionService()
        )

        self.validator = (
            validator
            or NDAValidator()
        )

        self.correction_engine = (
            correction_engine
            or CorrectionEngine()
        )

        self.document_modifier = (
            document_modifier
            or DocumentModifier()
        )

        self.report_generator = (
            report_generator
            or ReportGenerator()
        )

        self.output_directory = (
            Path(output_directory)
            if output_directory is not None
            else None
        )

    # ======================================================
    # MAIN WORKFLOW
    # ======================================================

    def run(
        self,
        input_path: str | Path,
        progress_callback: Callable[
            [str, str, int],
            None,
        ] | None = None,
    ) -> CorrectionWorkflowResult:
        """
        Run the complete NDA validation workflow.

        progress_callback, when provided, receives:
            (stage, message, progress)

        The callback is optional so existing callers continue
        to work without any changes.
        """

        def update_progress(
            stage: str,
            message: str,
            progress: int,
        ) -> None:
            if progress_callback is not None:
                progress_callback(
                    stage,
                    message,
                    progress,
                )

        source = Path(input_path)

        if not source.exists():
            raise FileNotFoundError(
                f"NDA not found: {source}"
            )

        if self.output_directory is None:
            raise ValueError(
                "output_directory must be provided. "
                "Use a temporary directory in production."
            )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        # --------------------------------------------------
        # 1. INGEST ORIGINAL NDA
        # --------------------------------------------------

        update_progress(
            "ingestion",
            "Ingesting NDA and extracting clauses.",
            20,
        )

        ingestion = self.ingestion_service.ingest(
            source
        )

        clauses = ingestion.get(
            "clause_data",
            [],
        )

        if not clauses:
            raise ValueError(
                "No clause data was extracted from the NDA."
            )

        # --------------------------------------------------
        # 2. INITIAL VALIDATION
        # --------------------------------------------------

        update_progress(
            "rule_book_retrieval",
            "Retrieving Rule Book requirements.",
            35,
        )

        update_progress(
            "validation",
            "Validating NDA against the Rule Book.",
            45,
        )

        original_validation = (
            self.validator.validate(
                clauses=clauses,
                file_name=source.name,
            )
        )

        # --------------------------------------------------
        # 3. IF ALREADY COMPLIANT
        # --------------------------------------------------

        if original_validation.success:

            update_progress(
                "completed",
                "NDA already satisfies the Rule Book.",
                100,
            )

            # Even when no correction is required,
            # create a corrected copy so the API can always
            # provide a corrected NDA download.

            corrected_path = (
                self._build_corrected_path(
                    source
                )
            )

            shutil.copy2(
                source,
                corrected_path,
            )

            report_path = (
                self._build_report_path(
                    source
                )
            )

            self._generate_report(
                source_name=source.name,
                original_validation=original_validation,
                final_validation=original_validation,
                corrections=[],
                report_path=report_path,
            )

            return CorrectionWorkflowResult(
                original_file=str(source),
                corrected_file=str(
                    corrected_path
                ),
                report_file=str(
                    report_path
                ),
                original_validation=(
                    original_validation
                ),
                final_validation=(
                    original_validation
                ),
                corrections=[],
                success=True,
            )

        # --------------------------------------------------
        # 4. FIND FAILED RULES
        # --------------------------------------------------

        update_progress(
            "correction",
            "Identifying failed rules and preparing corrections.",
            60,
        )

        failed_results = (
            self.correction_engine.find_failed_rules(
                original_validation.all_results
            )
        )

        if not failed_results:

            report_path = (
                self._build_report_path(
                    source
                )
            )

            self._generate_report(
                source_name=source.name,
                original_validation=original_validation,
                final_validation=original_validation,
                corrections=[],
                report_path=report_path,
            )

            return CorrectionWorkflowResult(
                original_file=str(source),
                corrected_file=None,
                report_file=str(
                    report_path
                ),
                original_validation=(
                    original_validation
                ),
                final_validation=(
                    original_validation
                ),
                corrections=[],
                success=False,
            )

        # --------------------------------------------------
        # 5. BUILD CLAUSE MAPPING
        # --------------------------------------------------

        clause_mapping = (
            self._build_clause_mapping(
                clauses
            )
        )

        # --------------------------------------------------
        # 6. BUILD RULE CONTEXT
        # --------------------------------------------------

        rule_context_mapping = (
            self._build_rule_context_mapping(
                failed_results
            )
        )

        # --------------------------------------------------
        # 7. GENERATE CORRECTIONS
        # --------------------------------------------------

        update_progress(
            "correction",
            "Generating corrections for failed requirements.",
            68,
        )

        corrections = (
            self.correction_engine.generate_corrections(
                failed_results=failed_results,
                clauses=clause_mapping,
                rule_contexts=rule_context_mapping,
            )
        )

        if not corrections:
            raise ValueError(
                "No corrections were generated."
            )

        # --------------------------------------------------
        # 8. CORRECTED FILE PATH
        # --------------------------------------------------

        corrected_path = (
            self._build_corrected_path(
                source
            )
        )

        # --------------------------------------------------
        # 9. APPLY CORRECTIONS
        # --------------------------------------------------

        update_progress(
            "correction",
            "Applying corrections to the NDA.",
            75,
        )

        self.document_modifier.modify(
            input_path=source,
            modifications=corrections,
            output_path=corrected_path,
        )

        # --------------------------------------------------
        # 10. RE-INGEST CORRECTED NDA
        # --------------------------------------------------

        update_progress(
            "revalidation",
            "Re-ingesting the corrected NDA.",
            82,
        )

        corrected_ingestion = (
            self.ingestion_service.ingest(
                corrected_path
            )
        )

        corrected_clauses = (
            corrected_ingestion.get(
                "clause_data",
                [],
            )
        )

        if not corrected_clauses:
            raise ValueError(
                "No clauses found in corrected NDA."
            )

        # --------------------------------------------------
        # 11. RE-VALIDATE
        # --------------------------------------------------

        update_progress(
            "revalidation",
            "Re-validating the corrected NDA.",
            88,
        )

        final_validation = (
            self.validator.validate(
                clauses=corrected_clauses,
                file_name=corrected_path.name,
            )
        )

        # --------------------------------------------------
        # 12. GENERATE PDF REPORT
        # --------------------------------------------------

        report_path = (
            self._build_report_path(
                source
            )
        )

        update_progress(
            "report_generation",
            "Generating the final PDF analysis report.",
            95,
        )

        self._generate_report(
            source_name=source.name,
            original_validation=original_validation,
            final_validation=final_validation,
            corrections=corrections,
            report_path=report_path,
        )

        # --------------------------------------------------
        # 13. RETURN FINAL RESULT
        # --------------------------------------------------

        update_progress(
            "completed",
            "NDA analysis and report generation completed.",
            100,
        )

        return CorrectionWorkflowResult(
            original_file=str(source),
            corrected_file=str(
                corrected_path
            ),
            report_file=str(
                report_path
            ),
            original_validation=(
                original_validation
            ),
            final_validation=(
                final_validation
            ),
            corrections=corrections,
            success=final_validation.success,
        )

    # ======================================================
    # REPORT
    # ======================================================

    def _generate_report(
        self,
        source_name: str,
        original_validation: NDAValidationResult,
        final_validation: NDAValidationResult,
        corrections: list[dict[str, Any]],
        report_path: Path,
    ) -> None:
        """Generate the final PDF analysis report."""

        results = [
            self._validation_result_to_dict(
                result
            )
            for result in final_validation.all_results
        ]

        validation_history = [
            {
                "iteration": 1,
                "status": (
                    original_validation.summary
                    .overall_status
                    .value
                ),
                "risk": (
                    original_validation.summary
                    .overall_risk
                    .value
                ),
                "passed_rules": (
                    original_validation.summary
                    .passed_rules
                ),
                "failed_rules": (
                    original_validation.summary
                    .failed_rules
                ),
            }
        ]

        if (
            final_validation.summary
            != original_validation.summary
        ):
            validation_history.append(
                {
                    "iteration": 2,
                    "status": (
                        final_validation.summary
                        .overall_status
                        .value
                    ),
                    "risk": (
                        final_validation.summary
                        .overall_risk
                        .value
                    ),
                    "passed_rules": (
                        final_validation.summary
                        .passed_rules
                    ),
                    "failed_rules": (
                        final_validation.summary
                        .failed_rules
                    ),
                }
            )

        report_data = (
            self.report_generator.generate_report_data(
                document_name=source_name,
                final_status=(
                    final_validation.summary
                    .overall_status
                    .value
                ),
                overall_risk=(
                    final_validation.summary
                    .overall_risk
                    .value
                ),
                validation_results=results,
                modifications=corrections,
                validation_history=validation_history,
            )
        )

        # Generate PDF report.
        self.report_generator.save_pdf(
            report_data=report_data,
            output_path=report_path,
        )

    # ======================================================
    # RESULT CONVERSION
    # ======================================================

    @staticmethod
    def _validation_result_to_dict(
        result: ValidationResult,
    ) -> dict[str, Any]:
        """Convert validation result to report data."""

        return {
            "rule_id": result.rule_id,
            "status": result.status.value,
            "risk": result.risk.value,
            "mandatory": result.mandatory,
            "nda_section": result.nda_section,
            "page_number": result.page_number,
            "evidence": result.evidence,
            "reason": result.reason,
            "required_change": result.required_change,
            "confidence": result.confidence,
        }

    # ======================================================
    # CLAUSE MAPPING
    # ======================================================

    @staticmethod
    def _build_clause_mapping(
        clauses: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Build clause mapping."""

        mapping: dict[str, str] = {}

        for clause in clauses:

            clause_id = str(
                clause.get(
                    "clause_id",
                    "",
                )
            ).strip()

            text = str(
                clause.get(
                    "text",
                    "",
                )
            ).strip()

            if clause_id and text:
                mapping[clause_id] = text

        return mapping

    # ======================================================
    # RULE CONTEXT MAPPING
    # ======================================================

    @staticmethod
    def _build_rule_context_mapping(
        results: list[ValidationResult],
    ) -> dict[str, str]:
        """Build Rule Book correction context."""

        return {
            result.rule_id: (
                result.required_change
                or result.reason
            )
            for result in results
        }

    # ======================================================
    # CORRECTED DOCUMENT PATH
    # ======================================================

    def _build_corrected_path(
        self,
        source: Path,
    ) -> Path:
        """Build corrected document path."""

        if self.output_directory is None:
            raise ValueError(
                "output_directory is not configured."
            )

        return (
            self.output_directory
            / f"{source.stem}_corrected{source.suffix}"
        )

    # ======================================================
    # PDF REPORT PATH
    # ======================================================

    def _build_report_path(
        self,
        source: Path,
    ) -> Path:
        """Build PDF analysis report path."""

        if self.output_directory is None:
            raise ValueError(
                "output_directory is not configured."
            )

        return (
            self.output_directory
            / f"{source.stem}_analysis_report.pdf"
        )