"""
BeamInput dataclass for glulam floor beam structural checks.

This is separate from FloorInput (panel checks) because beam geometry
and lookup keys are fundamentally different from panel checks.
"""

from dataclasses import dataclass, field


@dataclass
class BeamInput:
    """
    Input parameters for a simply-supported glulam floor beam check.

    Loads are specified as area loads (kN/m²) on the tributary area.
    The checker converts them to line loads using tributary_width.

    Attributes
    ----------
    span : float
        Clear span between supports, m.
    tributary_width : float
        Tributary floor width carried by this beam, m.
        Used to convert area loads → line loads: w = q × tributary_width.
    width_mm : int
        Beam width b, mm. Must match a tabulated width (80, 130, 175, 215, 265, 315, 365).
    depth_mm : int
        Beam depth d, mm. Must match a tabulated depth for the given width.
    species : str
        Species group. One of: "Spruce-Pine", "D.Fir-L".
        Note: "Spruce-Pine" is only available in grade "20f-E".
    grade : str
        Stress grade. One of: "20f-E", "24f-E".
    specified_dead_load : float
        Specified dead load on tributary area, kN/m².
        Should include self-weight of the floor system above the beam
        (panel, topping, finishes) but NOT the beam self-weight.
        The checker adds a representative beam self-weight of 0.5 kN/m²
        equivalent; adjust via beam_self_weight_kN_per_m if needed.
    specified_live_load : float
        Specified live load on tributary area, kN/m².
    bracing_condition : str
        Lateral bracing of the compression edge.
        "fully_braced" — KL = 1.0 (e.g. CLT/NLT deck bearing directly on beam).
        "unbraced"     — KL computed from slenderness CB using Table 2.9.
    unsupported_length_mm : float, optional
        Unsupported length between lateral restraint points, mm.
        Used only when bracing_condition == "unbraced".
        For UDL with intermediate support: Le = 1.92 × unsupported_length_mm (Table 2.8).
        Default 0.0 (ignored when fully_braced).
    beam_self_weight_kN_per_m : float, optional
        Self-weight of the beam as a line load, kN/m.
        Added directly to the beam line load before demand calculations.
        Default 0.0 — user should estimate from beam volume × unit weight (≈5 kN/m³ for glulam).
    """

    span: float                         # m — clear span
    tributary_width: float              # m — tributary floor width
    width_mm: int                       # mm — beam width b
    depth_mm: int                       # mm — beam depth d
    species: str                        # "Spruce-Pine" | "D.Fir-L"
    grade: str                          # "20f-E" | "24f-E"
    specified_dead_load: float          # kN/m² — area dead load on tributary
    specified_live_load: float          # kN/m² — area live load on tributary
    bracing_condition: str              # "fully_braced" | "unbraced"
    unsupported_length_mm: float = 0.0  # mm — used only if unbraced
    beam_self_weight_kN_per_m: float = 0.0  # kN/m — beam self-weight line load
