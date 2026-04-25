"""
app.py
======
Streamlit UI for the Mass Timber Floor Design Tool.

Run from the project root (ULS check/) with:
    C:/Users/cguo/AppData/Local/anaconda3/python.exe -m streamlit run mass_timber_tool/app.py
"""

from __future__ import annotations

import os
import sys

import streamlit as st

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mass_timber_tool.core.inputs import FloorInput
from mass_timber_tool.core.nlt_check import NLTChecker
from mass_timber_tool.core.glt_check import GLTChecker
from mass_timber_tool.core.clt_check import CLTChecker
from mass_timber_tool.core.results import CheckResult
from mass_timber_tool.core.beam_inputs import BeamInput
from mass_timber_tool.core.beam_results import BeamCheckResult
from mass_timber_tool.core.floor_and_beam_input import FloorAndBeamInput
from mass_timber_tool.core.glulam_beam_check import GlulamBeamChecker
from mass_timber_tool.core.glulam_beam_selector import GlulamBeamSelector, _GLULAM_DENSITY, _GLULAM_DENSITY_DEFAULT
from mass_timber_tool.core.panel_selector import PanelSelector
from mass_timber_tool.core.vibration_check import VibrationInput, VibrationResult, run_vibration_check
from mass_timber_tool.core.glt_beam_fire_check import apply_fire_upgrades
from mass_timber_tool.data.clt_tables import available_clt_sources, get_clt_grades

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mass Timber Floor Design Tool",
    page_icon="🪵",
    layout="wide",
)

# Concrete topping unit weight — consistent with vibration check (conc_density_kg_m3 = 2000)
_CONC_UNIT_WEIGHT_kN_m3: float = 2000 * 9.81 / 1000   # = 19.62 kN/m³

# ---------------------------------------------------------------------------
# Dropdown option maps
# ---------------------------------------------------------------------------
NLT_SPECIES = ["D.Fir-L", "Hem-Fir", "S-P-F", "Northern", "MSR"]

NLT_GRADES: dict[str, list[str]] = {
    "D.Fir-L":  ["SS", "No.1/No.2"],
    "Hem-Fir":  ["SS", "No.1/No.2"],
    "S-P-F":    ["SS", "No.1/No.2"],
    "Northern": ["SS", "No.1/No.2"],
    "MSR": [
        "1450Fb-1.3E", "1650Fb-1.5E", "1800Fb-1.6E",
        "1950Fb-1.7E", "2100Fb-1.8E", "2250Fb-1.9E", "2400Fb-2.0E",
    ],
}
NLT_THICK = [89, 140, 184, 235, 286]

GLT_SPECIES = ["Douglas Fir-Larch", "Spruce-Pine"]
GLT_GRADES  = ["20f-E", "24f-E"]
GLT_THICK   = [80, 130, 175, 215, 265, 315, 365]

CLT_GRADES  = ["E1", "E2", "E3", "V1", "V2"]
CLT_THICK_OPTIONS = {
    "105 mm (3-ply)": 105,
    "175 mm (5-ply)": 175,
    "245 mm (7-ply)": 245,
    "315 mm (9-ply)": 315,
}

