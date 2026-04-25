"""
glt_check.py
============
GLT (Glulam Timber) floor checker implementing CSA O86 ULS and SLS checks.

Follows the same :class:`FloorChecker` interface as :class:`NLTChecker`
so callers can swap panel types without changing downstream code.

Design assumptions
------------------
- One-way simply-supported span (two_sided support_condition).
- 1 m wide unit strip for all per-unit-width calculations.
- KD = 1.0 (standard load duration — governing combination already selected).
- KS = 1.0 (dry service conditions per CSA O86 Cl. 5.4).
- Mr and Vr from GLT_TABLES already include the phi (ϕ) factor.
- Creep factor = 2.0 for GLT under dry service (CSA O86).
- Specified dead load is used as-is; self-weight tracked separately for
  vibration engine and not added to structural demands.
- Deflection formula: simply-supported UDL, elastic beam theory.

References
----------
- CSA O86-19 Engineered Design in Wood, Clauses 5, 6, Annex A.
- CWC Wood Design Manual, Panel Selection Tables p. 100.
- NBCC 2020, Table 4.1.3.2 (ULS load combinations).
"""

from __future__ import annotations

from mass_timber_tool.core.nlt_check import FloorChecker
from mass_timber_tool.core.inputs import FloorInput
from mass_timber_tool.core.loads import factored_load, calculate_demands, sls_loads, load_duration_factor
from mass_timber_tool.core.results import CheckResult
from mass_timber_tool.data.glt_tables import get_glt_properties


