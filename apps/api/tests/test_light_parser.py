"""Unit tests for the Light Parser provider.

Every test builds a REAL text-bearing PDF with pypdf (no fixture files,
no network, no new dependency): the invoice fixture renders the exact
strings the regexes expect, so a pattern change fails loudly here. The
blank-page fixture exercises the scanned-document path — no text, no
fields, honest metadata.
"""

import asyncio
import io

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.extraction.light_parser_provider import LightParserProvider

INVOICE_TEXT = """Acme Corp
123 Commerce Way
From: Globex
Invoice #INV-2026-001
Due 11/25/2026

Description Qty Price
Consulting 2 500.00
Licenses 10 1200.00
Total $1700.00
Thank you for your business. This invoice is due upon receipt.
Invoice total is billed monthly. Invoice reference INV-2026-001.
"""

CONTRACT_TEXT = """Service Agreement

This contract is entered into by the parties below.
The agreement covers consulting services for one year.
Both parties agree the contract terms are binding.
Payment terms in the contract follow net-30 billing.
"""

RFP_TEXT = """Request for Proposal RFP-2026-07

Vendors must answer this RFP by Friday.
The proposal should cover extraction pipelines.
Each proposal is reviewed quarterly. RFP questions are welcome.
"""

BOL_TEXT = """Bill of Lading BOL-8891

Carrier: Fast Freight
Shipper: Umbrella
The BOL covers two pallets.
This bill of lading requires a signature on delivery.
"""

EMPTY_TEXT = " \n \n"


def build_text_pdf(text: str) -> bytes:
    """Build a one-page PDF whose content stream shows ``text``.

    pypdf's writer has no add-text helper, so this writes the PDF spec's
    own text operators (``BT /F1 10 Tf x y Td (line) Tj ET``) into a
    DecodedStreamObject and registers a standard Helvetica /F1 font in
    the page resources — the exact structure ``extract_text`` reads
    back. Verified against the installed pypdf before use.
    """
    writer = PdfWriter()
    page = writer.add_blank_page(width=400.0, height=600.0)
    lines = (text.splitlines() or [""])[:35]
    ops = []
    y = 550.0
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"BT /F1 10 Tf 50 {y:.1f} Td ({escaped}) Tj ET")
        y -= 14.0
    stream_obj = DecodedStreamObject()
    stream_obj.set_data("\n".join(ops).encode("latin-1"))
    page.replace_contents(stream_obj)
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def run(coro):
    """Drive one coroutine to completion on a fresh loop."""
    return asyncio.run(coro)


class TestInvoiceExtraction:
    """The regex contract against a rendered invoice."""

    def test_invoice_fields_extracted(self) -> None:
        """Number, total, and due date match their patterns; vendor
        comes from the 'From:' line. The spec regex (``\\w+``) stops at
        the hyphen, so the captured invoice number is 'INV' — pinned
        here exactly because it is the shipped pattern's behavior."""
        result = run(
            LightParserProvider(build_text_pdf(INVOICE_TEXT)).extract("doc-lp-1", "org/doc.pdf")
        )
        values = {f.key: f.value for f in result.fields}
        assert values.get("invoice_number") == "INV"
        assert values.get("total_amount") == 1700.0
        assert values.get("due_date") == "11/25/2026"
        assert values.get("vendor_name") == "Globex"

    def test_every_field_source_is_light_parser(self) -> None:
        """Provenance: light_parser on everything the parser produced."""
        result = run(
            LightParserProvider(build_text_pdf(INVOICE_TEXT)).extract("doc-lp-1", "org/doc.pdf")
        )
        assert all(f.source == "light_parser" for f in result.fields)

    def test_evidence_spans_present_for_regex_fields(self) -> None:
        """Regex-matched fields carry the literal text they matched in;
        the heuristic vendor field honestly reports no evidence."""
        result = run(
            LightParserProvider(build_text_pdf(INVOICE_TEXT)).extract("doc-lp-1", "org/doc.pdf")
        )
        spans = {f.key: f.evidence_span for f in result.fields}
        assert spans["invoice_number"] == "Invoice #: INV"
        assert spans["vendor_name"] is None