BEAM_GRADES: dict[str, list[str]] = {
    "D.Fir-L":    ["20f-E", "24f-E"],
    "Spruce-Pine": ["20f-E"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _show_check_row(label: str, demand: float, capacity: float,
                    util: float, passed: bool, unit: str = "") -> None:
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    c1.write(label)
    c2.write(f"{demand:.2f} {unit}")
    c3.write(f"{capacity:.2f} {unit}")
    if passed:
        c4.success(f"{util:.3f}  PASS")
    else:
        c4.error(f"{util:.3f}  FAIL")


def _show_defl_row(label: str, delta: float, limit: float, passed: bool) -> None:
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    c1.write(label)
    c2.write(f"{delta:.2f} mm")
    c3.write(f"{limit:.2f} mm")
    if passed:
        c4.success("PASS")
    else:
        c4.error("FAIL")


def _beam_detail(br: BeamCheckResult) -> None:
    """Render the full detail view for one beam check result."""
    bi = br.beam_input
    beam_span_mm = bi.span * 1000.0

    # Loads
    st.markdown("#### Loads")
    l1, l2, l3, l4, l5 = st.columns(5)
    l1.metric("Beam Span (m)",        f"{bi.span:.2f}")
    l2.metric("Trib. Width (m)",      f"{bi.tributary_width:.2f}")
    l3.metric("Trib. Area (m²)",      f"{bi.span * bi.tributary_width:.1f}")
    l4.metric("LLRF",                 f"{br.LLRF:.3f}")
    l5.metric("Live (reduced, kN/m²)", f"{br.live_load_reduced:.3f}")

    lu1, lu2, lu3 = st.columns(3)
    lu1.metric("wu  line load (kN/m)", f"{br.wu_kN_per_m:.2f}")
    lu2.metric("w   line load (kN/m)", f"{br.w_kN_per_m:.2f}")
    lu3.metric("KD",                   f"{br.KD:.3f}")

    st.divider()

    # Resistance factors
    st.markdown("#### Resistance Factors")
    rf1, rf2, rf3, rf4 = st.columns(4)
    rf1.metric("CB (slenderness)",   f"{br.CB:.2f}")
    rf2.metric("KL (lateral stab.)", f"{br.KL:.3f}")
    rf3.metric("KZbg (size factor)", f"{br.KZbg:.3f}")
    rf4.metric("Governing factor",   br.governing_factor)

    st.divider()

    # ULS checks
    st.markdown("#### ULS — Ultimate Limit State")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    c1.markdown("**Check**"); c2.markdown("**Demand**"); c3.markdown("**Capacity**"); c4.markdown("**Utilization**")

    _show_check_row(
        "Bending  Mf / Mr",
        br.Mf_kNm, br.Mr_kNm, br.bending_utilization, br.bending_pass, "kN·m",
    )
    _show_check_row(
        f"Shear (volume-based)  Wf / Wr  [V={br.beam_volume_m3:.3f} m³]",
        br.Wf_kN, br.Wr_kN, br.shear_utilization, br.shear_pass, "kN",
    )

    bx1, bx2 = st.columns(2)
    bx1.write(f"M'r (table, unadjusted): **{br.Mr_prime_kNm:.1f} kN·m**")
    bx2.write(f"Mf: **{br.Mf_kNm:.1f} kN·m**  |  Vf: **{br.Vf_kN:.1f} kN**  |  Wf: **{br.Wf_kN:.1f} kN**")

    st.divider()

    # SLS checks
    st.markdown("#### SLS — Serviceability Limit State (Deflections)")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    c1.markdown("**Check**"); c2.markdown("**Deflection**"); c3.markdown("**Limit**"); c4.markdown("**Status**")

    _show_defl_row(
        f"Live load  (L/360 = {beam_span_mm/360:.1f} mm)",
        br.delta_live_mm, beam_span_mm / 360.0, br.deflection_L360_pass,
    )
    _show_defl_row(
        f"Total  (L/180 = {beam_span_mm/180:.1f} mm)",
        br.delta_total_mm, beam_span_mm / 180.0, br.deflection_L180_pass,
    )

    st.divider()
    st.write(f"**EsI = {br.EsI_kNm2:.0f} kN·m²**")


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("Mass Timber Floor Design Tool")
st.caption("CSA O86-24")
st.divider()

# ---------------------------------------------------------------------------
# Full-page inputs — three card columns
# ---------------------------------------------------------------------------
st.subheader("Design Inputs")

col_geo, col_panel, col_support = st.columns(3)

# ── Card 1: Floor Geometry & Loads ─────────────────────────────────────────
with col_geo:
    st.markdown("##### Floor Geometry & Loads")
    span  = st.number_input("Panel Span (m)",  min_value=1.0, max_value=20.0, value=6.0,  step=0.1)
    width = st.number_input("Bay Width (m)",   min_value=1.0, max_value=30.0, value=6.0,  step=0.1)
    st.markdown("")
    SDL         = st.number_input("SDL (kN/m²)  excl. self-weight & topping", min_value=0.0, value=1.0, step=0.1)
    LL          = st.number_input("Live Load (kN/m²)", min_value=0.0, value=2.4, step=0.1)
    _conc_thick = st.number_input(
        "Concrete topping thickness (m)",
        min_value=0.0, max_value=0.30, value=0.0, step=0.01,
        help="Dead load added to SDL for ULS check and used in vibration check. Set 0 if none.",
    )
    _conc_DL = _conc_thick * _CONC_UNIT_WEIGHT_kN_m3
    if _conc_thick > 0:
        st.caption(f"Concrete topping DL: {_conc_DL:.2f} kN/m²  (density 2000 kg/m³)")

# ── Card 2: Panel ──────────────────────────────────────────────────────────
with col_panel:
    st.markdown("##### Panel")
    panel_type = st.selectbox("Panel Type", ["NLT", "GLT", "CLT"])
    clt_source = "CSA O86"

    if panel_type == "NLT":
        panel_species = st.selectbox("Species", NLT_SPECIES)
        panel_grade   = st.selectbox("Grade",   NLT_GRADES[panel_species])
        clt_axis      = "major"

    elif panel_type == "GLT":
        panel_species = st.selectbox("Species", GLT_SPECIES)
        panel_grade   = st.selectbox("Grade",   GLT_GRADES)
        clt_axis      = "major"

    else:  # CLT
        panel_species = ""
        clt_source    = st.selectbox("CLT Table Source", available_clt_sources(), index=0)
        clt_grades    = get_clt_grades(clt_source)
        default_idx   = clt_grades.index("E1") if "E1" in clt_grades else 0
        panel_grade   = st.selectbox("CLT Grade", clt_grades, index=default_idx)
        clt_axis      = st.radio(
            "Strength Axis",
            options=["major", "minor"],
            format_func=lambda x: "Major (span || outer-ply grain)" if x == "major" else "Minor (span perp. outer-ply grain)",
        )

# ── Card 3: Support & Beam ─────────────────────────────────────────────────
with col_support:
    st.markdown("##### Support & Beam")
    support_type = st.radio(
        "Support type",
        options=["rigid", "beam"],
        format_func=lambda x: "Rigid (wall / column)" if x == "rigid" else "Beam (auto-select glulam)",
    )

    if support_type == "beam":
        beam_species = st.selectbox("Beam Species", list(BEAM_GRADES.keys()))
        beam_grade   = st.selectbox("Beam Grade",   BEAM_GRADES[beam_species])
    else:
        beam_species = "D.Fir-L"
        beam_grade   = "24f-E"

st.divider()
run = st.button("Run Structural Check", type="primary", use_container_width=True)
st.divider()


# ---------------------------------------------------------------------------
# Run the check when button is pressed
# ---------------------------------------------------------------------------
if run:
    # Placeholder FloorInput — thickness is overridden per-section by PanelSelector
    floor_base = FloorInput(
        span=span,
        width=width,
        support_condition="two_sided",
        specified_dead_load=SDL + _conc_DL,
        specified_live_load=LL,
        panel_type=panel_type,
        nlt_species=panel_species,
        nlt_grade=panel_grade,
        nlt_thickness=0.0,   # overridden by PanelSelector
        clt_num_plies=3,     # overridden by PanelSelector for CLT
        clt_strength_axis=clt_axis,
        clt_data_source=clt_source,
        clt_layup_variant="",
    )

    _creep_map = {
        "NLT": NLTChecker.CREEP_FACTOR,
        "GLT": GLTChecker.CREEP_FACTOR,
        "CLT": CLTChecker.CREEP_FACTOR,
    }

    try:
        all_panel_results = PanelSelector().select_all(floor_base)
        passing_panels    = [r for r in all_panel_results if r.structural_pass]
        default_panel     = passing_panels[0] if passing_panels else None

        st.session_state["all_panel_results"] = all_panel_results
        st.session_state["panel_result"]      = default_panel
        st.session_state["floor"]             = default_panel.floor_input if default_panel else floor_base
        st.session_state["creep"]             = _creep_map[panel_type]
        st.session_state["error"]             = None
        st.session_state["support_type"]      = support_type

        if support_type == "beam" and default_panel is not None:
            _dp_fi = default_panel.floor_input
            inp = FloorAndBeamInput(
                span=span,
                width=width,
                support_condition="two_sided",
                specified_dead_load=SDL + _conc_DL,  # Include concrete topping in beam dead load
                specified_live_load=LL,
                panel_type=panel_type,
                panel_species=panel_species,
                panel_grade=panel_grade,
                panel_thickness_mm=_dp_fi.nlt_thickness,
                clt_strength_axis=clt_axis,
                support_type="beam",
                beam_species=beam_species,
                beam_grade=beam_grade,
            )
            try:
                all_beams = GlulamBeamSelector().select_all(inp, default_panel)
                st.session_state["all_beam_results"] = all_beams
                st.session_state["beam_error"]       = None
            except ValueError as e:
                st.session_state["all_beam_results"] = []
                st.session_state["beam_error"]       = str(e)
        else:
            st.session_state["all_beam_results"] = []
            st.session_state["beam_error"]       = None

        # Clear stale vibration results when structural inputs change
        st.session_state["vib_result"] = None
        st.session_state["vib_error"]  = None

    except Exception as e:
        st.session_state["error"]             = str(e)
        st.session_state["panel_result"]      = None
        st.session_state["all_panel_results"] = []


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if "error" in st.session_state and st.session_state["error"]:
    st.error(f"Error running check: {st.session_state['error']}")

elif "all_panel_results" in st.session_state and st.session_state.get("all_panel_results"):

    all_panels: list       = st.session_state.get("all_panel_results", [])
    pr: CheckResult        = st.session_state["panel_result"]   # thinnest passing (default)
    fl: FloorInput         = st.session_state["floor"]
    creep: float           = st.session_state["creep"]
    saved_support: str     = st.session_state.get("support_type", "rigid")
    all_beams: list        = st.session_state.get("all_beam_results", [])
    _beam_for_vib          = None   # set inside Tab 2 when beam support is active

    # Overall verdict banner
    _any_panel_passes = any(r.structural_pass for r in all_panels)
    beam_ok = (not all_beams) or all_beams[0].structural_pass
    if _any_panel_passes and beam_ok:
        st.success("### ALL CHECKS PASS")
    else:
        st.error("### ONE OR MORE CHECKS FAIL")

    # Tabs
    tab_labels = ["Floor Panel", "Glulam Beam"] if saved_support == "beam" else ["Floor Panel"]
    tabs = st.tabs(tab_labels)

    # -----------------------------------------------------------------------
    # TAB 1: Floor Panel
    # -----------------------------------------------------------------------
    with tabs[0]:
        import pandas as pd

        st.subheader(f"{panel_type} Panel — Auto-Selection  ({span} m span)")

        # -- Summary table: all thicknesses --
        def _thick_label(r: CheckResult) -> str:
            t = int(r.floor_input.nlt_thickness)
            if r.floor_input.panel_type == "CLT":
                layup = f", {r.floor_input.clt_layup_variant}" if r.floor_input.clt_layup_variant else ""
                return f"{t} mm ({r.floor_input.clt_num_plies}-ply{layup})"
            return f"{t} mm"

        _rows_p = []
        for _r in all_panels:
            _L   = _r.floor_input.span
            _ll  = _L / 360.0 * 1000.0   # mm limit live
            _li  = _L / 240.0 * 1000.0   # mm limit total instantaneous
            _lt  = _L / 180.0 * 1000.0   # mm limit long-term
            _rows_p.append({
                "Thickness":    _thick_label(_r),
                "Mr util":      f"{_r.bending_utilization * 100:.0f}%",
                "Vr util":      f"{_r.shear_utilization * 100:.0f}%",
                "δ_live/L360":  f"{_r.delta_live / _ll * 100:.0f}%",
                "δ_inst/L240":   f"{_r.delta_instantaneous / _li * 100:.0f}%",
                "δ_LT/L180":    f"{_r.delta_longterm / _lt * 100:.0f}%",
                "SW (kN/m²)":   f"{_r.self_weight_kN_per_m2:.3f}",
                "Pass":         "✓" if _r.structural_pass else "✗",
            })
        st.dataframe(pd.DataFrame(_rows_p), use_container_width=True, hide_index=True)

        st.divider()

        # -- Dropdown: passing thicknesses only --
        _passing_panels = [_r for _r in all_panels if _r.structural_pass]
        if not _passing_panels:
            st.error("No thickness passes all structural checks. Check span, loads, or species/grade.")
        else:
            _picked_panel = st.selectbox(
                "Select thickness for vibration check",
                options=range(len(_passing_panels)),
                format_func=lambda i: _thick_label(_passing_panels[i]),
            )
            pr = _passing_panels[_picked_panel]   # reassign pr for detail display + vibration
            fl = pr.floor_input

            st.subheader(f"Detail: {_thick_label(pr)}")

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("wu  (kN/m²)",    f"{pr.wu:.3f}")
            m2.metric("KD",             f"{pr.KD:.3f}")
            m3.metric("Mf  (kN·m/m)",  f"{pr.Mf:.2f}")
            m4.metric("Mr  (kN·m/m)",  f"{pr.Mr:.2f}")
            m5.metric("Vf  (kN/m)",    f"{pr.Vf:.2f}")
            m6.metric("Vr  (kN/m)",    f"{pr.Vr:.2f}")

            st.divider()

            ci1, ci2, ci3 = st.columns(3)
            _src = f" ({pr.floor_input.clt_data_source})" if pr.floor_input.panel_type == "CLT" else ""
            ci1.write(f"**Species / Grade:** {pr.floor_input.nlt_species or '—'} / {pr.floor_input.nlt_grade}{_src}")
            ci2.write(f"**Thickness:** {int(pr.floor_input.nlt_thickness)} mm")
            ci3.write(f"**Self-weight:** {pr.self_weight_kN_per_m2:.3f} kN/m²")

            st.divider()

            st.markdown("#### ULS — Ultimate Limit State")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.markdown("**Check**"); c2.markdown("**Demand**"); c3.markdown("**Capacity**"); c4.markdown("**Utilization**")

            _show_check_row("Bending  Mf / Mr", pr.Mf, pr.Mr, pr.bending_utilization, pr.bending_pass, "kN·m/m")
            _show_check_row("Shear  Vf / Vr",   pr.Vf, pr.Vr, pr.shear_utilization,   pr.shear_pass,   "kN/m")

            st.divider()

            span_mm = fl.span * 1000.0
            st.markdown("#### SLS — Serviceability Limit State (Deflections)")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.markdown("**Check**"); c2.markdown("**Deflection**"); c3.markdown("**Limit**"); c4.markdown("**Status**")

            _show_defl_row(f"Live load  (L/360 = {span_mm/360:.1f} mm)",         pr.delta_live,          span_mm / 360.0, pr.deflection_L360_pass)
            _show_defl_row(f"Total inst. D+L  (L/240 = {span_mm/240:.1f} mm)",   pr.delta_instantaneous, span_mm / 240.0, pr.deflection_L240_pass)
            _show_defl_row(f"Long-term  (L/180 = {span_mm/180:.1f} mm)  [dead x {creep}]", pr.delta_longterm, span_mm / 180.0, pr.deflection_L180_pass)

            st.divider()
            st.write(f"**EI = {pr.EI:.0f} kN·m²/m** — available for vibration check")

    # -----------------------------------------------------------------------
    # TAB 2: Glulam Beam  (index 1, only when beam support)
    # -----------------------------------------------------------------------
    if saved_support == "beam":
        with tabs[1]:
            import pandas as pd
            beam_err = st.session_state.get("beam_error")
            if beam_err:
                st.error(f"Beam selection failed: {beam_err}")
            elif not all_beams:
                st.info("Beam results not available. Click 'Run Check'.")
            else:
                st.subheader(f"Passing Sections — {all_beams[0].beam_input.species}  {all_beams[0].beam_input.grade}")

                # -- Filter sliders --
                st.markdown("**Section filter limits**")
                _fc1, _fc2 = st.columns(2)
                _min_mu = _fc1.slider("Min moment util (%)",        0, 100, 70, 5) / 100.0
                _min_vu = _fc2.slider("Min shear util (%)",         0, 100,  0, 5) / 100.0
                _min_dl = _fc1.slider("Min live defl (% of L/360)", 0, 100, 50, 5) / 100.0
                _min_dt = _fc2.slider("Min total defl (% of L/180)", 0, 100, 50, 5) / 100.0

                def _beam_ok(b: BeamCheckResult) -> bool:
                    _ll = b.beam_input.span * 1000.0 / 360.0
                    _lt = b.beam_input.span * 1000.0 / 180.0
                    return (
                        b.bending_utilization >= _min_mu
                        and b.shear_utilization   >= _min_vu
                        and b.delta_live_mm       >= _min_dl * _ll
                        and b.delta_total_mm       >= _min_dt * _lt
                    )

                _filtered_beams = [b for b in all_beams if _beam_ok(b)]

                # -- Summary table (filtered sections only) --
                _rows_b = []
                for b in _filtered_beams:
                    bi   = b.beam_input
                    _ll  = bi.span * 1000.0 / 360.0
                    _lt  = bi.span * 1000.0 / 180.0
                    _rows_b.append({
                        "Section":       f"{bi.width_mm}×{bi.depth_mm} mm",
                        "Mr util":       f"{b.bending_utilization * 100:.0f}%",
                        "Vr util":       f"{b.shear_utilization * 100:.0f}%",
                        "δ_live/L360":   f"{b.delta_live_mm / _ll * 100:.0f}%",
                        "δ_total/L180":  f"{b.delta_total_mm / _lt * 100:.0f}%",
                        "EsI (kN·m²)":   f"{b.EsI_kNm2:.0f}",
                        "Volume (m³)":   f"{b.beam_volume_m3:.3f}",
                    })
                if _rows_b:
                    st.dataframe(pd.DataFrame(_rows_b), use_container_width=True, hide_index=True)
                else:
                    st.warning("No section meets the filter limits — relax the sliders above.")

                # -- Fire Rating (immediately after filtered table) --
                _fire_opt   = "None"
                _fire_pairs = []
                if _filtered_beams:
                    st.divider()
                    st.subheader("Fire Rating (CSA O86-24 Annex B)")
                    st.caption(
                        "3-sided exposure (top protected). "
                        "β_n = 0.70 mm/min · x_t = 7 mm · K_fi = 1.35 · φ_fire = 1.0 · K_D = 1.15 (short-term). "
                        "Full Annex B capacity check — finds minimum section where Mr_fire ≥ Mf_fire (unfactored D+L)."
                    )
                    _fire_opt = st.radio(
                        "Fire rating",
                        options=["None", "1 hour", "2 hours"],
                        horizontal=True,
                    )
                    if _fire_opt != "None":
                        _fire_hours = 1 if _fire_opt == "1 hour" else 2
                        _fire_pairs = apply_fire_upgrades(_filtered_beams, _fire_hours)

                        _fire_rows = []
                        for _r, _fu in _fire_pairs:
                            _amb = f"{_fu.ambient_b} × {_fu.ambient_d} mm"
                            if not _fu.no_section_found:
                                _fire_sec = f"{_fu.fire_b} × {_fu.fire_d} mm"
                                _status   = "PASS" if _fu.fire_utilization <= 1.0 else "FAIL"
                            else:
                                _fire_sec = "— (no section)"
                                _status   = "✗ No section"
                            _fire_rows.append({
                                "Structural":    _amb,
                                "Fire section":  _fire_sec,
                                "b_eff (mm)":    f"{_fu.b_eff_after_char:.0f}",
                                "d_eff (mm)":    f"{_fu.d_eff_after_char:.0f}",
                                "Δb (mm)":       f"+{_fu.width_added_mm}",
                                "Δd (mm)":       f"+{_fu.depth_added_mm}",
                                "Lams added":    _fu.lams_added,
                                "Mf_fire (kN·m)": f"{_fu.Mf_fire_kNm:.1f}",
                                "Mr_fire (kN·m)": f"{_fu.Mr_fire_kNm:.1f}",
                                "Utilization":   f"{_fu.fire_utilization:.3f}",
                                "Status":        _status,
                            })

                        st.dataframe(pd.DataFrame(_fire_rows), use_container_width=True, hide_index=True)
                        st.caption(f"Layup note: {_fire_pairs[0][1].layup_note}")

                st.divider()

                # -- Section selector for vibration check (width then depth) --
                if _filtered_beams:
                    st.markdown("**Select section for vibration check**")
                    _sel_col1, _sel_col2 = st.columns(2)

                    _use_fire = _fire_opt != "None" and any(fu.fire_d is not None for _, fu in _fire_pairs)

                    if _use_fire:
                        # Build selector from fire sections only (those with a valid fire_d)
                        _valid_pairs = [(r, fu) for r, fu in _fire_pairs if fu.fire_d is not None]
                        _avail_widths = sorted({fu.fire_b for _, fu in _valid_pairs})
                        _picked_width = _sel_col1.selectbox(
                            "Width (mm)",
                            options=_avail_widths,
                            format_func=lambda w: f"{w} mm",
                        )
                        _pairs_at_w = [(r, fu) for r, fu in _valid_pairs if fu.fire_b == _picked_width]
                        _avail_depths = [fu.fire_d for _, fu in _pairs_at_w]
                        _picked_depth = _sel_col2.selectbox(
                            "Depth (mm)",
                            options=_avail_depths,
                            format_func=lambda d: f"{d} mm",
                        )
                        _orig_result = next(r for r, fu in _pairs_at_w if fu.fire_d == _picked_depth)
                        _bi0 = _orig_result.beam_input
                        _rho = _GLULAM_DENSITY.get(_bi0.species, _GLULAM_DENSITY_DEFAULT)
                        _fire_sw = (_picked_width / 1000.0) * (_picked_depth / 1000.0) * _rho * 9.81 / 1000.0
                        _fire_bi = BeamInput(
                            span=_bi0.span,
                            tributary_width=_bi0.tributary_width,
                            width_mm=_picked_width,
                            depth_mm=_picked_depth,
                            species=_bi0.species,
                            grade=_bi0.grade,
                            specified_dead_load=_bi0.specified_dead_load,
                            specified_live_load=_bi0.specified_live_load,
                            bracing_condition=_bi0.bracing_condition,
                            unsupported_length_mm=_bi0.unsupported_length_mm,
                            beam_self_weight_kN_per_m=_fire_sw,
                        )
                        _beam_for_vib = GlulamBeamChecker().run(_fire_bi)
                    else:
                        # Use structural sections
                        _avail_widths = sorted({b.beam_input.width_mm for b in _filtered_beams})
                        _picked_width = _sel_col1.selectbox(
                            "Width (mm)",
                            options=_avail_widths,
                            format_func=lambda w: f"{w} mm",
                        )
                        _beams_at_w = [b for b in _filtered_beams if b.beam_input.width_mm == _picked_width]
                        _avail_depths = [b.beam_input.depth_mm for b in _beams_at_w]
                        _picked_depth = _sel_col2.selectbox(
                            "Depth (mm)",
                            options=_avail_depths,
                            format_func=lambda d: f"{d} mm",
                        )
                        _beam_for_vib = next(b for b in _beams_at_w if b.beam_input.depth_mm == _picked_depth)

                    br: BeamCheckResult = _beam_for_vib
                    st.subheader(f"Detail: {_picked_width} × {_picked_depth} mm")
                    if br.structural_pass:
                        st.success("PASS")
                    else:
                        st.error("FAIL")
                    st.divider()
                    _beam_detail(br)

    # -----------------------------------------------------------------------
    # Vibration section — only available when all structural checks pass
    # -----------------------------------------------------------------------
    if pr is not None and pr.structural_pass and beam_ok:
        st.divider()
        st.subheader("Vibration Check")
        st.caption("All structural checks passed. Select a vibration method to proceed.")

        _M_CSA   = "CSA O86-24  (Span Limit)"
        _M_AISC  = "AISC DG11  (Walking Acceleration)"
        _M_PREC5 = "prEC5  (RMS Velocity / Acceleration)"
        _M_ALL   = "All Methods"

        vib_method = st.radio(
            "Vibration method",
            options=[_M_CSA, _M_AISC, _M_PREC5, _M_ALL],
            horizontal=True,
        )

        # -- Method-specific inputs --
        needs_aisc  = vib_method in (_M_AISC,  _M_ALL)
        needs_prec5 = vib_method in (_M_PREC5, _M_ALL)
        needs_conc  = vib_method in (_M_AISC, _M_PREC5, _M_ALL)

        _beta       = 0.03
        _f_step     = 1.8
        _floor_type = "timber_concrete"
        _occupancy  = "residential"
        _num_bays   = 1

        if vib_method != _M_CSA:
            inp_cols = st.columns(2 if needs_aisc and needs_prec5 else 1)
            col_idx  = 0

            if needs_aisc:
                with inp_cols[col_idx]:
                    st.markdown("**AISC DG11 parameters**")
                    _beta     = st.number_input("Damping ratio β", 0.01, 0.20, 0.03, 0.01)
                    _f_step   = st.number_input("Step frequency (Hz)", 1.0, 3.0, 1.8, 0.1)
                    _num_bays = st.number_input("Number of bays", 1, 20, 1, 1)
                col_idx += 1

            if needs_prec5:
                with inp_cols[col_idx]:
                    st.markdown("**prEC5 parameters**")
                    _floor_type = st.selectbox(
                        "Floor type",
                        options=["timber_concrete", "joisted", "joisted_floating", "timber_concrete_floating"],
                        format_func=lambda x: {
                            "timber_concrete":          "Timber-concrete / rib / slab (CLT, LVL, GL)  — ζ = 0.025",
                            "joisted":                  "Joisted  — ζ = 0.020",
                            "joisted_floating":         "Joisted + floating floor  — ζ = 0.030",
                            "timber_concrete_floating": "Timber-concrete / rib / slab + floating floor  — ζ = 0.040",
                        }[x],
                    )
                    _occupancy = st.selectbox(
                        "Occupancy type",
                        options=["residential", "office"],
                        format_func=lambda x: {
                            "residential": "Residential (Use A)",
                            "office":      "Office / commercial (Use B)",
                        }[x],
                        help="Residential: f1,lim = 6 Hz  |  Office: f1,lim = 8 Hz",
                    )
                    if not needs_aisc:
                        _num_bays = st.number_input("Number of bays", 1, 20, 1, 1)

        run_vib = st.button("Run Vibration Check", type="primary")

        if run_vib:
            _vib_in = VibrationInput(
                beta=_beta,
                f_step=_f_step,
                floor_type=_floor_type,
                occupancy_type=_occupancy,
                conc_thickness_m=_conc_thick,
                num_bays=int(_num_bays),
            )
            try:
                _vr = run_vibration_check(pr, fl, _vib_in, _beam_for_vib)
                st.session_state["vib_result"] = _vr
                st.session_state["vib_method"] = vib_method
                st.session_state["vib_error"]  = None
            except Exception as _ve:
                st.session_state["vib_result"] = None
                st.session_state["vib_error"]  = str(_ve)

        # -- Results --
        vib_err: str | None        = st.session_state.get("vib_error")
        vr: VibrationResult | None = st.session_state.get("vib_result")
        saved_vib_method: str      = st.session_state.get("vib_method", "")

        if vib_err:
            st.error(f"Vibration check error: {vib_err}")

        elif vr is not None:
            st.divider()
            st.caption(
                f"Panel mass (self-weight only): {vr.mass_per_m2_kg:.1f} kg/m²  |  "
                f"EI_long: {vr.EI_long_Nm2_per_m/1000:.0f} kN·m²/m  |  "
                f"EI_trans: {vr.EI_trans_Nm2_per_m/1000:.0f} kN·m²/m"
            )

            show_csa   = saved_vib_method in (_M_CSA,   _M_ALL)
            show_aisc  = saved_vib_method in (_M_AISC,  _M_ALL)
            show_prec5 = saved_vib_method in (_M_PREC5, _M_ALL)

            # -------------------------------------------------------------------
            # CSA O86-24
            # -------------------------------------------------------------------
            if show_csa:
                st.markdown("### CSA O86-24 Cl. 9.4.3.1 — Vibration-Controlled Span")
                c1, c2, c3 = st.columns(3)
                c1.metric("Actual span (m)",  f"{fl.span:.2f}")
                c2.metric("Span limit lv (m)", f"{vr.lv_limit_m:.2f}")
                c3.metric("lv / span",         f"{vr.lv_limit_m / fl.span:.3f}")
                if vr.lv_pass:
                    st.success(f"PASS — lv = {vr.lv_limit_m:.2f} m  >  span = {fl.span:.2f} m")
                else:
                    st.error(f"FAIL — lv = {vr.lv_limit_m:.2f} m  <  span = {fl.span:.2f} m")
                if show_aisc or show_prec5:
                    st.divider()

            # -------------------------------------------------------------------
            # AISC Design Guide 11
            # -------------------------------------------------------------------
            if show_aisc:
                st.markdown("### AISC Design Guide 11 — Walking Vibration")
                _aisc_limit_ms2 = 0.05   # m/s² — acceptance threshold
                if vr.fn_combined_Hz is not None:
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        st.markdown("#### Panel-only mode")
                        st.metric("fn (Hz)",        f"{vr.fn_panel_Hz:.2f}")
                        st.metric("ap (m/s²)",      f"{vr.ap_panel_g * 9.81:.4f}")
                        st.metric("W_eff (kN)",     f"{vr.W_panel_kN:.1f}")
                        st.metric("M_eff (kg)",     f"{vr.W_panel_kN * 1000 / 9.81:.0f}")
                        st.write(f"**Class:** {vr.aisc_panel_method}")
                    with ac2:
                        st.markdown("#### Combined beam-supported system")
                        st.metric("fn (Hz)",        f"{vr.fn_combined_Hz:.2f}")
                        st.metric("ap (m/s²)",      f"{vr.ap_combined_g * 9.81:.4f}")
                        st.metric("W_eff (kN)",     f"{vr.W_combined_kN:.1f}")
                        st.metric("M_eff (kg)",     f"{vr.W_combined_kN * 1000 / 9.81:.0f}")
                        st.write(f"**Class:** {vr.aisc_beam_method}")
                    aisc_ap_ms2 = vr.ap_combined_g * 9.81
                else:
                    ai1, ai2, ai3, ai4 = st.columns(4)
                    ai1.metric("fn (Hz)",    f"{vr.fn_panel_Hz:.2f}")
                    ai2.metric("ap (m/s²)", f"{vr.ap_panel_g * 9.81:.4f}")
                    ai3.metric("W_eff (kN)", f"{vr.W_panel_kN:.1f}")
                    ai4.metric("M_eff (kg)", f"{vr.W_panel_kN * 1000 / 9.81:.0f}")
                    st.write(f"**Class:** {vr.aisc_panel_method}")
                    aisc_ap_ms2 = vr.ap_panel_g * 9.81
                if aisc_ap_ms2 <= _aisc_limit_ms2:
                    st.success(f"PASS — ap = {aisc_ap_ms2:.4f} m/s²  ≤  {_aisc_limit_ms2} m/s²")
                else:
                    st.error(f"FAIL — ap = {aisc_ap_ms2:.4f} m/s²  >  {_aisc_limit_ms2} m/s²")
                if show_prec5:
                    st.divider()

            # -------------------------------------------------------------------
            # prEC5
            # -------------------------------------------------------------------
            if show_prec5:
                st.markdown("### prEC5 Table 9.3 — Performance Level Assessment")

                # Computed values
                has_beam_prec5 = vr.fn_prEC5_beam_Hz is not None
                _fn_show  = vr.fn_prEC5_beam_Hz if has_beam_prec5 else vr.fn_prEC5_Hz
                _v_show   = vr.v_rms_beam_ms    if has_beam_prec5 else vr.v_rms_ms
                _a_show   = vr.a_rms_beam_ms2   if has_beam_prec5 else vr.a_rms_ms2

                _defl_show = (vr.deflection_1kN_beam_mm
                              if (has_beam_prec5 and vr.deflection_1kN_beam_mm is not None)
                              else vr.deflection_1kN_mm)

                cv1, cv2, cv3, cv4, cv5 = st.columns(5)
                cv1.metric("f₁ (Hz)",              f"{_fn_show:.2f}")
                cv2.metric("w₁ₖₙ (mm)",            f"{_defl_show:.3f}")
                cv3.metric("v_rms (mm/s)",          f"{_v_show * 1000:.4f}")
                cv4.metric("M* (kg)",               f"{vr.modal_mass_prEC5_kg:.0f}")
                if _a_show is not None:
                    cv5.metric("a_rms (m/s²)",      f"{_a_show:.4f}")
                else:
                    cv5.metric("a_rms",             "Transient — N/A")

                st.write(
                    f"**Response:** {vr.prEC5_response}  |  "
                    f"**f₁,lim = {vr.prEC5_f1_lim_Hz:.1f} Hz**  |  "
                    f"**B_eff = {vr.bef_m:.2f} m**"
                )
                if has_beam_prec5:
                    st.caption(
                        f"Panel-only: fn = {vr.fn_prEC5_Hz:.2f} Hz, "
                        f"w₁ₖₙ = {vr.deflection_1kN_mm:.3f} mm, "
                        f"v_rms = {vr.v_rms_ms*1000:.4f} mm/s  |  "
                        f"Combined beam: fn = {vr.fn_prEC5_beam_Hz:.2f} Hz, "
                        f"w₁ₖₙ = {vr.deflection_1kN_beam_mm:.3f} mm"
                    )

                # Achieved level banner
                _achieved = vr.prEC5_achieved_level_beam if has_beam_prec5 else vr.prEC5_achieved_level
                if _achieved:
                    st.success(f"Achieves Performance Level **{_achieved}**")
                else:
                    st.error("Does not meet any performance level (Level VIII)")

                # Per-level results table
                import pandas as pd
                _TICK, _CROSS, _NA = "✓", "✗", "—"

                def _cell(val) -> str:
                    if val is None:  return _NA
                    return _TICK if val else _CROSS

                rows = []
                for lr in vr.prEC5_level_results:
                    freq_pass  = lr["freq_pass_beam"]      if has_beam_prec5 else lr["freq_pass"]
                    stiff_pass = lr["stiffness_pass_beam"] if has_beam_prec5 else lr["stiffness_pass"]
                    vel_pass   = lr["velocity_pass_beam"]  if has_beam_prec5 else lr["velocity_pass"]
                    acc_pass   = lr["accel_pass_beam"]     if has_beam_prec5 else lr["accel_pass"]
                    overall    = lr["overall_pass_beam"]   if has_beam_prec5 else lr["overall_pass"]
                    rows.append({
                        "Level":           lr["level"],
                        "Freq ≥ (Hz)":     f"{lr['freq_criterion_Hz']:.1f}",
                        "Freq":            _cell(freq_pass),
                        "w_lim (mm)":      f"{lr['w_lim_mm']:.2f}",
                        "Stiffness":       _cell(stiff_pass),
                        "v_rms,lim (mm/s)":f"{lr['v_rms_lim_ms']*1000:.1f}",
                        "Velocity":        _cell(vel_pass),
                        "a_rms,lim (m/s²)":f"{lr['a_rms_lim_ms2']:.2f}" if lr["a_rms_lim_ms2"] else "—",
                        "Accel":           _cell(acc_pass),
                        "Overall":         _cell(overall),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

else:
    st.info("Configure inputs in the sidebar and click **Run Structural Check** to see results.")
