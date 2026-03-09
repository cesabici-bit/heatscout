"""Analisi economica: risparmio, payback, NPV, IRR."""

from __future__ import annotations

from dataclasses import dataclass

import numpy_financial as npf

from heatscout.core.technology_selector import TechRecommendation
from heatscout.knowledge.cost_correlations import (
    estimate_capex,
    estimate_opex,
    estimate_total_investment,
)
from heatscout.knowledge.incentives import TEEResult, calc_tee


@dataclass
class EconomicResult:
    """Risultato dell'analisi economica per una raccomandazione tecnologica."""

    tech_recommendation: TechRecommendation
    capex_EUR: float
    capex_min_EUR: float
    capex_max_EUR: float
    total_investment_EUR: float
    opex_EUR_anno: float
    annual_savings_EUR: float
    net_annual_benefit_EUR: float  # savings - opex
    payback_years: float
    npv_EUR: float
    irr_pct: float | None  # None se non calcolabile
    cumulative_cashflows: list[float]  # per grafico
    horizon_years: int


def calc_annual_savings(Q_recovered_kW: float, hours_per_day: float,
                        days_per_year: float, energy_price_EUR_kWh: float) -> float:
    """Calcola risparmio annuo [EUR/anno].

    savings = Q_recovered × ore/giorno × giorni/anno × prezzo_energia
    """
    return Q_recovered_kW * hours_per_day * days_per_year * energy_price_EUR_kWh


def calc_payback(capex: float, annual_savings: float, opex: float) -> float:
    """Calcola payback semplice [anni].

    payback = CAPEX / (savings - OPEX)
    Se net benefit ≤ 0, ritorna inf.
    """
    assert capex >= 0, f"CAPEX negativo: {capex}"
    assert annual_savings >= 0, f"Savings negativo: {annual_savings}"
    assert opex >= 0, f"OPEX negativo: {opex}"
    net = annual_savings - opex
    if net <= 0:
        return float("inf")
    return capex / net


def calc_npv(capex: float, annual_savings: float, opex: float,
             discount_rate: float = 0.05, years: int = 10) -> float:
    """Calcola NPV (Net Present Value) [EUR].

    NPV = -CAPEX + Σ (savings - opex) / (1+r)^t per t=1..years
    """
    net_annual = annual_savings - opex
    cashflows = [-capex] + [net_annual] * years
    return float(npf.npv(discount_rate, cashflows))


def calc_irr(capex: float, annual_savings: float, opex: float,
             years: int = 10) -> float | None:
    """Calcola IRR (Internal Rate of Return) [%].

    Ritorna None se IRR non è calcolabile (cashflow sempre negativo).
    """
    net_annual = annual_savings - opex
    if net_annual <= 0:
        return None
    cashflows = [-capex] + [net_annual] * years
    try:
        irr = float(npf.irr(cashflows))
        if irr != irr or irr < -1:  # NaN check
            return None
        return irr * 100  # in percentuale
    except Exception:
        return None


def economic_analysis(
    rec: TechRecommendation,
    energy_price_EUR_kWh: float = 0.08,
    discount_rate: float = 0.05,
    years: int = 10,
) -> EconomicResult:
    """Analisi economica completa per una TechRecommendation.

    Args:
        rec: Raccomandazione tecnologica
        energy_price_EUR_kWh: Prezzo energia [€/kWh]
        discount_rate: Tasso di sconto per NPV
        years: Orizzonte temporale [anni]

    Returns:
        EconomicResult con tutti i parametri economici
    """
    tech_id = rec.technology.id
    Q_kW = rec.Q_recovered_kW

    # Costi
    investment = estimate_total_investment(tech_id, Q_kW)
    capex = investment["capex"]
    total_inv = investment["total_medio"]
    opex = estimate_opex(tech_id, capex["medio"])

    # Risparmio: usiamo il risparmio gia calcolato nella raccomandazione
    annual_savings = rec.savings_EUR

    # Calcoli economici
    net_annual = annual_savings - opex
    payback = calc_payback(total_inv, annual_savings, opex)
    npv = calc_npv(total_inv, annual_savings, opex, discount_rate, years)
    irr = calc_irr(total_inv, annual_savings, opex, years)

    # Cashflow cumulativo per grafici
    cumulative = [-total_inv]
    for t in range(1, years + 1):
        cumulative.append(cumulative[-1] + net_annual / (1 + discount_rate) ** t)

    # Fail-fast: payback corto ma NPV molto negativo = probabile errore
    # (payback semplice non sconta, NPV sì — divergenza leggera è ok)
    if payback < years * 0.5 and npv < -total_inv * 0.1:
        assert False, (
            f"Inconsistenza: payback={payback:.1f}yr << horizon/2={years/2}yr "
            f"ma NPV={npv:.0f} molto negativo (>{total_inv*0.1:.0f}). "
            f"capex={total_inv:.0f}, savings={annual_savings:.0f}, opex={opex:.0f}"
        )

    return EconomicResult(
        tech_recommendation=rec,
        capex_EUR=capex["medio"],
        capex_min_EUR=capex["min"],
        capex_max_EUR=capex["max"],
        total_investment_EUR=total_inv,
        opex_EUR_anno=opex,
        annual_savings_EUR=annual_savings,
        net_annual_benefit_EUR=net_annual,
        payback_years=round(payback, 1),
        npv_EUR=round(npv, 0),
        irr_pct=round(irr, 1) if irr is not None else None,
        cumulative_cashflows=cumulative,
        horizon_years=years,
    )