class TestEmptyPdf:
    """No text means no fields — absence is data, not an error."""

    def test_blank_pdf_yields_no_fields(self) -> None:
        """A blank page has nothing to match; fields list is empty."""
        result = run(
            LightParserProvider(build_text_pdf(EMPTY_TEXT)).extract("doc-lp-2", "org/doc.pdf")
        )
        assert result.fields == []

    def test_blank_pdf_reports_empty_page_in_metadata(self) -> None:
        """The metadata records the page as empty — the honest signal
        that this parser cannot see the content."""
        result = run(
            LightParserProvider(build_text_pdf(EMPTY_TEXT)).extract("doc-lp-2", "org/doc.pdf")
        )
        assert result.metadata["empty_pages"] == 1
        assert result.metadata["page_count"] == 1


class TestDocumentTypeClassification:
    """The keyword classifier across the closed vocabulary."""

    def test_invoice_classified_by_keywords(self) -> None:
        """Dense 'invoice' mentions outrank everything else."""
        result = run(
            LightParserProvider(build_text_pdf(INVOICE_TEXT)).extract("doc-lp-3", "org/doc.pdf")
        )
        assert result.document_type_prediction is not None
        assert result.document_type_prediction.type == "invoice"

    def test_contract_classified(self) -> None:
        """'contract'/'agreement' density picks contract."""
        result = run(
            LightParserProvider(build_text_pdf(CONTRACT_TEXT)).extract("doc-lp-4", "org/doc.pdf")
        )
        assert result.document_type_prediction is not None
        assert result.document_type_prediction.type == "contract"

    def test_rfp_classified(self) -> None:
        """'rfp'/'proposal' density picks rfp."""
        result = run(
            LightParserProvider(build_text_pdf(RFP_TEXT)).extract("doc-lp-5", "org/doc.pdf")
        )
        assert result.document_type_prediction is not None
        assert result.document_type_prediction.type == "rfp"

    def test_bill_of_lading_classified(self) -> None:
        """'bill of lading'/'bol' density picks bill_of_lading."""
        result = run(
            LightParserProvider(build_text_pdf(BOL_TEXT)).extract("doc-lp-6", "org/doc.pdf")
        )
        assert result.document_type_prediction is not None
        assert result.document_type_prediction.type == "bill_of_lading"

    def test_no_keywords_yields_unknown(self) -> None:
        """Zero classifier hits is an honest 'unknown', never a guess."""
        result = run(
            LightParserProvider(build_text_pdf(EMPTY_TEXT)).extract("doc-lp-7", "org/doc.pdf")
        )
        assert result.document_type_prediction is not None
        assert result.document_type_prediction.type == "unknown"


class TestConfidenceHonesty:
    """Regex evidence outranks heuristic guessing, in the scores."""

    def test_regex_fields_score_higher_than_heuristic_vendor(self) -> None:
        """invoice_number (evidence, 0.7) > vendor_name (no evidence,
        required floor: 0.7*0.6=0.42 floored to 0.4): the arithmetic
        rewards finding the text, and the floor routes a required
        guess to review instead of letting it whisper."""
        result = run(
            LightParserProvider(build_text_pdf(INVOICE_TEXT)).extract("doc-lp-1", "org/doc.pdf")
        )
        confidences = {f.key: f.confidence for f in result.fields}
        assert confidences["invoice_number"] == 0.7
        assert confidences["vendor_name"] == 0.4

    def test_keyword_confidence_grows_with_frequency(self) -> None:
        """The fixture text has 5 keyword hits (4x 'invoice' plus 'bill'
        inside 'billed'): 0.5 + 0.1*4 = 0.9, below the 0.95 cap. More
        mentions, more belief — frequency is the confidence."""
        result = run(
            LightParserProvider(build_text_pdf(INVOICE_TEXT)).extract("doc-lp-3", "org/doc.pdf")
        )
        assert result.document_type_prediction is not None
        assert result.document_type_prediction.confidence == 0.9


class TestMissingPatterns:
    """When the regex fails, the field is absent — never invented."""

    def test_non_invoice_text_yields_no_invoice_number(self) -> None:
        """Contract text has no 'Invoice #'; the field simply does not
        appear, which the review UI reads as 'missing'."""
        result = run(
            LightParserProvider(build_text_pdf(CONTRACT_TEXT)).extract("doc-lp-8", "org/doc.pdf")
        )
        keys = {f.key for f in result.fields}
        assert "invoice_number" not in keys
        assert "total_amount" not in keys
