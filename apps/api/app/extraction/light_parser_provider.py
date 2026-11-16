"""The Light Parser: real extraction with no LLM, built on pypdf + regex.

Uses pypdf text extraction and regex patterns to pull invoice fields from
text-based PDFs, plus a keyword classifier for document type. Suitable
for Local Docker Mode when cost control is critical: it reads the real
bytes, so its output is honest about the document, but it sees nothing
on scanned/image-only pages — those need the Phase 10 Vision provider.

Design notes:
- Patterns are module constants, tested as their own unit, so adding a
  field means one regex plus one result entry — never a provider rewrite.
- The provider is stateless per call: ``extract`` parses the bytes it is
  handed and builds the result from what it actually found. Fields whose
  pattern did not match are simply absent from the result; absence is
  data (the review UI shows them as missing), not an error.
"""

import io
import re
import time
from typing import Any

import structlog
from pypdf import PdfReader

from app.errors import ExtractionProviderException
from app.extraction.base import ExtractionProvider
from app.extraction.confidence import calculate_confidence
from app.schemas.extraction import (
    DocumentTypePrediction,
    ExtractedField,
    ExtractedTable,
    ExtractionResult,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for invoice fields. Each is exercised against fixture
# text in tests/test_light_parser.py; a pattern change is a contract
# change and must update those fixtures in the same commit.
# ---------------------------------------------------------------------------

PATTERN_INVOICE_NUMBER = r"Invoice\s*#?\s*(\w+)"
PATTERN_TOTAL_AMOUNT = r"Total.*?\$?(\d+\.?\d*)"
PATTERN_DUE_DATE = r"Due.*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"

# A page with less text than this is "empty" (a scanned image page, or a
# divider): the count of such pages is recorded in metadata, because it
# is the honest signal that this parser cannot see the content.
MIN_TEXT_PER_PAGE = 50

# Keyword classifier vocabulary. The score is a mention count; ties
# resolve to the type declared earlier in this mapping.
DOCUMENT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "invoice": ["invoice", "bill"],
    "contract": ["contract", "agreement"],
    "rfp": ["rfp", "proposal"],
    "bill_of_lading": ["bill of lading", "bol"],
}


