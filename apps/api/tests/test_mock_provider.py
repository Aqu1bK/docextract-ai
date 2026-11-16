"""Unit tests for the deterministic Mock extraction provider.

Determinism is the contract under test: the same document_id twice must
produce byte-equal results (model_dump comparison), while a different
document_id must move in the fixture space. Latency is pinned to zero
by monkeypatching the module constants — the RNG stream is untouched,
so the values under test remain the seeded, deterministic ones.
"""

import asyncio

import pytest

from app.extraction import mock_provider
from app.extraction.factory import get_extraction_provider
from app.extraction.mock_provider import MockExtractionProvider


@pytest.fixture
def fast_mock(monkeypatch: pytest.MonkeyPatch) -> MockExtractionProvider:
    """A mock whose artificial latency is pinned to zero.

    ``asyncio.sleep(0)`` still yields to the loop (so the async path is
    exercised), but the test does not pay 0.5-2.0s per call. The RNG
    draw for ``uniform`` happens before the bounds are read, so pinning
    the bounds cannot shift the seeded sequence.
    """
    monkeypatch.setattr(mock_provider, "MIN_LATENCY_SECONDS", 0.0)
    monkeypatch.setattr(mock_provider, "MAX_LATENCY_SECONDS", 0.0)
    return MockExtractionProvider()


def run(coro):
    """Drive one coroutine to completion on a fresh loop."""
    return asyncio.run(coro)


class TestDeterminism:
    """Same id in, identical result out — the core contract."""

    def test_same_document_id_yields_identical_output(
        self, fast_mock: MockExtractionProvider
    ) -> None:
        """Two runs on one id are equal on every field and value."""
        first = run(fast_mock.extract("doc-11111111", "org/doc.pdf"))
        second = run(fast_mock.extract("doc-11111111", "org/doc.pdf"))
        assert first.model_dump() == second.model_dump()

    def test_different_document_id_yields_different_output(
        self, fast_mock: MockExtractionProvider
    ) -> None:
        """A different id walks a different seeded path (invoice number
        is the most visible marker of the RNG stream diverging)."""
        first = run(fast_mock.extract("doc-11111111", "org/a.pdf"))
        second = run(fast_mock.extract("doc-22222222", "org/b.pdf"))
        first_values = {f.key: f.value for f in first.fields}
        second_values = {f.key: f.value for f in second.fields}
        assert first_values != second_values


class TestFields:
    """The fixture contract: the sample invoice's shape."""

    def test_expected_invoice_fields_present(self, fast_mock: MockExtractionProvider) -> None:
        """vendor_name, invoice_number, total_amount, due_date all ship."""
        result = run(fast_mock.extract("doc-33333333", "org/doc.pdf"))
        keys = {f.key for f in result.fields}
        assert {"vendor_name", "invoice_number", "total_amount", "due_date"} <= keys

    def test_line_items_table_present(self, fast_mock: MockExtractionProvider) -> None:
        """One line-items table whose prices sum to the total."""
        result = run(fast_mock.extract("doc-33333333", "org/doc.pdf"))
        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.headers == ["SKU", "Description", "Price"]
        total = {f.key: f.value for f in result.fields}["total_amount"]
        assert isinstance(total, float)
        assert sum(float(row[2]) for row in table.rows) == pytest.approx(total, abs=0.01)

    def test_line_items_sum_matches_total(self, fast_mock: MockExtractionProvider) -> None:
        """The table is internally consistent: rows sum to the headline."""
        result = run(fast_mock.extract("doc-44444444", "org/doc.pdf"))
        total = {f.key: f.value for f in result.fields}["total_amount"]
        assert isinstance(total, float)
        assert sum(float(row[2]) for row in result.tables[0].rows) == pytest.approx(total, abs=0.01)


class TestConfidenceSpread:
    """Most fields high, at least one below threshold — routing works."""

    def test_some_fields_below_review_threshold(self, fast_mock: MockExtractionProvider) -> None:
        """due_date carries no evidence (0.57) while others are 0.95,
        so the result demonstrates both sides of CONFIDENCE_THRESHOLD."""
        result = run(fast_mock.extract("doc-55555555", "org/doc.pdf"))
        confidences = {f.key: f.confidence for f in result.fields}
        assert confidences["due_date"] < 0.75
        assert confidences["total_amount"] >= 0.75

    def test_all_fields_have_source_mock(self, fast_mock: MockExtractionProvider) -> None:
        """Provenance is part of the contract: source='mock' everywhere."""
        result = run(fast_mock.extract("doc-55555555", "org/doc.pdf"))
        assert all(f.source == "mock" for f in result.fields)
        assert all(t.source == "mock" for t in result.tables)

    def test_confidences_within_bounds(self, fast_mock: MockExtractionProvider) -> None:
        """Every confidence is a legal 0.0-1.0 float, capped at 0.99."""
        result = run(fast_mock.extract("doc-55555555", "org/doc.pdf"))
        for f in result.fields:
            assert 0.0 <= f.confidence <= 0.99


class TestDocumentType:
    """The mock always predicts invoice — the demo's sample domain."""

    def test_prediction_is_invoice(self, fast_mock: MockExtractionProvider) -> None:
        """type='invoice' with confidence 0.95, per the fixture spec."""
        result = run(fast_mock.extract("doc-66666666", "org/doc.pdf"))
        assert result.document_type_prediction is not None
        assert result.document_type_prediction.type == "invoice"
        assert result.document_type_prediction.confidence == 0.95


class TestFactorySelection:
    """The env-var seam: EXTRACTION_MODE=mock picks the mock."""

    def test_factory_returns_mock_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default EXTRACTION_MODE is 'mock', so the factory hands back
        the mock provider without any environment mutation."""
        provider = get_extraction_provider()
        assert isinstance(provider, MockExtractionProvider)
