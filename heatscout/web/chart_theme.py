"""HeatScout UI — Shared Plotly dark chart theme.

Provides a layout dict for consistent dark-themed charts with
transparent backgrounds and teal-green accent color.
"""

ACCENT = "#00D4AA"

PLOTLY_DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e6edf3", size=12),
    xaxis=dict(
        gridcolor="rgba(139,148,158,0.15)",
        zerolinecolor="rgba(139,148,158,0.25)",
    ),
    yaxis=dict(
        gridcolor="rgba(139,148,158,0.15)",
        zerolinecolor="rgba(139,148,158,0.25)",
    ),
    margin=dict(t=40, b=40, l=60, r=20),
)
