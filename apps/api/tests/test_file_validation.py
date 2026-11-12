# docextract-ai/apps/api/tests/test_file_validation.py

"""Unit tests for pure file validation: magic bytes, encryption, page count.

These are the server's own checks on the bytes, so every test builds a
REAL PDF with pypdf — a blank-page document is a minimal valid PDF —
rather than a fixture file, keeping the tests hermetic and the bytes
under the test's control.
"""

import io

from pypdf import PdfReader, PdfWriter

from app.errors import (
    EncryptedPdfException,
    PageLimitExceededException,
    UnsupportedFileTypeException,
)
from app.services.file_validation import validate_magic_bytes, validate_pdf_structure


def build_pdf(page_count: int, encrypt: bool = False, user_password: str = "secret") -> bytes:
    """Build an in-memory PDF with a chosen page count and encryption."""

    def render() -> bytes:
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=200.0, height=200.0)
        if encrypt:
            writer.encrypt(user_password)
        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()

    return render()


class TestValidateMagicBytes:
    """The four-byte signature check at the very front of validation."""

    def test_real_pdf_header_passes(self) -> None:
        """A pypdf-built file starts with %PDF and is accepted."""
        validate_magic_bytes(build_pdf(1))

    def test_png_bytes_are_rejected(self) -> None:
        """A PNG header is not %PDF; 415 is the response contract."""
        try:
            validate_magic_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
        except UnsupportedFileTypeException as exc:
            assert exc.details["expected_magic"] == "%PDF"
        else:
            raise AssertionError("PNG bytes must be rejected")

    def test_plain_text_is_rejected(self) -> None:
        """A renamed text file fails the signature check before parsing."""
        try:
            validate_magic_bytes(b"hello, not a pdf at all")
        except UnsupportedFileTypeException:
            pass
        else:
            raise AssertionError("plain text must be rejected")


class TestValidatePdfStructure:
    """Structure checks: encryption and the true page count."""

    def test_page_count_returned(self) -> None:
        """The parser returns what the file really contains."""
        assert validate_pdf_structure(build_pdf(3), max_pages=20) == 3

    def test_encrypted_pdf_raises(self) -> None:
        """An encrypted file cannot be read; 422 is the contract."""
        try:
            validate_pdf_structure(build_pdf(1, encrypt=True), max_pages=20)
        except EncryptedPdfException as exc:
            assert exc.details["reason"] == "encrypted_pdf"
        else:
            raise AssertionError("encrypted PDF must raise EncryptedPdfException")

    def test_page_limit_enforced(self) -> None:
        """A 21-page file against MAX_PAGES=20 raises 422 with the limit."""
        try:
            validate_pdf_structure(build_pdf(21), max_pages=20)
        except PageLimitExceededException as exc:
            assert exc.details["max_pages"] == 20
        else:
            raise AssertionError("21 pages against a 20-page limit must raise")


class TestReaderAgreement:
    """Sanity: our builder and pypdf agree on what a PDF contains."""

    def test_built_pdf_parses(self) -> None:
        """The fixture builder produces files pypdf can actually read."""
        reader = PdfReader(io.BytesIO(build_pdf(2)))
        assert len(reader.pages) == 2
