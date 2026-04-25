"""
loads.py
========
NBCC load combination helpers and structural demand calculations.

All loads are in kN/m² (pressure) unless otherwise stated.  Demand outputs
are per-unit-width values (kN·m/m and kN/m) for a one-metre-wide strip model.

Load combinations implemented (NBCC 2020 Table 4.1.3.2, Case 1 and 2):
    1.  1.4 D
    2.  1.25 D + 1.5 L
    3.  0.9 D + 1.5 L   (uplift / minimum gravity companion)

The governing (maximum) factored load is returned by :func:`factored_load`.
"""

from __future__ import annotations

import math


def load_duration_factor(dead: float, live: float) -> float:
    """
    Calculate the load duration factor K_D per CSA O86 Cl. 5.3.2.3 / Table 2.11.

    Formula (CSA O86 Note 1):
        K_D = 1.0 - 0.50 * log10(P_L / P_S),  bounded to [0.65, 1.0]

    Where:
        P_L = specified long-term load  = dead load (kN/m²)
        P_S = specified standard-term load = live load (kN/m²)
            (per Note 2: P_S = S, L, S + 0.5L, or 0.5S + L)

    Special cases:
        - If P_L = 0  →  K_D = 1.0  (no long-term load, no reduction)
        - If P_S = 0  →  K_D = 0.65 (all long-term, maximum reduction)
        - K_D is bounded: minimum 0.65, maximum 1.0

    Parameters
    ----------
    dead : float
        Specified long-term load P_L (kN/m²) — typically dead / SDL.
    live : float
        Specified standard-term load P_S (kN/m²) — typically live or snow.

    Returns
    -------
    float
        K_D load duration factor (dimensionless), in range [0.65, 1.0].
    """
    if dead <= 0.0:
        return 1.0                                     # no long-term load → no reduction
    if live <= 0.0:
        return 0.65                                    # all long-term load → maximum reduction

    KD: float = 1.0 - 0.50 * math.log10(dead / live)  # dimensionless — CSA O86 formula
    return max(min(KD, 1.0), 0.65)                    # bounded: 0.65 <= K_D <= 1.0


def factored_load(dead: float, live: float) -> float:
    """
    Return the governing ULS factored load *wu* (kN/m²) from NBCC combinations.

    Three combinations are evaluated:

    =========  =============================================
    Case       Combination
    =========  =============================================
    1          1.4 D
    2          1.25 D + 1.5 L
    3          0.9 D + 1.5 L  (minimum dead, companion live)
    =========  =============================================

    Parameters
    ----------
    dead : float
        Total dead load (self-weight + SDL) in kN/m².
    live : float
        Specified live load in kN/m².

    Returns
    -------
    float
        Governing factored load *wu* in kN/m².
    """
    combo_1 = 1.4 * dead                    # kN/m² — NBCC Case 1: dead only
    combo_2 = 1.25 * dead + 1.5 * live      # kN/m² — NBCC Case 2: principal live
    combo_3 = 0.9 * dead + 1.5 * live       # kN/m² — NBCC Case 3: min dead + live

    wu = max(combo_1, combo_2, combo_3)     # kN/m² — governing factored load
    return wu


def calculate_demands(wu: float, span: float) -> tuple[float, float]:
    """
    Calculate factored moment and shear demands for a simply-supported span.

    Uses standard beam mechanics for a uniformly distributed load on a
    simply-supported single span.  All values are per unit width (1 m strip).

    Parameters
    ----------
    wu : float
        Governing factored uniform load in kN/m²
        (treated as kN/m per metre width for a 1 m strip).
    span : float
        Clear span *L* between supports in metres (m).

    Returns
    -------
    Mf : float
        Factored midspan moment demand, kN·m/m.
        ``Mf = wu * L² / 8``
    Vf : float
        Factored end shear demand, kN/m.
        ``Vf = wu * L / 2``
    """
    Mf: float = wu * span ** 2 / 8.0   # kN·m/m — simply-supported midspan moment
    Vf: float = wu * span / 2.0        # kN/m   — simply-supported end shear

    return Mf, Vf


def sls_loads(dead: float, live: float) -> tuple[float, float]:
    """
    Return SLS (serviceability limit state) loads for deflection checks.

    No load factors are applied at SLS; specified (characteristic) loads are
    used directly per NBCC and CSA O86 serviceability requirements.

    Parameters
    ----------
    dead : float
        Total dead load (self-weight + SDL) in kN/m².
    live : float
        Specified live load in kN/m².

    Returns
    -------
    w_total : float
        Total instantaneous SLS load (D + L) in kN/m².
        Used for instantaneous deflection checks (L/240).
    w_dead : float
        Dead load only in kN/m².
        Used for long-term / creep deflection calculations (L/180).
    """
    w_total: float = dead + live    # kN/m² — instantaneous total (D + L)
    w_dead: float = dead            # kN/m² — dead load component only

    return w_total, w_dead
