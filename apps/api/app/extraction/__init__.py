"""Extraction engine: the provider seam that turns stored PDFs into data.

This package owns the extraction contract (Pydantic result models, the
``ExtractionProvider`` interface, confidence scoring, and the env-var
factory). It deliberately has no FastAPI, no database, and no queue
imports: Phase 6 is a pure library that Phase 7's worker will call, which
is what lets the whole engine be tested with zero infrastructure.
"""
