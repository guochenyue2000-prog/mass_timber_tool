"""
clt_tables.py
=============
CLT (Cross-Laminated Timber) panel section property tables sourced from the
Wood Design Manual (CWC), Panel Selection Tables — Bending Members.

  Page 115 : CLT Strength  — Mr and Vr for major and minor strength axes.
  Table 2.12 (p. 111) : Effective bending stiffness (EI)eff and
                         in-plane shear rigidity (GA)eff.

Ply thickness: 35 mm (values apply to 35 mm ply layup).

Notes from source:
  1. Values are per metre width of panel.
  2. Table represents a typical CLT layup. CLT can be manufactured by
     varying lamination grades, thicknesses, orientations, and layer
     arrangements in the layup.

Table structure:
    CLT_TABLES[grade][num_plies][thickness_mm] = {
        # Major strength axis (span parallel to outer-ply grain)
        "Mr_major_kNm_per_m"  : float,   # factored moment resistance, kN·m/m
        "Vr_major_kN_per_m"   : float,   # factored shear resistance, kN/m
        "EI_major_kNm2_per_m" : float,   # (EI)eff,y  bending stiffness, kN·m²/m
        "GA_major_kN_per_m"   : float,   # (GA)eff,zy in-plane shear rigidity, kN/m
        # Minor strength axis (span perpendicular to outer-ply grain)
        "Mr_minor_kNm_per_m"  : float,   # factored moment resistance, kN·m/m
        "Vr_minor_kN_per_m"   : float,   # factored shear resistance, kN/m
        "EI_minor_kNm2_per_m" : float,   # (EI)eff,x  bending stiffness, kN·m²/m
        "GA_minor_kN_per_m"   : float,   # (GA)eff,zx in-plane shear rigidity, kN/m
        "self_weight_kN_per_m2": float,  # panel self-weight, kN/m²
    }

EI conversion (Table 2.12): values given as EI × 10⁹ N·mm²/m.
    10⁹ N·mm²/m × (1 kN/1000 N) × (1 m/1000 mm)² = 1 kN·m²/m
    → table values are numerically equal to kN·m²/m directly.

GA conversion (Table 2.12): values given as GA × 10⁶ N/m.
    10⁶ N/m × (1 kN/1000 N) = 10³ kN/m
    → multiply table values by 1000 to get kN/m.

Self-weight: grade-specific CLT densities (kg/m³):
    E1, V2 → 420 kg/m³
    E2, V1 → 490 kg/m³
    E3     → 350 kg/m³
    SW = density × thickness(m) × 9.81 / 1000  [kN/m²]

Grades: E1, E2, E3 (engineered), V1, V2 (visually graded).
"""

from __future__ import annotations

# Grade-specific CLT densities (kg/m³)
_CLT_DENSITY: dict[str, float] = {
    "E1": 420.0,
    "V2": 420.0,
    "E2": 490.0,
    "V1": 490.0,
    "E3": 350.0,
}


def _sw(thickness_mm: float, density_kg_m3: float) -> float:
    """Calculate CLT panel self-weight in kN/m²."""
    return density_kg_m3 * (thickness_mm / 1000.0) * 9.81 / 1000.0


# Grade-specific self-weight helpers
_sw_E1 = lambda t: _sw(t, _CLT_DENSITY["E1"])   # 420 kg/m³
_sw_E2 = lambda t: _sw(t, _CLT_DENSITY["E2"])   # 490 kg/m³
_sw_E3 = lambda t: _sw(t, _CLT_DENSITY["E3"])   # 350 kg/m³
_sw_V1 = lambda t: _sw(t, _CLT_DENSITY["V1"])   # 490 kg/m³
_sw_V2 = lambda t: _sw(t, _CLT_DENSITY["V2"])   # 420 kg/m³


# ---------------------------------------------------------------------------
# Master lookup table
# ---------------------------------------------------------------------------
# Source: CWC Wood Design Manual, p. 111 (Table 2.12) and p. 115 (Strength).
# Structure: CLT_TABLES[grade][num_plies] = {thickness_mm: {...}}
# ---------------------------------------------------------------------------

