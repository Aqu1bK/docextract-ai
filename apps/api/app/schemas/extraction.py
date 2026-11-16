"""Extraction result models: the wire contract of every extraction run.

These Pydantic models are the single shape every provider returns and the
Phase 7 worker will persist (and later expose through the API). They are
declared here, in ``app.schemas``, rather than inside the extraction
package, so the dependency arrow stays one-directional: the provider
interface (``app.extraction.base``) imports the models, never the other
way around — the same flat-dependency rule ``app.domain.enums`` follows.

``value`` on ``ExtractedField`` is a union, not a typed column: it is the
in-memory wire shape; persistence maps it onto the typed columns
(``value_text``/``value_number``/``value_date``/``value_json``) declared
by the Phase 3 ``extracted_fields`` table.
"""

from typing import Any

from pydantic import BaseModel, Field

# The closed vocabulary of extraction sources: which backend produced a
# field. The confidence module maps each of these to a source quality.
SOURCES = ("mock", "light_parser", "vision_llm")

# The closed vocabulary of document types the classifier can predict.
DOCUMENT_TYPES = ("invoice", "contract", "rfp", "bill_of_lading", "unknown")


class DocumentTypePrediction(BaseModel):
    """What the classifier believes a document is, with how much belief.

    ``confidence`` is a 0.0-1.0 float produced by the confidence module's
    rules (keyword frequency for the Light Parser, fixed for the mock) —
    never a black-box score.
    """

    type: str = Field(pattern="^(invoice|contract|rfp|bill_of_lading|unknown)$")
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedField(BaseModel):
    """One key/value the pipeline pulled out of a document.

    ``evidence_span`` is the literal text surrounding the match — it is
    what a reviewer glances at to approve or correct the value, and what
    the confidence module means by an evidence match.
    """

    key: str
    label: str
    value: str | float | dict[str, Any] | None
    confidence: float = Field(ge=0.0, le=1.0)
    page_number: int | None = None
    evidence_span: str | None = None
    source: str = Field(pattern="^(mock|light_parser|vision_llm)$")


class ExtractedTable(BaseModel):
    """One table the pipeline extracted, as headers plus string rows."""

    headers: list[str]
    rows: list[list[str]]
    confidence: float = Field(ge=0.0, le=1.0)
    page_number: int | None = None
    source: str = Field(pattern="^(mock|light_parser|vision_llm)$")


class ExtractionResult(BaseModel):
    """Everything one extraction run produced for one document.

    ``processing_time_seconds`` measures the provider call itself (the
    mock's artificial latency included), which is what the Phase 7 job's
    timing columns will record. ``metadata`` carries provider-specific
    context (page counts, classifier keywords) without growing the model.
    """

    document_id: str
    fields: list[ExtractedField]
    tables: list[ExtractedTable]
    document_type_prediction: DocumentTypePrediction | None = None
    processing_time_seconds: float
    metadata: dict[str, Any] = Field(default_factory=dict)
