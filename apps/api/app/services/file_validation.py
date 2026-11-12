"""Pure file-content validation: magic bytes, encryption, page count.

Why extension and client-declared MIME are never trusted (OWASP File
Upload Cheat Sheet, "List of validated files" guidance): both are client
claims — a file named ``invoice.pdf`` with ``Content-Type: application/pdf``
can still be a renamed executable or a crafted file aimed at a parser
bug. The only facts the server controls are the bytes themselves, so the
checks run on content: the PDF magic signature, real encryption state,
and the true page count from parsing the file with pypdf. These functions
are deliberately pure (bytes in, verdict out) so they are unit-testable
with zero I/O and reusable from any endpoint or the live verification
script without a database or storage backend.
"""

import io

from pypdf import PdfReader

from app.errors import (
    EncryptedPdfException,
    PageLimitExceededException,
    UnsupportedFileTypeException,
)

PDF_MAGIC_BYTES = b"%PDF"


def validate_magic_bytes(data: bytes) -> None:
    """Check the file starts with the literal PDF signature ``%PDF``.

    The header of a PDF is exactly those four bytes before the version,
    which no PNG, ZIP, or script can start with; anything else is
    rejected before a PDF parser ever touches the data.

    Raises:
        UnsupportedFileTypeException: If the bytes do not start with ``%PDF``.
    """
    if not data.startswith(PDF_MAGIC_BYTES):
        raise UnsupportedFileTypeException(details={"expected_magic": "%PDF"})


def validate_pdf_structure(data: bytes, max_pages: int) -> int:
    """Parse the PDF and return its true page count.

    One pypdf pass answers three questions the file name cannot: is it
    actually parseable as a PDF, is it encrypted (the demo cannot extract
    from what it cannot read), and how many pages does it really contain.
    ``len(reader.pages)`` counts what the file says it contains, not what
    the client claimed.

    Args:
        data: The full file bytes as stored by the backend.
        max_pages: The per-document page limit from settings.

    Returns:
        The page count, persisted on the documents row.

    Raises:
        EncryptedPdfException: If the file is password-protected.
        PageLimitExceededException: If the page count exceeds ``max_pages``.
    """
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise EncryptedPdfException(details={"reason": "encrypted_pdf"})
    page_count = len(reader.pages)
    if page_count > max_pages:
        raise PageLimitExceededException(details={"max_pages": max_pages})
    return page_count
