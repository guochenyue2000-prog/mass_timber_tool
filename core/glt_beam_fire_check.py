"""
glt_beam_fire_check.py
======================
CSA O86-24 Annex B fire-resistance check for glulam beams — full capacity method.

Method (Annex B B.6 / B.7)
---------------------------
For 3-sided fire exposure (top protected, bottom and both sides exposed):

1.  Char removal per exposed face:
        removal = β_n × t × 60 + x_t
    where β_n = 0.70 mm/min (notional charring rate, Table B.2),
          x_t = 7 mm (zero-strength layer, t ≥ 20 min, Cl. B.5).

2.  Effective cross-section of a trial fire section (b_fire × d_fire):
        b_eff = b_fire − 2 × removal   (both sides exposed)
        d_eff = d_fire −     removal   (bottom face only)

3.  Unfactored fire demand (Annex B B.7 — specified D+L, no load factors):
        Mf_fire = w_specified × L² / 8
    where w_specified = result.w_kN_per_m (SLS total line load already in
    BeamCheckResult).

4.  Fire moment resistance of the effective section:
        Mr_fire = M'r_table(b_fire,d_fire)
                  × (b_eff × d_eff²) / (b_fire × d_fire²)
                  × (φ_fire / φ_ambient)
                  × K_fi
                  × K_Zbg_orig
                  × K_D_fire

    Factors (Annex B B.3):
        φ_fire     = 1.0   (resistance factor for fire)
        φ_ambient  = 0.9   (embedded in CWC table M'r values)
        K_fi       = 1.35  (mean-strength conversion, Table B.1, glulam)
        K_Zbg_orig = size factor from ORIGINAL ambient section dims
        K_D_fire   = 1.15  (short-term loading per Cl. 5.3.2)

5.  Section passes fire if Mr_fire ≥ Mf_fire.

Search strategy
---------------
Starting from the ambient structural section (b_amb × d_amb), iterate
standard sections in ascending order of width then depth.  The first
section that satisfies Mr_fire ≥ Mf_fire is returned.  This gives the
most economical (smallest area) fire section.  The ambient section itself
is checked first — if it already passes, no size increase is needed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ..data.glulam_beam_tables import GLULAM_BEAM_TABLES, get_glulam_beam_properties
from .beam_results import BeamCheckResult


# ---------------------------------------------------------------------------
# Constants — CSA O86-24 Annex B
# ---------------------------------------------------------------------------
_BETA_N: float    = 0.70   # mm/min  — notional charring rate, GLT (Table B.2)
_X_T: float       = 7.0    # mm      — zero-strength layer depth (t ≥ 20 min, Cl. B.5)
_K_FI: float      = 1.35   # —       — mean-strength factor for glulam (Table B.1)
_PHI_AMBIENT: float = 0.9  # —       — resistance factor embedded in CWC table M'r values
_K_D_FIRE: float  = 1.15   # —       — short-term load duration factor (Annex B B.3)

# Lumped φ and K_fi multiplier applied when scaling M'r to fire conditions
_K_FIRE_STRENGTH: float = _K_FI / _PHI_AMBIENT   # = 1.35 / 0.9 ≈ 1.500


def _removal_mm(fire_hours: int) -> float:
    """Total material removed per exposed face for the given fire rating."""
    return _BETA_N * fire_hours * 60.0 + _X_T


def _kzbg(b_mm: float, d_mm: float, span_m: float) -> float:
    """
    Size factor K_Zbg per CSA O86 / CWC Wood Design Manual.
    K_Zbg = (130/b)^(1/10) × (610/d)^(1/10) × (9100/L_mm)^(1/10), capped at 1.3.
    """
    l_mm = span_m * 1000.0
    return min(
        (130.0 / b_mm) ** 0.1
        * (610.0 / d_mm) ** 0.1
        * (9100.0 / l_mm) ** 0.1,
        1.3,
    )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class BeamFireUpgrade:
    """
    Fire-resistance check result for one glulam beam section.

    Attributes
    ----------
    fire_hours : int
        Target rating (1 or 2).
    removal_mm : float
        Char + zero-strength layer removed per exposed face, mm.

    ambient_b, ambient_d : int
        Original structurally-designed section dimensions, mm.

    fire_b, fire_d : int | None
        Recommended fire-rated section from the standard table, mm.
        None if no suitable section exists in the table.

    b_eff_after_char, d_eff_after_char : float
        Effective cross-section dimensions after charring, mm.
        b_eff = fire_b − 2×removal,  d_eff = fire_d − removal.

    Mf_fire_kNm : float
        Unfactored fire moment demand (specified D+L), kN·m.
    Mr_fire_kNm : float
        Fire moment resistance of the effective section (Annex B B.6), kN·m.
    fire_utilization : float
        Mf_fire / Mr_fire.  ≤ 1.0 means section passes the fire check.

    width_added_mm, depth_added_mm : int
        Section increase over the ambient structural section, mm.
        0 means no change in that dimension.
    lams_added : int
        Number of 38 mm laminations added in depth (informational).
    layup_note : str
        Manufacturing layup modification required per CSA O86 Cl. B.2.2.
    no_section_found : bool
        True if no standard section in the table satisfies the fire check.
    """

    fire_hours: int
    removal_mm: float

    ambient_b: int
    ambient_d: int

    fire_b: Optional[int]
    fire_d: Optional[int]

    b_eff_after_char: float
    d_eff_after_char: float

    Mf_fire_kNm: float
    Mr_fire_kNm: float
    fire_utilization: float

    width_added_mm: int
    depth_added_mm: int
    lams_added: int

    layup_note: str
    no_section_found: bool


# ---------------------------------------------------------------------------
# Standard section helpers
# ---------------------------------------------------------------------------

def _available_depths(width_mm: int, species: str, grade: str) -> list[int]:
    """Return sorted standard depths for (width, species, grade)."""
    depth_dict = GLULAM_BEAM_TABLES.get(width_mm, {})
    return sorted(
        d for d, sp_dict in depth_dict.items()
        if species in sp_dict and grade in sp_dict[species]
    )


def _available_widths(species: str, grade: str) -> list[int]:
    """Return sorted standard widths for (species, grade)."""
    return sorted(
        w for w, d_dict in GLULAM_BEAM_TABLES.items()
        if any(
            species in sp_dict and grade in sp_dict[species]
            for sp_dict in d_dict.values()
        )
    )


# ---------------------------------------------------------------------------
# Core fire check
# ---------------------------------------------------------------------------

def suggest_fire_upgrade(
    result: BeamCheckResult,
    fire_hours: int,
) -> BeamFireUpgrade:
    """
    Find the minimum standard glulam section that satisfies the CSA O86-24
    Annex B fire-resistance check for the given fire rating.

    The ambient structural section is checked first.  If it already passes
    (possible for lightly loaded or short-duration ratings), no size increase
    is needed.  Otherwise the search steps through standard sections in
    ascending order of width then depth until one passes.

    Parameters
    ----------
    result : BeamCheckResult
        Completed ambient structural check (structural_pass=True expected).
    fire_hours : int
        Target fire-resistance rating: 1 or 2.

    Returns
    -------
    BeamFireUpgrade
        Fire check result including recommended section and utilization ratio.
    """
    if fire_hours not in (1, 2):
        raise ValueError("fire_hours must be 1 or 2.")

    b_amb    = result.beam_input.width_mm
    d_amb    = result.beam_input.depth_mm
    span     = result.beam_input.span
    species  = result.beam_input.species
    grade    = result.beam_input.grade

    removal  = _removal_mm(fire_hours)

    # ------------------------------------------------------------------
    # Unfactored fire demand (Annex B B.7: specified D+L, no load factors)
    # result.w_kN_per_m = (D + L_red) × trib + self_weight — SLS line load
    # ------------------------------------------------------------------
    Mf_fire: float = result.w_kN_per_m * span ** 2 / 8.0  # kN·m

    # ------------------------------------------------------------------
    # K_Zbg from original ambient section dimensions (Annex B B.3)
    # Reuse the value already computed in the ambient structural check.
    # ------------------------------------------------------------------
    K_Zbg_orig: float = result.KZbg

    # ------------------------------------------------------------------
    # Section search: ascending width (≥ ambient), then ascending depth (≥ ambient)
    # ------------------------------------------------------------------
    fire_b: Optional[int]   = None
    fire_d: Optional[int]   = None
    Mr_fire_found: float    = 0.0

    for b_fire in _available_widths(species, grade):
        if b_fire < b_amb:
            continue   # never narrow the beam

        b_eff: float = b_fire - 2.0 * removal
        if b_eff <= 0.0:
            continue   # section fully charred through in width — skip entire width

        for d_fire in _available_depths(b_fire, species, grade):
            if d_fire < d_amb:
                continue   # never reduce depth

            d_eff: float = d_fire - removal
            if d_eff <= 0.0:
                continue   # fully charred through in depth

            # Look up M'r for the full fire section from the table
            entry          = get_glulam_beam_properties(b_fire, d_fire, species, grade)
            Mr_prime_table = entry["Mr_prime_kNm"]   # kN·m — includes φ = 0.9

            # Scale M'r to the effective (charred) cross-section and apply
            # fire-specific factors (Annex B B.3):
            #   φ_fire / φ_ambient = 1.0 / 0.9
            #   K_fi = 1.35  (mean strength for glulam)
            #   K_Zbg from original dims  (already in K_Zbg_orig)
            #   K_D = 1.15   (short-term)
            S_ratio: float  = (b_eff * d_eff ** 2) / (b_fire * d_fire ** 2)
            Mr_prime_fire   = Mr_prime_table * S_ratio * _K_FIRE_STRENGTH
            Mr_fire: float  = Mr_prime_fire * K_Zbg_orig * _K_D_FIRE

            if Mr_fire >= Mf_fire:
                fire_b        = b_fire
                fire_d        = d_fire
                Mr_fire_found = Mr_fire
                break   # minimum depth at this width found

        if fire_b is not None:
            break   # minimum width found

    # ------------------------------------------------------------------
    # Assemble result
    # ------------------------------------------------------------------
    if fire_b is not None:
        b_eff_final    = float(fire_b) - 2.0 * removal
        d_eff_final    = float(fire_d) - removal
        fire_util      = Mf_fire / Mr_fire_found
        width_added    = fire_b - b_amb
        depth_added    = fire_d - d_amb
        lams_added     = round(depth_added / 38.0) if depth_added > 0 else 0
        no_section     = False
    else:
        # No standard section in the table passes the fire check
        b_eff_final = float(b_amb) - 2.0 * removal
        d_eff_final = float(d_amb) - removal
        fire_util   = float("inf")
        width_added = 0
        depth_added = 0
        lams_added  = 0
        no_section  = True

    # Layup modification note (Cl. B.2.2 — top protected, positive bending)
    if fire_hours == 1:
        layup_note = (
            "1 h (top protected): remove 1 core lam; "
            "add one 38 mm outer tension lam at bottom  [CSA O86 Cl. B.2.2a]"
        )
    else:
        layup_note = (
            "2 h (top protected): remove 2 core lams; "
            "add two 38 mm outer tension lams at bottom  [CSA O86 Cl. B.2.2c]"
        )

    return BeamFireUpgrade(
        fire_hours        = fire_hours,
        removal_mm        = round(removal, 1),
        ambient_b         = b_amb,
        ambient_d         = d_amb,
        fire_b            = fire_b,
        fire_d            = fire_d,
        b_eff_after_char  = round(b_eff_final, 1),
        d_eff_after_char  = round(d_eff_final, 1),
        Mf_fire_kNm       = round(Mf_fire, 1),
        Mr_fire_kNm       = round(Mr_fire_found, 1),
        fire_utilization  = round(fire_util, 3),
        width_added_mm    = width_added,
        depth_added_mm    = depth_added,
        lams_added        = lams_added,
        layup_note        = layup_note,
        no_section_found  = no_section,
    )


# ---------------------------------------------------------------------------
# Bulk upgrade
# ---------------------------------------------------------------------------

def apply_fire_upgrades(
    results: list[BeamCheckResult],
    fire_hours: int,
) -> list[tuple[BeamCheckResult, BeamFireUpgrade]]:
    """
    Apply fire check to every structurally passing beam section.

    Parameters
    ----------
    results : list[BeamCheckResult]
        Structurally passing beam results.
    fire_hours : int
        Target rating: 1 or 2.

    Returns
    -------
    list of (BeamCheckResult, BeamFireUpgrade)
    """
    return [(r, suggest_fire_upgrade(r, fire_hours)) for r in results]


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def print_fire_upgrade_table(
    pairs: list[tuple[BeamCheckResult, BeamFireUpgrade]],
) -> None:
    """Print a compact table of structural → fire section results."""
    if not pairs:
        print("  (no sections to display)")
        return

    fire_hours = pairs[0][1].fire_hours
    removal    = pairs[0][1].removal_mm
    print(
        f"\n  Fire Rating : {fire_hours} h  |  "
        f"Removal/face : {removal:.0f} mm  "
        f"(β_n×{fire_hours*60:.0f} + x_t={_X_T:.0f})  |  "
        f"Method: CSA O86-24 Annex B full capacity check"
    )
    print(
        f"  Factors: φ_fire/φ_amb={_K_FIRE_STRENGTH:.3f}  "
        f"K_fi={_K_FI}  K_D(short)={_K_D_FIRE}  K_Zbg from original dims"
    )
    print(
        f"  {'Structural':<20}  {'Fire section':<20}  "
        f"{'b_eff':>7}  {'d_eff':>7}  "
        f"{'Δb':>6}  {'Δd':>6}  "
        f"{'Mf_fire':>9}  {'Mr_fire':>9}  {'Util':>6}  Status"
    )
    print("  " + "-" * 105)

    for _r, fu in pairs:
        amb  = f"{fu.ambient_b}×{fu.ambient_d}"
        if not fu.no_section_found:
            fire_sec = f"{fu.fire_b}×{fu.fire_d}"
            status   = "PASS" if fu.fire_utilization <= 1.0 else "FAIL"
        else:
            fire_sec = "— none —"
            status   = "NO SECTION"

        print(
            f"  {amb:<20}  {fire_sec:<20}  "
            f"{fu.b_eff_after_char:>6.0f}m  {fu.d_eff_after_char:>6.0f}m  "
            f"{fu.width_added_mm:>+6}  {fu.depth_added_mm:>+6}  "
            f"{fu.Mf_fire_kNm:>8.1f}k  {fu.Mr_fire_kNm:>8.1f}k  "
            f"{fu.fire_utilization:>6.3f}  {status}"
        )

    print(f"\n  Layup note: {pairs[0][1].layup_note}\n")
