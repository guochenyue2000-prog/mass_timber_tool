"""
inputs.py
=========
Input data model for mass timber floor structural checks.

The :class:`FloorInput` dataclass is intentionally panel-type agnostic so that
CLT, GLT, and NLT checkers can share the same input interface.  Panel-specific
parameters (grade, species, thickness) are carried as plain strings / floats
and interpreted by each checker independently.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FloorInput:
    """
    Input parameters for a mass timber floor panel structural check.

    Designed to be panel-type agnostic so that CLT, GLT, and NLT checkers
    can all consume the same input object without modification.

    Attributes
    ----------
    span : float
        Clear span between supports, in metres (m).
    width : float
        Floor panel width (perpendicular to span), in metres (m).
        Used for load take-down and total modal mass calculations.
    support_condition : str
        Boundary condition descriptor.  Currently supported values:

        - ``"two_sided"``  — simply supported on two edges (span direction).
        - ``"four_sided"`` — supported on all four edges (two-way action).

        The NLT checker assumes ``"two_sided"`` (one-way strip).
    specified_dead_load : float
        Dead load in kN/m², **including concrete topping weight (if any) but excluding** panel self-weight.
        Panel self-weight is added automatically from the section property table by the checker.
    specified_live_load : float
        Specified live load in kN/m² per NBCC Table 4.1.5.3.
    panel_type : str
        Panel system identifier, e.g. ``"NLT"``, ``"CLT"``, ``"GLT"``.
        Used by the checker factory to route to the correct engine.
    nlt_grade : str
        Lumber visual grade, e.g. ``"No.2"``, ``"SS"``, ``"No.1"``.
        Ignored for non-NLT panel types.
    nlt_species : str
        Lumber species group, e.g. ``"SPF"``, ``"HF"``, ``"D.Fir-L"``.
        Ignored for non-NLT panel types.
    nlt_thickness : float
        Total NLT panel thickness in millimetres (mm).
        Must correspond to a key in the NLT section property table.
    """

    span: float                  # m   — clear span between supports
    width: float                 # m   — panel width perpendicular to span
    support_condition: str       # "two_sided" | "four_sided"
    specified_dead_load: float   # kN/m² — SDL + topping, excludes panel self-weight (added in checker)
    specified_live_load: float   # kN/m² — specified live load (NBCC)
    panel_type: str              # "NLT" | "CLT" | "GLT"
    nlt_grade: str               # grade: e.g. "No.2", "SS" for NLT/GLT; "E1","E2","V1","V2" for CLT
    nlt_species: str             # species for NLT/GLT; leave "" for CLT
    nlt_thickness: float         # mm  — total panel thickness
    # --- CLT-specific (ignored for NLT/GLT) ---
    clt_num_plies: int = 0       # number of CLT plies: 3, 5, 7, or 9
    clt_strength_axis: str = "major"  # "major" or "minor" — loading axis relative to grain
    clt_data_source: str = "CSA O86"  # CLT property source: "CSA O86" or "Nordic"
    clt_layup_variant: str = ""       # optional CLT layup tag (e.g., "7s", "7l")
