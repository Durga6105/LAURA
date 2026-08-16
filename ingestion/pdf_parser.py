from pathlib import Path
from typing import Any

import pymupdf


class PDFParser:
    """Parse PDF documents."""

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"PDF not found: {path}"
            )

        pages = []

        with pymupdf.open(path) as document:
            for page_number, page in enumerate(
                document,
                start=1,
            ):
                text = page.get_text("text").strip()

                pages.append(
                    {
                        "page_number": page_number,
                        "text": text,
                    }
                )

        return {
            "file_name": path.name,
            "file_type": "pdf",
            "pages": pages,
        }