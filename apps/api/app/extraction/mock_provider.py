"""The deterministic mock extraction provider for the hosted demo.

Deterministic mocking ensures the same sample document always yields
identical output, which is critical for two things: testing (an
assertion on a mock result is stable across runs, machines, and
contributors) and demo consistency (the public demo shows the same
invoice fields every time, so a screen recording never goes stale).

The trick is hash-based seeding: ``random.Random`` seeded from a stable
digest of the document_id gives a private, reproducible random stream —
the same document_id always walks the same path through field
generation, while different document_ids spread across the fixture
space. Nothing global is shared, so parallel extractions cannot
interfere with each other's sequences.
"""

import asyncio
import hashlib
import random
import time
from typing import Any

from app.extraction.base import ExtractionProvider
from app.extraction.confidence import calculate_confidence
from app.schemas.extraction import (
    DocumentTypePrediction,
    ExtractedField,
    ExtractedTable,
    ExtractionResult,
)

# Fixture vocabulary: the sample space the mock draws from. Kept small
# and legible on purpose — the demo's job is to look like a real run,
# not to be one.
SAMPLE_VENDORS = ["Acme Corp", "Globex", "Initech", "Umbrella", "Stark Industries"]
LINE_ITEM_DESCRIPTIONS = ["Consulting", "Licenses", "Hardware", "Support", "Training"]

# Latency bounds, read at call time so tests can pin them to zero
# without touching the seeded RNG stream (uniform consumes one draw
# whatever the bounds are — determinism is preserved either way).
MIN_LATENCY_SECONDS = 0.5
MAX_LATENCY_SECONDS = 2.0


class MockExtractionProvider(ExtractionProvider):
    """Deterministic fake extractor: reads no bytes, returns fixtures.

    Every field's confidence is produced by the real
    :func:`app.extraction.confidence.calculate_confidence`, so the mock
    exercises the actual scoring path (and the actual review-routing
    consequences) rather than inventing plausible-looking numbers: most
    fields carry full signals and score 0.95, and one deliberately
    degraded field (no evidence) scores low enough to route to review.
    """

    def _seeded_rng(self, document_id: str) -> random.Random:
        """Return a private RNG seeded from the document_id.

        Seeding from a stable SHA-256 digest of the id (rather than the
        built-in ``hash()``, which is salted per process) keeps output
        identical across process restarts — the whole point of
        determinism.
        """
        seed = int.from_bytes(hashlib.sha256(document_id.encode()).digest()[:8], "big")
        return random.Random(seed)

    async def extract(self, document_id: str, storage_path: str) -> ExtractionResult:
        """Generate the deterministic fixture result for this document.

        Args:
            document_id: Seeds the RNG; the same id always produces the
                same fields, values, and confidences.
            storage_path: Accepted for interface parity; the mock never
                reads bytes.

        Returns:
            The fixture ``ExtractionResult`` with source "mock" on every
            field and an always-invoice type prediction.
        """
        started = time.perf_counter()
        rng = self._seeded_rng(document_id)

        # Artificial latency: makes the demo feel real and gives the
        # Phase 7 worker an await point to yield on from day one.
        await asyncio.sleep(rng.uniform(MIN_LATENCY_SECONDS, MAX_LATENCY_SECONDS))

        invoice_number = f"INV-{rng.randint(10000, 99999)}"
        total_amount = round(rng.uniform(100.0, 10000.0), 2)
        due_date = f"2026-0{rng.randint(1, 9)}-2{rng.randint(0, 8)}"

        # Line items whose prices sum exactly to the total: a reviewer
        # who adds the table sees the headline number agree, which is
        # the cheapest realism the mock can buy.
        item_count = rng.randint(2, 4)
        items: list[list[str]] = []
        remaining = total_amount
        for i in range(item_count):
            price = remaining if i == item_count - 1 else round(remaining / 2, 2)
            remaining = round(remaining - price, 2)
            items.append(
                [
                    f"SKU-{rng.randint(100, 999)}",
                    LINE_ITEM_DESCRIPTIONS[rng.randrange(len(LINE_ITEM_DESCRIPTIONS))],
                    f"{price:.2f}",
                ]
            )

        fields: list[ExtractedField] = [
            ExtractedField(
                key="vendor_name",
                label="Vendor Name",
                value=SAMPLE_VENDORS[rng.randrange(len(SAMPLE_VENDORS))],
                confidence=calculate_confidence(
                    source="mock", evidence_match=True, validation_passed=True, is_required=True
                ),
                page_number=1,
                evidence_span="Vendor:",
                source="mock",
            ),
            ExtractedField(
                key="invoice_number",
                label="Invoice Number",
                value=invoice_number,
                confidence=calculate_confidence(
                    source="mock", evidence_match=True, validation_passed=True, is_required=True
                ),
                page_number=1,
                evidence_span=f"Invoice #: {invoice_number}",
                source="mock",
            ),
            ExtractedField(
                key="total_amount",
                label="Total Amount",
                value=total_amount,
                confidence=calculate_confidence(
                    source="mock", evidence_match=True, validation_passed=True, is_required=True
                ),
                page_number=1,
                evidence_span=f"Total: ${total_amount:.2f}",
                source="mock",
            ),
            ExtractedField(
                key="due_date",
                label="Due Date",
                value=due_date,
                # Deliberately degraded: no evidence text for the value,
                # so this field scores below the review threshold and
                # the mock demonstrates routing, not just happy paths.
                confidence=calculate_confidence(
                    source="mock", evidence_match=False, validation_passed=True, is_required=False
                ),
                page_number=1,
                evidence_span=None,
                source="mock",
            ),
        ]

        tables = [
            ExtractedTable(
                headers=["SKU", "Description", "Price"],
                rows=items,
                confidence=calculate_confidence(
                    source="mock", evidence_match=True, validation_passed=True, is_required=False
                ),
                page_number=1,
                source="mock",
            )
        ]

        elapsed = time.perf_counter() - started
        metadata: dict[str, Any] = {
            "provider": "mock",
            "seed_source": "document_id",
            "field_count": len(fields),
        }
        return ExtractionResult(
            document_id=document_id,
            fields=fields,
            tables=tables,
            document_type_prediction=DocumentTypePrediction(type="invoice", confidence=0.95),
            processing_time_seconds=round(elapsed, 3),
            metadata=metadata,
        )
