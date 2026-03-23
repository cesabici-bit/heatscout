"""Pinch Analysis visualizations: Composite Curves and Grand Composite Curve."""

from __future__ import annotations

import plotly.graph_objects as go

from heatscout.core.pinch import PinchResult
from heatscout.web.chart_theme import ACCENT, PLOTLY_DARK_LAYOUT

# Colors
_HOT_COLOR = "rgba(220, 50, 50, 0.85)"
_HOT_FILL = "rgba(220, 50, 50, 0.08)"
_COLD_COLOR = "rgba(50, 120, 220, 0.85)"
_COLD_FILL = "rgba(50, 120, 220, 0.08)"
_PINCH_COLOR = "rgba(255, 255, 255, 0.5)"


def create_composite_curves(result: PinchResult) -> go.Figure:
    """Create T-H diagram with hot and cold composite curves.

    Args:
        result: PinchResult from pinch_analysis().

    Returns:
        Plotly Figure with hot (red) and cold (blue) composite curves,
        pinch point annotation, and utility targets.
    """
    fig = go.Figure()

    # Hot composite curve
    if result.hot_composite_T and result.hot_composite_H:
        fig.add_trace(
            go.Scatter(
                x=result.hot_composite_H,
                y=result.hot_composite_T,
                mode="lines+markers",
                name="Hot Composite",
                line=dict(color=_HOT_COLOR, width=3),
                marker=dict(size=6, color=_HOT_COLOR),
                fill="tozeroy",
                fillcolor=_HOT_FILL,
            )
        )

    # Cold composite curve
    if result.cold_composite_T and result.cold_composite_H:
        fig.add_trace(
            go.Scatter(
                x=result.cold_composite_H,
                y=result.cold_composite_T,
                mode="lines+markers",
                name="Cold Composite",
                line=dict(color=_COLD_COLOR, width=3),
                marker=dict(size=6, color=_COLD_COLOR),
                fill="tozeroy",
                fillcolor=_COLD_FILL,
            )
        )

    # Pinch point annotation
    # Find the pinch on the composite curves (where they're closest)
    _annotate_pinch(fig, result)

    # Utility annotations
    _annotate_utilities(fig, result)

    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title=dict(
            text=f"Composite Curves (ΔT<sub>min</sub> = {result.dT_min}°C)",
            font=dict(size=16),
        ),
        xaxis_title="Enthalpy [kW]",
        yaxis_title="Temperature [°C]",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="closest",
    )

    return fig


def create_grand_composite(result: PinchResult) -> go.Figure:
    """Create Grand Composite Curve (shifted T vs net heat flow).

    Args:
        result: PinchResult from pinch_analysis().

    Returns:
        Plotly Figure with GCC curve, pinch annotation, and utility regions.
    """
    fig = go.Figure()

    if result.gcc_T and result.gcc_H:
        fig.add_trace(
            go.Scatter(
                x=result.gcc_H,
                y=result.gcc_T,
                mode="lines+markers",
                name="Grand Composite",
                line=dict(color=ACCENT, width=3),
                marker=dict(size=6, color=ACCENT),
                fill="tozerox",
                fillcolor="rgba(0, 212, 170, 0.08)",
            )
        )

        # Pinch point (where GCC touches zero)
        min_H = min(result.gcc_H)
        min_idx = result.gcc_H.index(min_H)
        pinch_T = result.gcc_T[min_idx]

        fig.add_annotation(
            x=min_H,
            y=pinch_T,
            text=f"Pinch ({pinch_T:.0f}°C)",
            showarrow=True,
            arrowhead=2,
            arrowcolor=_PINCH_COLOR,
            font=dict(color="#e6edf3", size=12),
            bgcolor="rgba(13, 17, 23, 0.8)",
            bordercolor=ACCENT,
            borderwidth=1,
            ax=40,
            ay=-30,
        )

        # QH_min annotation at top
        if result.QH_min > 0.5:
            fig.add_annotation(
                x=result.gcc_H[0],
                y=result.gcc_T[0],
                text=f"Q<sub>H,min</sub> = {result.QH_min:.1f} kW",
                showarrow=True,
                arrowhead=2,
                arrowcolor=_HOT_COLOR,
                font=dict(color="#e6edf3", size=11),
                bgcolor="rgba(13, 17, 23, 0.8)",
                bordercolor=_HOT_COLOR,
                borderwidth=1,
                ax=50,
                ay=0,
            )

        # QC_min annotation at bottom
        if result.QC_min > 0.5:
            fig.add_annotation(
                x=result.gcc_H[-1],
                y=result.gcc_T[-1],
                text=f"Q<sub>C,min</sub> = {result.QC_min:.1f} kW",
                showarrow=True,
                arrowhead=2,
                arrowcolor=_COLD_COLOR,
                font=dict(color="#e6edf3", size=11),
                bgcolor="rgba(13, 17, 23, 0.8)",
                bordercolor=_COLD_COLOR,
                borderwidth=1,
                ax=50,
                ay=0,
            )

    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title=dict(
            text=f"Grand Composite Curve (ΔT<sub>min</sub> = {result.dT_min}°C)",
            font=dict(size=16),
        ),
        xaxis_title="Net Heat Flow [kW]",
        yaxis_title="Shifted Temperature [°C]",
        height=500,
        showlegend=False,
    )

    return fig


