"""
glt_tables.py
=============
GLT (Glulam Timber) panel section property tables sourced from the
Wood Design Manual (CWC), Panel Selection Tables — Bending Members, page 100.

Notes from source:
  1. Values are per metre width of panel.
  2. Size factor K_zb calculated based on the full thickness of the GLT panel,
     not the lamination dimensions.
  3. There is no advantage in specifying higher grade glulam in panel applications.

Table structure:
    GLT_TABLES[species][grade][thickness_mm] = {
        "Mr_kNm_per_m"         : float,  # factored moment resistance, kN·m per metre width
        "Vr_kN_per_m"          : float,  # factored shear resistance, kN per metre width
        "EI_kNm2_per_m"        : float,  # bending stiffness, kN·m² per metre width
        "self_weight_kN_per_m2": float,  # panel self-weight, kN/m²
    }

EI conversion: table gives EI × 10⁹ N·mm²/m.
    10⁹ N·mm²/m × (1 kN / 1000 N) × (1 m / 1000 mm)² = 1 kN·m²/m
    → table values are numerically equal to kN·m²/m directly.

Self-weight calculated as: density (kg/m³) × thickness (m) × 9.81 / 1000 (kN/m²)
    Douglas Fir-Larch: ~490 kg/m³
    Spruce-Pine:       ~440 kg/m³

Grade note: "All Grades" label applies — 20f-E and 24f-E share the same
panel properties per CWC note 3 (no advantage in higher grade for panels).
Both grades are entered separately for user clarity.
"""

from __future__ import annotations


def _sw(density_kg_m3: float, thickness_mm: float) -> float:
    """Calculate panel self-weight in kN/m²."""
    return density_kg_m3 * (thickness_mm / 1000.0) * 9.81 / 1000.0


# ---------------------------------------------------------------------------
# Master lookup table
# ---------------------------------------------------------------------------
# Source: CWC Wood Design Manual, Panel Selection Tables p. 100.
# ---------------------------------------------------------------------------

