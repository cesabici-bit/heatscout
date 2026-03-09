"""Export analisi HeatScout in formato Excel (.xlsx).

Genera un file con 3 fogli:
1. Streams — dati termici di ogni stream
2. Technologies — raccomandazioni tecnologiche con CAPEX/risparmio
3. Economics — analisi economica con confronto incentivi
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from heatscout.core.economics import EconomicResult, IncentiveSummary


def export_to_excel(
    summary: dict,
    econ_results: list[EconomicResult],
    incentive_summaries: list[IncentiveSummary] | None = None,
    energy_price: float = 0.08,
) -> bytes:
    """Genera file Excel con i risultati dell'analisi.

    Args:
        summary: Output di FactoryHeatBalance.summary()
        econ_results: Lista di EconomicResult
        incentive_summaries: Lista di IncentiveSummary (opzionale)
        energy_price: Prezzo energia usato [€/kWh]

    Returns:
        Bytes del file .xlsx
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _write_streams_sheet(writer, summary)
        _write_technologies_sheet(writer, econ_results)
        _write_economics_sheet(writer, econ_results, incentive_summaries, energy_price)

    return output.getvalue()


def _write_streams_sheet(writer: pd.ExcelWriter, summary: dict) -> None:
    """Foglio 1: Stream termici."""
    rows = []
    for r in summary["stream_results"]:
        rows.append(
            {
                "Name": r["name"],
                "Type": r["stream_type"],
                "Fluid": r["fluid_type"],
                "T_in (°C)": r["T_in"],
                "T_out (°C)": r["T_out"],
                "T_mean (°C)": r["T_mean"],
                "Thermal power (kW)": round(r["Q_kW"], 1),
                "Annual energy (MWh/yr)": round(r["E_MWh_anno"], 1),
                "Exergy (kW)": round(r["Ex_kW"], 1),
                "T class": r["T_class"],
            }
        )

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name="Streams", index=False)


def _write_technologies_sheet(writer: pd.ExcelWriter, econ_results: list[EconomicResult]) -> None:
    """Foglio 2: Raccomandazioni tecnologiche."""
    rows = []
    for econ in econ_results:
        rec = econ.tech_recommendation
        rows.append(
            {
                "Stream": rec.stream_name,
                "Technology": rec.technology.name,
                "Q available (kW)": round(rec.Q_available_kW, 1),
                "Q recovered (kW)": round(rec.Q_recovered_kW, 1),
                "E recovered (MWh/yr)": round(rec.E_recovered_MWh, 1),
                "Efficiency": round(rec.efficiency, 3),
                "CAPEX min (€)": round(econ.capex_min_EUR, 0),
                "CAPEX (€)": round(econ.capex_EUR, 0),
                "CAPEX max (€)": round(econ.capex_max_EUR, 0),
                "Total investment (€)": round(econ.total_investment_EUR, 0),
                "OPEX (€/yr)": round(econ.opex_EUR_anno, 0),
                "Annual savings (€/yr)": round(econ.annual_savings_EUR, 0),
            }
        )

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name="Technologies", index=False)


def _write_economics_sheet(
    writer: pd.ExcelWriter,
    econ_results: list[EconomicResult],
    incentive_summaries: list[IncentiveSummary] | None,
    energy_price: float,
) -> None:
    """Foglio 3: Analisi economica con confronto incentivi."""
    rows = []
    for i, econ in enumerate(econ_results):
        rec = econ.tech_recommendation
        row = {
            "Stream": rec.stream_name,
            "Technology": rec.technology.name,
            "Investment (€)": round(econ.total_investment_EUR, 0),
            "Annual savings (€/yr)": round(econ.annual_savings_EUR, 0),
            "OPEX (€/yr)": round(econ.opex_EUR_anno, 0),
            "Net annual benefit (€/yr)": round(econ.net_annual_benefit_EUR, 0),
            "Payback (yr)": econ.payback_years,
            "NPV 10yr (€)": round(econ.npv_EUR, 0),
            "IRR (%)": econ.irr_pct,
            "Energy price (€/kWh)": energy_price,
        }

        # Incentivi se disponibili
        if incentive_summaries and i < len(incentive_summaries):
            s = incentive_summaries[i]
            if s.capex_incentive:
                row["Incentive name"] = s.capex_incentive.nome_incentivo
                row["CAPEX reduction (%)"] = s.capex_incentive.riduzione_pct
                row["CAPEX net (€)"] = round(s.capex_incentive.capex_netto, 0)
                row["Payback w/ CAPEX inc. (yr)"] = s.payback_con_capex_inc
                row["NPV w/ CAPEX inc. (€)"] = s.npv_con_capex_inc
            if s.tee:
                row["TEP/yr"] = s.tee.tep_risparmiati_anno
                row["TEE eligible"] = "Yes" if s.tee.sopra_soglia else "No"
                row["TEE revenue/yr (€)"] = round(s.tee.ricavo_medio_anno, 0)
                row["Payback w/ TEE (yr)"] = s.payback_con_tee
                row["NPV w/ TEE (€)"] = s.npv_con_tee
            if s.npv_combinato is not None:
                row["Payback combined (yr)"] = s.payback_combinato
                row["NPV combined (€)"] = s.npv_combinato

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name="Economics", index=False)
