"""
nlt_tables.py
=============
NLT section property tables sourced from the Wood Design Manual (CWC),
Panel Selection Tables — Bending Members, pages 83–84.

Lamination thickness: 38 mm or 64 mm (values apply to both per table notes).

Notes from source:
  1. Values are per metre width of panel.
  2. Applicable to lamination thicknesses of 38 mm and 64 mm.
  3. Applicable to simple span, controlled random and two-span continuous layups.
  4. Mr and Vr based on case 1 system factor (K_H = 1.1).

IMPORTANT: These values are sourced from the CWC Wood Design Manual tables
(pages 83–84). Verify against your specific edition and project conditions
before use in final engineering calculations.

Table structure:
    NLT_TABLES[species][grade][thickness_mm] = {
        "Mr_kNm_per_m"         : float,  # factored moment resistance, kN·m per metre width
        "Vr_kN_per_m"          : float,  # factored shear resistance, kN per metre width
        "EI_kNm2_per_m"        : float,  # bending stiffness, kN·m² per metre width
        "self_weight_kN_per_m2": float,  # panel self-weight, kN/m²
    }

EI conversion: table gives EI × 10⁹ N·mm²/m.
    10⁹ N·mm²/m × (1 kN / 1000 N) × (1 m / 1000 mm)² = 1 kN·m²/m
    → table values are numerically equal to kN·m²/m directly.

Self-weight calculated as: density (kg/m³) × thickness (m) × 9.81 / 1000 (kN/m²)
    SPF:    ~420 kg/m³
    HF:     ~460 kg/m³
    D.Fir-L:~490 kg/m³
    Northern:~350 kg/m³
    MSR:    ~420 kg/m³ (SPF-based, oven-dry SG=0.42)

Species codes follow CSA O86 / NLGA conventions.
Grade codes: "SS" = Select Structural, "No.1/No.2" for sawn; MSR grades as labelled.
"""

from __future__ import annotations


def _sw(density_kg_m3: float, thickness_mm: float) -> float:
    """Calculate panel self-weight in kN/m²."""
    return density_kg_m3 * (thickness_mm / 1000.0) * 9.81 / 1000.0


# ---------------------------------------------------------------------------
# Master lookup table
# ---------------------------------------------------------------------------
# Source: CWC Wood Design Manual, Panel Selection Tables pp. 83–84.
# ---------------------------------------------------------------------------

