"""Unit tests for the confidence scoring module.

Every rule in :mod:`app.extraction.confidence` is one printable line of
arithmetic; these tests pin each line so the formula cannot drift
silently. The ordering test (mock > vision_llm > light_parser) is the
one that guards the source-quality table itself.
"""

from app.errors import ConfidenceScoringException
from app.extraction.confidence import calculate_confidence


class TestSourceQuality:
    """Baseline trust per source, before any signal."""

    def test_mock_outscores_light_parser(self) -> None:
        """mock=0.95 > light_parser=0.7: consistent-by-construction wins."""
        mock = calculate_confidence("mock", True, True, False)
        light = calculate_confidence("light_parser", True, True, False)
        assert mock > light

    def test_vision_llm_outscores_light_parser(self) -> None:
        """vision_llm=0.9 > light_parser=0.7: page-reading beats regex."""
        vision = calculate_confidence("vision_llm", True, True, False)
        light = calculate_confidence("light_parser", True, True, False)
        assert vision > light

    def test_mock_capped_below_perfect(self) -> None:
        """The mock never exceeds 0.99, whatever its signals."""
        assert calculate_confidence("mock", True, True, False) == 0.95
        assert calculate_confidence("mock", True, True, False) <= 0.99

    def test_unknown_source_raises(self) -> None:
        """No baseline trust for an unknown source; silent defaults
        would quietly inflate scores, so it is a hard failure."""
        try:
            calculate_confidence("garbage", True, True, False)
        except ConfidenceScoringException as exc:
            assert exc.details["unknown_source"] == "garbage"
        else:
            raise AssertionError("unknown source must raise ConfidenceScoringException")


class TestEvidencePenalty:
    """Missing evidence text is the heaviest single penalty (x0.6)."""

    def test_no_evidence_reduces_confidence(self) -> None:
        """0.95 * 0.6 = 0.57 for the mock: below review threshold."""
        with_evidence = calculate_confidence("mock", True, True, False)
        without_evidence = calculate_confidence("mock", False, True, False)
        assert without_evidence == round(with_evidence * 0.6, 2)

    def test_evidence_penalty_applies_to_light_parser(self) -> None:
        """0.7 * 0.6 = 0.42: vendor-name style guesses score low."""
        assert calculate_confidence("light_parser", False, True, False) == 0.42


class TestValidationPenalty:
    """Failed validation is a softer demotion (x0.8)."""

    def test_failed_validation_reduces_confidence(self) -> None:
        """0.95 * 0.8 = 0.76 for the mock: a nudge, not a collapse."""
        passed = calculate_confidence("mock", True, True, False)
        failed = calculate_confidence("mock", True, False, False)
        assert failed == round(passed * 0.8, 2)

    def test_both_penalties_stack(self) -> None:
        """0.95 * 0.6 * 0.8 = 0.46: penalties multiply, not min()."""
        both = calculate_confidence("mock", False, False, False)
        assert both == round(0.95 * 0.6 * 0.8, 2)


class TestRequiredFieldFloor:
    """A required field below 0.5 is floored to 0.4 for review routing."""

    def test_low_required_field_gets_floor(self) -> None:
        """0.42 (low) becomes 0.4 (floor): required fields never whisper."""
        assert calculate_confidence("light_parser", False, True, True) == 0.4

    def test_high_required_field_untouched(self) -> None:
        """A confident required field keeps its score; floor is a floor."""
        assert calculate_confidence("mock", True, True, True) == 0.95

    def test_optional_low_field_keeps_low_score(self) -> None:
        """Optional fields skip the floor: 0.42 stays 0.42."""
        assert calculate_confidence("light_parser", False, True, False) == 0.42


class TestMockCap:
    """The mock's ceiling: never 1.0, never 'trust me'."""

    def test_mock_cap_applies_even_with_all_signals(self) -> None:
        """Full-signal mock is 0.95, and no path reaches above 0.99."""
        assert calculate_confidence("mock", True, True, False) == 0.95

    def test_vision_llm_not_capped_at_mock_ceiling(self) -> None:
        """The cap is mock-specific; other sources keep their own bounds."""
        assert calculate_confidence("vision_llm", True, True, False) == 0.9
