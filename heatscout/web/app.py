"""HeatScout — Streamlit web interface for heat recovery analysis."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from heatscout.core.examples import list_examples, load_example
from heatscout.core.heat_balance import FactoryHeatBalance
from heatscout.core.stream import StreamType, ThermalStream
from heatscout.plotting.sankey import create_sankey

# ── Configurazione pagina ────────────────────────────────────────────────────

st.set_page_config(
    page_title="HeatScout — Industrial Heat Recovery",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
    /* Header gradient */
    .hero-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(255,107,53,0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 1.15rem;
        opacity: 0.85;
        margin-top: 0.5rem;
        font-weight: 300;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255,107,53,0.2);
        border: 1px solid rgba(255,107,53,0.4);
        color: #ff6b35;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 0.75rem;
    }

    /* Dark theme base — force light text everywhere */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    .stApp header {
        background-color: #0d1117 !important;
    }
    /* Global text override — all elements */
    .stApp, .stApp p, .stApp span, .stApp li, .stApp td, .stApp th,
    .stApp label, .stApp div, .stApp strong, .stApp em, .stApp a,
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5,
    .stMarkdown strong, .stMarkdown em, .stMarkdown a,
    .stMarkdown blockquote, .stMarkdown blockquote p,
    .stMarkdown code, .stMarkdown pre,
    [data-testid="stText"], [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] span {
        color: #e6edf3 !important;
    }
    /* Captions slightly dimmer */
    [data-testid="stCaptionContainer"] * {
        color: #8b949e !important;
    }
    /* Radio, checkbox, selectbox labels */
    .stRadio label, .stCheckbox label, .stSelectbox label,
    .stTextInput label, .stNumberInput label,
    .stRadio > div > label, .stRadio div[role="radiogroup"] label,
    [data-baseweb="radio"] span,
    .stSlider label {
        color: #e6edf3 !important;
    }
    /* Widget help text */
    .stTooltipIcon, small, .stApp small {
        color: #8b949e !important;
    }
    /* placeholder — alert box styles moved to end for specificity */
    /* Blockquote border */
    .stMarkdown blockquote {
        border-left-color: #ff6b35 !important;
    }
    /* Tab panel text */
    .stTabs [data-baseweb="tab-panel"] {
        color: #e6edf3 !important;
    }
    .stTabs [data-baseweb="tab-panel"] p,
    .stTabs [data-baseweb="tab-panel"] span,
    .stTabs [data-baseweb="tab-panel"] li,
    .stTabs [data-baseweb="tab-panel"] td {
        color: #e6edf3 !important;
    }
    /* Input text color + dark background */
    .stTextInput input, .stNumberInput input,
    .stSelectbox [data-baseweb="select"] span,
    [data-baseweb="select"] .css-1dimb5e-singleValue,
    [data-baseweb="input"] input {
        color: #e6edf3 !important;
        background-color: #161b22 !important;
    }
    /* Select/dropdown containers */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] {
        background-color: #161b22 !important;
    }
    /* Number input +/- buttons */
    .stNumberInput button {
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
        border: 1.5px solid #e6edf3 !important;
        transition: all 0.2s ease !important;
    }
    .stNumberInput button:hover {
        color: #0d1117 !important;
        background-color: #e6edf3 !important;
    }
    /* Expander header */
    .streamlit-expanderHeader, [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span {
        color: #e6edf3 !important;
        background-color: #161b22 !important;
    }
    /* Expander content */
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #0d1117 !important;
    }
    /* Dataframe text */
    .stDataFrame td, .stDataFrame th,
    [data-testid="stDataFrame"] td,
    [data-testid="stDataFrame"] th {
        color: #e6edf3 !important;
    }
    /* Download button — same style as all buttons */
    .stDownloadButton button {
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
        border: 1.5px solid #e6edf3 !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton button:hover {
        color: #0d1117 !important;
        background-color: #e6edf3 !important;
    }

    /* Metric cards — dark */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(255,107,53,0.15);
        border-color: #ff6b35;
    }
    div[data-testid="stMetric"] label {
        font-weight: 600 !important;
        color: #8b949e !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #f0f6fc !important;
    }

    /* Impact banner — dark */
    .impact-banner {
        background: linear-gradient(135deg, #1c1a00 0%, #2a2600 100%);
        border-left: 5px solid #ff6b35;
        border-radius: 0 12px 12px 0;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
    }
    .impact-banner p {
        margin: 0;
        font-size: 1.1rem;
        color: #ffb088;
    }

    /* Section headers — dark */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 0;
        margin-top: 1.5rem;
        border-bottom: 2px solid #21262d;
        margin-bottom: 1rem;
    }
    .section-header h2 {
        margin: 0;
        font-weight: 700;
        color: #f0f6fc !important;
    }

    /* Temperature class cards — dark */
    .temp-card {
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .temp-card:hover {
        transform: scale(1.02);
    }
    .temp-alta { background: linear-gradient(135deg, #3b1012, #4a1518); border: 1px solid #7f1d1d; }
    .temp-media { background: linear-gradient(135deg, #3b2508, #4a2e0a); border: 1px solid #92400e; }
    .temp-bassa { background: linear-gradient(135deg, #3b3508, #4a420a); border: 1px solid #854d0e; }
    .temp-card .temp-label { font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem; color: #e6edf3; }
    .temp-card .temp-value { font-size: 1.5rem; font-weight: 800; color: #f0f6fc; }
    .temp-card .temp-detail { font-size: 0.85rem; color: #8b949e; margin-top: 0.25rem; }

    /* Sidebar — dark */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #21262d;
    }
    section[data-testid="stSidebar"] .stButton > button {
        border-radius: 8px;
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
        border: 1.5px solid #e6edf3 !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        color: #0d1117 !important;
        background-color: #e6edf3 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e6edf3 !important;
    }

    /* Expanders — dark */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 1rem !important;
        color: #e6edf3 !important;
        background-color: #161b22 !important;
        border-color: #30363d !important;
    }
    details[data-testid="stExpander"] {
        background-color: #161b22;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
    }

    /* Tabs — dark */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8b949e !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ff6b35 !important;
    }

    /* Inputs — dark */
    .stTextInput > div > div, .stNumberInput > div > div,
    .stSelectbox > div > div {
        background-color: #161b22 !important;
        border-color: #30363d !important;
        color: #e6edf3 !important;
    }

    /* Dataframe — dark */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 8px;
    }

    /* Info/Success/Error boxes — dark */
    .stAlert {
        border-radius: 10px !important;
    }

    /* All buttons — white border, dark bg, light text; hover inverts */
    .stButton > button {
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
        border: 1.5px solid #e6edf3 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        color: #0d1117 !important;
        background-color: #e6edf3 !important;
        border-color: #e6edf3 !important;
    }

    /* Analyze button — same base + bigger */
    .stButton > button[kind="primary"] {
        border-radius: 12px !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        padding: 0.75rem !important;
        letter-spacing: 0.5px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }

    /* Footer — dark */
    .footer {
        text-align: center;
        color: #484f58;
        font-size: 0.8rem;
        padding: 2rem 0 1rem 0;
        border-top: 1px solid #21262d;
        margin-top: 3rem;
    }
    .footer a { color: #8b949e; text-decoration: none; }
    .footer a:hover { color: #ff6b35; }

    /* ── ANIMATIONS ── */

    /* Pulsing glow on hero */
    .hero-container {
        animation: heroGlow 4s ease-in-out infinite alternate;
    }
    @keyframes heroGlow {
        0% { box-shadow: 0 0 20px rgba(255,107,53,0.05); }
        100% { box-shadow: 0 0 40px rgba(255,107,53,0.15); }
    }

    /* Fade-in + slide-up for metric cards */
    div[data-testid="stMetric"] {
        animation: slideUp 0.6s ease-out both;
    }
    div[data-testid="stMetric"]:nth-child(1) { animation-delay: 0s; }
    div[data-testid="stMetric"]:nth-child(2) { animation-delay: 0.1s; }
    div[data-testid="stMetric"]:nth-child(3) { animation-delay: 0.2s; }
    div[data-testid="stMetric"]:nth-child(4) { animation-delay: 0.3s; }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Temperature cards — fade in */
    .temp-card {
        animation: fadeScale 0.5s ease-out both;
    }
    .temp-alta { animation-delay: 0s; }
    .temp-media { animation-delay: 0.15s; }
    .temp-bassa { animation-delay: 0.3s; }
    @keyframes fadeScale {
        from { opacity: 0; transform: scale(0.92); }
        to { opacity: 1; transform: scale(1); }
    }

    /* Impact banner — slide in from left */
    .impact-banner {
        animation: slideRight 0.7s ease-out both;
        animation-delay: 0.2s;
    }
    @keyframes slideRight {
        from { opacity: 0; transform: translateX(-30px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* Badge shimmer effect */
    .hero-badge {
        position: relative;
        overflow: hidden;
    }
    .hero-badge::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
        animation: shimmer 3s ease-in-out infinite;
    }
    @keyframes shimmer {
        0% { left: -100%; }
        50% { left: 100%; }
        100% { left: 100%; }
    }

    /* Fire icon pulse in hero */
    .hero-title {
        animation: firePulse 2s ease-in-out infinite alternate;
    }
    @keyframes firePulse {
        0% { text-shadow: 0 0 10px rgba(255,107,53,0.3); }
        100% { text-shadow: 0 0 25px rgba(255,107,53,0.6), 0 0 50px rgba(255,50,0,0.2); }
    }

    /* Analyze button pulse */
    .stButton > button[kind="primary"] {
        animation: btnPulse 2.5s ease-in-out infinite;
    }
    @keyframes btnPulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255,107,53,0.4); }
        50% { box-shadow: 0 0 0 8px rgba(255,107,53,0); }
    }

    /* ── ALERT BOXES: dark text on light bg (MUST be last for specificity) ── */
    .stApp [data-testid="stNotification"],
    .stApp [data-testid="stNotification"] *,
    .stApp .stAlert,
    .stApp .stAlert *,
    .stApp [data-testid="stNotificationContentSuccess"],
    .stApp [data-testid="stNotificationContentSuccess"] *,
    .stApp [data-testid="stNotificationContentInfo"],
    .stApp [data-testid="stNotificationContentInfo"] *,
    .stApp [data-testid="stNotificationContentWarning"],
    .stApp [data-testid="stNotificationContentWarning"] *,
    .stApp [data-testid="stNotificationContentError"],
    .stApp [data-testid="stNotificationContentError"] *,
    .stApp [role="alert"],
    .stApp [role="alert"] *,
    .stApp [role="alert"] p,
    .stApp [role="alert"] span,
    .stApp [role="alert"] strong,
    .stApp [role="alert"] a,
    .stApp [role="alert"] div {
        color: #e6edf3 !important;
    }

    /* ── GLOBAL HOVER OVERRIDE — max specificity ── */
    .stApp .stButton > button:hover,
    .stApp .stButton > button:focus,
    .stApp .stButton > button:active,
    .stApp section[data-testid="stSidebar"] .stButton > button:hover,
    .stApp section[data-testid="stSidebar"] .stButton > button:focus,
    .stApp .stDownloadButton button:hover,
    .stApp .stDownloadButton button:focus,
    .stApp .stNumberInput button:hover,
    .stApp .stNumberInput button:focus {
        color: #0d1117 !important;
        background-color: #e6edf3 !important;
        border-color: #e6edf3 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── Load available fluids ────────────────────────────────────────────────────

FLUIDS_PATH = Path(__file__).parent.parent / "data" / "fluids.json"
with open(FLUIDS_PATH, encoding="utf-8") as f:
    FLUIDS_DB = json.load(f)["fluids"]

FLUID_OPTIONS = {f["id"]: f["name"] for f in FLUIDS_DB}
FLUID_IDS = list(FLUID_OPTIONS.keys())
FLUID_NAMES = list(FLUID_OPTIONS.values())

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ General Parameters")
    factory_name = st.text_input("Plant name", value="My plant")

    col_t, col_p = st.columns(2)
    with col_t:
        T_ambient = st.number_input(
            "Ambient T (°C)", value=25.0, min_value=-20.0, max_value=50.0, step=1.0
        )
    with col_p:
        energy_price = st.number_input(
            "€/kWh",
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
                help="WACC or cost of capital. Typical: 3-5% (EU), 5-8% (US/emerging). Used for NPV calculation.",
            )
            / 100.0
        )
    with col_hz:
        _hz_default = st.session_state.pop("loaded_horizon_years", 10)
        horizon_years = st.number_input(
            "Analysis horizon (yr)",
            value=_hz_default,
            min_value=3,
            max_value=30,
            step=1,
            help="Economic analysis period. Match to equipment lifetime: HX 15-20yr, heat pump 10-15yr, ORC 15-20yr.",
        )

    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        st.caption(
            "Adjust cost model parameters. Default values are industry averages from literature."
        )
        _opex_default = st.session_state.pop("loaded_opex_multiplier", 1.0)
        opex_multiplier = st.slider(
            "OPEX multiplier",
            min_value=0.5,
            max_value=2.0,
            value=_opex_default,
            step=0.1,
            help="Scale annual maintenance costs. 1.0 = default from literature. "
            "Increase for harsh environments, remote sites. Decrease for in-house maintenance.",
        )
        _inst_default = st.session_state.pop("loaded_install_multiplier", 1.0)
        install_multiplier = st.slider(
            "Installation cost multiplier",
            min_value=0.5,
            max_value=2.0,
            value=_inst_default,
            step=0.1,
            help="Scale installation/piping/engineering overhead. 1.0 = default. "
            "Increase for brownfield/retrofit, high labor cost countries. "
            "Decrease for greenfield, low labor cost regions.",
        )

    # Incentives
    st.divider()
    st.markdown("### Incentives")

    # Generic CAPEX incentive (international)
    capex_inc_enabled = st.checkbox(
        "CAPEX reduction (tax credit / grant)",
        value=False,
        help="Any incentive that reduces investment cost: IRA §48C (US), IETF (UK), EU Innovation Fund, etc.",
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
                help="Percentage of investment covered by the incentive",
            )
        with col_ci2:
            capex_inc_nome = st.text_input(
                "Incentive name",
                value="Tax credit / Grant",
                help="E.g.: IRA §48C, IETF, Transizione 5.0, EU Innovation Fund",
            )

    # TEE — Italian incentive
    tee_enabled = st.checkbox(
        "Certificati Bianchi / TEE (Italy)",
        value=False,
        help="Italian White Certificates — DM MASE 21/07/2025",
    )
    if tee_enabled:
        col_tee1, col_tee2 = st.columns(2)
        with col_tee1:
            tee_prezzo = st.number_input(
                "TEE price (€/TEE)",
                value=250.0,
                min_value=50.0,
                max_value=500.0,
                step=10.0,
                help="Indicative value — GME market avg. ~250 €/TEE",
            )
        with col_tee2:
            tee_eta_rif = st.number_input(
                "Ref. boiler eff.",
                value=0.90,
                min_value=0.50,
                max_value=1.00,
                step=0.05,
                format="%.2f",
                help="Efficiency of the boiler that heat recovery replaces",
            )
        st.caption("Source: DM MASE 21/07/2025 — TEE value subject to market variations")

    st.divider()
    st.markdown("### 📥 Energy Input")
    energy_input_mode = st.radio(
        "Energy input estimate",
        ["Automatic (eff. 85%)", "Manual"],
        key="energy_input_mode",
        horizontal=True,
    )
    manual_consumption = None
    manual_unit = None
    if energy_input_mode == "Manual":
        manual_consumption = st.number_input(
            "Annual consumption", value=100000.0, min_value=0.0, step=1000.0
        )
        manual_unit = st.selectbox("Unit", ["Sm3/anno", "MWh/anno", "kWh/anno", "tep/anno"])

    st.divider()
    st.markdown("### 📂 Preloaded Examples")
    examples = list_examples()
    example_options = ["-- Select --"] + [
        f"{e['name']} ({e['n_streams']} stream)" for e in examples
    ]
    example_choice = st.selectbox("Load an example", example_options, label_visibility="collapsed")

    def _load_selected_example():
        """Load selected example into session state."""
        if example_choice != "-- Select --":
            idx = example_options.index(example_choice) - 1
            example_id = examples[idx]["id"]
            streams, meta = load_example(example_id)
            st.session_state.n_streams = len(streams)
            st.session_state.loaded_example = {
                "streams": streams,
                "meta": meta,
            }
        else:
            st.session_state.pop("loaded_example", None)

    st.button("📂 Load example", on_click=_load_selected_example, use_container_width=True)

    # Save/Load analysis
    st.divider()
    st.markdown("### 💾 Save / Load Analysis")
    uploaded_json = st.file_uploader(
        "Load analysis (.json)",
        type=["json"],
        help="Upload a previously saved HeatScout analysis file",
        label_visibility="collapsed",
    )
    if uploaded_json is not None:
        try:
            from heatscout.core.stream import StreamType
            from heatscout.report.persistence import load_analysis

            content = uploaded_json.read().decode("utf-8")
            loaded_data = load_analysis(content)

            # Map stream dicts to ThermalStream-like objects for the UI
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
            # Restore economic parameters (backward compatible with v1.0 files)
            if "discount_rate" in loaded_data:
                st.session_state["loaded_discount_rate"] = loaded_data["discount_rate"]
            if "horizon_years" in loaded_data:
                st.session_state["loaded_horizon_years"] = loaded_data["horizon_years"]
            if "opex_multiplier" in loaded_data:
                st.session_state["loaded_opex_multiplier"] = loaded_data["opex_multiplier"]
            if "install_multiplier" in loaded_data:
                st.session_state["loaded_install_multiplier"] = loaded_data["install_multiplier"]
            st.success(f"Loaded: {loaded_data['factory_name']} ({len(restored_streams)} streams)")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    # Import streams from CSV/Excel
    st.divider()
    st.markdown("### 📤 Import Streams")
    col_tpl, col_imp = st.columns(2)
    with col_tpl:
        from heatscout.report.stream_import import generate_template

        st.download_button(
            "📋 Template CSV",
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

    # Sidebar footer
    st.divider()
    st.caption(
        "🔥 HeatScout v1.0  \nOpen source · [GitHub](https://github.com/cesabici-bit/heatscout)"
    )

# ── Hero section ─────────────────────────────────────────────────────────────

st.markdown(
    """