NLT_TABLES: dict[str, dict[str, dict[int, dict[str, float]]]] = {

    # =========================================================================
    # SAWN LUMBER (page 83)
    # =========================================================================

    "D.Fir-L": {
        "SS": {
            #   thickness  Mr(kN·m/m)  Vr(kN/m)   EI(kN·m²/m)  SW(kN/m²)
            89:  {"Mr_kNm_per_m": 36.7, "Vr_kN_per_m": 190, "EI_kNm2_per_m":   734, "self_weight_kN_per_m2": _sw(490,  89)},
            140: {"Mr_kNm_per_m": 74.7, "Vr_kN_per_m": 246, "EI_kNm2_per_m":  1860, "self_weight_kN_per_m2": _sw(490, 140)},
            184: {"Mr_kNm_per_m":  111, "Vr_kN_per_m": 277, "EI_kNm2_per_m":  6490, "self_weight_kN_per_m2": _sw(490, 184)},
            235: {"Mr_kNm_per_m":  165, "Vr_kN_per_m": 324, "EI_kNm2_per_m": 13500, "self_weight_kN_per_m2": _sw(490, 235)},
            286: {"Mr_kNm_per_m":  223, "Vr_kN_per_m": 359, "EI_kNm2_per_m": 24400, "self_weight_kN_per_m2": _sw(490, 286)},
        },
        "No.1/No.2": {
            89:  {"Mr_kNm_per_m": 22.2, "Vr_kN_per_m": 190, "EI_kNm2_per_m":   646, "self_weight_kN_per_m2": _sw(490,  89)},
            140: {"Mr_kNm_per_m": 45.3, "Vr_kN_per_m": 246, "EI_kNm2_per_m":  2520, "self_weight_kN_per_m2": _sw(490, 140)},
            184: {"Mr_kNm_per_m": 67.0, "Vr_kN_per_m": 277, "EI_kNm2_per_m":  5710, "self_weight_kN_per_m2": _sw(490, 184)},
            235: {"Mr_kNm_per_m":  100, "Vr_kN_per_m": 324, "EI_kNm2_per_m": 11900, "self_weight_kN_per_m2": _sw(490, 235)},
            286: {"Mr_kNm_per_m":  135, "Vr_kN_per_m": 359, "EI_kNm2_per_m": 21400, "self_weight_kN_per_m2": _sw(490, 286)},
        },
    },

    "Hem-Fir": {
        "SS": {
            89:  {"Mr_kNm_per_m": 35.5, "Vr_kN_per_m": 160, "EI_kNm2_per_m":   705, "self_weight_kN_per_m2": _sw(460,  89)},
            140: {"Mr_kNm_per_m": 72.4, "Vr_kN_per_m": 207, "EI_kNm2_per_m":  2740, "self_weight_kN_per_m2": _sw(460, 140)},
            184: {"Mr_kNm_per_m":  107, "Vr_kN_per_m": 233, "EI_kNm2_per_m":  6230, "self_weight_kN_per_m2": _sw(460, 184)},
            235: {"Mr_kNm_per_m":  160, "Vr_kN_per_m": 273, "EI_kNm2_per_m": 13000, "self_weight_kN_per_m2": _sw(460, 235)},
            286: {"Mr_kNm_per_m":  216, "Vr_kN_per_m": 302, "EI_kNm2_per_m": 23400, "self_weight_kN_per_m2": _sw(460, 286)},
        },
        "No.1/No.2": {
            89:  {"Mr_kNm_per_m": 24.4, "Vr_kN_per_m": 160, "EI_kNm2_per_m":   646, "self_weight_kN_per_m2": _sw(460,  89)},
            140: {"Mr_kNm_per_m": 49.8, "Vr_kN_per_m": 207, "EI_kNm2_per_m":  2520, "self_weight_kN_per_m2": _sw(460, 140)},
            184: {"Mr_kNm_per_m": 73.7, "Vr_kN_per_m": 233, "EI_kNm2_per_m":  5710, "self_weight_kN_per_m2": _sw(460, 184)},
            235: {"Mr_kNm_per_m":  110, "Vr_kN_per_m": 273, "EI_kNm2_per_m": 11900, "self_weight_kN_per_m2": _sw(460, 235)},
            286: {"Mr_kNm_per_m":  148, "Vr_kN_per_m": 302, "EI_kNm2_per_m": 21400, "self_weight_kN_per_m2": _sw(460, 286)},
        },
    },

    "S-P-F": {
        "SS": {
            89:  {"Mr_kNm_per_m": 36.7, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   617, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 74.7, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  2400, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  111, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  5450, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  165, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 11400, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  223, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 20500, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "No.1/No.2": {
            89:  {"Mr_kNm_per_m": 26.2, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   558, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 53.4, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  2170, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m": 79.1, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  4930, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  118, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 10300, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  159, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 18500, "self_weight_kN_per_m2": _sw(350, 286)},
        },
    },

    "Northern": {
        "SS": {
            89:  {"Mr_kNm_per_m": 23.6, "Vr_kN_per_m": 130, "EI_kNm2_per_m":   441, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 48.0, "Vr_kN_per_m": 168, "EI_kNm2_per_m":  1720, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m": 71.1, "Vr_kN_per_m": 189, "EI_kNm2_per_m":  3890, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  106, "Vr_kN_per_m": 222, "EI_kNm2_per_m":  8110, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  143, "Vr_kN_per_m": 245, "EI_kNm2_per_m": 14600, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "No.1/No.2": {
            89:  {"Mr_kNm_per_m": 16.9, "Vr_kN_per_m": 130, "EI_kNm2_per_m":   411, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 34.4, "Vr_kN_per_m": 168, "EI_kNm2_per_m":  1600, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m": 50.9, "Vr_kN_per_m": 189, "EI_kNm2_per_m":  3630, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m": 76.2, "Vr_kN_per_m": 222, "EI_kNm2_per_m":  7570, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  103, "Vr_kN_per_m": 245, "EI_kNm2_per_m": 13600, "self_weight_kN_per_m2": _sw(350, 286)},
        },
    },

    # =========================================================================
    # MSR — Machine Stress-Rated Lumber (page 84)
    # Species assumed SPF-based (density 470 kg/m³) unless manufacturer specifies.
    # =========================================================================

    "MSR": {
        "1450Fb-1.3E": {
            89:  {"Mr_kNm_per_m": 27.4, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   529, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 67.9, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  2060, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  117, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  4670, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  191, "Vr_kN_per_m": 256, "EI_kNm2_per_m":  9730, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  283, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 17500, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "1650Fb-1.5E": {
            89:  {"Mr_kNm_per_m": 31.2, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   605, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 77.3, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  2360, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  134, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  5350, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  218, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 11100, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  323, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 20100, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "1800Fb-1.6E": {
            89:  {"Mr_kNm_per_m": 34.1, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   646, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 84.4, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  2520, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  146, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  5710, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  238, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 11900, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  352, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 21400, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "1950Fb-1.7E": {
            89:  {"Mr_kNm_per_m": 36.9, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   687, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 91.2, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  2680, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  158, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  6070, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  257, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 12700, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  381, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 22800, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "2100Fb-1.8E": {
            89:  {"Mr_kNm_per_m": 39.7, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   728, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m": 98.3, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  2840, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  170, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  6440, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  277, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 13400, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  410, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 24200, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "2250Fb-1.9E": {
            89:  {"Mr_kNm_per_m": 42.6, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   770, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m":  105, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  3000, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  182, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  6800, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  297, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 14200, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  440, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 25500, "self_weight_kN_per_m2": _sw(350, 286)},
        },
        "2400Fb-2.0E": {
            89:  {"Mr_kNm_per_m": 45.4, "Vr_kN_per_m": 150, "EI_kNm2_per_m":   811, "self_weight_kN_per_m2": _sw(350,  89)},
            140: {"Mr_kNm_per_m":  112, "Vr_kN_per_m": 194, "EI_kNm2_per_m":  3160, "self_weight_kN_per_m2": _sw(350, 140)},
            184: {"Mr_kNm_per_m":  194, "Vr_kN_per_m": 219, "EI_kNm2_per_m":  7160, "self_weight_kN_per_m2": _sw(350, 184)},
            235: {"Mr_kNm_per_m":  316, "Vr_kN_per_m": 256, "EI_kNm2_per_m": 14900, "self_weight_kN_per_m2": _sw(350, 235)},
            286: {"Mr_kNm_per_m":  468, "Vr_kN_per_m": 283, "EI_kNm2_per_m": 26900, "self_weight_kN_per_m2": _sw(350, 286)},
        },
    },
}


# ---------------------------------------------------------------------------
# Public accessor
# ---------------------------------------------------------------------------

def get_nlt_properties(species: str, grade: str, thickness_mm: float) -> dict[str, float]:
    """
    Look up NLT section properties from the table.

    Parameters
    ----------
    species : str
        Lumber species group: ``"D.Fir-L"``, ``"Hem-Fir"``, ``"S-P-F"``,
        ``"Northern"``, or ``"MSR"``.
    grade : str
        Visual grade (``"SS"``, ``"No.1/No.2"``) or MSR grade
        (e.g. ``"1800Fb-1.6E"``).
    thickness_mm : float
        Nominal panel thickness in mm. Must match a table key exactly:
        89, 140, 184, 235, or 286.

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
        props = NLT_TABLES[species][grade][thickness_key]
    except KeyError:
        available_species = list(NLT_TABLES.keys())
        raise KeyError(
            f"NLT properties not found for species='{species}', grade='{grade}', "
            f"thickness={thickness_mm} mm. "
            f"Available species: {available_species}. "
            "Verify the combination exists in NLT_TABLES or add it."
        )

    return props
