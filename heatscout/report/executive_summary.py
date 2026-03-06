"""Generazione automatica dell'Executive Summary."""

from __future__ import annotations

from heatscout.core.economics import EconomicResult


def generate_executive_summary(
    summary: dict,
    econ_results: list[EconomicResult],
    energy_price: float = 0.08,
) -> str:
    """Genera il testo dell'Executive Summary.

    Args:
        summary: Output di FactoryHeatBalance.summary()
        econ_results: Lista di EconomicResult per le tecnologie selezionate
        energy_price: Prezzo energia EUR/kWh

    Returns:
        Testo strutturato per l'executive summary
    """
    factory = summary.get("factory_name", "Impianto")
    total_waste_kW = summary["total_waste_kW"]
    total_waste_MWh = summary["total_waste_MWh_anno"]
    waste_pct = summary.get("waste_pct_of_input")
    n_streams = summary["n_hot_waste"]

    cost_waste = total_waste_MWh * 1000 * energy_price

    lines = []
    lines.append(f"EXECUTIVE SUMMARY — {factory}")
    lines.append("=" * 60)
    lines.append("")

    # Situazione attuale
    lines.append("SITUAZIONE ATTUALE")
    lines.append("-" * 40)
    pct_str = f" ({waste_pct:.0f}% dell'input energetico)" if waste_pct else ""
    lines.append(
        f"L'impianto disperde {total_waste_kW:,.0f} kW di calore{pct_str} "
        f"attraverso {n_streams} flussi termici di scarto."
    )
    lines.append(
        f"Questo equivale a {total_waste_MWh:,.0f} MWh/anno di energia termica "
        f"non utilizzata, con un costo opportunita' di circa EUR {cost_waste:,.0f}/anno."
    )
    lines.append("")

    # Breakdown per classe
    by_class = summary["by_temperature_class"]
    for cls, label in [("alta", "Alta T (>250°C)"), ("media", "Media T (80-250°C)"), ("bassa", "Bassa T (<80°C)")]:
        data = by_class[cls]
        if data["count"] > 0:
            lines.append(
                f"  - {label}: {data['count']} stream, {data['Q_kW']:,.0f} kW ({data['pct_of_waste']:.0f}%)"
            )
    lines.append("")

    if econ_results:
        # Migliore intervento
        best = min(econ_results, key=lambda e: e.payback_years)
        total_capex = sum(e.total_investment_EUR for e in econ_results)
        total_savings = sum(e.annual_savings_EUR for e in econ_results)
        total_npv = sum(e.npv_EUR for e in econ_results)

        lines.append("INTERVENTO RACCOMANDATO")
        lines.append("-" * 40)
        lines.append(
            f"L'intervento piu' conveniente e' l'installazione di un "
            f"{best.tech_recommendation.technology.name} "
            f"sullo stream '{best.tech_recommendation.stream_name}', "
            f"con un payback di {best.payback_years:.1f} anni."
        )
        lines.append("")
        lines.append(
            f"  - Investimento: EUR {best.total_investment_EUR:,.0f}")
        lines.append(
            f"  - Risparmio annuo: EUR {best.annual_savings_EUR:,.0f}")
        lines.append(
            f"  - NPV a {best.horizon_years} anni: EUR {best.npv_EUR:,.0f}")
        if best.irr_pct:
            lines.append(f"  - IRR: {best.irr_pct:.1f}%")
        lines.append("")

        if len(econ_results) > 1:
            lines.append("QUADRO COMPLESSIVO")
            lines.append("-" * 40)
            lines.append(f"  - Investimento totale (tutte le tecnologie): EUR {total_capex:,.0f}")
            lines.append(f"  - Risparmio annuo totale: EUR {total_savings:,.0f}")
            lines.append(f"  - NPV complessivo a 10 anni: EUR {total_npv:,.0f}")
            lines.append("")

        # Costo del non-intervento
        cost_10y = cost_waste * 10
        lines.append("COSTO DEL NON-INTERVENTO")
        lines.append("-" * 40)
        lines.append(
            f"NON intervenire costa EUR {cost_10y:,.0f} in 10 anni di energia sprecata."
        )
        lines.append("")

    lines.append("NOTA: Le stime hanno un'incertezza indicativa di +/-30% sul CAPEX")
    lines.append("e +/-15% sui risparmi annui. Si raccomanda uno studio di fattibilita'")
    lines.append("dettagliato prima di procedere con l'investimento.")

    return "\n".join(lines)
