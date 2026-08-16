"""
LAURA - Analysis API

Runs the complete NDA validation and correction workflow.

The Rule Book is constant and is NOT uploaded by the user.

The user uploads only an NDA:
- PDF
- DOCX

Generated files are stored only in a temporary directory
until they are downloaded.

Analysis context is kept in memory so that the Q&A endpoint
can answer questions about the completed analysis.
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

from correction.document_modifier import DocumentModifier
from ingestion.clause_extractor import ClauseExtractor
from ingestion.docx_parser import DOCXParser
from ingestion.pdf_parser import PDFParser
from validation.correction_workflow import CorrectionWorkflow


router = APIRouter()


ALLOWED_NDA_EXTENSIONS = {
    ".pdf",
    ".docx",
}


# =========================================================
# Temporary Analysis Registry
# =========================================================
#
# analysis_id -> analysis information
#
# This is NOT persistent storage.
#
# It exists only while the application is running.
# =========================================================

_ANALYSIS_RESULTS: dict[
    str,
    dict[str, Any],
] = {}


_ANALYSIS_STATUS: dict[
    str,
    dict[str, Any],
] = {}


def _set_analysis_status(
    analysis_id: str,
    *,
    status: str,
    stage: str,
    message: str,
    progress: int,
) -> None:
    """Store the current analysis progress in memory."""

    _ANALYSIS_STATUS[analysis_id] = {
        "analysis_id": analysis_id,
        "status": status,
        "stage": stage,
        "message": message,
        "progress": max(0, min(100, progress)),
    }


# =========================================================
# Document Context Extraction
# =========================================================


def _extract_document_clauses(
    file_path: Path,
) -> list[dict[str, Any]]:
    """
    Extract clause-level information from an NDA.

    This is used only to provide document context to the
    Q&A system.

    It does NOT perform validation or correction.
    """

    extension = file_path.suffix.lower()

    try:

        if extension == ".pdf":

            parsed_document = (
                PDFParser().parse(
                    file_path
                )
            )

            return (
                ClauseExtractor()
                .extract_from_pdf(
                    parsed_document
                )
            )

        if extension == ".docx":

            parsed_document = (
                DOCXParser().parse(
                    file_path
                )
            )

            return (
                ClauseExtractor()
                .extract_from_docx(
                    parsed_document
                )
            )

        return []

    except Exception:
        # Q&A should not cause a successful analysis
        # to fail merely because document-context
        # extraction failed.
        return []


# =========================================================
# Cleanup
# =========================================================


def _cleanup_analysis(
    analysis_id: str,
) -> None:
    """
    Remove temporary files for an analysis.

    The analysis context itself is intentionally kept in
    memory so Q&A can continue to work after downloads.
    """

    result = _ANALYSIS_RESULTS.get(
        analysis_id
    )

    if not result:
        return

    root = result.get(
        "root"
    )

    if root:

        shutil.rmtree(
            root,
            ignore_errors=True,
        )

    result[
        "files_cleaned"
    ] = True


# =========================================================
# Run Analysis
# =========================================================


async def _process_analysis(
    *,
    analysis_id: str,
    filename: str,
    input_path: Path,
    temp_root: Path,
    output_directory: Path,
) -> None:
    """Run the NDA workflow in the background."""

    try:
        _set_analysis_status(
            analysis_id,
            status="running",
            stage="nda_uploaded",
            message="NDA uploaded. Preparing analysis.",
            progress=10,
        )

        workflow = CorrectionWorkflow(
            output_directory=output_directory
        )

        def progress_callback(
            stage: str,
            message: str = "",
            progress: int = 0,
        ) -> None:
            """Receive real stage updates from the workflow."""

            _set_analysis_status(
                analysis_id,
                status="running",
                stage=stage,
                message=(
                    message
                    or stage.replace("_", " ").title()
                ),
                progress=progress,
            )

        # The next workflow-file change will add this callback
        # argument. The fallback keeps the current workflow
        # compatible until that change is made.
        try:
            result = workflow.run(
                input_path,
                progress_callback=progress_callback,
            )
        except TypeError as exc:
            if "progress_callback" not in str(exc):
                raise

            _set_analysis_status(
                analysis_id,
                status="running",
                stage="validation",
                message="Running NDA validation workflow.",
                progress=50,
            )

            result = workflow.run(
                input_path
            )

        if not result.corrected_file:
            raise RuntimeError(
                "Correction workflow did not "
                "produce a corrected document."
            )

        corrected_path = Path(
            result.corrected_file
        )

        if not result.report_file:
            raise RuntimeError(
                "Correction workflow did not "
                "produce an analysis report."
            )

        report_path = Path(
            result.report_file
        )

        if not corrected_path.exists():
            raise RuntimeError(
                "Corrected document was not created."
            )

        if not report_path.exists():
            raise RuntimeError(
                "Analysis report was not created."
            )

        _set_analysis_status(
            analysis_id,
            status="running",
            stage="report_generation",
            message="Preparing final analysis context.",
            progress=95,
        )

        original_clauses = _extract_document_clauses(
            input_path
        )

        corrected_clauses = _extract_document_clauses(
            corrected_path
        )

        _ANALYSIS_RESULTS[analysis_id] = {
            "root": temp_root,
            "corrected_file": corrected_path,
            "report_file": report_path,
            "corrected_downloaded": False,
            "report_downloaded": False,
            "files_cleaned": False,
            "file_name": filename,
            "analysis_id": analysis_id,
            "original_clauses": original_clauses,
            "corrected_clauses": corrected_clauses,
            "original_summary": (
                result.original_validation
                .summary
                .model_dump()
            ),
            "final_summary": (
                result.final_validation
                .summary
                .model_dump()
            ),
            "validation_results": [
                validation_result.model_dump()
                for validation_result in (
                    result.final_validation.all_results
                )
            ],
            "corrections": result.corrections,
            "process": [
                "NDA uploaded",
                "NDA ingested",
                "NDA clauses extracted",
                "Rule Book rules retrieved",
                "NDA validated",
                "Corrections generated",
                "Corrected NDA created",
                "Corrected NDA re-ingested",
                "Corrected NDA re-validated",
                "PDF analysis report generated",
            ],
            "report_name": report_path.name,
        }

        _set_analysis_status(
            analysis_id,
            status="completed",
            stage="completed",
            message="NDA analysis completed successfully.",
            progress=100,
        )

    except Exception as exc:
        _set_analysis_status(
            analysis_id,
            status="failed",
            stage="failed",
            message=f"NDA analysis failed: {exc}",
            progress=100,
        )

        shutil.rmtree(
            temp_root,
            ignore_errors=True,
        )


@router.post("/run")
async def run_analysis(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload an NDA and start the workflow in the background.

    The endpoint immediately returns an analysis_id.
    The frontend can poll /analysis/status/{analysis_id}.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file has no filename.",
        )

    filename = Path(
        file.filename
    ).name

    extension = Path(
        filename
    ).suffix.lower()

    if extension not in ALLOWED_NDA_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported NDA file type: "
                f"{extension}. "
                f"Allowed: "
                f"{sorted(ALLOWED_NDA_EXTENSIONS)}"
            ),
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded NDA file is empty.",
        )

    temp_root = Path(
        tempfile.mkdtemp(
            prefix="laura_"
        )
    )

    input_directory = temp_root / "input"
    output_directory = temp_root / "output"

    input_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    input_path = input_directory / filename
    input_path.write_bytes(content)

    analysis_id = uuid.uuid4().hex

    _set_analysis_status(
        analysis_id,
        status="queued",
        stage="start",
        message="Analysis queued.",
        progress=5,
    )

    if background_tasks is None:
        shutil.rmtree(
            temp_root,
            ignore_errors=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Background task manager is unavailable.",
        )

    background_tasks.add_task(
        _process_analysis,
        analysis_id=analysis_id,
        filename=filename,
        input_path=input_path,
        temp_root=temp_root,
        output_directory=output_directory,
    )

    return {
        "status": "started",
        "analysis_id": analysis_id,
        "file_name": filename,
        "status_endpoint": (
            f"/analysis/status/{analysis_id}"
        ),
        "message": (
            "NDA analysis started. "
            "Poll the status endpoint for live progress."
        ),
    }


@router.get("/status/{analysis_id}")
async def get_analysis_status(
    analysis_id: str,
):
    """Return the current live analysis progress."""

    status = _ANALYSIS_STATUS.get(
        analysis_id
    )

    if not status:
        raise HTTPException(
            status_code=404,
            detail="Analysis ID not found or expired.",
        )

    response = dict(status)

    if status["status"] == "completed":
        result = _ANALYSIS_RESULTS.get(
            analysis_id
        )

        if result:
            response["result"] = {
                "status": "success",
                "analysis_id": analysis_id,
                "file_name": result.get(
                    "file_name"
                ),
                "success": True,
                "original_summary": result.get(
                    "original_summary",
                    {},
                ),
                "final_summary": result.get(
                    "final_summary",
                    {},
                ),
                "validation_results": result.get(
                    "validation_results",
                    [],
                ),
                "corrections": result.get(
                    "corrections",
                    [],
                ),
                "downloads": {
                    "corrected_nda": (
                        f"/analysis/download/"
                        f"{analysis_id}/corrected"
                    ),
                    "analysis_report": (
                        f"/analysis/download/"
                        f"{analysis_id}/report"
                    ),
                },
            }

    return response


# =========================================================
# Download Corrected NDA
# =========================================================


@router.get(
    "/download/{analysis_id}/corrected"
)
async def download_corrected_nda(
    analysis_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Download the corrected NDA.
    """

    result = _ANALYSIS_RESULTS.get(
        analysis_id
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis result not found "
                "or expired."
            ),
        )

    corrected_path = Path(
        result["corrected_file"]
    )

    if not corrected_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Corrected NDA is no longer "
                "available."
            ),
        )

    result[
        "corrected_downloaded"
    ] = True

    # -----------------------------------------------------
    # If both files have now been downloaded, schedule
    # temporary-file cleanup after the response finishes.
    # -----------------------------------------------------

    if result[
        "report_downloaded"
    ]:

        background_tasks.add_task(
            _cleanup_analysis,
            analysis_id,
        )

    return FileResponse(
        path=corrected_path,
        filename=corrected_path.name,
        media_type=(
            "application/pdf"
            if corrected_path.suffix.lower()
            == ".pdf"
            else (
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            )
        ),
        background=background_tasks,
    )


# =========================================================
# Download Analysis Report
# =========================================================


@router.get(
    "/download/{analysis_id}/report"
)
async def download_analysis_report(
    analysis_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Download the PDF analysis report.
    """

    result = _ANALYSIS_RESULTS.get(
        analysis_id
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis result not found "
                "or expired."
            ),
        )

    report_path = Path(
        result["report_file"]
    )

    if not report_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis report is no longer "
                "available."
            ),
        )

    result[
        "report_downloaded"
    ] = True

    # -----------------------------------------------------
    # If both files have now been downloaded, schedule
    # temporary-file cleanup after the response finishes.
    # -----------------------------------------------------

    if result[
        "corrected_downloaded"
    ]:

        background_tasks.add_task(
            _cleanup_analysis,
            analysis_id,
        )

    return FileResponse(
        path=report_path,
        filename=report_path.name,
        media_type="application/pdf",
        background=background_tasks,
    )