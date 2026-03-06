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
