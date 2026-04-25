"""
panel_selector.py
=================
Runs structural checks for ALL available thicknesses of a given panel type
and returns the full list so the UI can present a summary and let the user
pick which thickness to carry into the vibration check.

Mirrors the GlulamBeamSelector pattern.
"""
from __future__ import annotations

from dataclasses import replace
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from mass_timber_tool.core.inputs import FloorInput
    from mass_timber_tool.core.results import CheckResult

from mass_timber_tool.core.nlt_check import NLTChecker
from mass_timber_tool.core.glt_check import GLTChecker
from mass_timber_tool.core.clt_check import CLTChecker
from mass_timber_tool.data.clt_tables import get_clt_section_options

# All available thicknesses per panel type (matches data tables)
_NLT_THICKNESSES: list[int] = [89, 140, 184, 235, 286]
_GLT_THICKNESSES: list[int] = [80, 130, 175, 215, 265, 315, 365]
class PanelSelector:
    """Iterate all thicknesses, run checks, return every result (pass and fail)."""

    def select_all(self, base: "FloorInput") -> List["CheckResult"]:
        """
        Run structural checks for every available thickness of the panel type
        specified in *base*.  Returns results sorted thinnest → thickest.
        Check result.structural_pass to separate passing from failing sections.
        """
        panel_type = base.panel_type
        results: List["CheckResult"] = []

        if panel_type == "NLT":
            checker = NLTChecker()
            for t in _NLT_THICKNESSES:
                try:
                    results.append(checker.run(replace(base, nlt_thickness=float(t))))
                except (KeyError, ValueError):
                    pass   # thickness not in table for this species/grade

        elif panel_type == "GLT":
            checker = GLTChecker()
            for t in _GLT_THICKNESSES:
                try:
                    results.append(checker.run(replace(base, nlt_thickness=float(t))))
                except (KeyError, ValueError):
                    pass

        elif panel_type == "CLT":
            checker = CLTChecker()
            try:
                options = get_clt_section_options(
                    grade=base.nlt_grade,
                    source=base.clt_data_source,
                )
            except KeyError:
                options = []
            for plies, thick, layup in options:
                try:
                    results.append(
                        checker.run(
                            replace(
                                base,
                                nlt_thickness=float(thick),
                                clt_num_plies=plies,
                                clt_layup_variant=layup,
                            )
                        )
                    )
                except (KeyError, ValueError):
                    pass

        return results
