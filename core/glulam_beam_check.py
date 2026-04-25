"""
Glulam beam ULS and SLS check engine — CSA O86 / CWC Wood Design Manual.

Design procedure:
    1.  Load takedown: area loads × tributary width → line loads
    2.  K_D: load duration factor (CSA O86 Cl. 5.3.2.3)
    3.  ULS demands: Mf = wu L²/8,  Vf = wu L/2,  Wf = wu L
    4.  Table lookup: M'r, Vr, WrL^0.18, EsI
    5.  K_Zbg size factor (capped at 1.3)
    6.  K_L lateral stability factor (Table 2.9, interpolated)
    7.  Adjusted Mr = M'r × min(KL, KZbg) × KD
    8.  Shear: Wr = WrL^0.18 / L^0.18   (C_v = 3.69 for all cases)
    9.  Deflections: 5wL⁴/(384EI)  →  limits L/360 (live), L/180 (total)
    10. Return BeamCheckResult

References:
    CSA O86-19 Clauses 5.3.2.3, 7.5.6, 7.5.7
    CWC Wood Design Manual (2017), Tables 2.8, 2.9, pp. 68–73
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ..core.beam_inputs import BeamInput
from ..core.beam_results import BeamCheckResult
from ..core.loads import factored_load, load_duration_factor
from ..data.glulam_beam_tables import get_glulam_beam_properties


# ---------------------------------------------------------------------------
# Table 2.9 — K_L values for glulam beams (CWC Wood Design Manual)
# Columns: "20f-E D.Fir-L", "20f-E Spruce-Pine", "24f-E D.Fir-L", "24f-E Hem-Fir"
# Rows: C_B values from 10 to 50 in steps of 2
# Note: For C_B < 10, KL = 1.0 (no stability reduction)
#       For C_B > 50, use lowest tabulated KL value (conservative)
# ---------------------------------------------------------------------------
_KL_CB_STEPS: Tuple[int, ...] = (
    10, 12, 14, 16, 18, 20, 22, 24, 26, 28,
    30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50,
)

# KL_TABLE[column_key] = list of KL values corresponding to _KL_CB_STEPS
_KL_TABLE: Dict[str, Tuple[float, ...]] = {
    "20f-E D.Fir-L": (
        1.000, 0.969, 0.942, 0.901, 0.841, 0.758, 0.651, 0.547, 0.466, 0.402,
        0.350, 0.307, 0.272, 0.243, 0.218, 0.197, 0.178, 0.163, 0.149, 0.137, 0.126,
    ),
    "20f-E Spruce-Pine": (
        1.000, 0.955, 0.916, 0.857, 0.770, 0.654, 0.540, 0.454, 0.387, 0.334,
        0.291, 0.255, 0.226, 0.202, 0.181, 0.163, 0.148, 0.135, 0.124, 0.114, 0.105,
    ),
    "24f-E D.Fir-L": (
        1.000, 0.958, 0.922, 0.867, 0.787, 0.676, 0.562, 0.472, 0.402, 0.347,
        0.302, 0.266, 0.235, 0.210, 0.188, 0.170, 0.154, 0.140, 0.128, 0.118, 0.109,
    ),
    "24f-E Hem-Fir": (
        1.000, 0.960, 0.926, 0.873, 0.797, 0.691, 0.575, 0.483, 0.412, 0.355,
        0.309, 0.272, 0.241, 0.215, 0.193, 0.174, 0.158, 0.144, 0.132, 0.121, 0.111,
    ),
}


def _kl_column_key(species: str, grade: str) -> str:
    """
    Map (species, grade) to the appropriate KL table column.

    Spruce-Pine is only available as 20f-E.
    D.Fir-L is available as 20f-E or 24f-E.
    Hem-Fir is available as 24f-E (future extension).
    """
    if species == "Spruce-Pine":
        return "20f-E Spruce-Pine"
    elif species == "D.Fir-L" and grade == "20f-E":
        return "20f-E D.Fir-L"
    elif species == "D.Fir-L" and grade == "24f-E":
        return "24f-E D.Fir-L"
    elif species == "Hem-Fir" and grade == "24f-E":
        return "24f-E Hem-Fir"
    else:
        raise ValueError(
            f"No KL column for species='{species}', grade='{grade}'. "
            "Valid combinations: ('Spruce-Pine','20f-E'), ('D.Fir-L','20f-E'), "
            "('D.Fir-L','24f-E'), ('Hem-Fir','24f-E')."
        )


def _interpolate_kl(cb: float, column_key: str) -> float:
    """
    Linearly interpolate K_L from Table 2.9 given slenderness C_B.

    Parameters
    ----------
    cb : float
        Slenderness ratio C_B = sqrt(Le * d / b²).
    column_key : str
        Table column identifier from _kl_column_key().

    Returns
    -------
    float
        K_L value, in range (0, 1.0].
    """
    kl_values = _KL_TABLE[column_key]

    if cb <= _KL_CB_STEPS[0]:
        return 1.0  # No stability reduction below minimum tabulated CB

    if cb >= _KL_CB_STEPS[-1]:
        return kl_values[-1]  # Conservative: use lowest tabulated value

    # Find bounding interval and interpolate
    for i in range(len(_KL_CB_STEPS) - 1):
        cb_lo = _KL_CB_STEPS[i]
        cb_hi = _KL_CB_STEPS[i + 1]
        if cb_lo <= cb <= cb_hi:
            t = (cb - cb_lo) / (cb_hi - cb_lo)  # interpolation fraction
            return kl_values[i] + t * (kl_values[i + 1] - kl_values[i])

    return kl_values[-1]  # Fallback (should not reach here)


def _compute_kl(beam: BeamInput) -> Tuple[float, float]:
    """
    Compute the lateral stability factor K_L and slenderness C_B.

    For "fully_braced": KL = 1.0, CB = 0.0.
    For "unbraced": Le = 1.92 × unsupported_length_mm (Table 2.8, UDL + intermediate support),
                    CB = sqrt(Le × d / b²), KL from Table 2.9.

    Returns
    -------
    (KL, CB) : Tuple[float, float]
    """
    if beam.bracing_condition == "fully_braced":
        return 1.0, 0.0

    b: float = beam.width_mm   # mm
    d: float = beam.depth_mm   # mm
    a: float = beam.unsupported_length_mm  # mm — unsupported length

    if a <= 0.0:
        raise ValueError(
            "unsupported_length_mm must be > 0 when bracing_condition == 'unbraced'."
        )

    le: float = 1.92 * a            # mm — effective length (Table 2.8, UDL, intermediate support)
    cb: float = math.sqrt(le * d / b ** 2)  # dimensionless — slenderness ratio

    col = _kl_column_key(beam.species, beam.grade)
    kl = _interpolate_kl(cb, col)
    return kl, cb


def _compute_kzbg(b_mm: float, d_mm: float, span_m: float) -> float:
    """
    Compute the size factor K_Zbg per CSA O86 / CWC Wood Design Manual.

    K_Zbg = (130/b)^(1/10) × (610/d)^(1/10) × (9100/L_mm)^(1/10)
    Capped at 1.3.

    Parameters
    ----------
    b_mm : float   Beam width, mm.
    d_mm : float   Beam depth, mm.
    span_m : float Beam span, m.

    Returns
    -------
    float  K_Zbg, dimensionless, ≤ 1.3.
    """
    l_mm: float = span_m * 1000.0  # convert to mm
    kzbg: float = (
        (130.0 / b_mm) ** (1.0 / 10.0)
        * (610.0 / d_mm) ** (1.0 / 10.0)
        * (9100.0 / l_mm) ** (1.0 / 10.0)
    )
    return min(kzbg, 1.3)


def _deflection_mm(w_kN_per_m: float, span_m: float, esi_kNm2: float) -> float:
    """
    Euler beam midspan deflection for a simply-supported UDL.

    delta = 5 w L⁴ / (384 EI)

    Parameters
    ----------
    w_kN_per_m : float   Applied line load, kN/m.
    span_m : float       Span, m.
    esi_kNm2 : float     E_s·I bending stiffness, kN·m².

    Returns
    -------
    float  Midspan deflection, mm.
    """
    delta_m: float = (5.0 * w_kN_per_m * span_m ** 4) / (384.0 * esi_kNm2)
    return delta_m * 1000.0  # convert m → mm


class GlulamBeamChecker:
    """
    Glulam floor beam ULS and SLS checker per CSA O86 / CWC Wood Design Manual.

    Checks performed
    ----------------
    ULS:
        Bending : Mr = M'r × min(KL, KZbg) × KD  ≥  Mf
        Shear   : Wr = WrL^0.18 / L^0.18          ≥  Wf   (volume-based, all volumes)
    SLS:
        L/360   : delta_live  ≤ L/360
        L/180   : delta_total ≤ L/180

    Usage
    -----
    >>> from mass_timber_tool.core.beam_inputs import BeamInput
    >>> from mass_timber_tool.core.glulam_beam_check import GlulamBeamChecker
    >>> beam = BeamInput(span=7.5, tributary_width=5.0, width_mm=175, depth_mm=608,
    ...                  species="D.Fir-L", grade="24f-E",
    ...                  specified_dead_load=2.0, specified_live_load=2.4,
    ...                  bracing_condition="fully_braced")
    >>> result = GlulamBeamChecker().run(beam)
    """

    def run(self, beam: BeamInput) -> BeamCheckResult:
        """
        Execute all ULS and SLS checks for the given beam input.

        Parameters
        ----------
        beam : BeamInput
            Fully populated beam input dataclass.

        Returns
        -------
        BeamCheckResult
            All intermediate and final check results.
        """
        L: float = beam.span                    # m
        b: float = float(beam.width_mm)         # mm
        d: float = float(beam.depth_mm)         # mm
        D: float = beam.specified_dead_load     # kN/m² — area dead load
        LL: float = beam.specified_live_load    # kN/m² — area live load (specified)
        trib: float = beam.tributary_width      # m

        # ------------------------------------------------------------------
        # Step 1: Live load reduction factor (LLRF) — NBC Article 4.1.5.8
        # Applied when tributary area > 20 m²
        # LLRF = 0.3 + sqrt(9.8 / A_trib),  capped at 1.0
        # ------------------------------------------------------------------
        A_trib: float = L * trib               # m² — tributary area
        if A_trib > 20.0:
            LLRF: float = min(0.3 + math.sqrt(9.8 / A_trib), 1.0)
        else:
            LLRF = 1.0                          # no reduction below 20 m²
        LL_red: float = LL * LLRF              # kN/m² — reduced live load

        # ------------------------------------------------------------------
        # Step 2: K_D — load duration factor (uses specified live load per CSA O86)
        # Specified (unreduced) live load is used for the P_L/P_S comparison,
        # not the LLRF-reduced value.
        # ------------------------------------------------------------------
        KD: float = load_duration_factor(D, LL)  # bounded [0.65, 1.0]

        # ------------------------------------------------------------------
        # Step 3: Load takedown — area loads → line loads
        # ------------------------------------------------------------------
        wu_area: float = factored_load(D, LL_red)    # kN/m² — governing ULS combo
        wu: float = wu_area * trib + 1.25 * beam.beam_self_weight_kN_per_m  # kN/m
        w: float = (D + LL_red) * trib + beam.beam_self_weight_kN_per_m     # kN/m — SLS total
        wL: float = LL_red * trib                                            # kN/m — SLS live only

        # ------------------------------------------------------------------
        # Step 4: ULS demands (simple span)
        # ------------------------------------------------------------------
        Mf: float = wu * L ** 2 / 8.0   # kN·m — factored midspan moment
        Vf: float = wu * L / 2.0        # kN   — factored shear at support
        Wf: float = wu * L              # kN   — total factored load on beam

        # ------------------------------------------------------------------
        # Step 4: Table lookup
        # ------------------------------------------------------------------
        entry = get_glulam_beam_properties(beam.width_mm, beam.depth_mm, beam.species, beam.grade)
        Mr_prime: float = entry["Mr_prime_kNm"]   # kN·m
        Vr_table: float = entry["Vr_kN"]          # kN
        WrL018: float   = entry["WrL018"]          # kN·m^0.18
        EsI: float      = entry["EsI_kNm2"]        # kN·m²

        # ------------------------------------------------------------------
        # Step 5: K_Zbg — size factor
        # ------------------------------------------------------------------
        KZbg: float = _compute_kzbg(b, d, L)

        # ------------------------------------------------------------------
        # Step 6: K_L — lateral stability factor
        # ------------------------------------------------------------------
        KL, CB = _compute_kl(beam)

        # ------------------------------------------------------------------
        # Step 7: Adjusted M_r
        # ------------------------------------------------------------------
        k_governing: float = min(KL, KZbg)
        governing_factor: str = "KL" if KL <= KZbg else "KZbg"
        Mr: float = Mr_prime * k_governing * KD   # kN·m

        # ------------------------------------------------------------------
        # Step 8: Shear resistance — volume-based (Cl. 7.5.7.2a)
        # C_v = 3.69 for simply-supported UDL (fixed, all cases)
        # Wr·L^0.18 is read directly from table, recover Wr:
        #   Wr = (WrL^0.18) / L^0.18
        # ------------------------------------------------------------------
        beam_volume: float = (b / 1000.0) * (d / 1000.0) * L  # m³
        Wr: float = WrL018 / (L ** 0.18)   # kN

        # ------------------------------------------------------------------
        # Step 9: ULS pass/fail
        # ------------------------------------------------------------------
        bending_util: float = Mf / Mr
        shear_util: float   = Wf / Wr
        bending_pass: bool  = bending_util <= 1.0
        shear_pass: bool    = shear_util <= 1.0

        # ------------------------------------------------------------------
        # Step 10: SLS deflections
        # ------------------------------------------------------------------
        delta_live: float  = _deflection_mm(wL, L, EsI)   # mm — live load
        delta_total: float = _deflection_mm(w, L, EsI)    # mm — total (D+L)

        limit_L360: float = (L * 1000.0) / 360.0   # mm
        limit_L180: float = (L * 1000.0) / 180.0   # mm

        defl_L360_pass: bool = delta_live  <= limit_L360
        defl_L180_pass: bool = delta_total <= limit_L180

        # ------------------------------------------------------------------
        # Step 11: Overall verdict
        # ------------------------------------------------------------------
        structural_pass: bool = (
            bending_pass and shear_pass and defl_L360_pass and defl_L180_pass
        )

        return BeamCheckResult(
            beam_input=beam,
            # Loads
            LLRF=LLRF,
            live_load_reduced=LL_red,
            wu_kN_per_m=wu,
            w_kN_per_m=w,
            wL_kN_per_m=wL,
            KD=KD,
            # Demands
            Mf_kNm=Mf,
            Vf_kN=Vf,
            Wf_kN=Wf,
            # Factors
            CB=CB,
            KL=KL,
            KZbg=KZbg,
            governing_factor=governing_factor,
            # Table values
            Mr_prime_kNm=Mr_prime,
            Vr_table_kN=Vr_table,
            WrL018=WrL018,
            EsI_kNm2=EsI,
            # Adjusted resistances
            Mr_kNm=Mr,
            Wr_kN=Wr,
            beam_volume_m3=beam_volume,
            # ULS results
            bending_utilization=bending_util,
            shear_utilization=shear_util,
            bending_pass=bending_pass,
            shear_pass=shear_pass,
            # SLS deflections
            delta_live_mm=delta_live,
            delta_total_mm=delta_total,
            deflection_L360_pass=defl_L360_pass,
            deflection_L180_pass=defl_L180_pass,
            # Overall
            structural_pass=structural_pass,
        )


def print_beam_report(result: BeamCheckResult) -> None:
    """
    Print a formatted summary of the glulam beam check results.

    Parameters
    ----------
    result : BeamCheckResult
        Completed beam check result.
    """
    b = result.beam_input
    r = result
    L = b.span

    verdict = "PASS" if r.structural_pass else "FAIL"
    sep = "=" * 60

    print(sep)
    print(f"  GLULAM BEAM CHECK  --  {verdict}")
    print(sep)
    print(f"  Beam        : {b.width_mm} x {b.depth_mm} mm  {b.species}  {b.grade}")
    print(f"  Span        : {L:.2f} m   Tributary width: {b.tributary_width:.2f} m")
    print(f"  Bracing     : {b.bracing_condition}")
    print()
    a_trib: float = b.span * b.tributary_width   # m²
    print("  LOADS")
    print(f"    Dead (area)       : {b.specified_dead_load:.2f} kN/m2")
    print(f"    Live (specified)  : {b.specified_live_load:.2f} kN/m2")
    print(f"    Tributary area    : {a_trib:.1f} m2")
    print(f"    LLRF              : {r.LLRF:.3f}  (NBC 4.1.5.8{'  -- no reduction' if r.LLRF == 1.0 else ''})")
    print(f"    Live (reduced)    : {r.live_load_reduced:.2f} kN/m2")
    print(f"    K_D               : {r.KD:.3f}")
    print(f"    wu (line, ULS)    : {r.wu_kN_per_m:.2f} kN/m")
    print(f"    w  (line, SLS)    : {r.w_kN_per_m:.2f} kN/m")
    print()
    print("  ULS DEMANDS")
    print(f"    Mf                : {r.Mf_kNm:.1f} kN.m")
    print(f"    Vf                : {r.Vf_kN:.1f} kN")
    print(f"    Wf (total)        : {r.Wf_kN:.1f} kN")
    print()
    print("  RESISTANCE FACTORS")
    print(f"    CB                : {r.CB:.2f}")
    print(f"    KL                : {r.KL:.3f}")
    print(f"    KZbg              : {r.KZbg:.3f}  (governing: {r.governing_factor})")
    print()
    print("  ULS CHECKS")
    bend_flag = "PASS" if r.bending_pass else "FAIL"
    shear_flag = "PASS" if r.shear_pass else "FAIL"
    print(f"    M'r (table)       : {r.Mr_prime_kNm:.1f} kN.m")
    print(f"    Mr (adjusted)     : {r.Mr_kNm:.1f} kN.m")
    print(f"    Mf / Mr           : {r.bending_utilization:.3f}  [{bend_flag}]")
    print(f"    Wr (volume-based) : {r.Wr_kN:.1f} kN   (volume={r.beam_volume_m3:.3f} m3)")
    print(f"    Wf / Wr           : {r.shear_utilization:.3f}  [{shear_flag}]")
    print()
    print("  SLS DEFLECTIONS")
    l360_flag = "PASS" if r.deflection_L360_pass else "FAIL"
    l180_flag = "PASS" if r.deflection_L180_pass else "FAIL"
    limit_l360 = L * 1000.0 / 360.0
    limit_l180 = L * 1000.0 / 180.0
    print(f"    EsI               : {r.EsI_kNm2:.0f} kN.m2")
    print(f"    d_live            : {r.delta_live_mm:.1f} mm  (limit L/360 = {limit_l360:.1f} mm)  [{l360_flag}]")
    print(f"    d_total           : {r.delta_total_mm:.1f} mm  (limit L/180 = {limit_l180:.1f} mm)  [{l180_flag}]")
    print()
    print(f"  OVERALL: {verdict}")
    print(sep)
