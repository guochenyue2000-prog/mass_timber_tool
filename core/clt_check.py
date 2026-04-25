"""
clt_check.py
============
CLT (Cross-Laminated Timber) floor checker implementing CSA O86 ULS and SLS checks.

Follows the same :class:`FloorChecker` interface as NLTChecker and GLTChecker.

CLT-specific behaviour
----------------------
- Two strength axes are supported: ``"major"`` (span parallel to outer-ply grain)
  and ``"minor"`` (span perpendicular to outer-ply grain).  Set via
  ``FloorInput.clt_strength_axis``.
- Deflection uses the Euler simply-supported UDL formula:
      δ = 5wL⁴/(384·EI)
  where EI is the effective bending stiffness from Table 2.12 for the selected axis.
- Grade is specified via ``FloorInput.nlt_grade`` (e.g. ``"E1"``, ``"V2"``).
- Number of plies via ``FloorInput.clt_num_plies``.
- Panel thickness via ``FloorInput.nlt_thickness``.

Design assumptions
------------------
- One-way simply-supported span.
- 1 m wide unit strip for all per-unit-width calculations.
- KD = per CSA O86 Cl. 5.3.2.3 (computed from dead/live ratio).
- KS = 1.0 (dry service conditions per CSA O86 Cl. 5.4).
- Mr and Vr from CLT_TABLES already include the phi (ϕ) factor.
- Creep factor = 2.0 for CLT under dry service (CSA O86).
- Self-weight not added to SDL demands; tracked separately for vibration.

References
----------
- CSA O86-19 Engineered Design in Wood, Clauses 5, 8, Annex B.
- CWC Wood Design Manual, p. 111 (Table 2.12) and p. 115 (Strength Tables).
- NBCC 2020, Table 4.1.3.2 (ULS load combinations).
"""

from __future__ import annotations

from mass_timber_tool.core.nlt_check import FloorChecker
from mass_timber_tool.core.inputs import FloorInput
from mass_timber_tool.core.loads import factored_load, calculate_demands, sls_loads, load_duration_factor
from mass_timber_tool.core.results import CheckResult
from mass_timber_tool.data.clt_tables import get_clt_properties


