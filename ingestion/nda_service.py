"""
LAURA - NDA Ingestion Service

Integrates the complete NDA ingestion pipeline:

PDF / DOCX
    ↓
Parser
    ↓
Clause Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
ChromaDB
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from embeddings.embedding_service import EmbeddingService
from ingestion.chunker import Chunker
from ingestion.clause_extractor import ClauseExtractor
from ingestion.docx_parser import DOCXParser
from ingestion.pdf_parser import PDFParser
from utils.logger import get_logger
from vector_db.chroma_store import ChromaStore


logger = get_logger(__name__)


class NDAIngestionService:
    """Complete NDA ingestion and indexing service."""

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".docx",
    }

    def __init__(
        self,
        pdf_parser: PDFParser | None = None,
        docx_parser: DOCXParser | None = None,
        clause_extractor: ClauseExtractor | None = None,
        chunker: Chunker | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: ChromaStore | None = None,
    ) -> None:

        self.pdf_parser = (
            pdf_parser or PDFParser()
        )

        self.docx_parser = (
            docx_parser or DOCXParser()
        )

        self.clause_extractor = (
            clause_extractor or ClauseExtractor()
        )

        self.chunker = (
            chunker or Chunker()
        )

        self.embedding_service = (
            embedding_service or EmbeddingService()
        )

        self.vector_store = (
            vector_store or ChromaStore()
        )

    def ingest(
        self,
        file_path: str | Path,
    ) -> dict[str, Any]:
        """
        Parse, extract, chunk, embed, and index an NDA.

        Supported formats:
            PDF
            DOCX
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"NDA not found: {path}"
            )

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported NDA format: {extension}"
            )

        logger.info(
            "Starting NDA ingestion: %s",
            path.name,
        )

        # ==================================================
        # 1. Parse document
        # ==================================================

        if extension == ".pdf":

            parsed_document = (
                self.pdf_parser.parse(path)
            )

            logger.info(
                "PDF parsed successfully"
            )

            clauses = (
                self.clause_extractor.extract_from_pdf(
                    parsed_document
                )
            )

        else:

            parsed_document = (
                self.docx_parser.parse(path)
            )

            logger.info(
                "DOCX parsed successfully"
            )

            clauses = (
                self.clause_extractor.extract_from_docx(
                    parsed_document
                )
            )

        logger.info(
            "Extracted %d clauses",
            len(clauses),
        )

        if not clauses:
            raise ValueError(
                "No usable clauses were extracted from the NDA."
            )

        # ==================================================
        # 2. Create chunks
        # ==================================================

        chunks = self.chunker.chunk(
            clauses
        )

        logger.info(
            "Created %d chunks",
            len(chunks),
        )

        if not chunks:
            raise ValueError(
                "No usable chunks were created from the NDA."
            )

        # ==================================================
        # 3. Generate embeddings
        # ==================================================

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        embeddings = (
            self.embedding_service.embed_texts(
                texts
            )
        )

        logger.info(
            "Generated %d NDA embeddings",
            len(embeddings),
        )

        # ==================================================
        # 4. Prepare ChromaDB records
        # ==================================================

        chroma_chunks = []

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):

            chroma_chunks.append(
                {
                    "id": (
                        f"{path.stem}-"
                        f"{chunk['chunk_id']}"
                    ),
                    "text": chunk["text"],
                    "embedding": embedding,
                    "metadata": {
                        "file_name": path.name,
                        "file_type": extension.lstrip("."),
                        "clause_id": chunk[
                            "clause_id"
                        ],
                        "section": (
                            chunk.get("section")
                            or ""
                        ),
                        "page_number": (
                            chunk.get("page_number")
                            or 0
                        ),
                        "paragraph_number": (
                            chunk.get(
                                "paragraph_number"
                            )
                            or 0
                        ),
                    },
                }
            )

        # ==================================================
        # 5. Store in ChromaDB
        # ==================================================

        self.vector_store.add_nda_chunks(
            chroma_chunks
        )

        logger.info(
            "Indexed %d NDA chunks in ChromaDB",
            len(chroma_chunks),
        )

        # ==================================================
        # 6. Return result
        # ==================================================

        return {
            "status": "success",
            "file_name": path.name,
            "file_type": extension.lstrip("."),

            # Existing count fields
            "clauses": len(clauses),
            "chunks": len(chunks),
            "indexed_chunks": len(chroma_chunks),

            # Actual extracted clause data
            "clause_data": clauses,
        }