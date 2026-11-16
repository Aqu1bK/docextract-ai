"""The extraction provider contract: one method, nothing more.

Why an interface instead of calling a specific extraction library: the
same product must run a deterministic Mock on the hosted demo (no cost,
no network, reproducible output), a pypdf-based Light Parser when cost
control matters, and a real Vision LLM in Local Docker Mode from Phase
10 — three backends behind one seam. Call sites depend on
``ExtractionProvider`` and never learn which backend answered; the
factory (``app.extraction.factory``) picks the implementation from
``EXTRACTION_MODE``, a configuration change rather than a code change.

The seam is also what keeps tests honest: a provider that honors this
contract can be swapped for a fake, and the deterministic mock means
end-to-end flows are assertable without stubbing anything. Keeping the
surface to exactly one async method means adding a second backend is
always additive — no call site changes, ever.
"""

from abc import ABC, abstractmethod

from app.schemas.extraction import ExtractionResult


class ExtractionProvider(ABC):
    """One-method contract every extraction backend must implement."""

    @abstractmethod
    async def extract(self, document_id: str, storage_path: str) -> ExtractionResult:
        """Run extraction for one stored document and return its result.

        Args:
            document_id: The document's identity, used for deterministic
                seeding (mock) and result correlation.
            storage_path: The object path in the storage backend; a real
                provider downloads bytes from it, the mock ignores it.

        Returns:
            The extraction result: fields, tables, document type
            prediction, timing, and metadata.

        Raises:
            ExtractionProviderException: If the backend fails (the Phase 7
                worker translates this into a failed job row).
        """
