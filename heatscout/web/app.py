"""HeatScout — Streamlit web interface for industrial waste heat recovery analysis."""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as sac
from streamlit_lottie import st_lottie

from heatscout.core.examples import list_examples, load_example
from heatscout.core.heat_balance import FactoryHeatBalance
from heatscout.core.stream import StreamType, ThermalStream
from heatscout.plotting.sankey import create_sankey
from heatscout.web.chart_theme import PLOTLY_DARK_LAYOUT
from heatscout.web.components import (
    footer,
    hero_section,
    impact_banner,
    section_header,
    temp_card,
)
from heatscout.web.styles import CSS

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HeatScout — Industrial Heat Recovery",
    page_icon="\U0001f525",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject CSS ───────────────────────────────────────────────────────────────

st.markdown(CSS, unsafe_allow_html=True)

# ── Load fluid database ─────────────────────────────────────────────────────

FLUIDS_PATH = Path(__file__).parent.parent / "data" / "fluids.json"
with open(FLUIDS_PATH, encoding="utf-8") as f:
    FLUIDS_DB = json.load(f)["fluids"]

FLUID_OPTIONS = {fl["id"]: fl["name"] for fl in FLUIDS_DB}
FLUID_IDS = list(FLUID_OPTIONS.keys())
FLUID_NAMES = list(FLUID_OPTIONS.values())

# ── Lottie animation data (inline, lightweight) ─────────────────────────────

