"""HeatScout UI — CSS design system.

Extracted from inline CSS. Uses glassmorphism cards, teal-green accent (#00D4AA),
dark theme (#0d1117 / #161b22), and subtle animations (slideUp, fadeScale).
"""

ACCENT = "#00D4AA"
ACCENT_RGB = "0, 212, 170"
BG_PRIMARY = "#0d1117"
BG_SECONDARY = "#161b22"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
BORDER = "#30363d"
BORDER_LIGHT = "#21262d"

CSS = f"""
<style>
/* ── Hide Streamlit chrome ───────────────────────────────────────── */
#MainMenu, footer, header {{visibility: hidden;}}
[data-testid="stToolbar"] {{display: none;}}

/* ── Hero container ──────────────────────────────────────────────── */
.hero-container {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    color: white;
    position: relative;
    overflow: hidden;
}}
.hero-container::before {{
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba({ACCENT_RGB},0.15) 0%, transparent 70%);
    border-radius: 50%;
}}
.hero-title {{
    font-size: 2.8rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.5px;
}}
.hero-subtitle {{
    font-size: 1.15rem;
    opacity: 0.85;
    margin-top: 0.5rem;
    font-weight: 300;
}}
.hero-badge {{
    display: inline-block;
    background: rgba({ACCENT_RGB},0.15);
    border: 1px solid rgba({ACCENT_RGB},0.4);
    color: {ACCENT};
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-top: 0.75rem;
    position: relative;
    overflow: hidden;
}}
.hero-badge::after {{
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    animation: shimmer 3s ease-in-out infinite;
}}
@keyframes shimmer {{
    0% {{ left: -100%; }}
    50% {{ left: 100%; }}
    100% {{ left: 100%; }}
}}

/* ── Dark theme base ─────────────────────────────────────────────── */
.stApp {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
}}
.stApp header {{
    background-color: {BG_PRIMARY} !important;
}}
.stApp, .stApp p, .stApp span, .stApp li, .stApp td, .stApp th,
.stApp label, .stApp div, .stApp strong, .stApp em, .stApp a,
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5,
.stMarkdown strong, .stMarkdown em, .stMarkdown a,
.stMarkdown blockquote, .stMarkdown blockquote p,
.stMarkdown code, .stMarkdown pre,
[data-testid="stText"], [data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] span {{
    color: {TEXT_PRIMARY} !important;
}}
[data-testid="stCaptionContainer"] * {{
    color: {TEXT_SECONDARY} !important;
}}
.stRadio label, .stCheckbox label, .stSelectbox label,
.stTextInput label, .stNumberInput label,
.stRadio > div > label, .stRadio div[role="radiogroup"] label,
[data-baseweb="radio"] span,
.stSlider label {{
    color: {TEXT_PRIMARY} !important;
}}
.stTooltipIcon, small, .stApp small {{
    color: {TEXT_SECONDARY} !important;
}}
.stMarkdown blockquote {{
    border-left-color: {ACCENT} !important;
}}
.stTabs [data-baseweb="tab-panel"],
.stTabs [data-baseweb="tab-panel"] p,
.stTabs [data-baseweb="tab-panel"] span,
.stTabs [data-baseweb="tab-panel"] li,
.stTabs [data-baseweb="tab-panel"] td {{
    color: {TEXT_PRIMARY} !important;
}}

/* ── Inputs — dark ───────────────────────────────────────────────── */
.stTextInput input, .stNumberInput input,
.stSelectbox [data-baseweb="select"] span,
[data-baseweb="select"] .css-1dimb5e-singleValue,
[data-baseweb="input"] input {{
    color: {TEXT_PRIMARY} !important;
    background-color: {BG_SECONDARY} !important;
}}
[data-baseweb="select"] > div,
[data-baseweb="input"] {{
    background-color: {BG_SECONDARY} !important;
}}
.stTextInput > div > div, .stNumberInput > div > div,
.stSelectbox > div > div {{
    background-color: {BG_SECONDARY} !important;
    border-color: {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
}}
.stNumberInput button {{
    color: {TEXT_PRIMARY} !important;
    background-color: {BG_PRIMARY} !important;
    border: 1.5px solid {TEXT_PRIMARY} !important;
    transition: all 0.2s ease !important;
}}
.stNumberInput button:hover {{
    color: {BG_PRIMARY} !important;
    background-color: {TEXT_PRIMARY} !important;
}}

/* ── KPI / Metric cards — glassmorphism ──────────────────────────── */
div[data-testid="stMetric"] {{
    background: rgba(22, 27, 34, 0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba({ACCENT_RGB}, 0.15);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    animation: slideUp 0.6s ease-out both;
}}
div[data-testid="stMetric"]:nth-child(1) {{ animation-delay: 0s; }}
div[data-testid="stMetric"]:nth-child(2) {{ animation-delay: 0.1s; }}
div[data-testid="stMetric"]:nth-child(3) {{ animation-delay: 0.2s; }}
div[data-testid="stMetric"]:nth-child(4) {{ animation-delay: 0.3s; }}
div[data-testid="stMetric"]:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 32px rgba({ACCENT_RGB},0.15);
    border-color: rgba({ACCENT_RGB}, 0.4);
}}
div[data-testid="stMetric"] label {{
    font-weight: 600 !important;
    color: {TEXT_SECONDARY} !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: #f0f6fc !important;
}}

/* ── Impact banner ───────────────────────────────────────────────── */
.impact-banner {{
    background: rgba(22, 27, 34, 0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-left: 4px solid {ACCENT};
    border-radius: 0 16px 16px 0;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0;
    animation: slideRight 0.7s ease-out both;
    animation-delay: 0.2s;
}}
.impact-banner p {{
    margin: 0;
    font-size: 1.05rem;
    color: {TEXT_PRIMARY};
}}

/* ── Section headers ─────────────────────────────────────────────── */
.section-header {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0;
    margin-top: 1.5rem;
    border-bottom: 2px solid {BORDER_LIGHT};
    margin-bottom: 1rem;
}}
.section-header h2 {{
    margin: 0;
    font-weight: 700;
    color: #f0f6fc !important;
}}

/* ── Temperature class cards ─────────────────────────────────────── */
.temp-card {{
    border-radius: 16px;
    padding: 1.25rem;
    text-align: center;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: transform 0.2s ease;
}}
.temp-card:hover {{ transform: scale(1.02); }}
.temp-alta {{ background: linear-gradient(135deg, #3b1012, #4a1518); border: 1px solid #7f1d1d; }}
.temp-media {{ background: linear-gradient(135deg, #3b2508, #4a2e0a); border: 1px solid #92400e; }}
.temp-bassa {{ background: linear-gradient(135deg, #3b3508, #4a420a); border: 1px solid #854d0e; }}
.temp-card .temp-label {{ font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem; color: {TEXT_PRIMARY}; }}
.temp-card .temp-value {{ font-size: 1.5rem; font-weight: 800; color: #f0f6fc; }}
.temp-card .temp-detail {{ font-size: 0.85rem; color: {TEXT_SECONDARY}; margin-top: 0.25rem; }}

/* ── Sidebar ─────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {BG_SECONDARY} 0%, {BG_PRIMARY} 100%);
    border-right: 1px solid {BORDER_LIGHT};
}}
section[data-testid="stSidebar"] .stButton > button {{
    border-radius: 8px;
    color: {TEXT_PRIMARY} !important;
    background-color: {BG_PRIMARY} !important;
    border: 1.5px solid {TEXT_PRIMARY} !important;
    transition: all 0.2s ease !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    color: {BG_PRIMARY} !important;
    background-color: {TEXT_PRIMARY} !important;
}}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h3 {{
    color: {TEXT_PRIMARY} !important;
}}

/* ── Expanders ───────────────────────────────────────────────────── */
.streamlit-expanderHeader, [data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span {{
    color: {TEXT_PRIMARY} !important;
    background-color: {BG_SECONDARY} !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    background-color: {BG_PRIMARY} !important;
}}
.streamlit-expanderHeader {{
    font-weight: 600 !important;
    font-size: 1rem !important;
    border-color: {BORDER} !important;
}}
details[data-testid="stExpander"] {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
}}

/* ── Tabs ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {BG_SECONDARY};
    border-radius: 8px;
    padding: 4px;
    gap: 8px;
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT_SECONDARY} !important;
    border-radius: 8px 8px 0 0;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
}}
.stTabs [aria-selected="true"] {{
    color: {ACCENT} !important;
}}

/* ── Dataframe ───────────────────────────────────────────────────── */
.stDataFrame {{ border: 1px solid {BORDER}; border-radius: 8px; }}
.stDataFrame td, .stDataFrame th,
[data-testid="stDataFrame"] td,
[data-testid="stDataFrame"] th {{
    color: {TEXT_PRIMARY} !important;
}}

/* ── Buttons ─────────────────────────────────────────────────────── */
.stButton > button {{
    color: {TEXT_PRIMARY} !important;
    background-color: {BG_PRIMARY} !important;
    border: 1.5px solid {TEXT_PRIMARY} !important;
    transition: all 0.2s ease !important;
}}
.stButton > button:hover {{
    color: {BG_PRIMARY} !important;
    background-color: {TEXT_PRIMARY} !important;
    border-color: {TEXT_PRIMARY} !important;
}}
.stButton > button[kind="primary"] {{
    border-radius: 12px !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    padding: 0.75rem !important;
    letter-spacing: 0.5px;
    border-color: {ACCENT} !important;
}}
.stDownloadButton button {{
    color: {TEXT_PRIMARY} !important;
    background-color: {BG_PRIMARY} !important;
    border: 1.5px solid {TEXT_PRIMARY} !important;
    transition: all 0.2s ease !important;
}}
.stDownloadButton button:hover {{
    color: {BG_PRIMARY} !important;
    background-color: {TEXT_PRIMARY} !important;
}}

/* ── Alert boxes ─────────────────────────────────────────────────── */
.stAlert {{ border-radius: 10px !important; }}
.stApp [data-testid="stNotification"],
.stApp [data-testid="stNotification"] *,
.stApp .stAlert, .stApp .stAlert *,
.stApp [role="alert"], .stApp [role="alert"] *,
.stApp [role="alert"] p, .stApp [role="alert"] span,
.stApp [role="alert"] strong, .stApp [role="alert"] a,
.stApp [role="alert"] div {{
    color: {TEXT_PRIMARY} !important;
}}

/* ── Footer ──────────────────────────────────────────────────────── */
.footer {{
    text-align: center;
    color: #484f58;
    font-size: 0.8rem;
    padding: 2rem 0 1rem 0;
    border-top: 1px solid {BORDER_LIGHT};
    margin-top: 3rem;
}}
.footer a {{ color: {TEXT_SECONDARY}; text-decoration: none; }}
.footer a:hover {{ color: {ACCENT}; }}

/* ── Animations (subtle only) ────────────────────────────────────── */
@keyframes slideUp {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeScale {{
    from {{ opacity: 0; transform: scale(0.92); }}
    to   {{ opacity: 1; transform: scale(1); }}
}}
@keyframes slideRight {{
    from {{ opacity: 0; transform: translateX(-30px); }}
    to   {{ opacity: 1; transform: translateX(0); }}
}}
.temp-card {{ animation: fadeScale 0.5s ease-out both; }}
.temp-alta {{ animation-delay: 0s; }}
.temp-media {{ animation-delay: 0.15s; }}
.temp-bassa {{ animation-delay: 0.3s; }}

/* ── Global hover override (max specificity) ─────────────────────── */
.stApp .stButton > button:hover,
.stApp .stButton > button:focus,
.stApp .stButton > button:active,
.stApp section[data-testid="stSidebar"] .stButton > button:hover,
.stApp section[data-testid="stSidebar"] .stButton > button:focus,
.stApp .stDownloadButton button:hover,
.stApp .stDownloadButton button:focus,
.stApp .stNumberInput button:hover,
.stApp .stNumberInput button:focus {{
    color: {BG_PRIMARY} !important;
    background-color: {TEXT_PRIMARY} !important;
    border-color: {TEXT_PRIMARY} !important;
}}
</style>
"""