class GLTChecker(FloorChecker):
    """
    GLT (Glulam Timber) floor checker per CSA O86.

    Executes the following check sequence when :meth:`run` is called:

    1. Table lookup — fetch Mr, Vr, EI, self_weight for the specified panel.
    2. Dead load — use specified_dead_load directly (self-weight tracked separately).
    3. ULS factored load — govern NBCC load combinations.
    4. ULS demands — midspan moment Mf and end shear Vf.
    5. ULS checks — bending (Mf ≤ Mr) and shear (Vf ≤ Vr).
    6. SLS loads — unfactored D and L for deflection calculations.
    7. Deflection calculations — instantaneous and long-term.
    8. SLS checks — L/360, L/240, L/180 limits.
    9. Overall verdict — all checks must pass.
    10. Assemble and return :class:`CheckResult`.

    Uses ``floor.nlt_species`` and ``floor.nlt_grade`` fields for GLT species
    and grade respectively (field names are inherited from FloorInput).

    Class Attributes
    ----------------
    CREEP_FACTOR : float
        Long-term creep multiplier for GLT in dry service (CSA O86 = 2.0).
    KD : float
        Load duration factor (standard loading = 1.0 per CSA O86 Cl. 5.3.2).
    KS : float
        Service condition factor (dry service = 1.0 per CSA O86 Table 5.4.2).
    """

    CREEP_FACTOR: float = 2.0   # CSA O86 creep factor — GLT, dry service conditions
    KD: float = 1.0              # load duration factor  — standard (≥ 7 day) loading
    KS: float = 1.0              # service condition     — dry (≤ 15 % MC in service)

    def run(self, floor: FloorInput) -> CheckResult:
        """
        Execute the full GLT floor check sequence.

        Parameters
        ----------
        floor : FloorInput
            Input parameters. Use ``nlt_species`` for GLT species
            (e.g. ``"Douglas Fir-Larch"``, ``"Spruce-Pine"``) and
            ``nlt_grade`` for GLT grade (e.g. ``"20f-E"``).
            ``nlt_thickness`` is the panel thickness in mm.

        Returns
        -------
        CheckResult
            Fully populated result object.

        Raises
        ------
        KeyError
            If the species / grade / thickness combination is absent from
            the GLT section property table.
        """

        # ----------------------------------------------------------------
        # Step 1: Section property table lookup
        # ----------------------------------------------------------------
        props: dict[str, float] = get_glt_properties(
            species=floor.nlt_species,      # GLT species (reuses nlt_species field)
            grade=floor.nlt_grade,          # GLT grade   (reuses nlt_grade field)
            thickness_mm=floor.nlt_thickness,
        )

        Mr_table: float = props["Mr_kNm_per_m"]           # kN·m/m — tabulated moment resistance (ϕ included)
        Vr_table: float = props["Vr_kN_per_m"]            # kN/m   — tabulated shear resistance (ϕ included)
        EI: float       = props["EI_kNm2_per_m"]          # kN·m²/m — bending stiffness per unit width
        sw: float       = props["self_weight_kN_per_m2"]  # kN/m²  — panel self-weight

        # ----------------------------------------------------------------
        # Step 2: Dead load — specified SDL + panel self-weight
        # ----------------------------------------------------------------
        D_total: float = floor.specified_dead_load + sw   # kN/m² — SDL + panel self-weight
        L: float       = floor.specified_live_load        # kN/m² — specified live load (alias)
        span: float    = floor.span                       # m     — clear span (alias)

        # ----------------------------------------------------------------
        # Step 3: Load duration factor K_D (CSA O86 Cl. 5.3.2.3)
        # P_L = dead (long-term), P_S = live (standard-term)
        # ----------------------------------------------------------------
        KD: float = load_duration_factor(dead=D_total, live=L)  # dimensionless — K_D per CSA O86
        Mr: float = Mr_table * KD                               # kN·m/m — K_D-adjusted moment resistance
        Vr: float = Vr_table * KD                               # kN/m   — K_D-adjusted shear resistance

        # ----------------------------------------------------------------
        # Step 4: Governing ULS factored load (NBCC load combinations)
        # ----------------------------------------------------------------
        wu: float = factored_load(dead=D_total, live=L)   # kN/m² — governing ULS factored load

        # ----------------------------------------------------------------
        # Step 4: ULS demands (per unit width — 1 m strip)
        # ----------------------------------------------------------------
        Mf: float   # kN·m/m — factored moment demand
        Vf: float   # kN/m   — factored shear demand
        Mf, Vf = calculate_demands(wu=wu, span=span)

        # ----------------------------------------------------------------
        # Step 5: ULS capacity checks
        # ----------------------------------------------------------------
        bending_utilization: float = Mf / Mr              # dimensionless — demand / capacity ratio
        shear_utilization: float   = Vf / Vr              # dimensionless — demand / capacity ratio
        bending_pass: bool = bending_utilization <= 1.0   # True if Mf does not exceed Mr
        shear_pass:   bool = shear_utilization   <= 1.0   # True if Vf does not exceed Vr

        # ----------------------------------------------------------------
        # Step 6: SLS unfactored loads
        # ----------------------------------------------------------------
        w_total: float   # kN/m² — total SLS load (D + L), for instantaneous deflection
        w_dead:  float   # kN/m² — dead load only, for long-term / creep deflection
        w_total, w_dead = sls_loads(dead=D_total, live=L)

        w_live: float = L   # kN/m² — live load only (alias), for L/360 check

        # ----------------------------------------------------------------
        # Step 7: Deflection calculations
        #
        # Formula (simply-supported UDL, elastic):
        #   δ = 5 * w * L⁴ / (384 * EI)
        #
        # Strip model: w [kN/m²] × 1 m width = w [kN/m] per metre of span.
        # EI in kN·m²/m.  Result is in metres; multiply by 1000 for mm.
        # ----------------------------------------------------------------
        coeff: float = 5.0 / 384.0   # dimensionless — UDL simply-supported formula coefficient

        delta_inst_m: float = coeff * w_total * span ** 4 / EI   # m — instantaneous (D+L)
        delta_live_m: float = coeff * w_live  * span ** 4 / EI   # m — live load only
        delta_dead_m: float = coeff * w_dead  * span ** 4 / EI   # m — dead load only

        delta_instantaneous: float = delta_inst_m * 1000.0        # mm — total instantaneous (D+L)
        delta_live:          float = delta_live_m * 1000.0        # mm — live load only
        delta_dead:          float = delta_dead_m * 1000.0        # mm — dead load instantaneous

        delta_longterm: float = delta_dead * self.CREEP_FACTOR    # mm — long-term creep deflection

        # ----------------------------------------------------------------
        # Step 8: SLS deflection limit checks
        # ----------------------------------------------------------------
        limit_L360: float = span * 1000.0 / 360.0   # mm — L/360 limit (live load only)
        limit_L240: float = span * 1000.0 / 240.0   # mm — L/240 limit (total instantaneous)
        limit_L180: float = span * 1000.0 / 180.0   # mm — L/180 limit (long-term)

        deflection_L360_pass: bool = delta_live          <= limit_L360   # live-load check
        deflection_L240_pass: bool = delta_instantaneous <= limit_L240   # total instantaneous check
        deflection_L180_pass: bool = delta_longterm      <= limit_L180   # long-term check

        # ----------------------------------------------------------------
        # Step 9: Overall structural verdict
        # ----------------------------------------------------------------
        structural_pass: bool = all([
            bending_pass,
            shear_pass,
            deflection_L360_pass,
            deflection_L240_pass,
            deflection_L180_pass,
        ])

        # ----------------------------------------------------------------
        # Step 10: Vibration engine input fields
        # ----------------------------------------------------------------
        # total_mass includes SDL + panel self-weight + concrete topping (all included in D_total)
        total_mass_kg_per_m2: float = D_total / 9.81 * 1000.0   # kg/m² — mass for vibration calcs
        EI_for_vibration:     float = EI                          # kN·m²/m — explicit copy for vibration engine
        EI_transverse:        float = EI / 30.0                   # kN·m²/m — E_T/E ≈ 1/30 for glulam (CSA O86)

        # ----------------------------------------------------------------
        # Assemble and return CheckResult
        # ----------------------------------------------------------------
        return CheckResult(
            # --- Input passthrough ---
            floor_input=floor,

            # --- ULS demands ---
            wu=wu,    # kN/m²  — governing ULS factored load
            Mf=Mf,    # kN·m/m — factored moment demand
            Vf=Vf,    # kN/m   — factored shear demand

            # --- Load duration factor ---
            KD=KD,    # dimensionless — CSA O86 K_D

            # --- Section properties ---
            Mr=Mr,    # kN·m/m — K_D-adjusted moment resistance
            Vr=Vr,    # kN/m   — K_D-adjusted shear resistance
            EI=EI,    # kN·m²/m — bending stiffness per unit width

            # --- ULS utilization and pass/fail ---
            bending_utilization=bending_utilization,
            shear_utilization=shear_utilization,
            bending_pass=bending_pass,
            shear_pass=shear_pass,

            # --- SLS deflections ---
            delta_instantaneous=delta_instantaneous,   # mm
            delta_live=delta_live,                     # mm
            delta_longterm=delta_longterm,              # mm

            # --- SLS pass/fail ---
            deflection_L360_pass=deflection_L360_pass,
            deflection_L240_pass=deflection_L240_pass,
            deflection_L180_pass=deflection_L180_pass,

            # --- Overall verdict ---
            structural_pass=structural_pass,

            # --- Vibration engine inputs ---
            self_weight_kN_per_m2=sw,
            EI_for_vibration=EI_for_vibration,
            total_mass_kg_per_m2=total_mass_kg_per_m2,
            EI_transverse=EI_transverse,

            # --- Vibration outputs (reserved, None until vibration engine runs) ---
            fn_analytical=None,
            modal_mass=None,
        )