# ── Helpers ──────────────────────────────────────────────────────────────


def _annotate_pinch(fig: go.Figure, result: PinchResult) -> None:
    """Add pinch point annotation to composite curves figure."""
    # Pinch is where hot and cold composites are closest
    # Approximate: use pinch_T_hot on hot curve, pinch_T_cold on cold curve
    pinch_T_mid = (result.pinch_T_hot + result.pinch_T_cold) / 2

    # Find H at pinch on hot composite (interpolate)
    pinch_H = _interpolate_H_at_T(
        result.hot_composite_T, result.hot_composite_H, result.pinch_T_hot
    )
    if pinch_H is not None:
        fig.add_annotation(
            x=pinch_H,
            y=pinch_T_mid,
            text=(
                f"Pinch: {result.pinch_T_hot:.0f}°C / "
                f"{result.pinch_T_cold:.0f}°C"
            ),
            showarrow=True,
            arrowhead=2,
            arrowcolor=_PINCH_COLOR,
            font=dict(color="#e6edf3", size=12),
            bgcolor="rgba(13, 17, 23, 0.8)",
            bordercolor=ACCENT,
            borderwidth=1,
            ax=-60,
            ay=-30,
        )

        # Dashed vertical line at pinch
        fig.add_vline(
            x=pinch_H,
            line=dict(color=_PINCH_COLOR, width=1, dash="dash"),
        )


def _annotate_utilities(fig: go.Figure, result: PinchResult) -> None:
    """Add QH_min and QC_min annotations to composite curves."""
    if result.QH_min > 0.5 and result.cold_composite_T:
        # QH_min is the horizontal gap at the cold-end top
        fig.add_annotation(
            x=result.cold_composite_H[-1] / 2,
            y=max(result.cold_composite_T) + 5,
            text=f"Q<sub>H,min</sub> = {result.QH_min:.1f} kW",
            showarrow=False,
            font=dict(color=_HOT_COLOR, size=11),
            bgcolor="rgba(13, 17, 23, 0.7)",
        )

    if result.QC_min > 0.5 and result.hot_composite_T:
        fig.add_annotation(
            x=result.hot_composite_H[-1] / 2,
            y=min(result.hot_composite_T) - 5,
            text=f"Q<sub>C,min</sub> = {result.QC_min:.1f} kW",
            showarrow=False,
            font=dict(color=_COLD_COLOR, size=11),
            bgcolor="rgba(13, 17, 23, 0.7)",
        )


def _interpolate_H_at_T(
    T_list: list[float], H_list: list[float], T_target: float
) -> float | None:
    """Linear interpolation of H at a given T on a composite curve."""
    if not T_list or not H_list:
        return None

    for i in range(len(T_list) - 1):
        T_lo, T_hi = T_list[i], T_list[i + 1]
        if T_lo <= T_target <= T_hi:
            if T_hi == T_lo:
                return H_list[i]
            frac = (T_target - T_lo) / (T_hi - T_lo)
            return H_list[i] + frac * (H_list[i + 1] - H_list[i])

    # T_target outside range — return closest endpoint
    if T_target <= T_list[0]:
        return H_list[0]
    return H_list[-1]