GLT_TABLES: dict[str, dict[str, dict[int, dict[str, float]]]] = {

    # =========================================================================
    # Douglas Fir-Larch — 20f-E and 24f-E
    # Per CWC note 3: no advantage in higher grade; both entries have same values.
    # =========================================================================
    "Douglas Fir-Larch": {
        "20f-E": {
            #   thickness  Mr(kN·m/m)  Vr(kN/m)   EI(kN·m²/m)  SW(kN/m²)
             80: {"Mr_kNm_per_m":  18.0, "Vr_kN_per_m": 171, "EI_kNm2_per_m":   469, "self_weight_kN_per_m2": _sw(490,  80)},
            130: {"Mr_kNm_per_m":  40.1, "Vr_kN_per_m": 234, "EI_kNm2_per_m":  2010, "self_weight_kN_per_m2": _sw(490, 130)},
            175: {"Mr_kNm_per_m":  62.7, "Vr_kN_per_m": 272, "EI_kNm2_per_m":  4910, "self_weight_kN_per_m2": _sw(490, 175)},
            215: {"Mr_kNm_per_m":  86.9, "Vr_kN_per_m": 307, "EI_kNm2_per_m":  9110, "self_weight_kN_per_m2": _sw(490, 215)},
            265: {"Mr_kNm_per_m":  121,  "Vr_kN_per_m": 346, "EI_kNm2_per_m": 17100, "self_weight_kN_per_m2": _sw(490, 265)},
            315: {"Mr_kNm_per_m":  154,  "Vr_kN_per_m": 373, "EI_kNm2_per_m": 28700, "self_weight_kN_per_m2": _sw(490, 315)},
            365: {"Mr_kNm_per_m":  186,  "Vr_kN_per_m": 386, "EI_kNm2_per_m": 44600, "self_weight_kN_per_m2": _sw(490, 365)},
        },
        "24f-E": {
            # Same values as 20f-E per CWC note 3
             80: {"Mr_kNm_per_m":  18.0, "Vr_kN_per_m": 171, "EI_kNm2_per_m":   469, "self_weight_kN_per_m2": _sw(490,  80)},
            130: {"Mr_kNm_per_m":  40.1, "Vr_kN_per_m": 234, "EI_kNm2_per_m":  2010, "self_weight_kN_per_m2": _sw(490, 130)},
            175: {"Mr_kNm_per_m":  62.7, "Vr_kN_per_m": 272, "EI_kNm2_per_m":  4910, "self_weight_kN_per_m2": _sw(490, 175)},
            215: {"Mr_kNm_per_m":  86.9, "Vr_kN_per_m": 307, "EI_kNm2_per_m":  9110, "self_weight_kN_per_m2": _sw(490, 215)},
            265: {"Mr_kNm_per_m":  121,  "Vr_kN_per_m": 346, "EI_kNm2_per_m": 17100, "self_weight_kN_per_m2": _sw(490, 265)},
            315: {"Mr_kNm_per_m":  154,  "Vr_kN_per_m": 373, "EI_kNm2_per_m": 28700, "self_weight_kN_per_m2": _sw(490, 315)},
            365: {"Mr_kNm_per_m":  186,  "Vr_kN_per_m": 386, "EI_kNm2_per_m": 44600, "self_weight_kN_per_m2": _sw(490, 365)},
        },
    },

    # =========================================================================
    # Spruce-Pine — 20f-E only (single grade listed in table)
    # =========================================================================
    "Spruce-Pine": {
        "20f-E": {
             80: {"Mr_kNm_per_m":  21.2, "Vr_kN_per_m": 135, "EI_kNm2_per_m":   405, "self_weight_kN_per_m2": _sw(440,  80)},
            130: {"Mr_kNm_per_m":  47.3, "Vr_kN_per_m": 185, "EI_kNm2_per_m":  1740, "self_weight_kN_per_m2": _sw(440, 130)},
            175: {"Mr_kNm_per_m":  74.0, "Vr_kN_per_m": 215, "EI_kNm2_per_m":  4240, "self_weight_kN_per_m2": _sw(440, 175)},
            215: {"Mr_kNm_per_m":  103,  "Vr_kN_per_m": 242, "EI_kNm2_per_m":  7870, "self_weight_kN_per_m2": _sw(440, 215)},
            265: {"Mr_kNm_per_m":  142,  "Vr_kN_per_m": 273, "EI_kNm2_per_m": 14700, "self_weight_kN_per_m2": _sw(440, 265)},
            315: {"Mr_kNm_per_m":  182,  "Vr_kN_per_m": 294, "EI_kNm2_per_m": 24700, "self_weight_kN_per_m2": _sw(440, 315)},
            365: {"Mr_kNm_per_m":  219,  "Vr_kN_per_m": 305, "EI_kNm2_per_m": 38500, "self_weight_kN_per_m2": _sw(440, 365)},
        },
    },
}


# ---------------------------------------------------------------------------
# Public accessor
# ---------------------------------------------------------------------------

def get_glt_properties(species: str, grade: str, thickness_mm: float) -> dict[str, float]:
    """
    Look up GLT panel section properties from the table.

    Parameters
    ----------
    species : str
        Glulam species: ``"Douglas Fir-Larch"`` or ``"Spruce-Pine"``.
    grade : str
        Glulam stress grade: ``"20f-E"`` or ``"24f-E"``.
    thickness_mm : float
        Nominal panel thickness in mm. Must match a table key exactly:
        80, 130, 175, 215, 265, 315, or 365.

    Returns
    -------
    dict[str, float]
        Keys: ``"Mr_kNm_per_m"``, ``"Vr_kN_per_m"``,
        ``"EI_kNm2_per_m"``, ``"self_weight_kN_per_m2"``.

    Raises
    ------
    KeyError
        If the species / grade / thickness combination is not in the table.
    """
    thickness_key = int(thickness_mm)  # table keys are integers

    try:
        props = GLT_TABLES[species][grade][thickness_key]
    except KeyError:
        available_species = list(GLT_TABLES.keys())
        raise KeyError(
            f"GLT properties not found for species='{species}', grade='{grade}', "
            f"thickness={thickness_mm} mm. "
            f"Available species: {available_species}. "
            "Verify the combination exists in GLT_TABLES or add it."
        )

    return props
