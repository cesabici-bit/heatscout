"""Grafici di confronto economico per le raccomandazioni tecnologiche."""

from __future__ import annotations

import plotly.graph_objects as go

from heatscout.core.economics import EconomicResult


def capex_comparison_chart(results: list[EconomicResult]) -> go.Figure:
    """Bar chart confronto CAPEX per tecnologia."""
    names = [r.tech_recommendation.technology.name for r in results]
    capex_mid = [r.capex_EUR for r in results]
    capex_min = [r.capex_min_EUR for r in results]
    capex_max = [r.capex_max_EUR for r in results]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names,
        y=capex_mid,
        name="CAPEX medio",
        marker_color="steelblue",
        error_y=dict(
            type="data",
            symmetric=False,
            array=[mx - mid for mx, mid in zip(capex_max, capex_mid)],
            arrayminus=[mid - mn for mid, mn in zip(capex_mid, capex_min)],
        ),
    ))
    fig.update_layout(
        title="Confronto CAPEX per tecnologia",
        yaxis_title="CAPEX (EUR)",
        xaxis_tickangle=-30,
        height=400,
    )
    return fig


def payback_comparison_chart(results: list[EconomicResult]) -> go.Figure:
    """Bar chart confronto payback per tecnologia."""
    names = [r.tech_recommendation.technology.name for r in results]
    payback = [min(r.payback_years, 20) for r in results]  # Cap a 20 per visualizzazione

    colors = ["green" if p < 5 else "orange" if p < 8 else "red" for p in payback]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names,
        y=payback,
        marker_color=colors,
        text=[f"{p:.1f} anni" for p in payback],
        textposition="outside",
    ))
    fig.update_layout(
        title="Confronto Payback per tecnologia",
        yaxis_title="Payback (anni)",
        xaxis_tickangle=-30,
        height=400,
    )
    # Linea soglia a 5 anni
    fig.add_hline(y=5, line_dash="dash", line_color="gray",
                  annotation_text="Soglia 5 anni", annotation_position="top right")
    return fig


def npv_comparison_chart(results: list[EconomicResult]) -> go.Figure:
    """Bar chart confronto NPV per tecnologia."""
    names = [r.tech_recommendation.technology.name for r in results]
    npv = [r.npv_EUR for r in results]

    colors = ["green" if n > 0 else "red" for n in npv]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names,
        y=npv,
        marker_color=colors,
        text=[f"€ {n:,.0f}" for n in npv],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"NPV a {results[0].horizon_years} anni per tecnologia" if results else "NPV",
        yaxis_title="NPV (EUR)",
        xaxis_tickangle=-30,
        height=400,
    )
    fig.add_hline(y=0, line_color="black", line_width=1)
    return fig


def cumulative_cashflow_chart(result: EconomicResult) -> go.Figure:
    """Grafico cashflow cumulativo per una singola tecnologia (break-even visuale)."""
    years = list(range(len(result.cumulative_cashflows)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years,
        y=result.cumulative_cashflows,
        mode="lines+markers",
        name="Cashflow cumulativo",
        line=dict(color="steelblue", width=2),
        fill="tozeroy",
        fillcolor="rgba(70, 130, 180, 0.1)",
    ))
    fig.add_hline(y=0, line_color="black", line_width=1, line_dash="dash")

    tech_name = result.tech_recommendation.technology.name
    fig.update_layout(
        title=f"Cashflow Cumulativo — {tech_name}",
        xaxis_title="Anno",
        yaxis_title="EUR cumulativo",
        height=400,
    )
    return fig


def do_nothing_comparison(results: list[EconomicResult], years: int = 10) -> go.Figure:
    """Confronto costo 'fare' vs 'non fare' a N anni."""
    if not results:
        return go.Figure()

    # Prendi la miglior tecnologia (primo risultato, gia ordinato per savings)
    best = results[0]

    # Costo "non fare" = energia sprecata in N anni
    cost_nothing = best.tech_recommendation.savings_EUR * years

    # Costo "fare" = investimento - risparmi + opex in N anni
    cost_doing = best.total_investment_EUR - (best.net_annual_benefit_EUR * years)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Non intervenire", f"Investire ({best.tech_recommendation.technology.name})"],
        y=[cost_nothing, max(cost_doing, 0)],
        marker_color=["red", "green"],
        text=[f"€ {cost_nothing:,.0f}", f"€ {max(cost_doing, 0):,.0f}"],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Costo a {years} anni: fare vs non fare",
        yaxis_title="Costo netto (EUR)",
        height=400,
    )
    return fig