class LightParserProvider(ExtractionProvider):
    """pypdf-based extractor: text out, regex in, no network, no cost.

    Confidence comes from :func:`app.extraction.confidence.calculate_confidence`
    fed with honest signals: a regex match means evidence was found next
    to the value; keyword frequency decides how much the type prediction
    believes itself; page coverage feeds the overall metadata, not a
    fabricated number.
    """

    def __init__(self, document_bytes: bytes | None = None) -> None:
        """Create a provider, optionally bound to one document's bytes.

        The ABC's ``extract(document_id, storage_path)`` signature is
        fixed by the Phase 6 contract, yet the parser needs the real
        bytes and Phase 6 has no worker to download them. Constructor
        binding resolves both: tests (and the Phase 7 worker) construct
        ``LightParserProvider(data=...)`` per document, and the
        interface stays exactly as specified. Unbound means "no bytes
        yet", which ``extract`` reports rather than guessing on empty
        input — a missing document is a provider failure, not an empty
        result.
        """
        self._document_bytes = document_bytes

    def _extract_page_texts(self, data: bytes) -> list[str]:
        """Return one text blob per page, empty pages included.

        Raises:
            ExtractionProviderException: If pypdf cannot parse the bytes
                at all (a corrupt object in storage despite the intake
                checks — the failure is the provider's to report, not
                to hide).
        """
        try:
            reader = PdfReader(io.BytesIO(data))
            return [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise ExtractionProviderException(details={"reason": repr(exc)}) from exc

    def _classify_document_type(self, text: str) -> DocumentTypePrediction:
        """Count classifier keywords and predict the document type.

        Keyword frequency is the confidence: one "invoice" mention is a
        weaker claim than five, and no keywords at all means "unknown"
        with a floor confidence — an honest "I do not know" instead of
        a confident guess.
        """
        lowered = text.lower()
        best_type, best_hits = "unknown", 0
        for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
            hits = sum(lowered.count(keyword) for keyword in keywords)
            if hits > best_hits:
                best_type, best_hits = doc_type, hits
        if best_type == "unknown":
            return DocumentTypePrediction(type="unknown", confidence=0.3)
        # 0.5 floor for one hit, +0.1 per additional hit, capped at 0.95:
        # enough keyword density to be believed, never certainty.
        confidence = min(0.5 + 0.1 * (best_hits - 1), 0.95)
        return DocumentTypePrediction(type=best_type, confidence=round(confidence, 2))

    def _vendor_from_text(self, text: str) -> str | None:
        """Return the line after ``From:``, or the first non-empty line.

        Invoices conventionally open with the vendor's letterhead, so
        the first non-empty text line is the cheapest reliable signal;
        an explicit ``From:`` label wins when present because it is the
        only line in the layout that names its own meaning.
        """
        lines = text.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("from:"):
                return stripped[5:].strip() or None
        for line in lines:
            stripped = line.strip()
            if stripped:
                return stripped
        return None

    def _find(self, pattern: str, text: str) -> str | None:
        """Return capture group 1 of the first pattern match, or None."""
        match = re.search(pattern, text)
        return match.group(1) if match else None

    async def extract(self, document_id: str, storage_path: str) -> ExtractionResult:
        """Parse the bound PDF bytes and extract what the patterns find.

        Args:
            document_id: Correlated into the result; the bytes alone
                decide the output (no seeding, no randomness).
            storage_path: Correlated into the result metadata.

        Returns:
            The extraction result with source "light_parser" on every
            field; patterns that did not match yield absent fields.

        Raises:
            ExtractionProviderException: If no bytes were bound at
                construction, or if the bytes cannot be parsed.
        """
        if self._document_bytes is None:
            raise ExtractionProviderException(
                details={"reason": "no_document_bytes", "storage_path": storage_path}
            )
        started = time.perf_counter()
        page_texts = self._extract_page_texts(self._document_bytes)
        full_text = "\n".join(page_texts)
        empty_pages = sum(1 for t in page_texts if len(t.strip()) < MIN_TEXT_PER_PAGE)

        fields: list[ExtractedField] = []

        invoice_number = self._find(PATTERN_INVOICE_NUMBER, full_text)
        if invoice_number is not None:
            fields.append(
                ExtractedField(
                    key="invoice_number",
                    label="Invoice Number",
                    value=invoice_number,
                    confidence=calculate_confidence(
                        source="light_parser",
                        evidence_match=True,
                        validation_passed=True,
                        is_required=True,
                    ),
                    page_number=1,
                    evidence_span=f"Invoice #: {invoice_number}",
                    source="light_parser",
                )
            )

        total_amount = self._find(PATTERN_TOTAL_AMOUNT, full_text)
        if total_amount is not None:
            fields.append(
                ExtractedField(
                    key="total_amount",
                    label="Total Amount",
                    value=float(total_amount),
                    confidence=calculate_confidence(
                        source="light_parser",
                        evidence_match=True,
                        validation_passed=True,
                        is_required=True,
                    ),
                    page_number=1,
                    evidence_span=f"Total: ${total_amount}",
                    source="light_parser",
                )
            )

        due_date = self._find(PATTERN_DUE_DATE, full_text)
        if due_date is not None:
            fields.append(
                ExtractedField(
                    key="due_date",
                    label="Due Date",
                    value=due_date,
                    confidence=calculate_confidence(
                        source="light_parser",
                        evidence_match=True,
                        validation_passed=True,
                        is_required=False,
                    ),
                    page_number=1,
                    evidence_span=f"Due: {due_date}",
                    source="light_parser",
                )
            )

        vendor_name = self._vendor_from_text(full_text)
        if vendor_name is not None:
            fields.append(
                ExtractedField(
                    key="vendor_name",
                    label="Vendor Name",
                    value=vendor_name,
                    confidence=calculate_confidence(
                        source="light_parser",
                        evidence_match=False,
                        validation_passed=True,
                        is_required=True,
                    ),
                    page_number=1,
                    evidence_span=None,
                    source="light_parser",
                )
            )

        tables: list[ExtractedTable] = []
        prediction = self._classify_document_type(full_text)

        elapsed = time.perf_counter() - started
        metadata: dict[str, Any] = {
            "provider": "light_parser",
            "storage_path": storage_path,
            "page_count": len(page_texts),
            "empty_pages": empty_pages,
            "matched_fields": [f.key for f in fields],
        }
        logger.info(
            "light_parser_extraction_complete",
            document_id=document_id,
            fields_found=len(fields),
            document_type=prediction.type,
        )
        return ExtractionResult(
            document_id=document_id,
            fields=fields,
            tables=tables,
            document_type_prediction=prediction,
            processing_time_seconds=round(elapsed, 3),
            metadata=metadata,
        )
