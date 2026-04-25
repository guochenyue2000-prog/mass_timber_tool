"""
main.py
=======
Entry point for the mass_timber_tool.

Edit the FloorAndBeamInput below, then run:
    C:/Users/cguo/AppData/Local/anaconda3/python.exe -m mass_timber_tool.main

support_type = "rigid"  ->  panel check only
support_type = "beam"   ->  panel check + automatic minimum glulam beam selection
"""

from __future__ import annotations

from mass_timber_tool.core.inputs import FloorInput
from mass_timber_tool.core.nlt_check import NLTChecker
from mass_timber_tool.core.glt_check import GLTChecker
from mass_timber_tool.core.clt_check import CLTChecker
from mass_timber_tool.core.results import CheckResult
from mass_timber_tool.core.glulam_beam_check import print_beam_report
from mass_timber_tool.core.floor_and_beam_input import FloorAndBeamInput
from mass_timber_tool.core.glulam_beam_selector import GlulamBeamSelector


def _pf(flag: bool) -> str:
    return "PASS" if flag else "FAIL"


def print_report(floor: FloorInput, r: CheckResult, creep_factor: float) -> None:
    """Print a formatted ULS + SLS summary report for any panel type."""
    span_mm: float    = floor.span * 1000.0
    limit_L360: float = span_mm / 360.0
    limit_L240: float = span_mm / 240.0
    limit_L180: float = span_mm / 180.0
    delta_live_mm: float = r.delta_live
    sep  = "=" * 64
    thin = "-" * 64

    print(sep)
    print(f"  MASS TIMBER TOOL -- {floor.panel_type} FLOOR CHECK SUMMARY")
    print("  CSA O86 ULS (Bending & Shear) + SLS (Deflection)")
    print(sep)
    print("\n  INPUTS")
    print(thin)
    print(f"  Panel type         : {floor.panel_type}")
    print(f"  Species / Grade    : {floor.nlt_species} {floor.nlt_grade}")
    print(f"  Thickness          : {floor.nlt_thickness:.0f} mm")
    print(f"  Span (L)           : {floor.span:.2f} m")
    print(f"  Width              : {floor.width:.2f} m")
    print(f"  Support condition  : {floor.support_condition}")
    print(f"  SDL (specified)    : {floor.specified_dead_load:.2f} kN/m2")
    print(f"  Live load          : {floor.specified_live_load:.2f} kN/m2")
    print(f"  Self-weight        : {r.self_weight_kN_per_m2:.2f} kN/m2  (from table)")
    print(f"\n  SECTION PROPERTIES  (from {floor.panel_type} table, per m width)")
    print(thin)
    print(f"  K_D (load duration factor) : {r.KD:.3f}  (CSA O86 Cl. 5.3.2.3)")
    print(f"  Mr (moment resistance)     : {r.Mr:.1f} kN.m/m  (table value x K_D)")
    print(f"  Vr (shear resistance)      : {r.Vr:.1f} kN/m    (table value x K_D)")
    print(f"  EI (bending stiffness)     : {r.EI:.0f} kN.m2/m")
    print("\n  ULS -- ULTIMATE LIMIT STATE CHECKS")
    print(thin)
    print(f"  Governing wu           : {r.wu:.3f} kN/m2  (NBCC load combinations)")
    print(f"  Factored moment  Mf    : {r.Mf:.3f} kN.m/m")
    print(f"  Factored shear   Vf    : {r.Vf:.3f} kN/m")
    print()
    print(f"  Bending check  Mf/Mr   : {r.bending_utilization:.3f}  "
          f"({r.Mf:.2f} / {r.Mr:.1f})    [{_pf(r.bending_pass)}]")
    print(f"  Shear check    Vf/Vr   : {r.shear_utilization:.3f}  "
          f"({r.Vf:.2f} / {r.Vr:.1f})    [{_pf(r.shear_pass)}]")
    print("\n  SLS -- SERVICEABILITY LIMIT STATE CHECKS (DEFLECTIONS)")
    print(thin)
    print(f"  Span for limits (L)          : {span_mm:.0f} mm")
    print()
    print(f"  Live-load instantaneous dL   : {delta_live_mm:.2f} mm")
    print(f"  Limit  L/360                 : {limit_L360:.2f} mm    [{_pf(r.deflection_L360_pass)}]")
    print()
    print(f"  Total instantaneous  d(D+L)  : {r.delta_instantaneous:.2f} mm")
    print(f"  Limit  L/240                 : {limit_L240:.2f} mm    [{_pf(r.deflection_L240_pass)}]")
    print()
    print(f"  Long-term (creep)  dLT       : {r.delta_longterm:.2f} mm  "
          f"(dead x {creep_factor:.1f})")
    print(f"  Limit  L/180                 : {limit_L180:.2f} mm    [{_pf(r.deflection_L180_pass)}]")
    print("\n  VIBRATION ENGINE INPUTS  (reserved for downstream check)")
    print(thin)
    print(f"  EI for vibration             : {r.EI_for_vibration:.0f} kN.m2/m")
    print(f"  Total mass                   : {r.total_mass_kg_per_m2:.1f} kg/m2")
    print(f"  fn (analytical)              : {r.fn_analytical}  (not yet calculated)")
    print(f"  Modal mass                   : {r.modal_mass}  (not yet calculated)")
    print()
    print(sep)
    overall_label = "ALL CHECKS PASS" if r.structural_pass else "ONE OR MORE CHECKS FAIL"
    print(f"  OVERALL RESULT  :  {overall_label}")
    print(sep)
    print()