<div class="hero-container">
    <p class="hero-title">🔥 HeatScout</p>
    <p class="hero-subtitle">
        From wasted heat to savings &mdash;
        analyze your plant's thermal streams and discover the best recovery technologies.
    </p>
    <span class="hero-badge">Open Source · Screening Tool</span>
</div>
""",
    unsafe_allow_html=True,
)

# ── Quick start (only if no analysis has been run) ───────────────────────────

if "last_summary" not in st.session_state:
    with st.container():
        st.markdown("#### Getting Started")
        qs1, qs2, qs3 = st.columns(3)
        with qs1:
            st.markdown(
                "**1. Enter your streams**  \nAdd your plant's thermal streams: temperatures, flow rate, fluid."
            )
        with qs2:
            st.markdown(
                "**2. Click Analyze**  \nHeatScout computes power, energy, exergy and selects the best technologies."
            )
        with qs3:
            st.markdown(
                "**3. Download the report**  \nGet a professional PDF with executive summary, charts and recommendations."
            )
        st.info("💡 **Tip:** Load an example from the sidebar to try it out right away!")

# ── Stream management in session state ───────────────────────────────────────

if "n_streams" not in st.session_state:
    st.session_state.n_streams = 1


def add_stream():
    st.session_state.n_streams = min(st.session_state.n_streams + 1, 10)


def remove_stream():
    st.session_state.n_streams = max(st.session_state.n_streams - 1, 1)


# ── Thermal stream input ─────────────────────────────────────────────────────

st.markdown(
    '<div class="section-header"><h2>📊 Thermal Streams</h2></div>',
    unsafe_allow_html=True,
)

col_info, col_add, col_rem = st.columns([4, 1, 1])
with col_info:
    n = st.session_state.n_streams
    st.markdown(f"**{n}** streams configured{'  — max 10' if n < 10 else '  — limit reached'}")
with col_add:
    st.button("➕ Add", on_click=add_stream, use_container_width=True, disabled=(n >= 10))
with col_rem:
    st.button(
        "➖ Remove",
        on_click=remove_stream,
        use_container_width=True,
        disabled=(n <= 1),
    )

# Pre-fill from loaded example
loaded = st.session_state.get("loaded_example")

streams_input = []
for i in range(st.session_state.n_streams):
    ex = None
    if loaded and i < len(loaded["streams"]):
        ex = loaded["streams"][i]

    # Color indicator in expander title
    type_indicator = "🔴" if (ex is None or ex.stream_type == StreamType.HOT_WASTE) else "🔵"
    label = f"{type_indicator} Stream {i + 1}" + (f" — {ex.name}" if ex else "")

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
                    "🔴 Waste heat" if x == StreamType.HOT_WASTE else "🔵 Heat demand"
                ),
                index=default_type_idx,
                key=f"type_{i}",
                help="HOT_WASTE: heat you want to recover (T_in > T_out). "
                "COLD_DEMAND: process that needs heat (T_in < T_out).",
            )
        with col2:
            T_in = st.number_input(
                "T inlet (°C)",
                value=ex.T_in if ex else 200.0,
                min_value=-200.0,
                max_value=1500.0,
                step=10.0,
                key=f"Tin_{i}",
                help="Temperature at the source (before cooling/heating).",
            )
            T_out = st.number_input(
                "T outlet (°C)",
                value=ex.T_out if ex else 80.0,
                min_value=-200.0,
                max_value=1500.0,
                step=10.0,
                key=f"Tout_{i}",
                help="Temperature after heat exchange. For HOT_WASTE: T_out < T_in.",
            )
        with col3:
            mass_flow = st.number_input(
                "Flow rate (kg/s)",
                value=ex.mass_flow if ex else 1.0,
                min_value=0.01,
                max_value=1000.0,
                step=0.1,
                key=f"mflow_{i}",
                help="Mass flow rate of the fluid in kg/s. Check process data or flow meters.",
            )
            hours = st.number_input(
                "Hours/day",
                value=ex.hours_per_day if ex else 16.0,
                min_value=0.5,
                max_value=24.0,
                step=0.5,
                key=f"hours_{i}",
                help="Average operating hours per day when this stream is active.",
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

st.markdown("")  # spacing
if st.button("🔍 Run Analysis", type="primary", use_container_width=True):
    # Validation and stream creation
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
            if "CoolProp" in type(e).__module__ if hasattr(type(e), "__module__") else False:
                errors.append(
                    f"Stream {i + 1} ({data['name']}): Fluid property calculation error: {error_msg}"
                )
            elif (
                "fluid" in error_msg.lower()
                or "coolprop" in error_msg.lower()
                or "property" in error_msg.lower()
            ):
                errors.append(
                    f"Stream {i + 1} ({data['name']}): Fluid property calculation error: {error_msg}"
                )
            else:
                errors.append(f"Stream {i + 1} ({data['name']}): {error_msg}")

    if errors:
        for err in errors:
            st.error(err)
    elif not hb.streams:
        st.error("Add at least one stream before analyzing.")
    elif all(s.stream_type == StreamType.COLD_DEMAND for s in hb.streams):
        st.error(
            "At least one **🔴 Waste heat** (HOT_WASTE) stream is required for heat recovery analysis."
        )
    else:
        try:
            with st.spinner(
                "Analysis in progress... computing thermal properties and selecting technologies"
            ):
                # Energy input
                if energy_input_mode == "Manual" and manual_consumption:
                    hb.set_energy_input("gas_naturale", manual_consumption, manual_unit)
                else:
                    hb.estimate_energy_input(efficiency=0.85)

                # Compute results
                summary = hb.summary()
                st.session_state.last_summary = summary
                st.session_state.last_hb = hb

                # Pre-compute technologies and economics
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
                stream_recs = {}  # stream.name -> list of (rec, econ)
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

                # Compute incentives if enabled
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

            # ── Success banner ────────────────────────────────────────────
            st.success(
                f"Analysis completed for **{summary['n_streams']}** streams — "
                f"found **{len(all_econ_results)}** recovery solutions"
            )

            # ══════════════════════════════════════════════════════════════
            # RESULTS IN TABS
            # ══════════════════════════════════════════════════════════════

            tab_panoramica, tab_tecnologie, tab_economia, tab_report = st.tabs(
                ["📊 Overview", "🔧 Technologies", "💰 Economics", "📄 Report"]
            )

            # ── TAB OVERVIEW ──────────────────────────────────────────────
            with tab_panoramica:
                # Key metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Waste power", f"{summary['total_waste_kW']:,.1f} kW")
                m2.metric("Annual energy", f"{summary['total_waste_MWh_anno']:,.1f} MWh/a")
                m3.metric("Waste exergy", f"{summary['total_waste_exergy_kW']:,.1f} kW")
                annual_cost = summary["total_waste_MWh_anno"] * 1000 * energy_price
                m4.metric("Annual waste cost", f"€ {annual_cost:,.0f}")

                # Impact banner
                waste_pct = summary.get("waste_pct_of_input")
                waste_pct_str = f" ({waste_pct:.0f}% of energy input)" if waste_pct else ""
                st.markdown(
                    f"""
                <div class="impact-banner">
                    <p>💡 You are wasting <strong>{summary["total_waste_kW"]:,.1f} kW</strong> of heat{waste_pct_str},
                    equal to <strong>{summary["total_waste_MWh_anno"]:,.1f} MWh/year</strong>,
                    costing approximately <strong>€ {annual_cost:,.0f}/year</strong>.</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Sankey
                st.markdown("#### Energy Balance")
                fig_sankey = create_sankey(hb, factory_name)
                st.plotly_chart(fig_sankey, use_container_width=True)

                # Temperature breakdown with colored cards
                st.markdown("#### Distribution by Temperature Class")
                by_class = summary["by_temperature_class"]
                tc1, tc2, tc3 = st.columns(3)

                for col, (cls, label, css_class) in zip(
                    [tc1, tc2, tc3],
                    [
                        ("alta", "High (>250°C)", "temp-alta"),
                        ("media", "Medium (80-250°C)", "temp-media"),
                        ("bassa", "Low (<80°C)", "temp-bassa"),
                    ],
                ):
                    cls_data = by_class[cls]
                    with col:
                        st.markdown(
                            f"""
                        <div class="temp-card {css_class}">
                            <div class="temp-label">{label}</div>
                            <div class="temp-value">{cls_data["Q_kW"]:,.1f} kW</div>
                            <div class="temp-detail">{cls_data["count"]} stream · {cls_data["pct_of_waste"]:.1f}% del totale</div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                # Detail table
                st.markdown("")  # spacing
                with st.expander("📋 Stream details", expanded=False):
                    rows = []
                    for r in summary["stream_results"]:
                        rows.append(
                            {
                                "Name": r["name"],
                                "Type": "🔴 Waste"
                                if r["stream_type"] == "hot_waste"
                                else "🔵 Demand",
                                "Fluid": r["fluid_type"],
                                "T in (°C)": r["T_in"],
                                "T out (°C)": r["T_out"],
                                "Q (kW)": f"{r['Q_kW']:,.1f}",
                                "E (MWh/a)": f"{r['E_MWh_anno']:,.1f}",
                                "Exergy (kW)": f"{r['Ex_kW']:,.1f}",
                                "Class": r["T_class"].capitalize(),
                                "Quality": f"{r['quality_ratio']:.1%}",
                            }
                        )
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # ── TAB TECHNOLOGIES ──────────────────────────────────────────
            with tab_tecnologie:
                if not stream_recs:
                    st.info("No recovery technologies found for the entered streams.")
                else:
                    for sname, recs_econs in stream_recs.items():
                        with st.expander(
                            f"🔥 {sname} — {len(recs_econs)} tecnologie", expanded=True
                        ):
                            # Best pick highlight
                            best_rec = min(recs_econs, key=lambda x: x[1].payback_years)
                            best_econ = best_rec[1]
                            st.markdown(
                                f"⭐ **Best:** {best_rec[0].technology.name} — "
                                f"payback **{best_econ.payback_years:.1f} years**, "
                                f"savings **€ {best_econ.annual_savings_EUR:,.0f}/year**"
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
                                        "Q recov. (kW)": f"{rec.Q_recovered_kW:,.1f}",
                                        "E recov. (MWh/a)": f"{rec.E_recovered_MWh:,.1f}",
                                        "Efficiency": eff_str,
                                        "CAPEX (€)": f"{econ.capex_EUR:,.0f}",
                                        "Savings/yr (€)": f"{econ.annual_savings_EUR:,.0f}",
                                        "Payback": f"{econ.payback_years:.1f} yr"
                                        if econ.payback_years < 50
                                        else ">50 yr",
                                        "NPV 10a (€)": f"{econ.npv_EUR:,.0f}",
                                    }
                                )

                            st.dataframe(
                                pd.DataFrame(tech_rows),
                                use_container_width=True,
                                hide_index=True,
                            )

                    # Streams without technologies
                    no_tech = [
                        s.name
                        for s in hb.streams
                        if s.stream_type == StreamType.HOT_WASTE and s.name not in stream_recs
                    ]
                    for sname in no_tech:
                        st.info(f"**{sname}**: no compatible technology found")

            # ── TAB ECONOMICS ─────────────────────────────────────────────
            with tab_economia:
                if all_econ_results:
                    # Disclaimer — always visible before results
                    st.warning(
                        "**Screening-level analysis** — CAPEX ±30%, savings ±15%. "
                        "Not a substitute for detailed engineering study. "
                        "Use these results to prioritize options, then commission a feasibility study."
                    )
                    best = min(all_econ_results, key=lambda e: e.payback_years)
                    total_capex = sum(e.total_investment_EUR for e in all_econ_results)
                    total_savings = sum(e.annual_savings_EUR for e in all_econ_results)
                    total_npv = sum(e.npv_EUR for e in all_econ_results)

                    # Economic metrics
                    e1, e2, e3, e4 = st.columns(4)
                    e1.metric("Total investment", f"€ {total_capex:,.0f}")
                    e2.metric("Annual savings", f"€ {total_savings:,.0f}")
                    e3.metric("Best payback", f"{best.payback_years:.1f} yr")
                    e4.metric(
                        "NPV totale 10a",
                        f"€ {total_npv:,.0f}",
                        delta="positive" if total_npv > 0 else "negative",
                    )

                    # Charts in 2x2
                    gc1, gc2 = st.columns(2)
                    with gc1:
                        st.plotly_chart(
                            payback_comparison_chart(all_econ_results),
                            use_container_width=True,
                        )
                    with gc2:
                        st.plotly_chart(
                            npv_comparison_chart(all_econ_results),
                            use_container_width=True,
                        )

                    gc3, gc4 = st.columns(2)
                    with gc3:
                        st.plotly_chart(
                            capex_comparison_chart(all_econ_results),
                            use_container_width=True,
                        )
                    with gc4:
                        st.plotly_chart(
                            do_nothing_comparison(all_econ_results),
                            use_container_width=True,
                        )

                    # Cumulative cashflow
                    st.markdown("#### Cumulative Cashflow — Best Project")
                    st.caption(f"{best.tech_recommendation.technology.name}")
                    st.plotly_chart(cumulative_cashflow_chart(best), use_container_width=True)

                    # Text summary
                    st.markdown(
                        f"> **Summary:** Investing **€ {total_capex:,.0f}** yields savings of "
                        f"**€ {total_savings:,.0f}/year** with payback in **{best.payback_years:.1f} years** "
                        f"and a net value at {horizon_years} years of **€ {total_npv:,.0f}**."
                    )

                    with st.expander("ℹ️ How to interpret these results"):
                        st.markdown(
                            "- **Payback**: years to recover the investment from energy savings. "
                            "Shorter is better; <3 yr is excellent, 3-5 yr is good, >7 yr needs careful evaluation.\n"
                            "- **NPV** (Net Present Value): total value of the project over the analysis horizon, "
                            "discounted at your cost of capital. Positive = profitable.\n"
                            "- **IRR** (Internal Rate of Return): the discount rate that makes NPV = 0. "
                            "Higher is better; compare with your WACC.\n"
                            "- **CAPEX range**: ±30% uncertainty is normal for screening-level estimates. "
                            "The actual cost depends on site-specific engineering.\n"
                            "- **Savings**: estimated ±15%. Actual savings depend on real operating conditions."
                        )

                    # ── INCENTIVES SECTION ────────────────────────────────
                    if has_incentives and all_summaries:
                        st.divider()
                        st.markdown("#### Incentive Comparison")

                        import pandas as pd

                        # Comparison table
                        inc_rows = []
                        for s in all_summaries:
                            tech_name = s.base.tech_recommendation.technology.name
                            stream_name = s.base.tech_recommendation.stream_name
                            row = {
                                "Stream": stream_name,
                                "Technology": tech_name,
                                "Payback base": f"{s.base.payback_years:.1f} yr",
                                "NPV base": f"€ {s.base.npv_EUR:,.0f}",
                            }
                            if capex_inc_enabled and s.capex_incentive:
                                row[f"CAPEX net ({capex_inc_nome})"] = (
                                    f"€ {s.capex_incentive.capex_netto:,.0f}"
                                )
                                row[f"Payback w/ {capex_inc_nome}"] = (
                                    f"{s.payback_con_capex_inc:.1f} yr"
                                )
                                row[f"NPV w/ {capex_inc_nome}"] = f"€ {s.npv_con_capex_inc:,.0f}"
                            if tee_enabled and s.tee:
                                row["TEP/yr"] = f"{s.tee.tep_risparmiati_anno:,.1f}"
                                row["TEE eligible"] = (
                                    "Yes" if s.tee.sopra_soglia else "No (<10 TEP)"
                                )
                                row["Payback w/ TEE"] = f"{s.payback_con_tee:.1f} yr"
                                row["NPV w/ TEE"] = f"€ {s.npv_con_tee:,.0f}"
                            if capex_inc_enabled and tee_enabled and s.npv_combinato is not None:
                                row["Payback combined"] = f"{s.payback_combinato:.1f} yr"
                                row["NPV combined"] = f"€ {s.npv_combinato:,.0f}"
                            inc_rows.append(row)

                        st.dataframe(
                            pd.DataFrame(inc_rows),
                            use_container_width=True,
                            hide_index=True,
                        )

                        # Aggregate metrics — best scenario
                        # Determine which incentive scenario to show in metrics
                        if capex_inc_enabled and tee_enabled:
                            # Combinato
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
                            label = f"{capex_inc_nome} + TEE"
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
                            label = capex_inc_nome
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
                            label = "TEE"

                        ct1, ct2 = st.columns(2)
                        ct1.metric(
                            f"Best payback w/ {label}",
                            f"{best_pb:.1f} yr",
                            delta=f"{best_pb - best.payback_years:+.1f} yr",
                        )
                        ct2.metric(
                            f"Total NPV w/ {label}",
                            f"€ {total_npv_inc:,.0f}",
                            delta=f"€ {total_npv_inc - total_npv:+,.0f}",
                        )

                        # Notes
                        if tee_enabled:
                            from heatscout.knowledge.incentives import (
                                TEE_DATA_AGGIORNAMENTO,
                                TEE_SOGLIA_MINIMA_TEP,
                            )

                            st.caption(
                                f"TEE: DM MASE 21/07/2025 — Min. {TEE_SOGLIA_MINIMA_TEP:.0f} TEP/yr — "
                                f"7 yr duration — Updated {TEE_DATA_AGGIORNAMENTO}"
                            )

                    # ── SENSITIVITY ANALYSIS ─────────────────────────────
                    st.divider()
                    st.markdown("#### Sensitivity Analysis — Energy Price")

                    import plotly.graph_objects as go

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
                                line=dict(color="#ff6b35", width=2),
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
                            xaxis_title="Energy price (€/kWh)",
                            yaxis_title="Payback (years)",
                            template="plotly_dark",
                            height=350,
                            margin=dict(t=40, b=40),
                        )
                        st.plotly_chart(fig_pb, use_container_width=True)

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
                            xaxis_title="Energy price (€/kWh)",
                            yaxis_title=f"NPV {horizon_years}yr (€)",
                            template="plotly_dark",
                            height=350,
                            margin=dict(t=40, b=40),
                        )
                        st.plotly_chart(fig_npv, use_container_width=True)

                    st.caption(
                        f"Sensitivity on best project ({best.tech_recommendation.technology.name}) — "
                        f"Energy price ±50% around € {energy_price:.3f}/kWh"
                    )

                    # ── TORNADO CHART ─────────────────────────────────
                    st.divider()
                    st.markdown("#### Tornado Chart — NPV Sensitivity (±20%)")
                    st.caption(
                        "One-at-a-time: each parameter varied ±20% while others held constant."
                    )

                    from heatscout.core.sensitivity import tornado_analysis

                    tornado_bars = tornado_analysis(
                        best,
                        base_price=energy_price,
                        variation_pct=20.0,
                        discount_rate=discount_rate,
                        years=horizon_years,
                    )

                    # Build horizontal bar chart
                    fig_tornado = go.Figure()
                    param_names = [b.param_name for b in tornado_bars]
                    base = tornado_bars[0].base_npv

                    # Low bars (negative impact relative to base)
                    fig_tornado.add_trace(
                        go.Bar(
                            y=param_names,
                            x=[b.npv_low - base for b in tornado_bars],
                            orientation="h",
                            name="−20%",
                            marker_color="#f85149",
                            customdata=[b.npv_low for b in tornado_bars],
                            hovertemplate="%{y}: NPV = € %{customdata:,.0f}<extra>−20%</extra>",
                        )
                    )
                    # High bars (positive impact relative to base)
                    fig_tornado.add_trace(
                        go.Bar(
                            y=param_names,
                            x=[b.npv_high - base for b in tornado_bars],
                            orientation="h",
                            name="+20%",
                            marker_color="#3fb950",
                            customdata=[b.npv_high for b in tornado_bars],
                            hovertemplate="%{y}: NPV = € %{customdata:,.0f}<extra>+20%</extra>",
                        )
                    )

                    fig_tornado.add_vline(x=0, line_color="#8b949e", line_width=1)
                    fig_tornado.update_layout(
                        title=f"NPV Impact (base: € {base:,.0f})",
                        xaxis_title="ΔNPV from base (€)",
                        template="plotly_dark",
                        height=300,
                        margin=dict(t=40, b=40, l=120),
                        barmode="overlay",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    st.plotly_chart(fig_tornado, use_container_width=True)

                else:
                    st.info(
                        "No economic results available. Verify that there are HOT_WASTE streams with compatible technologies."
                    )

            # ── TAB REPORT ────────────────────────────────────────────────
            with tab_report:
                if all_econ_results:
                    from heatscout.report.executive_summary import (
                        generate_executive_summary,
                    )
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
                                label="📥 Download PDF Report",
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
                                label="📊 Download Excel",
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
                            label="💾 Save Analysis",
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
                "Report it on [GitHub Issues](https://github.com/cesabici-bit/heatscout/issues) "
                "including the parameters you entered."
            )

# ── Methodology ──────────────────────────────────────────────────────────────

st.divider()
st.markdown("## 📖 Methodology & Sources")
st.caption(
    "HeatScout uses published correlations and models. "
    "All sources are cited below. CAPEX ±30%, savings ±15%."
)

with st.expander("Efficiency Models"):
    st.markdown(
        """**Heat Exchanger Effectiveness (ε)**
- Gas-gas: ε = 0.62 (range 0.50–0.75)
- Gas-liquid: ε = 0.68 (range 0.55–0.80)
- Liquid-liquid: ε = 0.75 (range 0.60–0.85)
- Adjustments: +0.05 if ΔT > 200°C, −0.05 if ΔT < 30°C
- *Source: Incropera, Fundamentals of Heat and Mass Transfer, Ch. 11*

**Heat Pump COP**
- COP = η_Carnot × T_sink / (T_sink − T_source), η_Carnot = 0.45
- Bounds: 1.5 ≤ COP ≤ 6.0
- *Source: ASHRAE Handbook, HVAC Systems and Equipment, Ch. 8*

**ORC Electrical Efficiency**
- η = 0.45 × (1 − T_sink/T_source), bounds: 0–25%
- *Source: Quoilin et al., Renewable & Sustainable Energy Reviews, 2013*

**Combustion Air Preheating**
- Savings = (T_air_out − T_air_in) / T_flame × 100%, T_flame = 1800°C
- *Source: Baukal, Industrial Combustion Pollution and Control, Ch. 6*"""
    )

with st.expander("CAPEX Correlations"):
    st.markdown("**General formula:** `CAPEX = a × Q^b` [€], Q in kW")
    st.markdown("")
    capex_data = [
        ["Gas-gas HX", "800", "0.80", "500–1,200", "3%", "1.5", "Thekdi & Belt, ACEEE (2011)"],
        ["Economizer", "600", "0.78", "400–900", "3%", "1.5", "Cleaver-Brooks + literature"],
        [
            "Liquid-liquid HX",
            "400",
            "0.75",
            "250–600",
            "2%",
            "1.3",
            "Alfa Laval + Perry's Handbook",
        ],
        ["HRSG", "1,500", "0.80", "1,000–2,000", "4%", "1.8", "Ganapathy (2003)"],
        [
            "Heat pump (air)",
            "600",
            "0.85",
            "450–800",
            "3%",
            "1.4",
            "IEA HPT Annex 48",
        ],
        [
            "Heat pump (water)",
            "550",
            "0.85",
            "400–750",
            "3%",
            "1.4",
            "IEA HPT Annex 48",
        ],
        ["ORC", "3,000", "0.75", "2,200–4,000", "5%", "1.6", "Quoilin et al. (2013)"],
        [
            "Air preheater",
            "300",
            "0.80",
            "200–450",
            "2%",
            "1.4",
            "Baukal (2004)",
        ],
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

| Technology | T range (°C) | Q range (kW) | Lifetime |
|---|---|---|---|
| Gas-gas HX | 80–800 | 10–5,000 | 15 yr |
| Economizer | 60–600 | 10–5,000 | 15 yr |
| Liquid-liquid HX | 20–200 | 5–5,000 | 20 yr |
| HRSG | 200–800 | 100–50,000 | 20 yr |
| Heat pump (air) | 15–80 | 5–1,000 | 15 yr |
| Heat pump (water) | 15–90 | 5–2,000 | 15 yr |
| ORC | 80–500 | 50–10,000 | 20 yr |
| Air preheater | 150–800 | 10–5,000 | 15 yr |

Technologies outside their valid range are not recommended."""
    )

