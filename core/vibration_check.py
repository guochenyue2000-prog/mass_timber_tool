"""
vibration_check.py
==================
Vibration checks for mass timber floors — three methods:

1. CSA O86-24 Cl. 9.4.3.1  — vibration-controlled span limit
2. AISC Design Guide 11     — natural frequency + peak acceleration (ap/g)
3. prEC5 Table 9.3          — performance level assessment (I–VIII)
   - Frequency, stiffness, velocity, and (if resonant) acceleration criteria
   - Achieved performance level determined automatically

Functions are adapted from integrated_vibration_analysis_normal.py.
Key changes vs. the original file:
  - All functions accept EI directly (kN·m²/m from CheckResult) rather than E + geometry.
  - calculate_rms_velocity() bug fixed: no longer references global variables.
  - Module-level analysis code removed; use run_vibration_check() as the entry point.

Units convention (internal):
  - EI in N·m²  (CheckResult.EI × 1000 = kN·m²/m → N·m²/m for 1 m strip)
  - mass in kg, force in N, length in m
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from mass_timber_tool.core.results import CheckResult
    from mass_timber_tool.core.inputs import FloorInput
    from mass_timber_tool.core.beam_results import BeamCheckResult


# ---------------------------------------------------------------------------
# Input / output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VibrationInput:
    """Extra inputs required by the vibration engine (not in the structural check)."""
    beta: float = 0.03            # damping ratio (AISC)
    f_step: float = 1.8           # step frequency Hz (AISC)
    floor_type: str = "timber_concrete"    # prEC5: 'joisted','timber_concrete','joisted_floating','timber_concrete_floating'
    occupancy_type: str = "residential"    # prEC5: 'residential' or 'office'
    conc_thickness_m: float = 0.0          # optional concrete topping (m)
    conc_density_kg_m3: float = 2000.0     # kg/m³
    E_conc_MPa: float = 30000.0            # MPa
    num_bays: int = 1                      # bays in span direction (scales effective mass)


@dataclass
class VibrationResult:
    """Combined output from all three vibration methods."""

    # --- Mass and EI used ---
    mass_per_m2_kg: float                  # total vibration mass (panel + concrete) kg/m²
    EI_long_Nm2_per_m: float               # longitudinal EI used, N·m²/m
    EI_trans_Nm2_per_m: float              # transverse EI used, N·m²/m (EI_long/30 for NLT/GLT; exact minor-axis for CLT)

    # --- CSA O86-24 ---
    lv_limit_m: float                      # vibration-controlled span limit (m)
    lv_pass: bool                          # actual span <= lv_limit

    # --- AISC DG11 — panel only ---
    fn_panel_Hz: float                     # natural frequency (panel)
    ap_panel_g: float                      # peak acceleration / g
    W_panel_kN: float                      # effective weight used
    B_eff_panel_m: float                   # effective width used
    aisc_panel_method: str                 # 'Low-Frequency' or 'High-Frequency (ESPA)'

    # --- AISC DG11 — beam-supported (None if rigid support) ---
    fn_beam_panel_Hz: Optional[float]      # panel mode freq (beam-supported system)
    fn_beam_beam_Hz: Optional[float]       # beam mode freq
    fn_combined_Hz: Optional[float]        # combined system freq
    ap_combined_g: Optional[float]         # peak acceleration / g (combined)
    W_combined_kN: Optional[float]         # effective weight (combined)
    aisc_beam_method: Optional[str]

    # --- prEC5 — panel only ---
    fn_prEC5_Hz: float
    v_rms_ms: float                        # RMS velocity (m/s)
    a_rms_ms2: Optional[float]             # RMS acceleration (m/s²); None if transient
    deflection_1kN_mm: float               # deflection under 1 kN point load (mm) — panel only
    bef_m: float                           # effective width (m)
    modal_mass_prEC5_kg: float             # modal mass M* (kg)
    prEC5_response: str                    # 'Resonant' or 'Transient'

    # --- prEC5 — beam-supported (None if rigid support) ---
    fn_prEC5_beam_Hz: Optional[float]      # combined beam-supported freq
    v_rms_beam_ms: Optional[float]
    a_rms_beam_ms2: Optional[float]

    # --- prEC5 performance level assessment ---
    prEC5_f1_lim_Hz: float                        # resonance/frequency threshold
    prEC5_resonant: bool                           # True if f1 < f1_lim
    prEC5_level_results: List[dict]                # per-level breakdown for all 8 levels
    prEC5_achieved_level: Optional[str]            # strictest passing level, e.g. "IV"
    prEC5_achieved_level_beam: Optional[str]       # same for beam-supported (None if rigid)

    # --- optional combined deflection (must be last — has default) ---
    deflection_1kN_beam_mm: Optional[float] = None  # combined panel+beam deflection under 1 kN (mm)


# ---------------------------------------------------------------------------
# CSA O86-24 — vibration-controlled span
# ---------------------------------------------------------------------------

def vibration_controlled_span(EI_Nm2_per_m: float, linear_mass_kg_per_m: float) -> float:
    """
    CSA O86-24 Cl. 9.4.3.1 vibration-controlled span limit.

    lv = 0.11 × EI^0.29 / m^0.12

    Parameters
    ----------
    EI_Nm2_per_m : float
        Effective bending stiffness per unit width (N·m²/m).
    linear_mass_kg_per_m : float
        Total linear mass for a 1 m wide strip (kg/m).

    Returns
    -------
    float
        Maximum vibration-controlled span (m).
    """
    return 0.11 * (EI_Nm2_per_m ** 0.29) / (linear_mass_kg_per_m ** 0.12)


# ---------------------------------------------------------------------------
# AISC Design Guide 11 — helpers
# ---------------------------------------------------------------------------

def _aisc_fn(EI_Nm2_per_m: float, mass_per_m2: float, span: float) -> float:
    """fn = (pi/2) * sqrt(g * EI / (w * L^4)) for a simply-supported UDL panel."""
    g = 9.81
    w = mass_per_m2 * g          # N/m² (force per m²); 1 m strip → N/m
    return (math.pi / 2) * math.sqrt(g * EI_Nm2_per_m / (w * span ** 4))


def _aisc_effective_weight(mass_per_m2: float, span: float, floor_width: float,
                            num_bays: int = 1) -> tuple:
    """
    Compute AISC effective width, effective mass and effective weight.

    Returns (W_N, B_eff_m, width_note).
    """
    B_calc = 0.8 * span
    B_limit = (2.0 / 3.0) * floor_width
    if B_calc <= B_limit:
        B_eff = B_calc
        note = f"0.8L = {B_calc:.2f} m"
    else:
        B_eff = B_limit
        note = f"2/3 x Width = {B_limit:.2f} m"
    W = mass_per_m2 * 9.81 * B_eff * span * num_bays
    return W, B_eff, note


def _aisc_acceleration(fn: float, W_N: float, beta: float, f_step: float) -> tuple:
    """
    AISC DG11 peak acceleration (ap/g).

    Returns (ap_g, method_string).
    """
    g = 9.81
    Po_low = 65.0 * 4.44822   # N — low-frequency excitation force
    P_high = 154.0 * 4.44822  # N — high-frequency

    if fn < 9.0:
        method = "Low-Frequency (fn < 9 Hz)"
        ap_g = (Po_low * math.exp(-0.35 * fn)) / (beta * W_N)
    else:
        method = "High-Frequency ESPA (fn >= 9 Hz)"
        if fn < 11.0:
            h = 5
        elif fn < 13.2:
            h = 6
        elif fn <= 15.4:
            h = 7
        else:
            h = round(fn / f_step)
        term1 = P_high / W_N
        term2 = (f_step ** 1.43) / (fn ** 0.3)
        num_sq = 1 - math.exp(-4 * math.pi * h * beta)
        den_sq = h * math.pi * beta
        ap_g = term1 * term2 * math.sqrt(num_sq / den_sq)
    return ap_g, method


# ---------------------------------------------------------------------------
# prEC5 — helpers (bug-fixed; no global references)
# ---------------------------------------------------------------------------

_BEAM_DENSITY: dict[str, float] = {
    "D.Fir-L":          490.0,   # Douglas Fir-Larch glulam, oven-dry SG = 0.49
    "Spruce-Pine":      440.0,   # Spruce-Pine glulam, oven-dry SG = 0.44
}
_BEAM_DENSITY_DEFAULT: float = 460.0   # fallback midpoint

_DAMPING_RATIOS = {
    "joisted": 0.02,
    "timber_concrete": 0.025,
    "joisted_floating": 0.03,
    "timber_concrete_floating": 0.04,
}
_WALKING_FREQ = {"residential": 1.5, "office": 2.0}
_F1_LIM       = {"residential": 6.0, "office": 8.0}   # resonance threshold Hz

# prEC5 Table 9.3 performance level limits:
# (freq_criterion_Hz_or_None, w_lim_max_mm, v_rms_lim_ms, a_rms_lim_ms2_or_None)
# None for freq_criterion means use f1,lim (levels V–VIII).
# None for a_rms means acceleration criterion not applicable.
_PERF_LEVEL_LIMITS: dict = {
    "I":    (4.5, 0.25,  0.0004, 0.02),
    "II":   (4.5, 0.25,  0.0008, 0.04),
    "III":  (4.5, 0.50,  0.0012, 0.06),
    "IV":   (4.5, 1.00,  0.0016, 0.08),
    "V":    (None, 1.25, 0.0024, None),
    "VI":   (None, 1.50, 0.0036, None),
    "VII":  (None, 1.75, 0.0042, None),
    "VIII": (None, 2.00, 0.0048, None),
}
# Levels IV–VIII use span-dependent deflection limit: min(max(w_lim_max*3.6/l, 0.5), w_lim_max)
# Levels I–III use fixed deflection limit: w_lim = w_lim_max
_SPAN_DEP_LEVELS = {"IV", "V", "VI", "VII", "VIII"}
_PERF_LEVELS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def _prEC5_fn(EI_Nm2_per_m: float, mass_per_m2: float, span: float) -> float:
    """prEC5 fundamental frequency (same formula as AISC for SS UDL)."""
    return _aisc_fn(EI_Nm2_per_m, mass_per_m2, span)


def _effective_width_prEC5(span: float, width: float,
                            EI_long_Nm2_per_m: float, EI_trans_Nm2_per_m: float) -> float:
    """b_ef = min(0.95 * span * (EI_T/EI_L)^0.25, width). EI per unit width."""
    if EI_trans_Nm2_per_m <= 0 or EI_long_Nm2_per_m <= 0:
        return width
    ratio = (EI_trans_Nm2_per_m / EI_long_Nm2_per_m) ** 0.25
    return min(0.95 * span * ratio, width)


def _deflection_1kN(span: float, EI_long_Nm2_per_m: float,
                    width: float, EI_trans_Nm2_per_m: float) -> float:
    """
    prEC5 deflection under 1 kN point load (mm).
    w_1kN = F * l^3 / (48 * EI_L_per_m * b_ef)
    """
    F = 1000.0  # N
    bef = _effective_width_prEC5(span, width, EI_long_Nm2_per_m, EI_trans_Nm2_per_m)
    denom = 48.0 * EI_long_Nm2_per_m * bef
    return (F * span ** 3) / denom * 1000.0  # mm


def _modal_mass_prEC5(mass_per_m2: float, span: float, width: float, num_bays: int = 1) -> float:
    """M* = (m * l * b) / 4 * num_bays  (kg)."""
    return (mass_per_m2 * span * width / 4.0) * num_bays


def _modal_impulse(fw: float, f1: float) -> float:
    """I_mod,mean = 42 * fw^1.43 / f1^1.3  (N·s)."""
    if f1 <= 0:
        return 0.0
    return 42.0 * (fw ** 1.43) / (f1 ** 1.3)


def _peak_velocity(kred: float, Imod: float, Mstar: float) -> float:
    """v1_peak = kred * Imod / (M* + 70)  (m/s)."""
    return kred * Imod / (Mstar + 70.0)


def _kimp(span: float, width: float,
          EI_long_Nm2_per_m: float, EI_trans_Nm2_per_m: float) -> float:
    """Higher-mode factor for velocity: max(0.48*(b/l)*(EI_L/EI_T)^0.25, 1.0)."""
    if EI_trans_Nm2_per_m <= 0:
        return 1.0
    val = 0.48 * (width / span) * (EI_long_Nm2_per_m / EI_trans_Nm2_per_m) ** 0.25
    return max(val, 1.0)


def _kres(span: float, width: float,
          EI_long_Nm2_per_m: float, EI_trans_Nm2_per_m: float) -> float:
    """Higher-mode factor for acceleration: max(0.19*(b/l)*(EI_L/EI_T)^0.25, 1.0)."""
    if EI_trans_Nm2_per_m <= 0:
        return 1.0
    val = 0.19 * (width / span) * (EI_long_Nm2_per_m / EI_trans_Nm2_per_m) ** 0.25
    return max(val, 1.0)


def _eta_factor(kimp_val: float, floor_type: str) -> float:
    """Intermediate parameter eta (prEC5 Formula 9.27)."""
    if floor_type in ("joisted", "joisted_floating"):
        return 1.35 - 0.4 * kimp_val if kimp_val <= 1.9 else 0.59
    else:
        return 1.35 - 0.4 * kimp_val if kimp_val <= 1.7 else 0.67


def _rms_velocity(v_tot_peak: float, f1: float, zeta: float,
                  floor_type: str, kimp_val: float) -> float:
    """v_rms = v_tot_peak * (0.65 - 0.01*f1) * (1.22 - 11*zeta) * eta."""
    eta = _eta_factor(kimp_val, floor_type)
    return v_tot_peak * (0.65 - 0.01 * f1) * (1.22 - 11.0 * zeta) * eta


def _rms_acceleration(kres_val: float, Mstar: float, zeta: float) -> float:
    """a_rms = (kres * 0.4 * 50) / (sqrt(2) * 2 * zeta * M*)  (m/s²)."""
    if zeta == 0 or Mstar == 0:
        return 0.0
    return (kres_val * 0.4 * 50.0) / (math.sqrt(2) * 2.0 * zeta * Mstar)


def _prEC5_single_panel(EI_long: float, EI_trans: float, mass_per_m2: float,
                         span: float, width: float, floor_type: str,
                         occupancy_type: str, num_bays: int) -> dict:
    """Run prEC5 for a panel-only floor. Returns dict of results."""
    damping   = _DAMPING_RATIOS.get(floor_type, 0.03)
    fw        = _WALKING_FREQ.get(occupancy_type, 2.0)
    f1_lim    = _F1_LIM.get(occupancy_type, 6.0)

    fn    = _prEC5_fn(EI_long, mass_per_m2, span)
    bef   = _effective_width_prEC5(span, width, EI_long, EI_trans)
    defl  = _deflection_1kN(span, EI_long, width, EI_trans)
    Mstar = _modal_mass_prEC5(mass_per_m2, span, width, num_bays)
    kred  = 0.7
    Imod      = _modal_impulse(fw, fn)
    kimp_val  = _kimp(span, width, EI_long, EI_trans)
    kres_val  = _kres(span, width, EI_long, EI_trans)
    v1_peak   = _peak_velocity(kred, Imod, Mstar)
    v_tot     = kimp_val * v1_peak
    v_rms     = _rms_velocity(v_tot, fn, damping, floor_type, kimp_val)

    resonant  = fn < f1_lim
    a_rms     = _rms_acceleration(kres_val, Mstar, damping) if resonant else None

    return {
        "fn": fn, "v_rms": v_rms, "a_rms": a_rms,
        "deflection_1kN_mm": defl, "bef": bef,
        "modal_mass_kg": Mstar,
        "response": "Resonant" if resonant else "Transient",
        "f1_lim": f1_lim, "resonant": resonant,
    }


def _evaluate_perf_levels(
    fn: float,
    w1kN_mm: float,
    v_rms: float,
    a_rms: Optional[float],
    f1_lim: float,
    span: float,
    resonant: bool,
    fn_beam: Optional[float] = None,
    w1kN_mm_beam: Optional[float] = None,
    v_rms_beam: Optional[float] = None,
    a_rms_beam: Optional[float] = None,
) -> tuple:
    """
    Evaluate all 8 prEC5 performance levels and determine the achieved level.

    Returns (level_results: List[dict], achieved_level: str|None, achieved_level_beam: str|None).
    achieved_level is the strictest (lowest Roman numeral) level where all criteria pass.
    """
    results = []
    for level in _PERF_LEVELS:
        freq_crit_fixed, w_lim_max, v_rms_lim, a_rms_lim_table = _PERF_LEVEL_LIMITS[level]

        # Frequency criterion
        freq_criterion = freq_crit_fixed if freq_crit_fixed is not None else f1_lim

        # Deflection limit
        # Levels I–III: fixed limit.  Levels IV–VIII: span-dependent (prEC5 Table 9.1)
        if level in _SPAN_DEP_LEVELS:
            w_lim = min(max(w_lim_max * 3.6 / span, 0.5), w_lim_max)
        else:
            w_lim = w_lim_max

        freq_pass      = fn >= freq_criterion
        stiffness_pass = w1kN_mm <= w_lim
        velocity_pass  = v_rms <= v_rms_lim

        # Acceleration criterion: only when resonant AND level has a limit (I–IV)
        if resonant and a_rms_lim_table is not None and a_rms is not None:
            accel_pass = a_rms <= a_rms_lim_table
        else:
            accel_pass = None   # not applicable

        overall_pass = (
            freq_pass and stiffness_pass and velocity_pass
            and (accel_pass is not False)
        )

        # Beam-supported overrides (combined fn, combined w1kN, beam v_rms/a_rms)
        if v_rms_beam is not None:
            fn_b                = fn_beam      if fn_beam      is not None else fn
            w_b                 = w1kN_mm_beam if w1kN_mm_beam is not None else w1kN_mm
            freq_pass_beam      = fn_b >= freq_criterion
            stiffness_pass_beam = w_b  <= w_lim
            vel_pass_beam       = v_rms_beam <= v_rms_lim
            if resonant and a_rms_lim_table is not None and a_rms_beam is not None:
                acc_pass_beam: Optional[bool] = a_rms_beam <= a_rms_lim_table
            else:
                acc_pass_beam = None
            overall_beam: Optional[bool] = (
                freq_pass_beam and stiffness_pass_beam and vel_pass_beam
                and (acc_pass_beam is not False)
            )
        else:
            freq_pass_beam = stiffness_pass_beam = vel_pass_beam = acc_pass_beam = overall_beam = None

        results.append({
            "level":                  level,
            "freq_criterion_Hz":      freq_criterion,
            "w_lim_mm":               w_lim,
            "v_rms_lim_ms":           v_rms_lim,
            "a_rms_lim_ms2":          a_rms_lim_table,
            "freq_pass":              freq_pass,
            "stiffness_pass":         stiffness_pass,
            "velocity_pass":          velocity_pass,
            "accel_pass":             accel_pass,
            "overall_pass":           overall_pass,
            "freq_pass_beam":         freq_pass_beam,
            "stiffness_pass_beam":    stiffness_pass_beam,
            "velocity_pass_beam":     vel_pass_beam,
            "accel_pass_beam":        acc_pass_beam,
            "overall_pass_beam":      overall_beam,
        })

    achieved      = next((r["level"] for r in results if r["overall_pass"]),       None)
    achieved_beam = next((r["level"] for r in results if r["overall_pass_beam"] is True), None)
    return results, achieved, achieved_beam


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_vibration_check(
    panel_result: "CheckResult",
    floor_input: "FloorInput",
    vib_input: VibrationInput,
    beam_result: Optional["BeamCheckResult"] = None,
) -> VibrationResult:
    """
    Run all three vibration checks and return a unified VibrationResult.

    Parameters
    ----------
    panel_result : CheckResult
        Completed structural check result (provides EI, self-weight).
    floor_input : FloorInput
        Original floor input (span, width, SDL, etc.).
    vib_input : VibrationInput
        Extra vibration parameters (damping, occupancy type, etc.).
    beam_result : BeamCheckResult, optional
        If provided, beam-supported vibration analyses are also run.

    Returns
    -------
    VibrationResult
    """
    g = 9.81

    # ------------------------------------------------------------------
    # Derive vibration mass and EI from structural results
    # ------------------------------------------------------------------
    panel_mass_kg_m2: float = panel_result.self_weight_kN_per_m2 / g * 1000.0
    conc_mass_kg_m2:  float = vib_input.conc_density_kg_m3 * vib_input.conc_thickness_m
    total_mass_kg_m2: float = panel_mass_kg_m2 + conc_mass_kg_m2

    # EI in N·m²/m (longitudinal = structural check axis; transverse = CLT other axis or 0)
    EI_long: float = panel_result.EI * 1000.0
    EI_panel_only: float = EI_long   # bare panel EI — used for CSA O86 lv only
    EI_trans: float = (
        panel_result.EI_transverse * 1000.0
        if panel_result.EI_transverse is not None
        else 0.0
    )

    # Concrete EI contribution (longitudinal only) — for frequency / AISC / prEC5
    if vib_input.conc_thickness_m > 0:
        E_conc_Pa = vib_input.E_conc_MPa * 1e6
        I_conc_per_m = (vib_input.conc_thickness_m ** 3) / 12.0
        EI_long += E_conc_Pa * I_conc_per_m

    span: float  = floor_input.span
    width: float = floor_input.width

    # ------------------------------------------------------------------
    # 1. CSA O86-24 vibration-controlled span
    # ------------------------------------------------------------------
    # CSA O86 uses bare panel EI and bare panel mass regardless of topping,
    # provided topping area density <= 2x bare panel area density.
    # Concrete EI and mass are both excluded from the lv calculation.
    # Applied to all panel types (NLT, GLT, CLT).
    if conc_mass_kg_m2 > 0 and conc_mass_kg_m2 <= 2.0 * panel_mass_kg_m2:
        lv_EI   = EI_panel_only    # bare panel EI — exclude concrete
        lv_mass = panel_mass_kg_m2  # bare panel mass — exclude concrete
    else:
        lv_EI   = EI_long           # full composite EI (no topping, or heavy topping)
        lv_mass = total_mass_kg_m2  # full mass
    lv = vibration_controlled_span(lv_EI, lv_mass)
    lv_pass = span <= lv

    # ------------------------------------------------------------------
    # 2. AISC DG11 — panel only
    # ------------------------------------------------------------------
    fn_panel = _aisc_fn(EI_long, total_mass_kg_m2, span)
    W_panel, B_eff_panel, b_note = _aisc_effective_weight(
        total_mass_kg_m2, span, width, vib_input.num_bays
    )
    ap_panel_g, aisc_panel_method = _aisc_acceleration(
        fn_panel, W_panel, vib_input.beta, vib_input.f_step
    )

    # ------------------------------------------------------------------
    # 3. AISC DG11 — beam-supported (only if beam_result provided)
    # ------------------------------------------------------------------
    fn_bp: Optional[float] = None
    fn_bb: Optional[float] = None
    fn_bc: Optional[float] = None
    ap_bc_g: Optional[float] = None
    W_bc_kN: Optional[float] = None
    aisc_beam_method: Optional[str] = None

    if beam_result is not None:
        bi = beam_result.beam_input
        EI_beam_Nm2: float = beam_result.EsI_kNm2 * 1000.0
        beam_span: float   = bi.span
        spacing: float     = floor_input.span

        mass_beam_lin = (bi.width_mm / 1000.0) * (bi.depth_mm / 1000.0) * _BEAM_DENSITY.get(bi.species, _BEAM_DENSITY_DEFAULT)
        w_beam_total  = mass_beam_lin * g   # beam self-weight only (floor load excluded per AISC/prEC5 convention)

        delta_g = (5 * w_beam_total * beam_span ** 4) / (384 * EI_beam_Nm2)
        fn_bb   = 0.18 * math.sqrt(g / delta_g)

        delta_p = (5 * total_mass_kg_m2 * g * span ** 4) / (384 * EI_long)
        fn_bp   = 0.18 * math.sqrt(g / delta_p)

        fn_bc = 1.0 / math.sqrt(1.0 / fn_bp ** 2 + 1.0 / fn_bb ** 2)

        W_panel_eff = total_mass_kg_m2 * g * (0.8 * span) * beam_span
        W_beam_eff  = w_beam_total * (0.8 * beam_span)
        delta_tot   = delta_p + delta_g
        W_bc  = ((delta_p / delta_tot) * W_panel_eff + (delta_g / delta_tot) * W_beam_eff) * vib_input.num_bays
        W_bc_kN = W_bc / 1000.0

        ap_bc_g, aisc_beam_method = _aisc_acceleration(
            fn_bc, W_bc, vib_input.beta, vib_input.f_step
        )

    # ------------------------------------------------------------------
    # 4. prEC5 — panel only
    # ------------------------------------------------------------------
    prec5 = _prEC5_single_panel(
        EI_long, EI_trans, total_mass_kg_m2,
        span, width, vib_input.floor_type, vib_input.occupancy_type, vib_input.num_bays
    )
    f1_lim   = prec5["f1_lim"]
    resonant = prec5["resonant"]

    # ------------------------------------------------------------------
    # 5. prEC5 — beam-supported (combined freq using 2/3 Dunkerley)
    # ------------------------------------------------------------------
    fn_prEC5_beam: Optional[float]      = None
    v_rms_beam: Optional[float]         = None
    a_rms_beam: Optional[float]         = None
    defl_1kN_beam_mm: Optional[float]   = None

    if beam_result is not None:
        EI_beam_Nm2  = beam_result.EsI_kNm2 * 1000.0
        bi           = beam_result.beam_input
        beam_span    = bi.span
        spacing      = floor_input.span

        damping_b = _DAMPING_RATIOS.get(vib_input.floor_type, 0.03)
        fw_b      = _WALKING_FREQ.get(vib_input.occupancy_type, 2.0)

        w_slab   = total_mass_kg_m2 * g
        delta_p2 = (5 * w_slab * span ** 4) / (384 * EI_long)
        f_p2     = 0.18 * math.sqrt(g / delta_p2)

        mass_beam_lin2 = (bi.width_mm / 1000.0) * (bi.depth_mm / 1000.0) * _BEAM_DENSITY.get(bi.species, _BEAM_DENSITY_DEFAULT)
        w_b2     = mass_beam_lin2 * g   # beam self-weight only (floor load excluded per prEC5 convention)
        delta_g2 = (5 * w_b2 * beam_span ** 4) / (384 * EI_beam_Nm2)
        f_g2     = 0.18 * math.sqrt(g / delta_g2)

        fn_prEC5_beam = 1.0 / math.sqrt(1.0 / f_p2 ** 2 + 2.0 / (3.0 * f_g2 ** 2))

        Mstar_b  = _modal_mass_prEC5(total_mass_kg_m2, span, beam_span, vib_input.num_bays)
        kred     = 0.7
        Imod_b   = _modal_impulse(fw_b, fn_prEC5_beam)
        kimp_b   = _kimp(span, beam_span, EI_long, EI_trans)
        kres_b   = _kres(span, beam_span, EI_long, EI_trans)
        v1_b     = _peak_velocity(kred, Imod_b, Mstar_b)
        v_rms_beam = _rms_velocity(kimp_b * v1_b, fn_prEC5_beam, damping_b, vib_input.floor_type, kimp_b)
        if fn_prEC5_beam < f1_lim:
            a_rms_beam = _rms_acceleration(kres_b, Mstar_b, damping_b)

        # Combined 1 kN point-load deflection: panel + beam (series springs)
        defl_beam_mm     = (1000.0 * beam_span ** 3) / (48.0 * EI_beam_Nm2) * 1000.0  # mm
        defl_1kN_beam_mm = prec5["deflection_1kN_mm"] + defl_beam_mm

    # ------------------------------------------------------------------
    # 6. prEC5 performance level evaluation
    # ------------------------------------------------------------------
    level_results, achieved_level, achieved_level_beam = _evaluate_perf_levels(
        fn=prec5["fn"],
        w1kN_mm=prec5["deflection_1kN_mm"],
        v_rms=prec5["v_rms"],
        a_rms=prec5["a_rms"],
        f1_lim=f1_lim,
        span=span,
        resonant=resonant,
        fn_beam=fn_prEC5_beam,
        w1kN_mm_beam=defl_1kN_beam_mm,
        v_rms_beam=v_rms_beam,
        a_rms_beam=a_rms_beam,
    )

    # ------------------------------------------------------------------
    # Assemble result
    # ------------------------------------------------------------------
    return VibrationResult(
        mass_per_m2_kg=total_mass_kg_m2,
        EI_long_Nm2_per_m=EI_long,
        EI_trans_Nm2_per_m=EI_trans,

        lv_limit_m=lv,
        lv_pass=lv_pass,

        fn_panel_Hz=fn_panel,
        ap_panel_g=ap_panel_g,
        W_panel_kN=W_panel / 1000.0,
        B_eff_panel_m=B_eff_panel,
        aisc_panel_method=aisc_panel_method,

        fn_beam_panel_Hz=fn_bp,
        fn_beam_beam_Hz=fn_bb,
        fn_combined_Hz=fn_bc,
        ap_combined_g=ap_bc_g,
        W_combined_kN=W_bc_kN,
        aisc_beam_method=aisc_beam_method,

        fn_prEC5_Hz=prec5["fn"],
        v_rms_ms=prec5["v_rms"],
        a_rms_ms2=prec5["a_rms"],
        deflection_1kN_mm=prec5["deflection_1kN_mm"],
        bef_m=prec5["bef"],
        modal_mass_prEC5_kg=prec5["modal_mass_kg"],
        prEC5_response=prec5["response"],

        fn_prEC5_beam_Hz=fn_prEC5_beam,
        v_rms_beam_ms=v_rms_beam,
        a_rms_beam_ms2=a_rms_beam,
        deflection_1kN_beam_mm=defl_1kN_beam_mm,

        prEC5_f1_lim_Hz=f1_lim,
        prEC5_resonant=resonant,
        prEC5_level_results=level_results,
        prEC5_achieved_level=achieved_level,
        prEC5_achieved_level_beam=achieved_level_beam,
    )