@dataclass
class EconomicComparison:
    """Confronto economico con e senza Certificati Bianchi."""

    base: EconomicResult  # Senza incentivi
    tee: TEEResult  # Dettaglio TEE
    npv_con_tee: float  # NPV con incentivo [€]
    payback_con_tee: float  # Payback con incentivo [anni]
    irr_con_tee: float | None  # IRR con incentivo [%]
    cumulative_con_tee: list[float]  # Cashflow cumulativo con incentivo


def economic_analysis_with_tee(
    econ: EconomicResult,
    prezzo_tee: float = 250.0,
    eta_riferimento: float = 0.90,
    discount_rate: float = 0.05,
) -> EconomicComparison:
    """Ricalcola NPV/payback/IRR includendo i ricavi da Certificati Bianchi.

    I TEE durano 7 anni (vita utile recupero calore). Il ricavo annuo si
    somma al beneficio netto durante quegli anni, poi torna a zero.

    Args:
        econ: Risultato economico base (senza incentivi)
        prezzo_tee: Prezzo TEE [€/TEE]
        eta_riferimento: Rendimento caldaia di riferimento
        discount_rate: Tasso di sconto per NPV

    Returns:
        EconomicComparison con dettaglio confronto
    """
    rec = econ.tech_recommendation
    tee_result = calc_tee(rec.E_recovered_MWh, prezzo_tee, eta_riferimento)

    capex = econ.total_investment_EUR
    savings = econ.annual_savings_EUR
    opex = econ.opex_EUR_anno
    years = econ.horizon_years
    net_base = savings - opex

    # Cashflow annuo: base + ricavo TEE (solo per vita utile TEE = 7 anni)
    cashflows_con_tee = [-capex]
    for t in range(1, years + 1):
        tee_ricavo = tee_result.ricavo_per_anno[t - 1] if t <= tee_result.vita_utile else 0.0
        cashflows_con_tee.append(net_base + tee_ricavo)

    # NPV con TEE
    npv_con_tee = float(npf.npv(discount_rate, cashflows_con_tee))

    # Payback con TEE (semplice, usa ricavo medio TEE sui primi anni)
    # Per coerenza col payback base (non scontato), uso net_base + ricavo_medio
    net_con_tee_medio = net_base + tee_result.ricavo_medio_anno
    if net_con_tee_medio > 0:
        payback_con_tee = capex / net_con_tee_medio
    else:
        payback_con_tee = float("inf")

    # IRR con TEE
    try:
        irr_val = float(npf.irr(cashflows_con_tee))
        if irr_val != irr_val or irr_val < -1:
            irr_con_tee = None
        else:
            irr_con_tee = round(irr_val * 100, 1)
    except Exception:
        irr_con_tee = None

    # Cashflow cumulativo scontato (per grafico)
    cumulative = [cashflows_con_tee[0]]
    for t in range(1, years + 1):
        cumulative.append(
            cumulative[-1] + cashflows_con_tee[t] / (1 + discount_rate) ** t
        )

    return EconomicComparison(
        base=econ,
        tee=tee_result,
        npv_con_tee=round(npv_con_tee, 0),
        payback_con_tee=round(payback_con_tee, 1),
        irr_con_tee=irr_con_tee,
        cumulative_con_tee=cumulative,
    )
