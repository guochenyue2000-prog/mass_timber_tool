"""
results.py
==========
Unified output data model for mass timber floor structural checks.

:class:`CheckResult` is returned by every floor checker (NLT, CLT, GLT) and
carries all ULS demands, section resistances, SLS deflections, pass/fail
flags, and reserved fields for the downstream vibration engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from mass_timber_tool.core.inputs import FloorInput


@dataclass
class CheckResult:
    """
    Complete result of a floor panel structural check.

    Includes all demand / capacity values, utilization ratios, SLS deflections,
    and pass/fail flags for ULS and SLS limit states.

    Fields prefixed with ``vibration_`` (or ``fn_`` / ``modal_``) are reserved
    for the downstream vibration engine and are populated after the structural
    check is complete.

    Attributes
    ----------
    floor_input : FloorInput
        Echo of the original input, retained for traceability.

    wu : float
        Governing ULS factored load in kN/m².
    Mf : float
        Factored midspan moment demand in kN·m/m (per unit width).
    Vf : float
        Factored end shear demand in kN/m (per unit width).

    Mr : float
        Factored moment resistance from table in kN·m/m.
    Vr : float
        Factored shear resistance from table in kN/m.
    EI : float
        Bending stiffness from table in kN·m²/m.

    bending_utilization : float
        Bending demand-to-capacity ratio: Mf / Mr.
    shear_utilization : float
        Shear demand-to-capacity ratio: Vf / Vr.
    bending_pass : bool
        True if bending_utilization <= 1.0.
    shear_pass : bool
        True if shear_utilization <= 1.0.

    delta_instantaneous : float
        Total instantaneous deflection under (D + L) in millimetres.
    delta_longterm : float
        Long-term deflection (dead load × creep factor) in millimetres.

    deflection_L360_pass : bool
        Live-load instantaneous deflection <= L / 360.
    deflection_L240_pass : bool
        Total instantaneous deflection (D + L) <= L / 240.
    deflection_L180_pass : bool
        Long-term deflection <= L / 180.

    structural_pass : bool
        True only when all ULS and SLS checks pass simultaneously.

    self_weight_kN_per_m2 : float
        Panel self-weight in kN/m², sourced from the section property table.
    EI_for_vibration : float
        Bending stiffness in kN·m²/m, duplicated here for explicit use by
        the vibration engine without re-querying the table.
    total_mass_kg_per_m2 : float
        Vibration mass in kg/m², computed as (SDL + concrete topping + panel weight) / 9.81 * 1000.
        Note: this now includes all components of the dead load used in structural design.

    fn_analytical : float or None
        Analytical natural frequency in Hz, populated by the vibration engine.
    modal_mass : float or None
        Modal mass in kg, populated by the vibration engine.
    """

    # --- Input passthrough ---
    floor_input: FloorInput                # original input for traceability

    # --- ULS demands ---
    wu: float                              # kN/m²  — governing factored load
    Mf: float                              # kN·m/m — factored moment demand
    Vf: float                              # kN/m   — factored shear demand

    # --- Load duration factor ---
    KD: float                              # dimensionless — CSA O86 Cl. 5.3.2.3 load duration factor

    # --- Section properties (sourced from NLT_TABLES) ---
    Mr: float                              # kN·m/m — factored moment resistance (after KD)
    Vr: float                              # kN/m   — factored shear resistance (after KD)
    EI: float                              # kN·m²/m — bending stiffness per unit width

    # --- ULS utilization ratios and pass/fail ---
    bending_utilization: float             # dimensionless — Mf / Mr
    shear_utilization: float               # dimensionless — Vf / Vr
    bending_pass: bool                     # True if Mf <= Mr
    shear_pass: bool                       # True if Vf <= Vr

    # --- SLS deflections ---
    delta_instantaneous: float             # mm — total (D + L) instantaneous deflection
    delta_live: float                      # mm — live-load-only instantaneous deflection
    delta_longterm: float                  # mm — dead-load long-term (creep) deflection

    # --- SLS pass/fail flags ---
    deflection_L360_pass: bool             # live-load deflection <= L / 360
    deflection_L240_pass: bool             # total instantaneous deflection <= L / 240
    deflection_L180_pass: bool             # long-term deflection <= L / 180

    # --- Overall structural verdict ---
    structural_pass: bool                  # True only if ALL ULS and SLS checks pass

    # --- Vibration engine inputs (populated downstream) ---
    self_weight_kN_per_m2: float           # kN/m²  — panel self-weight from table
    EI_for_vibration: float                # kN·m²/m — bending stiffness for vibration engine
    total_mass_kg_per_m2: float            # kg/m²  — (SDL + topping + panel weight) / 9.81 * 1000

    # --- Optional: vibration engine outputs (reserved) ---
    EI_transverse: Optional[float] = None  # kN·m²/m — transverse EI: CLT exact (minor axis); NLT/GLT ≈ EI/30
    fn_analytical: Optional[float] = None  # Hz — analytical natural frequency
    modal_mass: Optional[float] = None     # kg — modal mass