_LOTTIE_LOADING = {
    "v": "5.5.7",
    "fr": 30,
    "ip": 0,
    "op": 60,
    "w": 100,
    "h": 100,
    "layers": [
        {
            "ty": 4,
            "nm": "circle",
            "sr": 1,
            "ks": {
                "o": {"a": 0, "k": 100},
                "r": {"a": 1, "k": [{"t": 0, "s": [0]}, {"t": 60, "s": [360]}]},
                "p": {"a": 0, "k": [50, 50]},
                "s": {"a": 0, "k": [100, 100]},
            },
            "shapes": [
                {
                    "ty": "el",
                    "p": {"a": 0, "k": [0, 0]},
                    "s": {"a": 0, "k": [40, 40]},
                },
                {
                    "ty": "st",
                    "c": {"a": 0, "k": [0, 0.83, 0.67, 1]},
                    "o": {"a": 0, "k": 100},
                    "w": {"a": 0, "k": 4},
                    "d": [
                        {"n": "d", "nm": "dash", "v": {"a": 0, "k": 20}},
                        {"n": "g", "nm": "gap", "v": {"a": 0, "k": 80}},
                    ],
                },
            ],
            "ip": 0,
            "op": 60,
        }
    ],
}

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### General Settings")
    factory_name = st.text_input("Plant name", value="My plant")

    col_t, col_p = st.columns(2)
    with col_t:
        T_ambient = st.number_input(
            "Ambient T (\u00b0C)", value=25.0, min_value=-20.0, max_value=50.0, step=1.0
        )
    with col_p:
        energy_price = st.number_input(
            "\u20ac/kWh",
            value=0.08,
            min_value=0.01,
            max_value=1.0,
            step=0.01,
            format="%.3f",
            help="Your industrial energy cost per kWh. Check your latest utility bill.",
        )

    col_dr, col_hz = st.columns(2)
    with col_dr:
        _dr_default = st.session_state.pop("loaded_discount_rate", 0.05) * 100
        discount_rate = (
            st.number_input(
                "Discount rate (%)",
                value=_dr_default,
                min_value=0.0,
                max_value=25.0,
                step=0.5,
                format="%.1f",
                help="WACC or cost of capital. Typical: 3\u20135% (EU), 5\u20138% (US/emerging).",
            )
            / 100.0
        )
    with col_hz:
        _hz_default = st.session_state.pop("loaded_horizon_years", 10)
        horizon_years = st.number_input(
            "Horizon (yr)",
            value=_hz_default,
            min_value=3,
            max_value=30,
            step=1,
            help="Economic analysis period. Match to equipment lifetime.",
        )

    with st.expander("Advanced Settings"):
        st.caption("Adjust cost model parameters. Defaults are industry averages.")
        _opex_default = st.session_state.pop("loaded_opex_multiplier", 1.0)
        opex_multiplier = st.slider(
            "OPEX multiplier",
            0.5,
            2.0,
            _opex_default,
            0.1,
            help="Scale annual maintenance costs. 1.0 = default.",
        )
        _inst_default = st.session_state.pop("loaded_install_multiplier", 1.0)
        install_multiplier = st.slider(
            "Installation multiplier",
            0.5,
            2.0,
            _inst_default,
            0.1,
            help="Scale installation/piping/engineering overhead.",
        )

    # ── Incentives ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Incentives")

    capex_inc_enabled = st.checkbox(
        "CAPEX reduction (tax credit / grant)",
        value=False,
        help="Any incentive that reduces investment: IRA \u00a748C, IETF, EU Innovation Fund, etc.",
    )
    capex_riduzione_pct = 0.0
    capex_inc_nome = "Tax credit / Grant"
    if capex_inc_enabled:
        col_ci1, col_ci2 = st.columns(2)
        with col_ci1:
            capex_riduzione_pct = st.number_input(
                "CAPEX reduction %",
                value=30.0,
                min_value=1.0,
                max_value=100.0,
                step=5.0,
            )
        with col_ci2:
            capex_inc_nome = st.text_input("Incentive name", value="Tax credit / Grant")

    tee_enabled = st.checkbox(
        "White Certificates / TEE (Italy)",
        value=False,
        help="Italian White Certificates \u2014 DM MASE 21/07/2025",
    )
    if tee_enabled:
        col_tee1, col_tee2 = st.columns(2)
        with col_tee1:
            tee_prezzo = st.number_input(
                "TEE price (\u20ac/TEE)",
                value=250.0,
                min_value=50.0,
                max_value=500.0,
                step=10.0,
            )
        with col_tee2:
            tee_eta_rif = st.number_input(
                "Ref. boiler eff.",
                value=0.90,
                min_value=0.50,
                max_value=1.00,
                step=0.05,
                format="%.2f",
            )
        st.caption("Source: DM MASE 21/07/2025 \u2014 TEE value subject to market variations")

    # ── Energy input ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Energy Input")
    energy_input_mode = st.radio(
        "Energy input estimation",
        ["Automatic (85% eff.)", "Manual"],
        key="energy_input_mode",
        horizontal=True,
    )
    manual_consumption = None
    manual_unit = None
    if energy_input_mode == "Manual":
        manual_consumption = st.number_input(
            "Annual consumption", value=100000.0, min_value=0.0, step=1000.0
        )
        manual_unit = st.selectbox("Unit", ["Sm3/yr", "MWh/yr", "kWh/yr", "tep/yr"])

    # ── Load example ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Example Cases")
    examples = list_examples()
    example_options = ["-- Select --"] + [
        f"{e['name']} ({e['n_streams']} streams)" for e in examples
    ]
    example_choice = st.selectbox("Load an example", example_options, label_visibility="collapsed")

    def _load_selected_example():
        """Load selected example into session state."""
        if example_choice != "-- Select --":
            idx = example_options.index(example_choice) - 1
            example_id = examples[idx]["id"]
            streams, meta = load_example(example_id)
            st.session_state.n_streams = len(streams)
            st.session_state.loaded_example = {"streams": streams, "meta": meta}
        else:
            st.session_state.pop("loaded_example", None)

    st.button("Load example", on_click=_load_selected_example, use_container_width=True)

    # ── Save/Load analysis ───────────────────────────────────────────────
    st.divider()
    st.markdown("### Save / Load Analysis")
    uploaded_json = st.file_uploader(
        "Load analysis (.json)",
        type=["json"],
        help="Upload a previously saved HeatScout analysis file",
        label_visibility="collapsed",
    )
    if uploaded_json is not None:
        try:
            from heatscout.report.persistence import load_analysis

            content = uploaded_json.read().decode("utf-8")
            loaded_data = load_analysis(content)

            restored_streams = []
            for sd in loaded_data["streams"]:
                st_type = sd["stream_type"]
                if isinstance(st_type, str):
                    st_type = (
                        StreamType.HOT_WASTE if "hot" in st_type.lower() else StreamType.COLD_DEMAND
                    )
                restored_streams.append(
                    ThermalStream(
                        name=sd["name"],
                        fluid_type=sd["fluid_type"],
                        T_in=sd["T_in"],
                        T_out=sd["T_out"],
                        mass_flow=sd["mass_flow"],
                        hours_per_day=sd["hours_per_day"],
                        days_per_year=sd["days_per_year"],
                        stream_type=st_type,
                    )
                )

            st.session_state.n_streams = len(restored_streams)
            st.session_state.loaded_example = {
                "streams": restored_streams,
                "meta": {"name": loaded_data["factory_name"]},
            }
            for key in ("discount_rate", "horizon_years", "opex_multiplier", "install_multiplier"):
                if key in loaded_data:
                    st.session_state[f"loaded_{key}"] = loaded_data[key]
            st.success(f"Loaded: {loaded_data['factory_name']} ({len(restored_streams)} streams)")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    # ── Import streams ───────────────────────────────────────────────────
    st.divider()
    st.markdown("### Import Streams")
    col_tpl, col_imp = st.columns(2)
    with col_tpl:
        from heatscout.report.stream_import import generate_template

        st.download_button(
            "CSV Template",
            data=generate_template(),
            file_name="heatscout_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_imp:
        uploaded_streams = st.file_uploader(
            "Upload CSV/Excel",
            type=["csv", "xlsx", "xls"],
            help="Upload a CSV or Excel file with stream data",
            label_visibility="collapsed",
        )
    if uploaded_streams is not None:
        try:
            from heatscout.report.stream_import import import_streams

            stream_dicts = import_streams(uploaded_streams.getvalue(), uploaded_streams.name)
            restored = []
            for sd in stream_dicts:
                st_type_str = sd["stream_type"]
                st_type = StreamType.HOT_WASTE if "hot" in st_type_str else StreamType.COLD_DEMAND
                restored.append(
                    ThermalStream(
                        name=sd["name"],
                        fluid_type=sd["fluid_type"],
                        T_in=sd["T_in"],
                        T_out=sd["T_out"],
                        mass_flow=sd["mass_flow"],
                        hours_per_day=sd["hours_per_day"],
                        days_per_year=sd["days_per_year"],
                        stream_type=st_type,
                    )
                )
            st.session_state.n_streams = len(restored)
            st.session_state.loaded_example = {"streams": restored, "meta": {}}
            st.success(f"Imported {len(restored)} streams from {uploaded_streams.name}")
        except Exception as e:
            st.error(f"Import error: {e}")

    st.divider()
    st.caption(
        "HeatScout v1.0  \nOpen source \u00b7 [GitHub](https://github.com/cesabici-bit/heatscout)"
    )

# ── Hero section ─────────────────────────────────────────────────────────────

st.markdown(hero_section(), unsafe_allow_html=True)

# ── Quick start (only before first analysis) ─────────────────────────────────

if "last_summary" not in st.session_state:
    with st.container():
        st.markdown("#### How to get started")
        qs1, qs2, qs3 = st.columns(3)
        with qs1:
            st.markdown(
                "**1. Enter streams**  \n"
                "Add your plant's thermal streams: temperatures, flow rate, fluid."
            )
        with qs2:
            st.markdown(
                "**2. Click Analyze**  \n"
                "HeatScout computes power, energy, exergy and selects the best technologies."
            )
        with qs3:
            st.markdown(
                "**3. Download the report**  \n"
                "Get a professional PDF with executive summary, charts and recommendations."
            )
        st.info("Load an example from the sidebar to try it out right away!")

# ── Stream count management ──────────────────────────────────────────────────

if "n_streams" not in st.session_state:
    st.session_state.n_streams = 1


def add_stream():
    st.session_state.n_streams = min(st.session_state.n_streams + 1, 10)


def remove_stream():
    st.session_state.n_streams = max(st.session_state.n_streams - 1, 1)


# ── Stream input ─────────────────────────────────────────────────────────────

st.markdown(section_header("\U0001f4ca", "Thermal Streams"), unsafe_allow_html=True)

col_info, col_add, col_rem = st.columns([4, 1, 1])
with col_info:
    n = st.session_state.n_streams
    st.markdown(f"**{n}** stream(s) configured{'  — max 10' if n < 10 else '  — limit reached'}")
with col_add:
    st.button("+ Add", on_click=add_stream, use_container_width=True, disabled=(n >= 10))
with col_rem:
    st.button("\u2212 Remove", on_click=remove_stream, use_container_width=True, disabled=(n <= 1))

loaded = st.session_state.get("loaded_example")

streams_input = []
for i in range(st.session_state.n_streams):
    ex = None
    if loaded and i < len(loaded["streams"]):
        ex = loaded["streams"][i]

    type_indicator = (
        "\U0001f534" if (ex is None or ex.stream_type == StreamType.HOT_WASTE) else "\U0001f535"
    )
    label = f"{type_indicator} Stream {i + 1}" + (f" \u2014 {ex.name}" if ex else "")

    with st.expander(label, expanded=(i == 0)):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input(
                "Name",
                value=ex.name if ex else f"Stream {i + 1}",
                key=f"name_{i}",
            )
            default_fluid_idx = (
                FLUID_IDS.index(ex.fluid_type) if ex and ex.fluid_type in FLUID_IDS else 0
            )
            fluid_idx = st.selectbox(
                "Fluid",
                range(len(FLUID_IDS)),
                format_func=lambda x: FLUID_NAMES[x],
                index=default_fluid_idx,
                key=f"fluid_{i}",
            )
            default_type_idx = 0 if (ex is None or ex.stream_type == StreamType.HOT_WASTE) else 1
            stream_type = st.selectbox(
                "Type",
                [StreamType.HOT_WASTE, StreamType.COLD_DEMAND],
                format_func=lambda x: (
                    "\U0001f534 Waste heat"
                    if x == StreamType.HOT_WASTE
                    else "\U0001f535 Heat demand"
                ),
                index=default_type_idx,
                key=f"type_{i}",
                help="HOT_WASTE: heat to recover (T_in > T_out). "
                "COLD_DEMAND: process needing heat (T_in < T_out).",
            )
        with col2:
            T_in = st.number_input(
                "Inlet T (\u00b0C)",
                value=ex.T_in if ex else 200.0,
                min_value=-200.0,
                max_value=1500.0,
                step=10.0,
                key=f"Tin_{i}",
            )
            T_out = st.number_input(
                "Outlet T (\u00b0C)",
                value=ex.T_out if ex else 80.0,
                min_value=-200.0,
                max_value=1500.0,
                step=10.0,
                key=f"Tout_{i}",
            )
        with col3:
            mass_flow = st.number_input(
                "Flow rate (kg/s)",
                value=ex.mass_flow if ex else 1.0,
                min_value=0.01,
                max_value=1000.0,
                step=0.1,
                key=f"mflow_{i}",
            )
            hours = st.number_input(
                "Hours/day",
                value=ex.hours_per_day if ex else 16.0,
                min_value=0.5,
                max_value=24.0,
                step=0.5,
                key=f"hours_{i}",
            )
            days = st.number_input(
                "Days/year",
                value=ex.days_per_year if ex else 250.0,
                min_value=1.0,
                max_value=366.0,
                step=1.0,
                key=f"days_{i}",
            )

        streams_input.append(
            {
                "name": name,
                "fluid_type": FLUID_IDS[fluid_idx],
                "T_in": T_in,
                "T_out": T_out,
                "mass_flow": mass_flow,
                "hours_per_day": hours,
                "days_per_year": days,
                "stream_type": stream_type,
            }
        )

# ── Analyze button ───────────────────────────────────────────────────────────

st.markdown("")
if st.button("Run Analysis", type="primary", use_container_width=True):
    hb = FactoryHeatBalance(factory_name=factory_name, T_ambient=T_ambient)
    errors = []

    for i, data in enumerate(streams_input):
        try:
            stream = ThermalStream(**data)
            hb.add_stream(stream)
        except ValueError as e:
            errors.append(f"Stream {i + 1} ({data['name']}): {e}")
        except Exception as e:
            error_msg = str(e)
            if (
                "fluid" in error_msg.lower()
                or "coolprop" in error_msg.lower()
                or "property" in error_msg.lower()
            ):
                errors.append(f"Stream {i + 1} ({data['name']}): Fluid property error: {error_msg}")
            else:
                errors.append(f"Stream {i + 1} ({data['name']}): {error_msg}")

    if errors:
        for err in errors:
            st.error(err)
    elif not hb.streams:
        st.error("Add at least one stream before running analysis.")
    elif all(s.stream_type == StreamType.COLD_DEMAND for s in hb.streams):
        st.error(
            "At least one **Waste heat** (HOT_WASTE) stream is required for heat recovery analysis."
        )
    else:
        try:
            # Show Lottie loading animation
            lottie_placeholder = st.empty()
            with lottie_placeholder:
                st_lottie(_LOTTIE_LOADING, height=80, key="loading_anim")

            with st.spinner("Analyzing... computing thermal properties and selecting technologies"):
                if energy_input_mode == "Manual" and manual_consumption:
                    hb.set_energy_input("gas_naturale", manual_consumption, manual_unit)
                else:
                    hb.estimate_energy_input(efficiency=0.85)

                summary = hb.summary()
                st.session_state.last_summary = summary
                st.session_state.last_hb = hb

                from heatscout.core.economics import (
                    economic_analysis,
                    economic_analysis_with_incentives,
                )
                from heatscout.core.technology_selector import select_technologies
                from heatscout.plotting.comparison_chart import (
                    capex_comparison_chart,
                    cumulative_cashflow_chart,
                    do_nothing_comparison,
                    npv_comparison_chart,
                    payback_comparison_chart,
                )

                all_econ_results = []
                stream_recs = {}
                for stream in hb.streams:
                    if stream.stream_type != StreamType.HOT_WASTE:
                        continue
                    recs = select_technologies(stream, energy_price_EUR_kWh=energy_price)
                    if recs:
                        stream_recs[stream.name] = []
                        for rec in recs:
                            econ = economic_analysis(
                                rec,
                                energy_price_EUR_kWh=energy_price,
                                discount_rate=discount_rate,
                                years=horizon_years,
                                opex_multiplier=opex_multiplier,
                                install_multiplier=install_multiplier,
                            )
                            all_econ_results.append(econ)
                            stream_recs[stream.name].append((rec, econ))

                all_summaries = []
                has_incentives = capex_inc_enabled or tee_enabled
                if has_incentives and all_econ_results:
                    for econ in all_econ_results:
                        summ = economic_analysis_with_incentives(
                            econ,
                            capex_riduzione_pct=capex_riduzione_pct if capex_inc_enabled else 0.0,
                            nome_incentivo=capex_inc_nome,
                            tee_enabled=tee_enabled,
                            prezzo_tee=tee_prezzo if tee_enabled else 250.0,
                            eta_riferimento=tee_eta_rif if tee_enabled else 0.90,
                            discount_rate=discount_rate,
                        )
                        all_summaries.append(summ)

            # Clear loading animation
            lottie_placeholder.empty()

            # Save all results to session_state for tab persistence
            st.session_state.last_econ_results = all_econ_results
            st.session_state.last_stream_recs = stream_recs
            st.session_state.last_summaries = all_summaries
            st.session_state.last_has_incentives = has_incentives
            st.session_state.last_energy_price = energy_price
            st.session_state.last_factory_name = factory_name
            st.session_state.analysis_complete = True

            # Force rerun so tabs render from session_state (persistent across interactions)
            st.rerun()

            # NOTE: Code below is unreachable after st.rerun() but kept for reference
            st.success(
                f"Analysis complete for **{summary['n_streams']}** streams \u2014 "
                f"found **{len(all_econ_results)}** recovery solutions"
            )

            # ══════════════════════════════════════════════════════════
            # RESULTS IN TABS (using streamlit-antd-components)
            # ══════════════════════════════════════════════════════════

            # Check if pinch analysis is possible (both hot and cold streams)
            has_hot = any(s.stream_type == StreamType.HOT_WASTE for s in hb.streams)
            has_cold = any(s.stream_type == StreamType.COLD_DEMAND for s in hb.streams)
            pinch_available = has_hot and has_cold

            tab_items = [
                sac.TabsItem(label="Overview", icon="bar-chart-line"),
                sac.TabsItem(label="Technologies", icon="gear"),
                sac.TabsItem(label="Economics", icon="cash-coin"),
            ]
            if pinch_available:
                tab_items.append(sac.TabsItem(label="Pinch Analysis", icon="fire"))
            tab_items.append(sac.TabsItem(label="Report", icon="file-earmark-pdf"))

            selected_tab = sac.tabs(
                tab_items,
                align="center",
                variant="outline",
                use_container_width=True,
            )

            # Temperature class labels
            T_CLASS_MAP = {"alta": "High", "media": "Medium", "bassa": "Low"}

            # ── TAB: OVERVIEW ────────────────────────────────────────
            if selected_tab == "Overview":
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Waste power", f"{summary['total_waste_kW']:,.1f} kW")
                m2.metric("Annual energy", f"{summary['total_waste_MWh_anno']:,.1f} MWh/yr")
                m3.metric("Waste exergy", f"{summary['total_waste_exergy_kW']:,.1f} kW")
                annual_cost = summary["total_waste_MWh_anno"] * 1000 * energy_price
                m4.metric("Annual waste cost", f"\u20ac {annual_cost:,.0f}")

                waste_pct = summary.get("waste_pct_of_input")
                waste_pct_str = f" ({waste_pct:.0f}% of energy input)" if waste_pct else ""
                st.markdown(
                    impact_banner(
                        f"You are wasting <strong>{summary['total_waste_kW']:,.1f} kW</strong> "
                        f"of heat{waste_pct_str}, equivalent to "
                        f"<strong>{summary['total_waste_MWh_anno']:,.1f} MWh/year</strong>, "
                        f"costing approximately <strong>\u20ac {annual_cost:,.0f}/year</strong>."
                    ),
                    unsafe_allow_html=True,
                )

                st.markdown("#### Energy Balance")
                fig_sankey = create_sankey(hb, factory_name)
                st.plotly_chart(fig_sankey, use_container_width=True, theme=None)

                st.markdown("#### Temperature Class Breakdown")
                by_class = summary["by_temperature_class"]
                tc1, tc2, tc3 = st.columns(3)

                for col, (cls, label_en, css_class) in zip(
                    [tc1, tc2, tc3],
                    [
                        ("alta", "High (>250\u00b0C)", "temp-alta"),
                        ("media", "Medium (80\u2013250\u00b0C)", "temp-media"),
                        ("bassa", "Low (<80\u00b0C)", "temp-bassa"),
                    ],
                ):
                    cls_data = by_class[cls]
                    with col:
                        st.markdown(
                            temp_card(
                                label_en,
                                f"{cls_data['Q_kW']:,.1f} kW",
                                f"{cls_data['count']} stream(s) \u00b7 {cls_data['pct_of_waste']:.1f}% of total",
                                css_class,
                            ),
                            unsafe_allow_html=True,
                        )

                st.markdown("")
                with st.expander("Stream details", expanded=False):
                    rows = []
                    for r in summary["stream_results"]:
                        rows.append(
                            {
                                "Name": r["name"],
                                "Type": "\U0001f534 Waste"
                                if r["stream_type"] == "hot_waste"
                                else "\U0001f535 Demand",
                                "Fluid": r["fluid_type"],
                                "T in (\u00b0C)": r["T_in"],
                                "T out (\u00b0C)": r["T_out"],
                                "Q (kW)": f"{r['Q_kW']:,.1f}",
                                "E (MWh/yr)": f"{r['E_MWh_anno']:,.1f}",
                                "Exergy (kW)": f"{r['Ex_kW']:,.1f}",
                                "Class": T_CLASS_MAP.get(r["T_class"], r["T_class"]),
                                "Quality": f"{r['quality_ratio']:.1%}",
                            }
                        )
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # ── TAB: TECHNOLOGIES ────────────────────────────────────
            elif selected_tab == "Technologies":
                if not stream_recs:
                    st.info("No recovery technologies found for the given streams.")
                else:
                    for sname, recs_econs in stream_recs.items():
                        with st.expander(
                            f"\U0001f525 {sname} \u2014 {len(recs_econs)} technologies",
                            expanded=True,
                        ):
                            best_rec = min(recs_econs, key=lambda x: x[1].payback_years)
                            best_econ = best_rec[1]
                            st.markdown(
                                f"\u2b50 **Best pick:** {best_rec[0].technology.name} \u2014 "
                                f"payback **{best_econ.payback_years:.1f} yr**, "
                                f"savings **\u20ac {best_econ.annual_savings_EUR:,.0f}/yr**"
                            )

                            tech_rows = []
                            for rec, econ in recs_econs:
                                eff_str = (
                                    f"COP {rec.efficiency:.1f}"
                                    if rec.is_heat_pump
                                    else f"{rec.efficiency:.0%}"
                                )
                                tech_rows.append(
                                    {
                                        "Technology": rec.technology.name,
                                        "Q rec. (kW)": f"{rec.Q_recovered_kW:,.1f}",
                                        "E rec. (MWh/yr)": f"{rec.E_recovered_MWh:,.1f}",
                                        "Efficiency": eff_str,
                                        "CAPEX (\u20ac)": f"{econ.capex_EUR:,.0f}",
                                        "Savings/yr (\u20ac)": f"{econ.annual_savings_EUR:,.0f}",
                                        "Payback": f"{econ.payback_years:.1f} yr"
                                        if econ.payback_years < 50
                                        else ">50 yr",
                                        f"NPV {horizon_years}yr (\u20ac)": f"{econ.npv_EUR:,.0f}",
                                    }
                                )

                            st.dataframe(
                                pd.DataFrame(tech_rows),
                                use_container_width=True,
                                hide_index=True,
                            )

                    no_tech = [
                        s.name
                        for s in hb.streams
                        if s.stream_type == StreamType.HOT_WASTE and s.name not in stream_recs
                    ]
                    for sname in no_tech:
                        st.info(f"**{sname}**: no compatible technology found")

            # ── TAB: ECONOMICS ───────────────────────────────────────
            elif selected_tab == "Economics":
                if all_econ_results:
                    st.warning(
                        "**Screening-level analysis** \u2014 CAPEX \u00b130%, savings \u00b115%. "
                        "Not a substitute for detailed engineering study."
                    )
                    best = min(all_econ_results, key=lambda e: e.payback_years)
                    total_capex = sum(e.total_investment_EUR for e in all_econ_results)
                    total_savings = sum(e.annual_savings_EUR for e in all_econ_results)
                    total_npv = sum(e.npv_EUR for e in all_econ_results)

                    e1, e2, e3, e4 = st.columns(4)
                    e1.metric("Total investment", f"\u20ac {total_capex:,.0f}")
                    e2.metric("Annual savings", f"\u20ac {total_savings:,.0f}")
                    e3.metric("Best payback", f"{best.payback_years:.1f} yr")
                    e4.metric(
                        f"Total NPV {horizon_years}yr",
                        f"\u20ac {total_npv:,.0f}",
                        delta="positive" if total_npv > 0 else "negative",
                    )

                    gc1, gc2 = st.columns(2)
                    with gc1:
                        st.plotly_chart(
                            payback_comparison_chart(all_econ_results),
                            use_container_width=True,
                            theme=None,
                        )
                    with gc2:
                        st.plotly_chart(
                            npv_comparison_chart(all_econ_results),
                            use_container_width=True,
                            theme=None,
                        )

                    gc3, gc4 = st.columns(2)
                    with gc3:
                        st.plotly_chart(
                            capex_comparison_chart(all_econ_results),
                            use_container_width=True,
                            theme=None,
                        )
                    with gc4:
                        st.plotly_chart(
                            do_nothing_comparison(all_econ_results),
                            use_container_width=True,
                            theme=None,
                        )

                    st.markdown("#### Cumulative Cashflow \u2014 Best Project")
                    st.caption(f"{best.tech_recommendation.technology.name}")
                    st.plotly_chart(
                        cumulative_cashflow_chart(best), use_container_width=True, theme=None
                    )

                    st.markdown(
                        f"> **Summary:** Investing **\u20ac {total_capex:,.0f}** yields savings of "
                        f"**\u20ac {total_savings:,.0f}/yr** with payback in "
                        f"**{best.payback_years:.1f} years** "
                        f"and a {horizon_years}-year NPV of **\u20ac {total_npv:,.0f}**."
                    )

                    with st.expander("How to interpret these results"):
                        st.markdown(
                            "- **Payback**: years to recover investment from energy savings. "
                            "<3 yr excellent, 3\u20135 yr good, >7 yr needs careful evaluation.\n"
                            "- **NPV**: total project value over analysis horizon, discounted. "
                            "Positive = profitable.\n"
                            "- **IRR**: discount rate that makes NPV = 0. Compare with WACC.\n"
                            "- **CAPEX range**: \u00b130% is normal for screening. "
                            "Actual cost depends on site-specific engineering.\n"
                            "- **Savings**: estimated \u00b115%. Actual depends on real conditions."
                        )

                    # ── INCENTIVES ────────────────────────────────────
                    if has_incentives and all_summaries:
                        st.divider()
                        st.markdown("#### Incentive Comparison")

                        inc_rows = []
                        for s in all_summaries:
                            tech_name = s.base.tech_recommendation.technology.name
                            stream_name = s.base.tech_recommendation.stream_name
                            row = {
                                "Stream": stream_name,
                                "Technology": tech_name,
                                "Base payback": f"{s.base.payback_years:.1f} yr",
                                "Base NPV": f"\u20ac {s.base.npv_EUR:,.0f}",
                            }
                            if capex_inc_enabled and s.capex_incentive:
                                row[f"Net CAPEX ({capex_inc_nome})"] = (
                                    f"\u20ac {s.capex_incentive.capex_netto:,.0f}"
                                )
                                row[f"Payback w/ {capex_inc_nome}"] = (
                                    f"{s.payback_con_capex_inc:.1f} yr"
                                )
                                row[f"NPV w/ {capex_inc_nome}"] = (
                                    f"\u20ac {s.npv_con_capex_inc:,.0f}"
                                )
                            if tee_enabled and s.tee:
                                row["TEP/yr"] = f"{s.tee.tep_risparmiati_anno:,.1f}"
                                row["TEE eligible"] = (
                                    "Yes" if s.tee.sopra_soglia else "No (<10 TEP)"
                                )
                                row["Payback w/ TEE"] = f"{s.payback_con_tee:.1f} yr"
                                row["NPV w/ TEE"] = f"\u20ac {s.npv_con_tee:,.0f}"
                            if capex_inc_enabled and tee_enabled and s.npv_combinato is not None:
                                row["Payback combined"] = f"{s.payback_combinato:.1f} yr"
                                row["NPV combined"] = f"\u20ac {s.npv_combinato:,.0f}"
                            inc_rows.append(row)

                        st.dataframe(
                            pd.DataFrame(inc_rows),
                            use_container_width=True,
                            hide_index=True,
                        )

                        if capex_inc_enabled and tee_enabled:
                            best_s = min(
                                all_summaries,
                                key=lambda s: (
                                    s.payback_combinato
                                    if s.payback_combinato is not None
                                    else float("inf")
                                ),
                            )
                            total_npv_inc = sum(
                                s.npv_combinato
                                for s in all_summaries
                                if s.npv_combinato is not None
                            )
                            best_pb = best_s.payback_combinato
                            inc_label = f"{capex_inc_nome} + TEE"
                        elif capex_inc_enabled:
                            best_s = min(
                                all_summaries,
                                key=lambda s: (
                                    s.payback_con_capex_inc
                                    if s.payback_con_capex_inc is not None
                                    else float("inf")
                                ),
                            )
                            total_npv_inc = sum(
                                s.npv_con_capex_inc
                                for s in all_summaries
                                if s.npv_con_capex_inc is not None
                            )
                            best_pb = best_s.payback_con_capex_inc
                            inc_label = capex_inc_nome
                        else:
                            best_s = min(
                                all_summaries,
                                key=lambda s: (
                                    s.payback_con_tee
                                    if s.payback_con_tee is not None
                                    else float("inf")
                                ),
                            )
                            total_npv_inc = sum(
                                s.npv_con_tee for s in all_summaries if s.npv_con_tee is not None
                            )
                            best_pb = best_s.payback_con_tee
                            inc_label = "TEE"

                        ct1, ct2 = st.columns(2)
                        ct1.metric(
                            f"Best payback w/ {inc_label}",
                            f"{best_pb:.1f} yr",
                            delta=f"{best_pb - best.payback_years:+.1f} yr",
                        )
                        ct2.metric(
                            f"Total NPV w/ {inc_label}",
                            f"\u20ac {total_npv_inc:,.0f}",
                            delta=f"\u20ac {total_npv_inc - total_npv:+,.0f}",
                        )

                        if tee_enabled:
                            from heatscout.knowledge.incentives import (
                                TEE_DATA_AGGIORNAMENTO,
                                TEE_SOGLIA_MINIMA_TEP,
                            )

                            st.caption(
                                f"TEE: DM MASE 21/07/2025 \u2014 Min. {TEE_SOGLIA_MINIMA_TEP:.0f} TEP/yr \u2014 "
                                f"7 yr duration \u2014 Updated {TEE_DATA_AGGIORNAMENTO}"
                            )

                    # ── SENSITIVITY ANALYSIS ──────────────────────────
                    st.divider()
                    st.markdown("#### Sensitivity Analysis \u2014 Energy Price")

                    from heatscout.core.sensitivity import energy_price_sensitivity

                    sens_points = energy_price_sensitivity(
                        best,
                        base_price=energy_price,
                        n_points=15,
                        range_pct=50.0,
                        discount_rate=discount_rate,
                        years=horizon_years,
                    )
                    prices = [p.param_value for p in sens_points]
                    paybacks = [
                        p.payback_years if p.payback_years < 50 else None for p in sens_points
                    ]
                    npvs = [p.npv_EUR for p in sens_points]

                    sc1, sc2 = st.columns(2)
                    with sc1:
                        fig_pb = go.Figure()
                        fig_pb.add_trace(
                            go.Scatter(
                                x=prices,
                                y=paybacks,
                                mode="lines+markers",
                                line=dict(color="#00D4AA", width=2),
                                marker=dict(size=6),
                            )
                        )
                        fig_pb.add_vline(
                            x=energy_price,
                            line_dash="dash",
                            line_color="#8b949e",
                            annotation_text="current",
                        )
                        fig_pb.update_layout(
                            title="Payback vs Energy Price",
                            xaxis_title="Energy price (\u20ac/kWh)",
                            yaxis_title="Payback (years)",
                            height=350,
                            **PLOTLY_DARK_LAYOUT,
                        )
                        st.plotly_chart(fig_pb, use_container_width=True, theme=None)

                    with sc2:
                        fig_npv = go.Figure()
                        fig_npv.add_trace(
                            go.Scatter(
                                x=prices,
                                y=npvs,
                                mode="lines+markers",
                                line=dict(color="#58a6ff", width=2),
                                marker=dict(size=6),
                                fill="tozeroy",
                                fillcolor="rgba(88,166,255,0.1)",
                            )
                        )
                        fig_npv.add_vline(
                            x=energy_price,
                            line_dash="dash",
                            line_color="#8b949e",
                            annotation_text="current",
                        )
                        fig_npv.add_hline(y=0, line_dash="dot", line_color="#f85149")
                        fig_npv.update_layout(
                            title="NPV vs Energy Price",
                            xaxis_title="Energy price (\u20ac/kWh)",
                            yaxis_title=f"NPV {horizon_years}yr (\u20ac)",
                            height=350,
                            **PLOTLY_DARK_LAYOUT,
                        )
                        st.plotly_chart(fig_npv, use_container_width=True, theme=None)

                    st.caption(
                        f"Sensitivity on best project ({best.tech_recommendation.technology.name}) \u2014 "
                        f"Energy price \u00b150% around \u20ac {energy_price:.3f}/kWh"
                    )

                    # ── TORNADO CHART ─────────────────────────────────
                    st.divider()
                    st.markdown("#### Tornado Chart \u2014 NPV Sensitivity (\u00b120%)")
                    st.caption(
                        "One-at-a-time: each parameter varied \u00b120% while others held constant."
                    )

                    from heatscout.core.sensitivity import tornado_analysis

                    tornado_bars = tornado_analysis(
                        best,
                        base_price=energy_price,
                        variation_pct=20.0,
                        discount_rate=discount_rate,
                        years=horizon_years,
                    )

                    fig_tornado = go.Figure()
                    param_names = [b.param_name for b in tornado_bars]
                    base_npv = tornado_bars[0].base_npv

                    fig_tornado.add_trace(
                        go.Bar(
                            y=param_names,
                            x=[b.npv_low - base_npv for b in tornado_bars],
                            orientation="h",
                            name="\u221220%",
                            marker_color="#f85149",
                            customdata=[b.npv_low for b in tornado_bars],
                            hovertemplate="%{y}: NPV = \u20ac %{customdata:,.0f}<extra>\u221220%</extra>",
                        )
                    )
                    fig_tornado.add_trace(
                        go.Bar(
                            y=param_names,
                            x=[b.npv_high - base_npv for b in tornado_bars],
                            orientation="h",
                            name="+20%",
                            marker_color="#3fb950",
                            customdata=[b.npv_high for b in tornado_bars],
                            hovertemplate="%{y}: NPV = \u20ac %{customdata:,.0f}<extra>+20%</extra>",
                        )
                    )

                    fig_tornado.add_vline(x=0, line_color="#8b949e", line_width=1)
                    fig_tornado.update_layout(
                        title=f"NPV Impact (base: \u20ac {base_npv:,.0f})",
                        xaxis_title="\u0394NPV from base (\u20ac)",
                        height=300,
                        margin=dict(t=40, b=40, l=120),
                        barmode="overlay",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        **PLOTLY_DARK_LAYOUT,
                    )
                    st.plotly_chart(fig_tornado, use_container_width=True, theme=None)

                else:
                    st.info(
                        "No economic results available. Check that you have HOT_WASTE "
                        "streams with compatible technologies."
                    )

            # ── TAB: PINCH ANALYSIS ──────────────────────────────────
            elif selected_tab == "Pinch Analysis" and pinch_available:
                from heatscout.plotting.pinch_curves import (
                    create_composite_curves,
                    create_grand_composite,
                )

                section_header("Pinch Analysis", "fire")

                st.markdown(
                    "Pinch Analysis identifies the **maximum heat recovery** between "
                    "hot and cold streams, and the **minimum utility** (heating/cooling) "
                    "requirements. Adjust ΔT<sub>min</sub> to explore the trade-off "
                    "between heat recovery and heat exchanger area.",
                    unsafe_allow_html=True,
                )

                dT_min = st.slider(
                    "Minimum approach temperature ΔT_min (°C)",
                    min_value=1,
                    max_value=30,
                    value=10,
                    step=1,
                    help="Smaller ΔT_min = more recovery but larger heat exchangers. "
                    "Typical values: 10°C (liquids), 20°C (gases).",
                )

                try:
                    pinch_result = hb.pinch_analysis(dT_min=float(dT_min))

                    # Results metrics
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric(
                        "Min Hot Utility",
                        f"{pinch_result.QH_min:.1f} kW",
                        help="Minimum external heating required",
                    )
                    col2.metric(
                        "Min Cold Utility",
                        f"{pinch_result.QC_min:.1f} kW",
                        help="Minimum external cooling required",
                    )
                    col3.metric(
                        "Max Recovery",
                        f"{pinch_result.max_recovery:.1f} kW",
                        help="Maximum heat recoverable between streams",
                    )
                    col4.metric(
                        "Pinch Point",
                        f"{pinch_result.pinch_T_hot:.0f}°C / {pinch_result.pinch_T_cold:.0f}°C",
                        help="Hot side / Cold side pinch temperature",
                    )

                    st.markdown("")

                    # Charts
                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        fig_cc = create_composite_curves(pinch_result)
                        st.plotly_chart(fig_cc, use_container_width=True, theme=None)

                    with chart_col2:
                        fig_gcc = create_grand_composite(pinch_result)
                        st.plotly_chart(fig_gcc, use_container_width=True, theme=None)

                    # Interpretation
                    with st.expander("How to interpret these results", expanded=False):
                        st.markdown(f"""
**Composite Curves** show the aggregated heat available (hot, red) and
heat required (cold, blue) as a function of temperature. The horizontal
gap between the curves at the top represents the minimum hot utility
(**{pinch_result.QH_min:.1f} kW**), and at the bottom the minimum cold
utility (**{pinch_result.QC_min:.1f} kW**).

**Grand Composite Curve** shows the net heat flow at each temperature
level. Where the curve touches zero is the **pinch point**
({pinch_result.pinch_T_hot:.0f}°C / {pinch_result.pinch_T_cold:.0f}°C).
"Pockets" in the curve represent process-to-process heat recovery that
doesn't require external utilities.

**Design rules** (Linnhoff):
- Do not transfer heat across the pinch
- Do not use external cooling above the pinch
- Do not use external heating below the pinch
                        """)

                    # Problem Table details
                    with st.expander("Problem Table details", expanded=False):
                        interval_data = []
                        for iv in pinch_result.intervals:
                            interval_data.append(
                                {
                                    "T upper (°C)": f"{iv.T_upper:.1f}",
                                    "T lower (°C)": f"{iv.T_lower:.1f}",
                                    "Hot CP (kW/K)": f"{iv.hot_CP_total:.2f}",
                                    "Cold CP (kW/K)": f"{iv.cold_CP_total:.2f}",
                                    "ΔH (kW)": f"{iv.delta_H:.1f}",
                                }
                            )
                        st.dataframe(
                            pd.DataFrame(interval_data),
                            use_container_width=True,
                            hide_index=True,
                        )

                except ValueError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f"Error running Pinch Analysis: {e}")

            # ── TAB: REPORT ──────────────────────────────────────────
            elif selected_tab == "Report":
                if all_econ_results:
                    from heatscout.report.executive_summary import generate_executive_summary
                    from heatscout.report.pdf_generator import generate_report

                    st.markdown("#### Executive Summary")
                    exec_text = generate_executive_summary(summary, all_econ_results, energy_price)
                    st.text(exec_text)

                    st.divider()

                    col_pdf, col_xlsx, col_json, col_info = st.columns([2, 2, 2, 3])
                    with col_pdf:
                        try:
                            fig_sankey_pdf = create_sankey(hb, factory_name)
                            pdf_bytes = generate_report(
                                summary,
                                all_econ_results,
                                fig_sankey_pdf,
                                energy_price=energy_price,
                            )
                            st.download_button(
                                label="Download PDF Report",
                                data=pdf_bytes,
                                file_name=f"HeatScout_Report_{factory_name.replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary",
                            )
                        except Exception:
                            st.error(
                                "Error generating PDF report. "
                                "Results are still available in the tabs above."
                            )
                    with col_xlsx:
                        try:
                            from heatscout.report.excel_export import export_to_excel

                            xlsx_bytes = export_to_excel(
                                summary,
                                all_econ_results,
                                incentive_summaries=all_summaries if has_incentives else None,
                                energy_price=energy_price,
                            )
                            st.download_button(
                                label="Download Excel",
                                data=xlsx_bytes,
                                file_name=f"HeatScout_{factory_name.replace(' ', '_')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                            )
                        except Exception:
                            st.error("Error generating Excel export.")
                    with col_json:
                        from heatscout.report.persistence import save_analysis

                        inc_params = None
                        if has_incentives:
                            inc_params = {
                                "capex_reduction_pct": capex_riduzione_pct
                                if capex_inc_enabled
                                else 0,
                                "capex_incentive_name": capex_inc_nome if capex_inc_enabled else "",
                                "tee_enabled": tee_enabled,
                            }
                            if tee_enabled:
                                inc_params["tee_price"] = tee_prezzo
                                inc_params["tee_eta_ref"] = tee_eta_rif
                        json_str = save_analysis(
                            factory_name,
                            T_ambient,
                            energy_price,
                            streams_input,
                            inc_params,
                            discount_rate=discount_rate,
                            horizon_years=horizon_years,
                            opex_multiplier=opex_multiplier,
                            install_multiplier=install_multiplier,
                        )
                        st.download_button(
                            label="Save Analysis (JSON)",
                            data=json_str,
                            file_name=f"HeatScout_{factory_name.replace(' ', '_')}.json",
                            mime="application/json",
                            use_container_width=True,
                        )
                    with col_info:
                        st.caption(
                            "PDF: executive summary, charts, Sankey diagram. "
                            "Excel: 3 sheets with all data. "
                            "JSON: save inputs to reload later."
                        )
                else:
                    st.info("No results to export. Run an analysis with HOT_WASTE streams first.")

        except Exception:
            import traceback

            traceback.print_exc()
            st.error(
                "Unexpected error during analysis. "
                "Please report it on [GitHub Issues](https://github.com/cesabici-bit/heatscout/issues) "
                "with the parameters you entered."
            )

# ── Persistent Results Display (from session_state) ─────────────────────────

if st.session_state.get("analysis_complete"):
    _ss = st.session_state
    _summary = _ss.last_summary
    _hb = _ss.last_hb
    _all_econ = _ss.get("last_econ_results", [])
    _stream_recs = _ss.get("last_stream_recs", {})
    _all_summaries = _ss.get("last_summaries", [])
    _has_incentives = _ss.get("last_has_incentives", False)
    _energy_price = _ss.get("last_energy_price", 0.08)
    _factory_name = _ss.get("last_factory_name", "")

    st.success(
        f"Analysis complete for **{_summary['n_streams']}** streams — "
        f"found **{len(_all_econ)}** recovery solutions"
    )

    # Check if pinch analysis is possible
    _has_hot = any(s.stream_type == StreamType.HOT_WASTE for s in _hb.streams)
    _has_cold = any(s.stream_type == StreamType.COLD_DEMAND for s in _hb.streams)
    _pinch_available = _has_hot and _has_cold

    _tab_items = [
        sac.TabsItem(label="Overview", icon="bar-chart-line"),
        sac.TabsItem(label="Technologies", icon="gear"),
        sac.TabsItem(label="Economics", icon="cash-coin"),
    ]
    if _pinch_available:
        _tab_items.append(sac.TabsItem(label="Pinch Analysis", icon="fire"))
    _tab_items.append(sac.TabsItem(label="Report", icon="file-earmark-pdf"))

    _selected_tab = sac.tabs(
        _tab_items,
        align="center",
        variant="outline",
        use_container_width=True,
    )

    T_CLASS_MAP = {"alta": "High", "media": "Medium", "bassa": "Low"}

    # ── TAB: OVERVIEW ────────────────────────────────────────
    if _selected_tab == "Overview":
        section_header("Analysis Overview", "bar-chart-line")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Waste Heat", f"{_summary['total_waste_kW']:,.0f} kW")
        col2.metric("Annual Energy", f"{_summary['total_waste_MWh_anno']:,.0f} MWh/yr")
        col3.metric("Total Exergy", f"{_summary['total_waste_exergy_kW']:,.0f} kW")
        waste_cost = _summary["total_waste_MWh_anno"] * _energy_price * 1000
        col4.metric("Annual Cost of Waste", f"€{waste_cost:,.0f}/yr")

        st.markdown("")

        # Sankey diagram
        try:
            fig_sankey = create_sankey(_hb, _factory_name)
            st.plotly_chart(fig_sankey, use_container_width=True, theme=None)
        except Exception:
            st.warning("Could not render Sankey diagram.")

        # Temperature class breakdown
        section_header("Waste Heat by Temperature Class", "thermometer-half")
        class_data = _summary.get("by_temperature_class", {})
        tcols = st.columns(3)
        for i, (cls_key, cls_label) in enumerate(
            [("alta", "High >250°C"), ("media", "Medium 80-250°C"), ("bassa", "Low <80°C")]
        ):
            with tcols[i]:
                cls = class_data.get(cls_key, {})
                temp_card(
                    cls_label,
                    f"{cls.get('Q_kW', 0):,.0f} kW",
                    f"{cls.get('pct_of_waste', 0):.0f}% of total",
                    cls_key,
                )

        # Stream details table
        with st.expander("Stream Details", expanded=False):
            rows = []
            for r in _summary.get("stream_results", []):
                rows.append(
                    {
                        "Stream": r["name"],
                        "Type": r["stream_type"],
                        "T_in (°C)": r["T_in"],
                        "T_out (°C)": r["T_out"],
                        "Q (kW)": r["Q_kW"],
                        "E (MWh/yr)": r["E_MWh_anno"],
                        "Exergy (kW)": r["Ex_kW"],
                        "T Class": T_CLASS_MAP.get(r["T_class"], r["T_class"]),
                    }
                )
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── TAB: TECHNOLOGIES ────────────────────────────────────
    elif _selected_tab == "Technologies":
        section_header("Technology Recommendations", "gear")
        if _all_econ:
            for stream_name, rec_list in _stream_recs.items():
                st.markdown(f"##### {stream_name}")
                tech_rows = []
                for rec, econ in rec_list:
                    tech_rows.append(
                        {
                            "Technology": rec.technology.name,
                            "Q Recovered (kW)": f"{rec.Q_recovered_kW:.0f}",
                            "Efficiency": f"{rec.efficiency:.0%}",
                            "CAPEX (€)": f"{econ.capex_EUR:,.0f}",
                            "Payback (yr)": f"{econ.payback_years:.1f}",
                            "NPV (€)": f"{econ.npv_EUR:,.0f}",
                        }
                    )
                st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No technologies found for the given streams.")

    # ── TAB: ECONOMICS ───────────────────────────────────────
    elif _selected_tab == "Economics":
        section_header("Economic Analysis", "cash-coin")
        if _all_econ:
            from heatscout.plotting.comparison_chart import (
                capex_comparison_chart,
                cumulative_cashflow_chart,
                do_nothing_comparison,
                npv_comparison_chart,
                payback_comparison_chart,
            )

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.plotly_chart(
                    capex_comparison_chart(_all_econ), use_container_width=True, theme=None
                )
            with chart_col2:
                st.plotly_chart(
                    payback_comparison_chart(_all_econ), use_container_width=True, theme=None
                )

            chart_col3, chart_col4 = st.columns(2)
            with chart_col3:
                st.plotly_chart(
                    npv_comparison_chart(_all_econ), use_container_width=True, theme=None
                )
            with chart_col4:
                st.plotly_chart(
                    do_nothing_comparison(_all_econ), use_container_width=True, theme=None
                )

            if len(_all_econ) > 0:
                st.markdown("#### Cumulative Cash Flow")
                for econ in _all_econ:
                    with st.expander(
                        f"{econ.tech_recommendation.stream_name} — {econ.tech_recommendation.technology.name}"
                    ):
                        st.plotly_chart(
                            cumulative_cashflow_chart(econ), use_container_width=True, theme=None
                        )
        else:
            st.info("No economic results available.")

    # ── TAB: PINCH ANALYSIS ──────────────────────────────────
    elif _selected_tab == "Pinch Analysis" and _pinch_available:
        from heatscout.plotting.pinch_curves import (
            create_composite_curves,
            create_grand_composite,
        )

        section_header("Pinch Analysis", "fire")

        st.markdown(
            "Pinch Analysis identifies the **maximum heat recovery** between "
            "hot and cold streams, and the **minimum utility** (heating/cooling) "
            "requirements. Adjust ΔT<sub>min</sub> to explore the trade-off "
            "between heat recovery and heat exchanger area.",
            unsafe_allow_html=True,
        )

        dT_min = st.slider(
            "Minimum approach temperature ΔT_min (°C)",
            min_value=1,
            max_value=30,
            value=10,
            step=1,
            help="Smaller ΔT_min = more recovery but larger heat exchangers. "
            "Typical values: 10°C (liquids), 20°C (gases).",
        )

        try:
            pinch_result = _hb.pinch_analysis(dT_min=float(dT_min))

            col1, col2, col3, col4 = st.columns(4)
            col1.metric(
                "Min Hot Utility",
                f"{pinch_result.QH_min:.1f} kW",
                help="Minimum external heating required",
            )
            col2.metric(
                "Min Cold Utility",
                f"{pinch_result.QC_min:.1f} kW",
                help="Minimum external cooling required",
            )
            col3.metric(
                "Max Recovery",
                f"{pinch_result.max_recovery:.1f} kW",
                help="Maximum heat recoverable between streams",
            )
            col4.metric(
                "Pinch Point",
                f"{pinch_result.pinch_T_hot:.0f}°C / {pinch_result.pinch_T_cold:.0f}°C",
                help="Hot side / Cold side pinch temperature",
            )

            st.markdown("")

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                fig_cc = create_composite_curves(pinch_result)
                st.plotly_chart(fig_cc, use_container_width=True, theme=None)

            with chart_col2:
                fig_gcc = create_grand_composite(pinch_result)
                st.plotly_chart(fig_gcc, use_container_width=True, theme=None)

            with st.expander("How to interpret these results", expanded=False):
                st.markdown(f"""
**Composite Curves** show the aggregated heat available (hot, red) and
heat required (cold, blue) as a function of temperature. The horizontal
gap between the curves at the top represents the minimum hot utility
(**{pinch_result.QH_min:.1f} kW**), and at the bottom the minimum cold
utility (**{pinch_result.QC_min:.1f} kW**).

**Grand Composite Curve** shows the net heat flow at each temperature
level. Where the curve touches zero is the **pinch point**
({pinch_result.pinch_T_hot:.0f}°C / {pinch_result.pinch_T_cold:.0f}°C).
"Pockets" in the curve represent process-to-process heat recovery that
doesn't require external utilities.

**Design rules** (Linnhoff):
- Do not transfer heat across the pinch
- Do not use external cooling above the pinch
- Do not use external heating below the pinch
                """)

            with st.expander("Problem Table details", expanded=False):
                interval_data = []
                for iv in pinch_result.intervals:
                    interval_data.append(
                        {
                            "T upper (°C)": f"{iv.T_upper:.1f}",
                            "T lower (°C)": f"{iv.T_lower:.1f}",
                            "Hot CP (kW/K)": f"{iv.hot_CP_total:.2f}",
                            "Cold CP (kW/K)": f"{iv.cold_CP_total:.2f}",
                            "ΔH (kW)": f"{iv.delta_H:.1f}",
                        }
                    )
                st.dataframe(
                    pd.DataFrame(interval_data),
                    use_container_width=True,
                    hide_index=True,
                )

        except ValueError as e:
            st.warning(str(e))
        except Exception as e:
            st.error(f"Error running Pinch Analysis: {e}")

    # ── TAB: REPORT ──────────────────────────────────────────
    elif _selected_tab == "Report":
        if _all_econ:
            from heatscout.report.executive_summary import generate_executive_summary
            from heatscout.report.pdf_generator import generate_report

            st.markdown("#### Executive Summary")
            exec_text = generate_executive_summary(_summary, _all_econ, _energy_price)
            st.text(exec_text)

            st.divider()

            col_pdf, col_xlsx, col_json, col_info = st.columns([2, 2, 2, 3])
            with col_pdf:
                try:
                    fig_sankey_pdf = create_sankey(_hb, _factory_name)
                    pdf_bytes = generate_report(
                        _summary,
                        _all_econ,
                        fig_sankey_pdf,
                        energy_price=_energy_price,
                    )
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"HeatScout_Report_{_factory_name.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
                except Exception:
                    st.error("Error generating PDF report.")
            with col_xlsx:
                try:
                    from heatscout.report.excel_export import export_to_excel

                    xlsx_bytes = export_to_excel(
                        _summary,
                        _all_econ,
                        incentive_summaries=_all_summaries if _has_incentives else None,
                        energy_price=_energy_price,
                    )
                    st.download_button(
                        label="Download Excel",
                        data=xlsx_bytes,
                        file_name=f"HeatScout_{_factory_name.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except Exception:
                    st.error("Error generating Excel export.")
            with col_json:
                from heatscout.report.persistence import save_analysis

                json_str = save_analysis(
                    _factory_name,
                    _hb.T_ambient,
                    _energy_price,
                    streams_input,
                    None,
                )
                st.download_button(
                    label="Save Analysis (JSON)",
                    data=json_str,
                    file_name=f"HeatScout_{_factory_name.replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            with col_info:
                st.caption(
                    "PDF: executive summary, charts, Sankey diagram. "
                    "Excel: 3 sheets with all data. "
                    "JSON: save inputs to reload later."
                )
        else:
            st.info("No results to export. Run an analysis with HOT_WASTE streams first.")

# ── Methodology ──────────────────────────────────────────────────────────────

st.divider()
st.markdown("## Methodology & Sources")
st.caption(
    "HeatScout uses published correlations and models. "
    "All sources are cited below. CAPEX \u00b130%, savings \u00b115%."
)

with st.expander("Efficiency Models"):
    st.markdown(
        """**Heat Exchanger Effectiveness (\u03b5)**
- Gas-gas: \u03b5 = 0.62 (range 0.50\u20130.75)
- Gas-liquid: \u03b5 = 0.68 (range 0.55\u20130.80)
- Liquid-liquid: \u03b5 = 0.75 (range 0.60\u20130.85)
- Adjustments: +0.05 if \u0394T > 200\u00b0C, \u22120.05 if \u0394T < 30\u00b0C
- *Source: Incropera, Fundamentals of Heat and Mass Transfer, Ch. 11*

**Heat Pump COP**
- COP = \u03b7_Carnot \u00d7 T_sink / (T_sink \u2212 T_source), \u03b7_Carnot = 0.45
- Bounds: 1.5 \u2264 COP \u2264 6.0
- *Source: ASHRAE Handbook, HVAC Systems and Equipment, Ch. 8*

**ORC Electrical Efficiency**
- \u03b7 = 0.45 \u00d7 (1 \u2212 T_sink/T_source), bounds: 0\u201325%
- *Source: Quoilin et al., Renewable & Sustainable Energy Reviews, 2013*

**Combustion Air Preheating**
- Savings = (T_air_out \u2212 T_air_in) / T_flame \u00d7 100%, T_flame = 1800\u00b0C
- *Source: Baukal, Industrial Combustion Pollution and Control, Ch. 6*"""
    )

with st.expander("CAPEX Correlations"):
    st.markdown("**General formula:** `CAPEX = a \u00d7 Q^b` [\u20ac], Q in kW")
    st.markdown("")
    capex_data = [
        ["Gas-gas HX", "800", "0.80", "500\u20131,200", "3%", "1.5", "Thekdi & Belt, ACEEE (2011)"],
        ["Economizer", "600", "0.78", "400\u2013900", "3%", "1.5", "Cleaver-Brooks + literature"],
        [
            "Liquid-liquid HX",
            "400",
            "0.75",
            "250\u2013600",
            "2%",
            "1.3",
            "Alfa Laval + Perry\u2019s Handbook",
        ],
        ["HRSG", "1,500", "0.80", "1,000\u20132,000", "4%", "1.8", "Ganapathy (2003)"],
        ["Heat pump (air)", "600", "0.85", "450\u2013800", "3%", "1.4", "IEA HPT Annex 48"],
        ["Heat pump (water)", "550", "0.85", "400\u2013750", "3%", "1.4", "IEA HPT Annex 48"],
        ["ORC", "3,000", "0.75", "2,200\u20134,000", "5%", "1.6", "Quoilin et al. (2013)"],
        ["Air preheater", "300", "0.80", "200\u2013450", "2%", "1.4", "Baukal (2004)"],
    ]
    st.dataframe(
        pd.DataFrame(
            capex_data,
            columns=["Technology", "a", "b", "a range", "OPEX %", "Install", "Source"],
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Technology Selection Criteria"):
    st.markdown(
        """Each technology has a valid temperature and power range:

| Technology | T range (\u00b0C) | Q range (kW) | Lifetime |
|---|---|---|---|
| Gas-gas HX | 80\u2013800 | 10\u20135,000 | 15 yr |
| Economizer | 60\u2013600 | 10\u20135,000 | 15 yr |
| Liquid-liquid HX | 20\u2013200 | 5\u20135,000 | 20 yr |
| HRSG | 200\u2013800 | 100\u201350,000 | 20 yr |
| Heat pump (air) | 15\u201380 | 5\u20131,000 | 15 yr |
| Heat pump (water) | 15\u201390 | 5\u20132,000 | 15 yr |
| ORC | 80\u2013500 | 50\u201310,000 | 20 yr |
| Air preheater | 150\u2013800 | 10\u20135,000 | 15 yr |

Technologies outside their valid range are not recommended."""
    )

with st.expander("Uncertainty & Limitations"):
    st.markdown(
        """| Item | Uncertainty | Notes |
|---|---|---|
| CAPEX | \u00b130% | Min/max range on coefficient 'a' |
| Savings | \u00b115% | Efficiency model uncertainty |
| Payback | \u00b150% | Compounds CAPEX + savings uncertainty |
| COP / efficiency | Model-dependent | Simplified first-order models |

**Key limitations:**
- Correlations are from 2003\u20132026 literature; actual costs depend on market conditions
- Installation factor is an average \u2014 site-specific conditions may vary significantly
- Heat pump COP assumes ideal Carnot fraction (\u03b7=0.45) \u2014 actual COP depends on refrigerant and design
- ORC efficiency is for commercial modules \u2014 custom designs may differ
- This tool is for **screening only** \u2014 always commission a detailed feasibility study before investing"""
    )

with st.expander("Bibliography"):
    st.markdown(
        """1. Thekdi, A. & Belt, R. (2011). *Waste Heat Recovery*. ACEEE
2. Ganapathy, V. (2003). *Waste Heat Boiler Deskbook*. Fairmont Press
3. Quoilin, S. et al. (2013). *Techno-economic survey of ORC systems*. Ren. & Sust. Energy Rev., 17, 168\u2013186
4. Incropera, F.P. et al. *Fundamentals of Heat and Mass Transfer*. Ch. 11
5. ASHRAE (2021). *Handbook: HVAC Systems and Equipment*. Ch. 8
6. Baukal, C.E. (2004). *Industrial Combustion Pollution and Control*. Ch. 6
7. Perry\u2019s Chemical Engineers\u2019 Handbook (8th Ed.). Table 11-13
8. IEA HPT Annex 48. Industrial Heat Pump Market Survey
9. ARERA Delibera EEN 3/08 (TEP conversion)
10. DM MASE 21/07/2025 (White Certificates decree, art. 6\u20137)"""
    )

# ── Footer ───────────────────────────────────────────────────────────────────

st.markdown(footer(), unsafe_allow_html=True)