with st.expander("Uncertainty & Limitations"):
    st.markdown(
        """| Item | Uncertainty | Notes |
|---|---|---|
| CAPEX | ±30% | Min/max range on coefficient 'a' |
| Savings | ±15% | Efficiency model uncertainty |
| Payback | ±50% | Compounds CAPEX + savings uncertainty |
| COP / efficiency | Model-dependent | Simplified first-order models |

**Key limitations:**
- Correlations are from 2003–2026 literature; actual costs depend on market conditions
- Installation factor is an average — site-specific conditions may vary significantly
- Heat pump COP assumes ideal Carnot fraction (η=0.45) — actual COP depends on refrigerant and design
- ORC efficiency is for commercial modules — custom designs may differ
- This tool is for **screening only** — always commission a detailed feasibility study before investing"""
    )

with st.expander("Bibliography"):
    st.markdown(
        """1. Thekdi, A. & Belt, R. (2011). *Waste Heat Recovery*. ACEEE
2. Ganapathy, V. (2003). *Waste Heat Boiler Deskbook*. Fairmont Press
3. Quoilin, S. et al. (2013). *Techno-economic survey of ORC systems*. Ren. & Sust. Energy Rev., 17, 168–186
4. Incropera, F.P. et al. *Fundamentals of Heat and Mass Transfer*. Ch. 11
5. ASHRAE (2021). *Handbook: HVAC Systems and Equipment*. Ch. 8
6. Baukal, C.E. (2004). *Industrial Combustion Pollution and Control*. Ch. 6
7. Perry's Chemical Engineers' Handbook (8th Ed.). Table 11-13
8. IEA HPT Annex 48. Industrial Heat Pump Market Survey
9. ARERA Delibera EEN 3/08 (TEP conversion)
10. DM MASE 21/07/2025 (White Certificates decree, art. 6–7)"""
    )

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    """
<div class="footer">
    <strong>HeatScout</strong> · Industrial heat recovery analysis · Open Source (MIT)<br>
    <a href="https://github.com/cesabici-bit/heatscout">GitHub</a> ·
    <a href="https://github.com/cesabici-bit/heatscout/issues">Report an issue</a>
</div>
""",
    unsafe_allow_html=True,
)