CLT_TABLES: dict[str, dict[int, dict[int, dict[str, float]]]] = {

    # =========================================================================
    # Grade E1
    # =========================================================================
    "E1": {
        3: {
            105: {
                "Mr_major_kNm_per_m":   38.2,            # kN·m/m — major axis Mr
                "Vr_major_kN_per_m":    31.5,            # kN/m   — major axis Vr
                "EI_major_kNm2_per_m":  1090.0,          # kN·m²/m — (EI)eff,y
                "GA_major_kN_per_m":    7.31 * 1000,     # kN/m   — (GA)eff,zy
                "Mr_minor_kNm_per_m":   1.29,            # kN·m/m — minor axis Mr
                "Vr_minor_kN_per_m":    10.5,            # kN/m   — minor axis Vr
                "EI_minor_kNm2_per_m":  32.2,            # kN·m²/m — (EI)eff,x
                "GA_minor_kN_per_m":    9.06 * 1000,     # kN/m   — (GA)eff,zx
                "self_weight_kN_per_m2": _sw_E1(105),
            },
        },
        5: {
            175: {
                "Mr_major_kNm_per_m":   87.8,
                "Vr_major_kN_per_m":    52.5,
                "EI_major_kNm2_per_m":  4170.0,
                "GA_major_kN_per_m":    14.6 * 1000,
                "Mr_minor_kNm_per_m":   11.2,
                "Vr_minor_kN_per_m":    31.5,
                "EI_minor_kNm2_per_m":  837.0,
                "GA_minor_kN_per_m":    18.1 * 1000,
                "self_weight_kN_per_m2": _sw_E1(175),
            },
        },
        7: {
            245: {
                "Mr_major_kNm_per_m":   155,
                "Vr_major_kN_per_m":    73.5,
                "EI_major_kNm2_per_m":  10300.0,
                "GA_major_kN_per_m":    21.9 * 1000,
                "Mr_minor_kNm_per_m":   25.8,
                "Vr_minor_kN_per_m":    52.5,
                "EI_minor_kNm2_per_m":  3220.0,
                "GA_minor_kN_per_m":    27.2 * 1000,
                "self_weight_kN_per_m2": _sw_E1(245),
            },
        },
        9: {
            315: {
                "Mr_major_kNm_per_m":   240,
                "Vr_major_kN_per_m":    94.5,
                "EI_major_kNm2_per_m":  20500.0,
                "GA_major_kN_per_m":    29.3 * 1000,
                "Mr_minor_kNm_per_m":   45.6,
                "Vr_minor_kN_per_m":    73.5,
                "EI_minor_kNm2_per_m":  7980.0,
                "GA_minor_kN_per_m":    36.2 * 1000,
                "self_weight_kN_per_m2": _sw_E1(315),
            },
        },
    },

    # =========================================================================
    # Grade E2
    # =========================================================================
    "E2": {
        3: {
            105: {
                "Mr_major_kNm_per_m":   32.4,
                "Vr_major_kN_per_m":    39.7,
                "EI_major_kNm2_per_m":  958.0,
                "GA_major_kN_per_m":    7.98 * 1000,
                "Mr_minor_kNm_per_m":   0.845,
                "Vr_minor_kN_per_m":    13.2,
                "EI_minor_kNm2_per_m":  35.7,
                "GA_minor_kN_per_m":    8.17 * 1000,
                "self_weight_kN_per_m2": _sw_E2(105),
            },
        },
        5: {
            175: {
                "Mr_major_kNm_per_m":   74.5,
                "Vr_major_kN_per_m":    66.2,
                "EI_major_kNm2_per_m":  3670.0,
                "GA_major_kN_per_m":    16.0 * 1000,
                "Mr_minor_kNm_per_m":   7.34,
                "Vr_minor_kN_per_m":    39.7,
                "EI_minor_kNm2_per_m":  930.0,
                "GA_minor_kN_per_m":    16.3 * 1000,
                "self_weight_kN_per_m2": _sw_E2(175),
            },
        },
        7: {
            245: {
                "Mr_major_kNm_per_m":   132,
                "Vr_major_kN_per_m":    92.6,
                "EI_major_kNm2_per_m":  9100.0,
                "GA_major_kN_per_m":    23.9 * 1000,
                "Mr_minor_kNm_per_m":   16.9,
                "Vr_minor_kN_per_m":    66.2,
                "EI_minor_kNm2_per_m":  3570.0,
                "GA_minor_kN_per_m":    24.5 * 1000,
                "self_weight_kN_per_m2": _sw_E2(245),
            },
        },
        9: {
            315: {
                "Mr_major_kNm_per_m":   204,
                "Vr_major_kN_per_m":    119,
                "EI_major_kNm2_per_m":  18100.0,
                "GA_major_kN_per_m":    31.9 * 1000,
                "Mr_minor_kNm_per_m":   29.9,
                "Vr_minor_kN_per_m":    92.6,
                "EI_minor_kNm2_per_m":  8840.0,
                "GA_minor_kN_per_m":    32.7 * 1000,
                "self_weight_kN_per_m2": _sw_E2(315),
            },
        },
    },

    # =========================================================================
    # Grade E3
    # =========================================================================
    "E3": {
        3: {
            105: {
                "Mr_major_kNm_per_m":   23.6,
                "Vr_major_kN_per_m":    27.1,
                "EI_major_kNm2_per_m":  772.0,
                "GA_major_kN_per_m":    5.27 * 1000,
                "Mr_minor_kNm_per_m":   0.827,
                "Vr_minor_kN_per_m":    9.03,
                "EI_minor_kNm2_per_m":  23.2,
                "GA_minor_kN_per_m":    6.44 * 1000,
                "self_weight_kN_per_m2": _sw_E3(105),
            },
        },
        5: {
            175: {
                "Mr_major_kNm_per_m":   54.2,
                "Vr_major_kN_per_m":    45.2,
                "EI_major_kNm2_per_m":  2960.0,
                "GA_major_kN_per_m":    10.5 * 1000,
                "Mr_minor_kNm_per_m":   7.18,
                "Vr_minor_kN_per_m":    27.1,
                "EI_minor_kNm2_per_m":  605.0,
                "GA_minor_kN_per_m":    12.9 * 1000,
                "self_weight_kN_per_m2": _sw_E3(175),
            },
        },
        7: {
            245: {
                "Mr_major_kNm_per_m":   95.7,
                "Vr_major_kN_per_m":    63.2,
                "EI_major_kNm2_per_m":  7310.0,
                "GA_major_kN_per_m":    15.8 * 1000,
                "Mr_minor_kNm_per_m":   16.6,
                "Vr_minor_kN_per_m":    45.2,
                "EI_minor_kNm2_per_m":  2320.0,
                "GA_minor_kN_per_m":    19.3 * 1000,
                "self_weight_kN_per_m2": _sw_E3(245),
            },
        },
        9: {
            315: {
                "Mr_major_kNm_per_m":   148,
                "Vr_major_kN_per_m":    81.3,
                "EI_major_kNm2_per_m":  14600.0,
                "GA_major_kN_per_m":    21.1 * 1000,
                "Mr_minor_kNm_per_m":   29.3,
                "Vr_minor_kN_per_m":    63.2,
                "EI_minor_kNm2_per_m":  5760.0,
                "GA_minor_kN_per_m":    25.8 * 1000,
                "self_weight_kN_per_m2": _sw_E3(315),
            },
        },
    },

    # =========================================================================
    # Grade V1
    # =========================================================================
    "V1": {
        3: {
            105: {
                "Mr_major_kNm_per_m":   13.6,
                "Vr_major_kN_per_m":    39.7,
                "EI_major_kNm2_per_m":  1020.0,
                "GA_major_kN_per_m":    8.02 * 1000,
                "Mr_minor_kNm_per_m":   0.845,
                "Vr_minor_kN_per_m":    13.2,
                "EI_minor_kNm2_per_m":  35.7,
                "GA_minor_kN_per_m":    8.67 * 1000,
                "self_weight_kN_per_m2": _sw_V1(105),
            },
        },
        5: {
            175: {
                "Mr_major_kNm_per_m":   31.2,
                "Vr_major_kN_per_m":    66.2,
                "EI_major_kNm2_per_m":  3920.0,
                "GA_major_kN_per_m":    16.0 * 1000,
                "Mr_minor_kNm_per_m":   7.34,
                "Vr_minor_kN_per_m":    39.7,
                "EI_minor_kNm2_per_m":  930.0,
                "GA_minor_kN_per_m":    17.3 * 1000,
                "self_weight_kN_per_m2": _sw_V1(175),
            },
        },
        7: {
            245: {
                "Mr_major_kNm_per_m":   55.1,
                "Vr_major_kN_per_m":    92.6,
                "EI_major_kNm2_per_m":  9710.0,
                "GA_major_kN_per_m":    24.1 * 1000,
                "Mr_minor_kNm_per_m":   16.9,
                "Vr_minor_kN_per_m":    66.2,
                "EI_minor_kNm2_per_m":  3570.0,
                "GA_minor_kN_per_m":    26.0 * 1000,
                "self_weight_kN_per_m2": _sw_V1(245),
            },
        },
        9: {
            315: {
                "Mr_major_kNm_per_m":   85.5,
                "Vr_major_kN_per_m":    119,
                "EI_major_kNm2_per_m":  19400.0,
                "GA_major_kN_per_m":    32.1 * 1000,
                "Mr_minor_kNm_per_m":   29.9,
                "Vr_minor_kN_per_m":    92.6,
                "EI_minor_kNm2_per_m":  8850.0,
                "GA_minor_kN_per_m":    34.7 * 1000,
                "self_weight_kN_per_m2": _sw_V1(315),
            },
        },
    },

    # =========================================================================
    # Grade V2
    # =========================================================================
    "V2": {
        3: {
            105: {
                "Mr_major_kNm_per_m":   16.0,
                "Vr_major_kN_per_m":    31.5,
                "EI_major_kNm2_per_m":  884.0,
                "GA_major_kN_per_m":    7.19 * 1000,
                "Mr_minor_kNm_per_m":   1.29,
                "Vr_minor_kN_per_m":    10.5,
                "EI_minor_kNm2_per_m":  32.2,
                "GA_minor_kN_per_m":    7.52 * 1000,
                "self_weight_kN_per_m2": _sw_V2(105),
            },
        },
        5: {
            175: {
                "Mr_major_kNm_per_m":   36.8,
                "Vr_major_kN_per_m":    52.5,
                "EI_major_kNm2_per_m":  3390.0,
                "GA_major_kN_per_m":    14.4 * 1000,
                "Mr_minor_kNm_per_m":   11.2,
                "Vr_minor_kN_per_m":    31.5,
                "EI_minor_kNm2_per_m":  837.0,
                "GA_minor_kN_per_m":    15.0 * 1000,
                "self_weight_kN_per_m2": _sw_V2(175),
            },
        },
        7: {
            245: {
                "Mr_major_kNm_per_m":   65.1,
                "Vr_major_kN_per_m":    73.5,
                "EI_major_kNm2_per_m":  8390.0,
                "GA_major_kN_per_m":    21.6 * 1000,
                "Mr_minor_kNm_per_m":   25.7,
                "Vr_minor_kN_per_m":    52.5,
                "EI_minor_kNm2_per_m":  3210.0,
                "GA_minor_kN_per_m":    22.6 * 1000,
                "self_weight_kN_per_m2": _sw_V2(245),
            },
        },
        9: {
            315: {
                "Mr_major_kNm_per_m":   101,
                "Vr_major_kN_per_m":    94.5,
                "EI_major_kNm2_per_m":  16700.0,
                "GA_major_kN_per_m":    28.8 * 1000,
                "Mr_minor_kNm_per_m":   45.5,
                "Vr_minor_kN_per_m":    73.5,
                "EI_minor_kNm2_per_m":  7960.0,
                "GA_minor_kN_per_m":    30.1 * 1000,
                "self_weight_kN_per_m2": _sw_V2(315),
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Nordic X-Lam (E1) dataset
# Source: Nordic X-Lam design table supplied by user (Floor/Roof Slabs).
# Notes:
# - EI table units (10^9 N·mm²/m) are numerically equal to kN·m²/m.
# - GA table units (10^6 N/m) are converted by x1000 -> kN/m.
# - 245 mm has two layups (7s, 7l) with different directional properties.
# ---------------------------------------------------------------------------

_NORDIC_DENSITY_KG_M3: float = 515.0

_NORDIC_SW: dict[int, float] = {
    89: _sw(89, _NORDIC_DENSITY_KG_M3),
    105: _sw(105, _NORDIC_DENSITY_KG_M3),
    143: _sw(143, _NORDIC_DENSITY_KG_M3),
    175: _sw(175, _NORDIC_DENSITY_KG_M3),
    197: _sw(197, _NORDIC_DENSITY_KG_M3),
    213: _sw(213, _NORDIC_DENSITY_KG_M3),
    245: _sw(245, _NORDIC_DENSITY_KG_M3),
    267: _sw(267, _NORDIC_DENSITY_KG_M3),
}

NORDIC_CLT_TABLES: dict[str, dict[int, dict[int, dict[str, float] | dict[str, dict[str, float]]]]] = {
    "E1": {
        3: {
            89: {
                "Mr_major_kNm_per_m": 28.0,
                "Vr_major_kN_per_m": 27.0,
                "EI_major_kNm2_per_m": 683.0,
                "GA_major_kN_per_m": 7.6 * 1000.0,
                "Mr_minor_kNm_per_m": 0.38,
                "Vr_minor_kN_per_m": 5.7,
                "EI_minor_kNm2_per_m": 5.2,
                "GA_minor_kN_per_m": 5.7 * 1000.0,
                "self_weight_kN_per_m2": _NORDIC_SW[89],
            },
            105: {
                "Mr_major_kNm_per_m": 38.0,
                "Vr_major_kN_per_m": 32.0,
                "EI_major_kNm2_per_m": 1088.0,
                "GA_major_kN_per_m": 7.3 * 1000.0,
                "Mr_minor_kNm_per_m": 1.3,
                "Vr_minor_kN_per_m": 11.0,
                "EI_minor_kNm2_per_m": 32.0,
                "GA_minor_kN_per_m": 9.1 * 1000.0,
                "self_weight_kN_per_m2": _NORDIC_SW[105],
            },
        },
        5: {
            143: {
                "Mr_major_kNm_per_m": 65.0,
                "Vr_major_kN_per_m": 43.0,
                "EI_major_kNm2_per_m": 2531.0,
                "GA_major_kN_per_m": 15.0 * 1000.0,
                "Mr_minor_kNm_per_m": 5.0,
                "Vr_minor_kN_per_m": 22.0,
                "EI_minor_kNm2_per_m": 263.0,
                "GA_minor_kN_per_m": 11.0 * 1000.0,
                "self_weight_kN_per_m2": _NORDIC_SW[143],
            },
            175: {
                "Mr_major_kNm_per_m": 88.0,
                "Vr_major_kN_per_m": 53.0,
                "EI_major_kNm2_per_m": 4166.0,
                "GA_major_kN_per_m": 15.0 * 1000.0,
                "Mr_minor_kNm_per_m": 11.0,
                "Vr_minor_kN_per_m": 32.0,
                "EI_minor_kNm2_per_m": 837.0,
                "GA_minor_kN_per_m": 18.0 * 1000.0,
                "self_weight_kN_per_m2": _NORDIC_SW[175],
            },
        },
        7: {
            197: {
                "Mr_major_kNm_per_m": 116.0,
                "Vr_major_kN_per_m": 59.0,
                "EI_major_kNm2_per_m": 6194.0,
                "GA_major_kN_per_m": 23.0 * 1000.0,
                "Mr_minor_kNm_per_m": 11.0,
                "Vr_minor_kN_per_m": 38.0,
                "EI_minor_kNm2_per_m": 1045.0,
                "GA_minor_kN_per_m": 17.0 * 1000.0,
                "self_weight_kN_per_m2": _NORDIC_SW[197],
            },
            213: {
                "Mr_major_kNm_per_m": 158.0,
                "Vr_major_kN_per_m": 64.0,
                "EI_major_kNm2_per_m": 9117.0,
                "GA_major_kN_per_m": 25.0 * 1000.0,
                "Mr_minor_kNm_per_m": 5.0,
                "Vr_minor_kN_per_m": 22.0,
                "EI_minor_kNm2_per_m": 263.0,
                "GA_minor_kN_per_m": 14.0 * 1000.0,
                "self_weight_kN_per_m2": _NORDIC_SW[213],
            },
            245: {
                "7s": {
                    "Mr_major_kNm_per_m": 155.0,
                    "Vr_major_kN_per_m": 74.0,
                    "EI_major_kNm2_per_m": 10306.0,
                    "GA_major_kN_per_m": 22.0 * 1000.0,
                    "Mr_minor_kNm_per_m": 26.0,
                    "Vr_minor_kN_per_m": 53.0,
                    "EI_minor_kNm2_per_m": 3220.0,
                    "GA_minor_kN_per_m": 27.0 * 1000.0,
                    "self_weight_kN_per_m2": _NORDIC_SW[245],
                },
                "7l": {
                    "Mr_major_kNm_per_m": 200.0,
                    "Vr_major_kN_per_m": 74.0,
                    "EI_major_kNm2_per_m": 13279.0,
                    "GA_major_kN_per_m": 22.0 * 1000.0,
                    "Mr_minor_kNm_per_m": 11.0,
                    "Vr_minor_kN_per_m": 32.0,
                    "EI_minor_kNm2_per_m": 837.0,
                    "GA_minor_kN_per_m": 20.0 * 1000.0,
                    "self_weight_kN_per_m2": _NORDIC_SW[245],
                },
            },
        },
        9: {
            267: {
                "Mr_major_kNm_per_m": 239.0,
                "Vr_major_kN_per_m": 80.0,
                "EI_major_kNm2_per_m": 17327.0,
                "GA_major_kN_per_m": 32.0 * 1000.0,
                "Mr_minor_kNm_per_m": 11.0,
                "Vr_minor_kN_per_m": 38.0,
                "EI_minor_kNm2_per_m": 1045.0,
                "GA_minor_kN_per_m": 19.0 * 1000.0,
                "self_weight_kN_per_m2": _NORDIC_SW[267],
            },
        },
    },
}

_CLT_TABLES_BY_SOURCE = {
    "CSA O86": CLT_TABLES,
    "Nordic": NORDIC_CLT_TABLES,
}


# ---------------------------------------------------------------------------
# Public accessor
# ---------------------------------------------------------------------------

def available_clt_sources() -> list[str]:
    """Return supported CLT table source names."""
    return list(_CLT_TABLES_BY_SOURCE.keys())


def get_clt_grades(source: str = "CSA O86") -> list[str]:
    """Return available CLT grades for a selected source."""
    if source not in _CLT_TABLES_BY_SOURCE:
        raise KeyError(f"Unsupported CLT source '{source}'. Choose from {available_clt_sources()}.")
    return list(_CLT_TABLES_BY_SOURCE[source].keys())


def _is_props_dict(entry: dict) -> bool:
    return "Mr_major_kNm_per_m" in entry


def get_clt_section_options(grade: str, source: str = "CSA O86") -> list[tuple[int, int, str]]:
    """
    Return selectable CLT sections for a given grade/source.
    Each option is (num_plies, thickness_mm, layup_variant).
    layup_variant is "" when no variant tag is required.
    """
    if source not in _CLT_TABLES_BY_SOURCE:
        raise KeyError(f"Unsupported CLT source '{source}'. Choose from {available_clt_sources()}.")

    grade_data = _CLT_TABLES_BY_SOURCE[source].get(grade, {})
    options: list[tuple[int, int, str]] = []
    for plies, thickness_map in grade_data.items():
        for thickness, entry in thickness_map.items():
            if _is_props_dict(entry):
                options.append((plies, thickness, ""))
            else:
                for layup in sorted(entry.keys()):
                    options.append((plies, thickness, layup))
    options.sort(key=lambda x: (x[1], x[0], x[2]))
    return options


def get_clt_properties(
    grade: str,
    num_plies: int,
    thickness_mm: float,
    source: str = "CSA O86",
    layup_variant: str = "",
) -> dict[str, float]:
    """
    Look up CLT panel section properties from the table.

    Parameters
    ----------
    grade : str
        CLT grade: ``"E1"``, ``"E2"``, ``"E3"``, ``"V1"``, or ``"V2"``.
    num_plies : int
        Number of plies: 3, 5, 7, or 9.
    thickness_mm : float
        Nominal panel thickness in mm. Must match a table key exactly:
        105, 175, 245, or 315.

    Returns
    -------
    dict[str, float]
        All section property keys for both major and minor axes plus self-weight.

    Raises
    ------
    KeyError
        If the grade / num_plies / thickness combination is not in the table.
    """
    if source not in _CLT_TABLES_BY_SOURCE:
        raise KeyError(f"Unsupported CLT source '{source}'. Choose from {available_clt_sources()}.")

    thickness_key = int(thickness_mm)
    source_tables = _CLT_TABLES_BY_SOURCE[source]

    try:
        entry = source_tables[grade][num_plies][thickness_key]
    except KeyError:
        available_grades = list(source_tables.keys())
        raise KeyError(
            f"CLT properties not found for source='{source}', grade='{grade}', "
            f"num_plies={num_plies}, thickness={thickness_mm} mm. "
            f"Available grades: {available_grades}. "
            "Verify the combination exists in the selected CLT table source."
        )

    if _is_props_dict(entry):
        return entry

    # Entry contains multiple layup variants for the same thickness.
    if layup_variant:
        if layup_variant in entry:
            return entry[layup_variant]
        raise KeyError(
            f"CLT layup variant '{layup_variant}' not found for source='{source}', "
            f"grade='{grade}', num_plies={num_plies}, thickness={thickness_mm} mm. "
            f"Available variants: {sorted(entry.keys())}."
        )

    raise KeyError(
        f"CLT section source='{source}', grade='{grade}', num_plies={num_plies}, "
        f"thickness={thickness_mm} mm requires a layup variant. "
        f"Choose one of: {sorted(entry.keys())}."
    )

    return entry
