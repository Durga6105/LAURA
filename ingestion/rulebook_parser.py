"""
LAURA - Rule Book Parser

Parses Rule Books provided as TXT or XLSX files.
"""

from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".txt", ".xlsx"}


class RuleBookParser:
    """Parse Rule Books from supported file formats."""

    def parse(self, file_path: str | Path) -> Any:
        """
        Parse a Rule Book based on its file extension.

        Args:
            file_path: Path to the Rule Book.

        Returns:
            Raw Rule Book content.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is unsupported.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Rule Book not found: {path}")

        extension = path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported Rule Book format: {extension}. "
                f"Supported formats: {SUPPORTED_EXTENSIONS}"
            )

        if extension == ".txt":
            return self._parse_txt(path)

        if extension == ".xlsx":
            return self._parse_xlsx(path)

        raise ValueError(f"Unsupported Rule Book format: {extension}")

    def _parse_txt(self, path: Path) -> str:
        """Read a TXT Rule Book."""
        return path.read_text(encoding="utf-8")

    def _parse_xlsx(self, path: Path) -> list[dict[str, Any]]:
        """Read an XLSX Rule Book."""
        dataframe = pd.read_excel(path)

        # Convert NaN values to None.
        dataframe = dataframe.where(pd.notna(dataframe), None)

        return dataframe.to_dict(orient="records")