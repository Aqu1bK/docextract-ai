"""Confidence scoring: weighted signals, not a black-box score.

Every confidence value in DocExtract AI traces back to specific,
printable signals: where the value came from (source quality), whether
the literal evidence text was found next to it, whether the value passed
basic validation, and whether the field is required. A reviewer (or an
interviewer) can ask "why is this 0.42?" and get the exact arithmetic.
That transparency is the point: a magical number cannot be debugged,
defended in a review, or tuned — a formula can.

The same ``CONFIDENCE_THRESHOLD`` (0.75 in ``.env.example``) routes
fields to human review, so the arithmetic below is effectively the
review workload dial for the whole demo.
"""

# Baseline trust per source, before any evidence or validation signal:
# the mock reads nothing real but is consistent by construction; the
# Light Parser reads real bytes but its regexes are brittle; a Vision
# LLM reads the page like a human but can hallucinate.
SOURCE_QUALITY: dict[str, float] = {
    "mock": 0.95,
    "light_parser": 0.7,
    "vision_llm": 0.9,
}

# Multiplicative penalties. A field with no evidence text next to its
# value is the classic over-extraction failure, so it is the heaviest
# single penalty; failed validation is a softer demotion because the
# value shape looked right even if the content check missed.
NO_EVIDENCE_PENALTY = 0.6
VALIDATION_FAILED_PENALTY = 0.8

# A required field that still scores low is more dangerous than an
# optional one (downstream export depends on it), so it never keeps a
# sub-0.5 score: the floor guarantees review routing.
MISSING_REQUIRED_FLOOR = 0.4
REQUIRED_TRIGGER = 0.5

# The mock must never look perfect: 1.0 confidence from a source that
# read no bytes would teach users to trust output nobody verified.
MOCK_CAP = 0.99


def calculate_confidence(
    source: str, evidence_match: bool, validation_passed: bool, is_required: bool
) -> float:
    """Combine four signals into one 0.0-1.0 confidence score.

    The formula is deliberately flat and readable: start from the
    source's baseline trust, multiply in penalties for missing evidence
    and failed validation, apply the required-field floor, and cap the
    mock. Each step is a one-line rule a new graduate can recite.

    Args:
        source: Which backend produced the value ("mock",
            "light_parser", "vision_llm").
        evidence_match: Whether literal evidence text was found for the
            value (the strongest honesty signal a parser can produce).
        validation_passed: Whether the value passed basic content
            validation (parseable number/date, non-empty).
        is_required: Whether the field is required by the extraction
            contract for this document type.

    Returns:
        The combined score, rounded to two decimals.

    Raises:
        ConfidenceScoringException: If ``source`` is not in the known
            vocabulary — an unknown source has no baseline trust, and a
            silent default would quietly inflate scores.
    """
    if source not in SOURCE_QUALITY:
        from app.errors import ConfidenceScoringException

        raise ConfidenceScoringException(details={"unknown_source": source})

    base = SOURCE_QUALITY[source]

    if not evidence_match:
        base *= NO_EVIDENCE_PENALTY
    if not validation_passed:
        base *= VALIDATION_FAILED_PENALTY
    if is_required and base < REQUIRED_TRIGGER:
        base = MISSING_REQUIRED_FLOOR
    if source == "mock":
        base = min(base, MOCK_CAP)

    return round(base, 2)
