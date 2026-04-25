"""
test_nlt_check.py
=================
Pytest tests for :class:`NLTChecker`.

``get_nlt_properties`` is mocked via ``unittest.mock.patch`` so that tests are
independent of the NLT_TABLES content and can exercise specific capacity
combinations without requiring table entries to be added.

Test coverage
-------------
Test 1 — All checks pass          : well-proportioned floor, generous capacities.
Test 2 — Bending fails (long span): undersized Mr for a long span + heavy loads.
Test 3 — Deflection fails (low EI): adequate strength but very low stiffness.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from mass_timber_tool.core.inputs import FloorInput
from mass_timber_tool.core.nlt_check import NLTChecker
from mass_timber_tool.core.results import CheckResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_floor(
    span: float,
    specified_dead_load: float,
    specified_live_load: float,
    width: float = 6.0,
    nlt_thickness: float = 235.0,
    nlt_species: str = "SPF",
    nlt_grade: str = "No.2",
) -> FloorInput:
    """Construct a FloorInput with sensible defaults for testing."""
    return FloorInput(
        span=span,
        width=width,
        support_condition="two_sided",
        specified_dead_load=specified_dead_load,
        specified_live_load=specified_live_load,
        panel_type="NLT",
        nlt_grade=nlt_grade,
        nlt_species=nlt_species,
        nlt_thickness=nlt_thickness,
    )


def _mock_props(
    Mr: float,
    Vr: float,
    EI: float,
    self_weight: float = 1.2,
) -> dict[str, float]:
    """Return a mock section property dictionary."""
    return {
        "Mr_kNm_per_m":          Mr,           # kN·m/m — factored moment resistance
        "Vr_kN_per_m":           Vr,           # kN/m   — factored shear resistance
        "EI_kNm2_per_m":         EI,           # kN·m²/m — bending stiffness
        "self_weight_kN_per_m2": self_weight,  # kN/m²  — self-weight
    }


# ---------------------------------------------------------------------------
# Test 1 — All checks pass
# ---------------------------------------------------------------------------

class TestAllChecksPass:
    """
    Verify that a well-proportioned floor with generous capacities
    produces structural_pass=True with all individual checks passing.

    Setup
    -----
    Mock properties : Mr=30.0 kN·m/m, Vr=35.0 kN/m, EI=8000 kN·m²/m, sw=1.2 kN/m²
    Floor           : span=4.0 m, SDL=0.5 kN/m², LL=1.5 kN/m²
    """

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_structural_pass_is_true(self, mock_get: MagicMock) -> None:
        """All ULS and SLS checks should pass for these inputs."""
        mock_get.return_value = _mock_props(Mr=30.0, Vr=35.0, EI=8000.0, self_weight=1.2)

        floor = _make_floor(span=4.0, specified_dead_load=0.5, specified_live_load=1.5)
        result: CheckResult = NLTChecker().run(floor)

        # Overall verdict
        assert result.structural_pass is True, (
            f"Expected structural_pass=True; got bending_util={result.bending_utilization:.3f}, "
            f"shear_util={result.shear_utilization:.3f}, "
            f"δ_inst={result.delta_instantaneous:.2f} mm, "
            f"δ_lt={result.delta_longterm:.2f} mm"
        )

        # Individual ULS checks
        assert result.bending_pass is True, \
            f"Bending should pass: Mf={result.Mf:.3f}, Mr={result.Mr:.1f}"
        assert result.shear_pass is True, \
            f"Shear should pass: Vf={result.Vf:.3f}, Vr={result.Vr:.1f}"

        # Individual SLS checks
        assert result.deflection_L360_pass is True, \
            f"L/360 check should pass"
        assert result.deflection_L240_pass is True, \
            f"L/240 check should pass"
        assert result.deflection_L180_pass is True, \
            f"L/180 check should pass"

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_utilization_ratios_are_below_unity(self, mock_get: MagicMock) -> None:
        """Bending and shear utilization ratios must both be <= 1.0."""
        mock_get.return_value = _mock_props(Mr=30.0, Vr=35.0, EI=8000.0, self_weight=1.2)

        floor = _make_floor(span=4.0, specified_dead_load=0.5, specified_live_load=1.5)
        result: CheckResult = NLTChecker().run(floor)

        assert result.bending_utilization <= 1.0, \
            f"Bending utilization {result.bending_utilization:.3f} should be <= 1.0"
        assert result.shear_utilization <= 1.0, \
            f"Shear utilization {result.shear_utilization:.3f} should be <= 1.0"


# ---------------------------------------------------------------------------
# Test 2 — Bending fails (long span, undersized section)
# ---------------------------------------------------------------------------

class TestBendingFails:
    """
    Verify that a long-span floor with an undersized moment resistance
    produces bending_pass=False.

    Setup
    -----
    Mock properties : Mr=10.0 kN·m/m (deliberately low), Vr=35.0 kN/m,
                      EI=8000 kN·m²/m, sw=1.2 kN/m²
    Floor           : span=7.0 m (long), SDL=1.0 kN/m², LL=2.4 kN/m²

    Expected Mf ≈ (1.25*(1.0+1.2) + 1.5*2.4) * 7² / 8
               ≈ (2.75 + 3.6) * 49/8
               ≈ 6.35 * 6.125 ≈ 38.9 kN·m/m  >> Mr=10.0 kN·m/m
    """

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_bending_pass_is_false(self, mock_get: MagicMock) -> None:
        """Bending check must fail when Mf >> Mr."""
        mock_get.return_value = _mock_props(Mr=10.0, Vr=35.0, EI=8000.0, self_weight=1.2)

        floor = _make_floor(span=7.0, specified_dead_load=1.0, specified_live_load=2.4)
        result: CheckResult = NLTChecker().run(floor)

        assert result.bending_pass is False, (
            f"Expected bending_pass=False; "
            f"Mf={result.Mf:.3f} kN·m/m, Mr={result.Mr:.1f} kN·m/m, "
            f"utilization={result.bending_utilization:.3f}"
        )

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_bending_utilization_exceeds_unity(self, mock_get: MagicMock) -> None:
        """Bending utilization ratio must be strictly greater than 1.0."""
        mock_get.return_value = _mock_props(Mr=10.0, Vr=35.0, EI=8000.0, self_weight=1.2)

        floor = _make_floor(span=7.0, specified_dead_load=1.0, specified_live_load=2.4)
        result: CheckResult = NLTChecker().run(floor)

        assert result.bending_utilization > 1.0, \
            f"Bending utilization should exceed 1.0; got {result.bending_utilization:.3f}"

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_structural_pass_is_false_when_bending_fails(self, mock_get: MagicMock) -> None:
        """Overall structural_pass must be False when bending fails."""
        mock_get.return_value = _mock_props(Mr=10.0, Vr=35.0, EI=8000.0, self_weight=1.2)

        floor = _make_floor(span=7.0, specified_dead_load=1.0, specified_live_load=2.4)
        result: CheckResult = NLTChecker().run(floor)

        assert result.structural_pass is False, \
            "structural_pass must be False when bending check fails"


# ---------------------------------------------------------------------------
# Test 3 — Deflection fails (adequate strength, very low EI)
# ---------------------------------------------------------------------------

class TestDeflectionFails:
    """
    Verify that a floor with adequate strength but very low bending stiffness
    fails at least one SLS deflection limit.

    Setup
    -----
    Mock properties : Mr=50.0 kN·m/m (large — strength OK), Vr=50.0 kN/m,
                      EI=500 kN·m²/m (very low — will cause excessive deflection),
                      sw=1.2 kN/m²
    Floor           : span=6.0 m, SDL=1.5 kN/m², LL=3.0 kN/m²

    Expected deflections (approximate, for verification):
        w_total = 1.2 + 1.5 + 3.0 = 5.7 kN/m
        δ_inst  = 5/384 * 5.7 * 6⁴ / 500 * 1000 ≈ 182 mm >> L/240 = 25 mm
    """

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_at_least_one_deflection_check_fails(self, mock_get: MagicMock) -> None:
        """At least one of L/360, L/240, or L/180 must fail with EI=500."""
        mock_get.return_value = _mock_props(Mr=50.0, Vr=50.0, EI=500.0, self_weight=1.2)

        floor = _make_floor(span=6.0, specified_dead_load=1.5, specified_live_load=3.0)
        result: CheckResult = NLTChecker().run(floor)

        any_deflection_fails: bool = not any([
            result.deflection_L360_pass,
            result.deflection_L240_pass,
            result.deflection_L180_pass,
        ])

        # At least one must fail
        at_least_one_fails: bool = not (
            result.deflection_L360_pass
            and result.deflection_L240_pass
            and result.deflection_L180_pass
        )

        assert at_least_one_fails, (
            f"Expected at least one deflection check to fail; "
            f"δ_inst={result.delta_instantaneous:.2f} mm, "
            f"δ_lt={result.delta_longterm:.2f} mm, "
            f"L/360={'PASS' if result.deflection_L360_pass else 'FAIL'}, "
            f"L/240={'PASS' if result.deflection_L240_pass else 'FAIL'}, "
            f"L/180={'PASS' if result.deflection_L180_pass else 'FAIL'}"
        )

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_strength_checks_still_pass(self, mock_get: MagicMock) -> None:
        """ULS bending and shear should still pass despite deflection failure."""
        mock_get.return_value = _mock_props(Mr=50.0, Vr=50.0, EI=500.0, self_weight=1.2)

        floor = _make_floor(span=6.0, specified_dead_load=1.5, specified_live_load=3.0)
        result: CheckResult = NLTChecker().run(floor)

        assert result.bending_pass is True, \
            f"Bending should pass with Mr=50 kN·m/m; Mf={result.Mf:.2f} kN·m/m"
        assert result.shear_pass is True, \
            f"Shear should pass with Vr=50 kN/m; Vf={result.Vf:.2f} kN/m"

    @patch("mass_timber_tool.core.nlt_check.get_nlt_properties")
    def test_structural_pass_is_false_when_deflection_fails(self, mock_get: MagicMock) -> None:
        """Overall structural_pass must be False when any SLS check fails."""
        mock_get.return_value = _mock_props(Mr=50.0, Vr=50.0, EI=500.0, self_weight=1.2)

        floor = _make_floor(span=6.0, specified_dead_load=1.5, specified_live_load=3.0)
        result: CheckResult = NLTChecker().run(floor)

        assert result.structural_pass is False, \
            "structural_pass must be False when any SLS deflection check fails"
