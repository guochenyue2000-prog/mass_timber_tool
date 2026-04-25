"""
BeamCheckResult dataclass — output of a glulam beam ULS + SLS check.

All computed quantities are stored here so the caller can inspect
any intermediate value, print reports, or feed results downstream
(e.g. vibration checks on the supporting beam).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .beam_inputs import BeamInput


@dataclass
class BeamCheckResult:
    """
    Complete results of a glulam beam ULS and SLS structural check.

    Attributes
    ----------
    beam_input : BeamInput
        Reference to the original input (pass-through for reporting).

    --- Load takedown ---
    wu_kN_per_m : float
        Governing ULS factored line load on beam, kN/m.
        = governing NBCC combo × tributary_width + 1.25 × beam self-weight.
    w_kN_per_m : float
        Specified total line load (D + L) for SLS, kN/m.
    wL_kN_per_m : float
        Specified live-load line load only, kN/m (for L/360 deflection).
    KD : float
        Load duration factor per CSA O86 Cl. 5.3.2.3, bounded [0.65, 1.0].

    --- ULS demands ---
    Mf_kNm : float
        Factored midspan moment, kN·m. = wu × L² / 8.
    Vf_kN : float
        Factored shear at support, kN. = wu × L / 2.
    Wf_kN : float
        Total factored load on beam, kN. = wu × L (used for Wr check).

    --- Resistance adjustment factors ---
    CB : float
        Slenderness ratio C_B = √(Le × d / b²). 0.0 if fully braced.
    KL : float
        Lateral stability factor (Table 2.9). 1.0 if fully braced.
    KZbg : float
        Size factor K_Zbg = (130/b)^(1/10) × (610/d)^(1/10) × (9100/L_mm)^(1/10),
        capped at 1.3.
    governing_factor : str
        Which of KL or KZbg governs (lower value): "KL" or "KZbg".

    --- Table-lookup values ---
    Mr_prime_kNm : float
        M'r from Beam Selection Table (unadjusted), kN·m.
    Vr_table_kN : float
        V_r from table (simplified shear check, volume < 2 m³), kN.
    WrL018 : float
        W_r·L^0.18 product from table (volume-based shear), kN·m^0.18.
    EsI_kNm2 : float
        E_s·I bending stiffness from table, kN·m².

    --- Adjusted resistances ---
    Mr_kNm : float
        Adjusted factored moment resistance: M'r × min(KL, KZbg) × KD, kN·m.
    Wr_kN : float
        Volume-based shear resistance: WrL018 / L^0.18, kN.
    beam_volume_m3 : float
        Total beam volume b × d × L, m³. Determines which shear method governs.

    --- ULS check results ---
    bending_utilization : float
        Mf / Mr (dimensionless). < 1.0 = pass.
    shear_utilization : float
        Governing shear utilization ratio (dimensionless). < 1.0 = pass.
        Uses Wf/Wr (volume-based method, Cl. 7.5.7.2a) as the governing check.
    bending_pass : bool
        True if Mf ≤ Mr.
    shear_pass : bool
        True if shear utilization ≤ 1.0.

    --- SLS deflection results ---
    delta_live_mm : float
        Instantaneous live-load deflection, mm. = 5 wL L⁴ / (384 EI).
    delta_total_mm : float
        Instantaneous total (D+L) deflection, mm.
    deflection_L360_pass : bool
        True if delta_live ≤ L/360.
    deflection_L180_pass : bool
        True if delta_total ≤ L/180.

    --- Overall verdict ---
    structural_pass : bool
        True only if bending_pass AND shear_pass AND deflection_L360_pass
        AND deflection_L180_pass are all True.

    --- Reserved for downstream vibration check ---
    fn_analytical : float or None
        Analytical natural frequency, Hz. Populated by vibration engine.
    modal_mass : float or None
        Modal mass, kg. Populated by vibration engine.
    """

    # Input reference
    beam_input: "BeamInput"

    # Load takedown
    LLRF: float                     # dimensionless — live load reduction factor (NBC 4.1.5.8)
    live_load_reduced: float        # kN/m² — reduced live load = specified_live_load × LLRF
    wu_kN_per_m: float              # kN/m — governing ULS line load
    w_kN_per_m: float               # kN/m — specified total line load (SLS)
    wL_kN_per_m: float              # kN/m — live-only line load (SLS)
    KD: float                       # dimensionless — load duration factor

    # ULS demands
    Mf_kNm: float                   # kN·m — factored moment
    Vf_kN: float                    # kN   — factored shear
    Wf_kN: float                    # kN   — total factored load

    # Adjustment factors
    CB: float                       # dimensionless — slenderness ratio
    KL: float                       # dimensionless — lateral stability factor
    KZbg: float                     # dimensionless — size factor
    governing_factor: str           # "KL" or "KZbg"

    # Table-lookup values
    Mr_prime_kNm: float             # kN·m — M'r unadjusted
    Vr_table_kN: float              # kN   — Vr from table
    WrL018: float                   # kN·m^0.18 — Wr·L^0.18 product
    EsI_kNm2: float                 # kN·m² — bending stiffness

    # Adjusted resistances
    Mr_kNm: float                   # kN·m — adjusted Mr
    Wr_kN: float                    # kN   — volume-based shear resistance
    beam_volume_m3: float           # m³   — beam volume

    # ULS results
    bending_utilization: float      # dimensionless — Mf / Mr
    shear_utilization: float        # dimensionless — Wf / Wr
    bending_pass: bool
    shear_pass: bool

    # SLS deflections
    delta_live_mm: float            # mm — live-load deflection
    delta_total_mm: float           # mm — total deflection
    deflection_L360_pass: bool      # live ≤ L/360
    deflection_L180_pass: bool      # total ≤ L/180

    # Overall verdict
    structural_pass: bool

    # Reserved for vibration engine
    fn_analytical: Optional[float] = None   # Hz
    modal_mass: Optional[float] = None      # kg