def main() -> None:
    """
    Edit FloorAndBeamInput below, then run the script.

    Panel type options
    ------------------
    "NLT"
        nlt_species  : "S-P-F", "D.Fir-L", "Hem-Fir", "Northern", "MSR"
        nlt_grade    : "SS", "No.1/No.2"  or MSR grade e.g. "1650Fb-1.5E"
        nlt_thickness: 89, 140, 184, 235, 286  (mm)
    "GLT"
        nlt_species  : "Douglas Fir-Larch", "Spruce-Pine"
        nlt_grade    : "20f-E", "24f-E"
        nlt_thickness: 80, 130, 175, 215, 265, 315, 365  (mm)
    "CLT"
        nlt_grade         : "E1", "E2", "E3", "V1", "V2"
        clt_num_plies     : 3, 5, 7, or 9
        nlt_thickness     : 105, 175, 245, 315  (mm)
        clt_strength_axis : "major" or "minor"
        nlt_species       : "" (not used for CLT)

    Beam options (when support_type == "beam")
    ------------------------------------------
    beam_species : "Spruce-Pine" (20f-E only) | "D.Fir-L"
    beam_grade   : "20f-E" | "24f-E"
    (bracing is always fully_braced — floor panel continuously braces compression edge)
    """
    inp = FloorAndBeamInput(
        # --- Floor panel ---
        span=6.1,                        # m   — panel clear span
        width=7.5,                       # m   — bay width = beam span
        support_condition="two_sided",
        specified_dead_load=3.24,         # kN/m² — SDL excl. panel self-weight
        specified_live_load=1.9,         # kN/m²
        panel_type="CLT",                # *** EDIT: "NLT", "GLT", or "CLT" ***
        panel_species="",                # NLT: "S-P-F","D.Fir-L","Hem-Fir","Northern","MSR"
                                         # GLT: "Douglas Fir-Larch","Spruce-Pine"
                                         # CLT: leave as ""
        panel_grade="E1",                # NLT: "SS","No.1/No.2" or MSR grade
                                         # GLT: "20f-E","24f-E"
                                         # CLT: "E1","E2","E3","V1","V2"
        panel_thickness_mm=175.0,        # NLT: 89,140,184,235,286
                                         # GLT: 80,130,175,215,265,315,365
                                         # CLT: 105,175,245,315 (plies derived: thickness/35)
        clt_strength_axis="major",       # CLT only: "major" or "minor"
        # --- Support type ---
        support_type="beam",             # *** EDIT: "rigid" or "beam" ***
        # --- Beam selection (used only when support_type == "beam") ---
        beam_species="D.Fir-L",         # "Spruce-Pine" | "D.Fir-L"
        beam_grade="20f-E",             # "20f-E" | "24f-E"
    )

    # Derive CLT num_plies from thickness (standard 35 mm ply)
    clt_num_plies: int = round(inp.panel_thickness_mm / 35)

    # Build FloorInput for the panel checker
    floor = FloorInput(
        span=inp.span,
        width=inp.width,
        support_condition=inp.support_condition,
        specified_dead_load=inp.specified_dead_load,
        specified_live_load=inp.specified_live_load,
        panel_type=inp.panel_type,
        nlt_species=inp.panel_species,
        nlt_grade=inp.panel_grade,
        nlt_thickness=inp.panel_thickness_mm,
        clt_num_plies=clt_num_plies,
        clt_strength_axis=inp.clt_strength_axis,
    )

    # Step 1: Panel check
    checkers = {"NLT": NLTChecker(), "GLT": GLTChecker(), "CLT": CLTChecker()}
    checker = checkers.get(inp.panel_type)
    if checker is None:
        raise ValueError(f"Unknown panel_type '{inp.panel_type}'.")
    panel_result: CheckResult = checker.run(floor)
    print_report(floor, panel_result, type(checker).CREEP_FACTOR)

    # Step 2: Beam selection (only if beam support)
    if inp.support_type == "beam":
        print("  Selecting minimum glulam beam section...")
        beam_result = GlulamBeamSelector().select(inp, panel_result)
        b = beam_result.beam_input
        print(f"  SELECTED SECTION: {b.width_mm} x {b.depth_mm} mm  {b.species}  {b.grade}")
        print()
        print_beam_report(beam_result)


if __name__ == "__main__":
    main()