class CLTChecker(FloorChecker):
    """
    CLT (Cross-Laminated Timber) floor checker per CSA O86.

    Uses ``FloorInput.nlt_grade`` for CLT grade (e.g. ``"E1"``),
    ``FloorInput.clt_num_plies`` for number of plies,
    ``FloorInput.nlt_thickness`` for panel thickness (mm), and
    ``FloorInput.clt_strength_axis`` for ``"major"`` or ``"minor"``.

    Class Attributes
    ----------------
    CREEP_FACTOR : float
        Long-term creep multiplier for CLT in dry service (CSA O86 = 2.0).
    KS : float
        Service condition factor (dry service = 1.0).
    """

    CREEP_FACTOR: float = 2.0   # CSA O86 creep factor — CLT, dry service
    KS: float = 1.0              # service condition factor — dry service

    def run(self, floor: FloorInput) -> CheckResult:
        """
        Execute the full CLT floor check sequence.

        Parameters
        ----------
        floor : FloorInput
            Input parameters:
            - ``nlt_grade``        : CLT grade, e.g. ``"E1"``, ``"V2"``
            - ``clt_num_plies``    : number of plies (3, 5, 7, or 9)
            - ``nlt_thickness``    : panel thickness in mm (105, 175, 245, 315)
            - ``clt_strength_axis``: ``"major"`` or ``"minor"``

        Returns
        -------
        CheckResult
            Fully populated result object.

        Raises
        ------
        KeyError
            If grade / num_plies / thickness combination is absent from the table.
        ValueError
            If ``clt_strength_axis`` is not ``"major"`` or ``"minor"``.
        """

        # ----------------------------------------------------------------
        # Step 1: Section property table lookup
        # ----------------------------------------------------------------
        props: dict[str, float] = get_clt_properties(
            grade=floor.nlt_grade,
            num_plies=floor.clt_num_plies,
            thickness_mm=floor.nlt_thickness,
            source=floor.clt_data_source,
            layup_variant=floor.clt_layup_variant,
        )

        axis: str = floor.clt_strength_axis.lower()   # "major" or "minor"
        if axis not in ("major", "minor"):
            raise ValueError(
                f"clt_strength_axis must be 'major' or 'minor', got '{axis}'."
            )

        Mr_table: float = props[f"Mr_{axis}_kNm_per_m"]    # kN·m/m — tabulated Mr (ϕ included)
        Vr_table: float = props[f"Vr_{axis}_kN_per_m"]     # kN/m   — tabulated Vr (ϕ included)
        EI: float       = props[f"EI_{axis}_kNm2_per_m"]   # kN·m²/m — effective bending stiffness
        GA: float       = props[f"GA_{axis}_kN_per_m"]     # kN/m   — effective shear rigidity
        sw: float       = props["self_weight_kN_per_m2"]   # kN/m²  — panel self-weight

        # ----------------------------------------------------------------
        # Step 2: Dead load — specified SDL + panel self-weight
        # ----------------------------------------------------------------
        D_total: float = floor.specified_dead_load + sw   # kN/m² — SDL + panel self-weight
        L: float       = floor.specified_live_load        # kN/m² — specified live load
        span: float    = floor.span                       # m     — clear span

        # ----------------------------------------------------------------
        # Step 3: Load duration factor K_D (CSA O86 Cl. 5.3.2.3)
        # ----------------------------------------------------------------
        KD: float = load_duration_factor(dead=D_total, live=L)  # dimensionless — K_D
        Mr: float = Mr_table * KD                               # kN·m/m — adjusted Mr
        Vr: float = Vr_table * KD                               # kN/m   — adjusted Vr

        # ----------------------------------------------------------------
        # Step 4: Governing ULS factored load (NBCC load combinations)
        # ----------------------------------------------------------------
        wu: float = factored_load(dead=D_total, live=L)   # kN/m² — governing ULS factored load

        # ----------------------------------------------------------------
        # Step 5: ULS demands (per unit width — 1 m strip)
        # ----------------------------------------------------------------
        Mf: float   # kN·m/m — factored moment demand
        Vf: float   # kN/m   — factored shear demand
        Mf, Vf = calculate_demands(wu=wu, span=span)

        # ----------------------------------------------------------------
        # Step 6: ULS capacity checks
        # ----------------------------------------------------------------
        bending_utilization: float = Mf / Mr              # dimensionless
        shear_utilization: float   = Vf / Vr              # dimensionless
        bending_pass: bool = bending_utilization <= 1.0
        shear_pass:   bool = shear_utilization   <= 1.0

        # ----------------------------------------------------------------
        # Step 7: SLS unfactored loads
        # ----------------------------------------------------------------
        w_total: float   # kN/m² — D + L instantaneous
        w_dead:  float   # kN/m² — dead load only (for creep)
        w_total, w_dead = sls_loads(dead=D_total, live=L)

        w_live: float = L   # kN/m² — live load only, for L/360 check

        # ----------------------------------------------------------------
        # Step 8: Deflection calculations — bending + shear (CLT)
        #
        #   delta = 5wL^4 / (384*EI)  +  wL^2 / (8*GA)
        #
        # EI [kN.m2/m] — effective bending stiffness (selected axis)
        # GA [kN/m]    — effective shear rigidity (selected axis)
        # Strip model: w [kN/m2] x 1 m = w [kN/m]; result in m, x1000 = mm.
        # ----------------------------------------------------------------
        coeff: float = 5.0 / 384.0   # dimensionless — UDL bending coefficient

        def _defl_mm(w: float) -> float:
            """Bending + shear deflection in mm for load intensity w [kN/m2]."""
            bending: float = coeff * w * span ** 4 / EI * 1000.0  # mm
            shear:   float = w * span ** 2 / (8.0 * GA) * 1000.0  # mm
            return bending + shear

        delta_instantaneous: float = _defl_mm(w_total)   # mm — total (D+L)
        delta_live:          float = _defl_mm(w_live)    # mm — live load only
        delta_dead:          float = _defl_mm(w_dead)    # mm — dead load only

        delta_longterm: float = delta_dead * self.CREEP_FACTOR  # mm — long-term creep

        # ----------------------------------------------------------------
        # Step 9: SLS deflection limit checks
        # ----------------------------------------------------------------
        limit_L360: float = span * 1000.0 / 360.0   # mm — L/360 (live load)
        limit_L240: float = span * 1000.0 / 240.0   # mm — L/240 (total instantaneous)
        limit_L180: float = span * 1000.0 / 180.0   # mm — L/180 (long-term)

        deflection_L360_pass: bool = delta_live          <= limit_L360
        deflection_L240_pass: bool = delta_instantaneous <= limit_L240
        deflection_L180_pass: bool = delta_longterm      <= limit_L180

        # ----------------------------------------------------------------
        # Step 10: Overall structural verdict
        # ----------------------------------------------------------------
        structural_pass: bool = all([
            bending_pass,
            shear_pass,
            deflection_L360_pass,
            deflection_L240_pass,
            deflection_L180_pass,
        ])

        # ----------------------------------------------------------------
        # Step 11: Vibration engine input fields
        # ----------------------------------------------------------------
        # total_mass includes SDL + panel self-weight + concrete topping (all included in D_total)
        total_mass_kg_per_m2: float = D_total / 9.81 * 1000.0   # kg/m²
        EI_for_vibration:     float = EI                          # kN·m²/m

        # Transverse EI for prEC5 vibration (other axis)
        other_axis: str = "minor" if axis == "major" else "major"
        EI_transverse: float = props[f"EI_{other_axis}_kNm2_per_m"]  # kN·m²/m

        # ----------------------------------------------------------------
        # Assemble and return CheckResult
        # ----------------------------------------------------------------
        return CheckResult(
            floor_input=floor,

            wu=wu,
            Mf=Mf,
            Vf=Vf,

            KD=KD,
            Mr=Mr,
            Vr=Vr,
            EI=EI,

            bending_utilization=bending_utilization,
            shear_utilization=shear_utilization,
            bending_pass=bending_pass,
            shear_pass=shear_pass,

            delta_instantaneous=delta_instantaneous,
            delta_live=delta_live,
            delta_longterm=delta_longterm,

            deflection_L360_pass=deflection_L360_pass,
            deflection_L240_pass=deflection_L240_pass,
            deflection_L180_pass=deflection_L180_pass,

            structural_pass=structural_pass,

            self_weight_kN_per_m2=sw,
            EI_for_vibration=EI_for_vibration,
            total_mass_kg_per_m2=total_mass_kg_per_m2,

            EI_transverse=EI_transverse,
            fn_analytical=None,
            modal_mass=None,
        )
