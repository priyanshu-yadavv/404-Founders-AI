"""
404 FOUNDERS — Document Intelligence Pipeline
Provides secure multi-format document extraction (PDF, DOCX, TXT, CSV, JSON, Markdown),
table parsing, prompt injection defense, document chunking, and grounded question answering.
"""

import csv
from dataclasses import dataclass, field
import io
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import docx
import pypdf

from core.exceptions import PromptInjectionDetectedError
from multimodal.text.text_processor import DocumentChunk, MultimodalTextProcessor
from security.sanitization import PROMPT_INJECTION_SIGNATURES, inspect_prompt_safety


@dataclass
class DocumentMetadata:
    """Quantitative properties of an inspected document file."""
    format: str
    page_count: int
    word_count: int
    character_count: int
    file_size_bytes: int
    has_tables: bool


@dataclass
class DocumentTable:
    """Structured table extracted from document."""
    table_id: int
    headers: List[str]
    rows: List[List[str]]
    row_count: int


@dataclass
class DocumentSecurityReport:
    """Security audit evaluating untrusted document contents for prompt injection."""
    is_safe: bool
    detected_injection_patterns: List[str]
    risk_level: str  # "SAFE", "SUSPICIOUS", "ADVERSARIAL_INJECTION"


@dataclass
class DocumentAnalysisResult:
    """Comprehensive output schema for document intelligence processing."""
    metadata: DocumentMetadata
    is_valid: bool
    extracted_text: str
    chunks: List[DocumentChunk]
    tables: List[DocumentTable]
    summary: str
    security_report: DocumentSecurityReport
    processing_notice: str = (
        "SECURITY NOTICE: Document contents treated as untrusted input. "
        "Scanned for prompt injection and privilege escalation markers."
    )


