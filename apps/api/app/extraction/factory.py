"""Extraction provider selection: one function, driven by one env var.

Mirrors the storage factory seam from Phase 5 on purpose: ``EXTRACTION_MODE``
selects the backend exactly as ``STORAGE_PROVIDER`` does, so operating-mode
changes are a matter of environment, never code. Unlike storage, the
factory is a plain function (not a FastAPI dependency) because Phase 6 has
no endpoints — the Phase 7 worker calls it directly when a job is claimed.

The mock is returned without arguments and the Light Parser without I/O
at construction time; both defer any real work to ``extract`` so building
a provider is always cheap and side-effect free.
"""

from app.config import get_settings
from app.errors import InternalErrorException
from app.extraction.base import ExtractionProvider


def get_extraction_provider() -> ExtractionProvider:
    """Return the extraction provider selected by ``EXTRACTION_MODE``.

    Raises:
        InternalErrorException: If ``EXTRACTION_MODE`` is not one of the
            supported values; the envelope's ``details`` names the value
            so an operator sees the misconfiguration immediately.
    """
    mode = get_settings().EXTRACTION_MODE
    if mode == "mock":
        from app.extraction.mock_provider import MockExtractionProvider

        return MockExtractionProvider()
    if mode == "light_parser":
        from app.extraction.light_parser_provider import LightParserProvider

        return LightParserProvider()
    raise InternalErrorException(details={"extraction_mode": mode})
