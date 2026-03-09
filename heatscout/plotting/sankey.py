"""Diagramma Sankey per bilancio termico di fabbrica."""

from __future__ import annotations

import plotly.graph_objects as go

from heatscout.core.heat_balance import FactoryHeatBalance


def _temperature_color(T_mean: float) -> str:
    """Colore basato sulla temperatura media dello stream."""
    if T_mean > 250:
        return "rgba(220, 50, 50, 0.7)"  # rosso — alta T
    elif T_mean >= 80:
        return "rgba(240, 140, 40, 0.7)"  # arancione — media T
    else:
        return "rgba(240, 200, 50, 0.7)"  # giallo — bassa T


def create_sankey(heat_balance: FactoryHeatBalance, factory_name: str = "") -> go.Figure:
    """Crea diagramma Sankey del bilancio termico.

    Struttura:
      Input Energia → Processo Utile
      Input Energia → Scarto 1 (hot_waste)
      Input Energia → Scarto 2 (hot_waste)
      ...
      Input Energia → Perdite varie

    Args:
        heat_balance: FactoryHeatBalance calcolato
        factory_name: Nome da mostrare nel titolo

    Returns:
        Plotly Figure con Sankey interattivo
    """
    summary = heat_balance.summary()
    stream_results = [r for r in summary["stream_results"] if r["stream_type"] == "hot_waste"]

    if not stream_results:
        fig = go.Figure()
        fig.add_annotation(text="Nessuno stream di scarto da visualizzare", showarrow=False)
        return fig

    total_waste_kW = summary["total_waste_kW"]

    # Stima input energetico se non disponibile
    energy_input_kW = summary.get("energy_input_kW")
    if energy_input_kW is None or energy_input_kW <= 0:
        # Stima: scarto = 15-20% dell'input → input = scarto / 0.15
        heat_balance.estimate_energy_input(efficiency=0.85)
        summary = heat_balance.summary()
        energy_input_kW = summary["energy_input_kW"]

    # Calcola "processo utile" = input - scarti - perdite stimate
    losses_kW = energy_input_kW * 0.05  # 5% perdite varie
    useful_kW = energy_input_kW - total_waste_kW - losses_kW
    if useful_kW < 0:
        useful_kW = 0
        losses_kW = energy_input_kW - total_waste_kW

    # ── Costruzione nodi e link ──────────────────────────────────────────
    # Nodo 0: Input Energia
    # Nodo 1: Processo Utile
    # Nodo 2+: Scarti individuali
    # Ultimo nodo: Perdite varie

    labels = ["Input Energia", "Processo Utile"]
    node_colors = [
        "rgba(100, 100, 200, 0.8)",  # Input: blu
        "rgba(60, 180, 75, 0.8)",  # Utile: verde
    ]

    for r in stream_results:
        labels.append(f"Scarto: {r['name']}")
        node_colors.append(_temperature_color(r["T_mean"]))

    # Aggiungi nodo perdite
    labels.append("Perdite varie")
    node_colors.append("rgba(180, 180, 180, 0.6)")

    # Link: tutti partono dal nodo 0 (Input Energia)
    sources = []
    targets = []
    values = []
    link_colors = []

    # Input → Processo Utile
    if useful_kW > 0:
        sources.append(0)
        targets.append(1)
        values.append(round(useful_kW, 1))
        link_colors.append("rgba(60, 180, 75, 0.4)")

    # Input → ciascun scarto
    for i, r in enumerate(stream_results):
        sources.append(0)
        targets.append(2 + i)
        values.append(r["Q_kW"])
        link_colors.append(_temperature_color(r["T_mean"]).replace("0.7", "0.4"))

    # Input → Perdite
    if losses_kW > 0:
        sources.append(0)
        targets.append(len(labels) - 1)
        values.append(round(losses_kW, 1))
        link_colors.append("rgba(180, 180, 180, 0.3)")

    # ── Etichette personalizzate ─────────────────────────────────────────
    custom_labels = [f"{labels[0]}<br>{energy_input_kW:,.0f} kW"]
    custom_labels.append(
        f"{labels[1]}<br>{useful_kW:,.0f} kW ({useful_kW / energy_input_kW * 100:.0f}%)"
    )
    for r in stream_results:
        pct = r["Q_kW"] / energy_input_kW * 100
        custom_labels.append(
            f"Scarto: {r['name']}<br>{r['Q_kW']:,.0f} kW ({pct:.1f}%)<br>{r['T_class'].capitalize()} T"
        )
    custom_labels.append(f"Perdite<br>{losses_kW:,.0f} kW")

    # ── Creazione figura ─────────────────────────────────────────────────
    title = factory_name or heat_balance.factory_name or "Bilancio Termico"

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=20,
                    thickness=30,
                    line=dict(color="black", width=0.5),
                    label=custom_labels,
                    color=node_colors,
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=link_colors,
                ),
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b> — Bilancio Energetico",
            font=dict(size=18),
        ),
        font=dict(size=12),
        height=500,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    return fig