class DocumentProcessor:
    """
    Document Intelligence Processor.
    Extracts text, metadata, and tables from PDF, DOCX, CSV, JSON, TXT, and Markdown files.
    Enforces prompt injection filtering and generates bounded chunk representations.
    """

    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
    MAX_PAGES = 500                          # 500 pages maximum

    MAGIC_HEADERS = {
        "PDF": b"%PDF-",
        "DOCX": b"PK\x03\x04",  # ZIP container for Office Open XML
    }

    def __init__(self, text_processor: Optional[MultimodalTextProcessor] = None) -> None:
        self.text_processor = text_processor or MultimodalTextProcessor()

    def validate_document_bytes(
        self,
        doc_bytes: bytes,
        filename_hint: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Validate document buffer against size limits and format signatures."""
        if not doc_bytes:
            return False, "Document byte buffer is empty."

        if len(doc_bytes) > self.MAX_FILE_SIZE_BYTES:
            return False, f"File size ({len(doc_bytes)} bytes) exceeds limit of {self.MAX_FILE_SIZE_BYTES} bytes."

        detected = None
        if doc_bytes.startswith(self.MAGIC_HEADERS["PDF"]):
            detected = "PDF"
        elif doc_bytes.startswith(self.MAGIC_HEADERS["DOCX"]):
            detected = "DOCX"
        elif filename_hint:
            ext = Path(filename_hint).suffix.lower().strip(".")
            if ext in ["csv", "json", "txt", "md", "markdown"]:
                detected = ext.upper()

        # Fallback to UTF-8 text attempt if text-like
        if not detected:
            try:
                sample = doc_bytes[:512].decode("utf-8")
                if sample.strip().startswith("{") or sample.strip().startswith("["):
                    detected = "JSON"
                elif "," in sample and "\n" in sample:
                    detected = "CSV"
                else:
                    detected = "TXT"
            except Exception:
                return False, "Unsupported binary file format: does not match PDF, DOCX, CSV, JSON, or TXT."

        return True, detected

    def detect_format(self, doc_bytes: bytes, filename_hint: Optional[str] = None) -> str:
        """Helper to return document format name (or 'UNKNOWN') for raw bytes."""
        valid, fmt = self.validate_document_bytes(doc_bytes, filename_hint)
        return fmt if valid else "UNKNOWN"

    def extract_pdf(self, doc_bytes: bytes) -> Tuple[str, int]:
        """Extract text and page count from PDF stream via PyPDF."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(doc_bytes))
            page_count = len(reader.pages)
            if page_count > self.MAX_PAGES:
                raise ValueError(f"PDF page count ({page_count}) exceeds limit of {self.MAX_PAGES}.")

            text_parts = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            full_text = "\n\n".join(text_parts)
            return full_text, page_count
        except Exception as e:
            raise ValueError(f"Failed to extract PDF stream: {e}")

    def extract_docx(self, doc_bytes: bytes) -> Tuple[str, int, List[DocumentTable]]:
        """Extract text and tables from Word DOCX stream."""
        try:
            doc = docx.Document(io.BytesIO(doc_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)

            tables: List[DocumentTable] = []
            for idx, table in enumerate(doc.tables):
                rows_data: List[List[str]] = []
                for row in table.rows:
                    rows_data.append([cell.text.strip() for cell in row.cells])
                if rows_data:
                    headers = rows_data[0]
                    content_rows = rows_data[1:] if len(rows_data) > 1 else []
                    tables.append(DocumentTable(
                        table_id=idx + 1,
                        headers=headers,
                        rows=content_rows,
                        row_count=len(rows_data),
                    ))

            return full_text, max(1, len(paragraphs) // 5), tables
        except Exception as e:
            raise ValueError(f"Failed to extract DOCX stream: {e}")

    def extract_csv(self, doc_bytes: bytes) -> Tuple[str, List[DocumentTable]]:
        """Parse structured tabular data from CSV stream."""
        try:
            text = doc_bytes.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            rows = [r for r in reader if any(cell.strip() for cell in r)]
            if not rows:
                return "", []

            headers = rows[0]
            content_rows = rows[1:] if len(rows) > 1 else []
            table = DocumentTable(
                table_id=1,
                headers=headers,
                rows=content_rows,
                row_count=len(rows),
            )
            return text, [table]
        except Exception as e:
            raise ValueError(f"Failed to parse CSV stream: {e}")

    def audit_security(self, text: str) -> DocumentSecurityReport:
        """Scan extracted text for prompt injection and adversarial override attempts."""
        try:
            safe, detected = inspect_prompt_safety(text)
        except PromptInjectionDetectedError:
            safe = False
            detected = [sig for sig in PROMPT_INJECTION_SIGNATURES if re.search(sig, text, re.IGNORECASE)]

        risk = "SAFE" if safe else ("ADVERSARIAL_INJECTION" if len(detected) > 1 else "SUSPICIOUS")

        return DocumentSecurityReport(
            is_safe=safe,
            detected_injection_patterns=detected,
            risk_level=risk,
        )

    def process(
        self,
        input_data: Union[bytes, str, Path],
        filename_hint: Optional[str] = None,
    ) -> DocumentAnalysisResult:
        """Execute complete document intelligence pipeline."""
        if isinstance(input_data, (str, Path)):
            p = Path(input_data)
            if not p.is_file():
                raise FileNotFoundError(f"Document file not found: {p}")
            data_bytes = p.read_bytes()
            fname = filename_hint or p.name
        else:
            data_bytes = input_data
            fname = filename_hint or "uploaded_document"

        is_valid, detected_format = self.validate_document_bytes(data_bytes, fname)
        if not is_valid:
            raise ValueError(f"Document validation failed: {detected_format}")

        extracted_text = ""
        page_count = 1
        tables: List[DocumentTable] = []

        if detected_format == "PDF":
            extracted_text, page_count = self.extract_pdf(data_bytes)
        elif detected_format == "DOCX":
            extracted_text, page_count, tables = self.extract_docx(data_bytes)
        elif detected_format == "CSV":
            extracted_text, tables = self.extract_csv(data_bytes)
        elif detected_format == "JSON":
            try:
                data_dict = json.loads(data_bytes.decode("utf-8"))
                extracted_text = json.dumps(data_dict, indent=2)
            except Exception as e:
                extracted_text = data_bytes.decode("utf-8", errors="replace")
        else:  # TXT, MD
            extracted_text = data_bytes.decode("utf-8", errors="replace")

        # Security scan
        security_report = self.audit_security(extracted_text)

        # Chunking
        chunks = self.text_processor.chunk_text(extracted_text)

        # Summary
        summary = self.text_processor.summarize(extracted_text) if len(extracted_text.split()) > 40 else extracted_text.strip()

        word_count = len(extracted_text.split())
        metadata = DocumentMetadata(
            format=detected_format,
            page_count=page_count,
            word_count=word_count,
            character_count=len(extracted_text),
            file_size_bytes=len(data_bytes),
            has_tables=len(tables) > 0,
        )

        return DocumentAnalysisResult(
            metadata=metadata,
            is_valid=True,
            extracted_text=extracted_text,
            chunks=chunks,
            tables=tables,
            summary=summary,
            security_report=security_report,
        )
