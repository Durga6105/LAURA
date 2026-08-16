"""
LAURA - File Utilities

Common file and document handling utilities.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from config.settings import settings


class FileUtils:
    """Utility methods for LAURA file management."""

    SUPPORTED_RULEBOOK_EXTENSIONS = {
        ".txt",
        ".xlsx",
    }

    SUPPORTED_NDA_EXTENSIONS = {
        ".pdf",
        ".docx",
    }

    @staticmethod
    def ensure_directories() -> None:
        """Create required LAURA directories."""

        directories = [
            settings.rulebook_directory,
            settings.nda_directory,
            settings.output_directory,
            settings.chroma_persist_directory,
        ]

        for directory in directories:
            Path(directory).mkdir(
                parents=True,
                exist_ok=True,
            )

    @staticmethod
    def validate_rulebook_file(
        file_path: str | Path,
    ) -> Path:
        """
        Validate a Rule Book file.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Rule Book not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Rule Book path is not a file: {path}"
            )

        if (
            path.suffix.lower()
            not in FileUtils.SUPPORTED_RULEBOOK_EXTENSIONS
        ):
            raise ValueError(
                "Unsupported Rule Book format. "
                "Allowed: TXT, XLSX."
            )

        return path

    @staticmethod
    def validate_nda_file(
        file_path: str | Path,
    ) -> Path:
        """
        Validate an NDA file.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"NDA not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"NDA path is not a file: {path}"
            )

        if (
            path.suffix.lower()
            not in FileUtils.SUPPORTED_NDA_EXTENSIONS
        ):
            raise ValueError(
                "Unsupported NDA format. "
                "Allowed: PDF, DOCX."
            )

        return path

    @staticmethod
    def save_uploaded_file(
        source_path: str | Path,
        destination_directory: str | Path,
    ) -> Path:
        """
        Copy an uploaded file into a LAURA data directory.

        The original source is not modified.
        """

        source = Path(source_path)
        destination_dir = Path(destination_directory)

        if not source.exists():
            raise FileNotFoundError(
                f"Source file not found: {source}"
            )

        destination_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = destination_dir / source.name

        shutil.copy2(
            source,
            destination,
        )

        return destination

    @staticmethod
    def create_output_path(
        original_filename: str,
        suffix: str = "_validated",
    ) -> Path:
        """
        Create a path for a generated NDA.

        Example:
            NDA.docx
            ->
            NDA_validated.docx
        """

        original = Path(original_filename)

        output_directory = Path(
            settings.output_directory
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return output_directory / (
            f"{original.stem}"
            f"{suffix}"
            f"{original.suffix}"
        )

    @staticmethod
    def get_file_extension(
        file_path: str | Path,
    ) -> str:
        """Return lowercase file extension."""

        return Path(file_path).suffix.lower()

    @staticmethod
    def get_file_name(
        file_path: str | Path,
    ) -> str:
        """Return filename."""

        return Path(file_path).name