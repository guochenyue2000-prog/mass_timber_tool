"""
GlulamBeamSelector — automatically find the minimum glulam beam section.

Given a FloorAndBeamInput and the floor panel CheckResult, iterates through
all tabulated sections for the specified species and grade in order of
increasing cross-section area, returning the first section that passes all
ULS and SLS checks.

Load path
---------
    D_beam = specified_dead_load + panel_result.self_weight_kN_per_m2
    L_beam = specified_live_load  (LLRF applied inside GlulamBeamChecker)
    beam_span = floor.width            (bay width = beam span)
    tributary_width = floor.span / 2   (half panel span per beam)
    beam_self_weight = b * d * GLULAM_UNIT_WEIGHT_kN_per_m3  (estimated)
"""

from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

from ..core.beam_inputs import BeamInput
from ..core.beam_results import BeamCheckResult
from ..core.glulam_beam_check import GlulamBeamChecker
from ..data.glulam_beam_tables import GLULAM_BEAM_TABLES

if TYPE_CHECKING:
    from ..core.floor_and_beam_input import FloorAndBeamInput
    from ..core.results import CheckResult


# Glulam density by species (kg/m³) — used to estimate beam self-weight
_GLULAM_DENSITY: dict = {
    "D.Fir-L":    490.0,
    "Spruce-Pine": 440.0,
}
_GLULAM_DENSITY_DEFAULT: float = 460.0   # kg/m³ — fallback


def _sorted_sections(species: str, grade: str) -> List[Tuple[int, int]]:
    """
    Return all (width_mm, depth_mm) pairs available for the given species and grade,
    sorted by cross-section area (width × depth) ascending.

    Parameters
    ----------
    species : str   e.g. "D.Fir-L", "Spruce-Pine"
    grade   : str   e.g. "20f-E", "24f-E"

    Returns
    -------
    List of (width_mm, depth_mm) tuples, smallest area first.
    """
    sections: List[Tuple[int, int]] = []
    for width_mm, depth_dict in GLULAM_BEAM_TABLES.items():
        for depth_mm, species_dict in depth_dict.items():
            if species in species_dict and grade in species_dict[species]:
                sections.append((width_mm, depth_mm))
    # Sort by cross-section area ascending (smallest first)
    sections.sort(key=lambda bd: bd[0] * bd[1])
    return sections


class GlulamBeamSelector:
    """
    Selects glulam beam cross-sections that pass all ULS and SLS checks.

    Usage
    -----
    >>> selector = GlulamBeamSelector()
    >>> all_results = selector.select_all(inp, panel_result)  # all passing sections
    >>> min_result  = selector.select(inp, panel_result)      # minimum section only
    """

    def _build_inputs(
        self,
        inp: "FloorAndBeamInput",
        panel_result: "CheckResult",
    ):
        """Derive shared beam parameters and return (D_beam, L_beam, beam_span, trib, checker, sections)."""
        D_beam: float = inp.specified_dead_load + panel_result.self_weight_kN_per_m2
        L_beam: float = inp.specified_live_load
        beam_span: float = inp.width
        trib: float = inp.span / 2.0
        checker = GlulamBeamChecker()
        sections = _sorted_sections(inp.beam_species, inp.beam_grade)
        if not sections:
            raise ValueError(
                f"No tabulated sections found for species='{inp.beam_species}', "
                f"grade='{inp.beam_grade}'."
            )
        return D_beam, L_beam, beam_span, trib, checker, sections

    def _run_section(
        self,
        width_mm: int, depth_mm: int,
        species: str, grade: str,
        D_beam: float, L_beam: float,
        beam_span: float, trib: float,
        checker: GlulamBeamChecker,
    ) -> BeamCheckResult:
        rho = _GLULAM_DENSITY.get(species, _GLULAM_DENSITY_DEFAULT)
        sw: float = (width_mm / 1000.0) * (depth_mm / 1000.0) * rho * 9.81 / 1000.0
        beam = BeamInput(
            span=beam_span,
            tributary_width=trib,
            width_mm=width_mm,
            depth_mm=depth_mm,
            species=species,
            grade=grade,
            specified_dead_load=D_beam,
            specified_live_load=L_beam,
            bracing_condition="fully_braced",
            unsupported_length_mm=0.0,
            beam_self_weight_kN_per_m=sw,
        )
        return checker.run(beam)

    def select_all(
        self,
        inp: "FloorAndBeamInput",
        panel_result: "CheckResult",
    ) -> "List[BeamCheckResult]":
        """
        Return ALL passing glulam beam sections, sorted by cross-section area (smallest first).

        Raises ValueError if no section passes.
        """
        D_beam, L_beam, beam_span, trib, checker, sections = self._build_inputs(inp, panel_result)

        passing: List[BeamCheckResult] = []
        for width_mm, depth_mm in sections:
            result = self._run_section(
                width_mm, depth_mm, inp.beam_species, inp.beam_grade,
                D_beam, L_beam, beam_span, trib, checker,
            )
            if result.structural_pass:
                passing.append(result)

        if not passing:
            raise ValueError(
                f"No tabulated section passes all checks for "
                f"species='{inp.beam_species}', grade='{inp.beam_grade}', "
                f"beam_span={beam_span:.2f} m, D={D_beam:.2f} kN/m2, L={L_beam:.2f} kN/m2. "
                f"Consider a different species/grade or reducing loads."
            )
        return passing

    def select(
        self,
        inp: "FloorAndBeamInput",
        panel_result: "CheckResult",
    ) -> BeamCheckResult:
        """Return the minimum (lightest) passing glulam beam section."""
        return self.select_all(inp, panel_result)[0]
