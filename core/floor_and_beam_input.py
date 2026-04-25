"""
FloorAndBeamInput dataclass — unified input for integrated floor + beam sizing.

The user specifies the floor geometry and loads once, then chooses whether
supports are rigid walls ("rigid") or glulam beams ("beam"). For beam supports,
the tool automatically selects the minimum passing cross-section.
"""

from dataclasses import dataclass, field


@dataclass
class FloorAndBeamInput:
    """
    Unified input for a floor panel check followed by optional beam selection.

    Floor Panel Parameters
    ----------------------
    span : float
        Panel clear span between supports, m.
        For beam supports this equals 2 × beam tributary width.
    width : float
        Floor bay width perpendicular to panel span, m.
        For beam supports this equals the beam clear span.
    support_condition : str
        "two_sided" or "four_sided".
    specified_dead_load : float
        Dead load including concrete topping weight (if any) but excluding panel self-weight, kN/m².
        Panel self-weight is read from the lookup table and automatically added to the floor panel
        and beam dead loads during structural checks.
    specified_live_load : float
        Specified live load, kN/m². LLRF is applied automatically for the beam check.
    panel_type : str
        "NLT", "GLT", or "CLT".
    panel_grade : str
        Panel grade. For NLT: "SS", "No.1/No.2", or MSR grade.
        For GLT: "20f-E", "24f-E". For CLT: "E1", "E2", "E3", "V1", "V2".
    panel_species : str
        Panel species. Not used for CLT (leave as "").
    panel_thickness_mm : float
        Panel thickness, mm.
        For CLT: number of plies is automatically derived as thickness / 35
        (standard 35 mm ply: 105→3, 175→5, 245→7, 315→9).
    clt_strength_axis : str
        "major" or "minor". Only used when panel_type == "CLT".

    Support Parameters
    ------------------
    support_type : str
        "rigid" — supports are walls or columns; no beam check performed.
        "beam"  — supports are glulam beams; auto-selection is performed.

    Beam Selection Parameters (used only when support_type == "beam")
    -----------------------------------------------------------------
    beam_species : str
        Glulam beam species. "Spruce-Pine" (20f-E only) or "D.Fir-L".
    beam_grade : str
        Glulam stress grade. "20f-E" or "24f-E".
    Bracing is always fully_braced: the floor panel continuously braces the
    beam's compression edge, so KL = 1.0 always applies.
    """

    # --- Floor panel (required) ---
    span: float                      # m — panel clear span
    width: float                     # m — bay width = beam span
    support_condition: str           # "two_sided" | "four_sided"
    specified_dead_load: float       # kN/m² — SDL excl. panel self-weight
    specified_live_load: float       # kN/m²
    panel_type: str                  # "NLT" | "GLT" | "CLT"
    panel_grade: str                 # grade — e.g. "No.1/No.2", "20f-E", "V1"
    panel_species: str               # species — e.g. "S-P-F", "D.Fir-L", "" for CLT
    panel_thickness_mm: float        # mm — total panel thickness
                                     # For CLT: num_plies derived as thickness / 35 mm per ply

    # --- Floor panel (optional with defaults) ---
    clt_strength_axis: str = "major" # CLT only: "major" | "minor"

    # --- Support type ---
    support_type: str = "rigid"      # "rigid" | "beam"

    # --- Beam selection (used only when support_type == "beam") ---
    beam_species: str = "D.Fir-L"          # "Spruce-Pine" | "D.Fir-L"
    beam_grade: str = "24f-E"              # "20f-E" | "24f-E"
    # Bracing is always fully_braced: floor panel continuously braces compression edge (KL = 1.0)
