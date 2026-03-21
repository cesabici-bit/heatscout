"""Economic analysis: savings, payback, NPV, IRR."""

from __future__ import annotations

from dataclasses import dataclass

import numpy_financial as npf

from heatscout.core.technology_selector import TechRecommendation
from heatscout.knowledge.cost_correlations import (
    estimate_opex,
    estimate_total_investment,
)
from heatscout.knowledge.incentives import (
    CapexIncentiveResult,
    TEEResult,
    calc_capex_incentive,
    calc_tee,
)


@dataclass
class EconomicResult:
    """Economic analysis result for a technology recommendation."""

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


def calc_annual_savings(
    Q_recovered_kW: float,
    hours_per_day: float,
    days_per_year: float,
    energy_price_EUR_kWh: float,
) -> float:
    """Calculate annual savings [EUR/year].

    savings = Q_recovered × hours/day × days/year × energy_price
    """
    return Q_recovered_kW * hours_per_day * days_per_year * energy_price_EUR_kWh


def calc_payback(capex: float, annual_savings: float, opex: float) -> float:
    """Calculate simple payback [years].

    payback = CAPEX / (savings - OPEX)
    Returns inf if net benefit <= 0.
    """
    assert capex >= 0, f"CAPEX negativo: {capex}"
    assert annual_savings >= 0, f"Savings negativo: {annual_savings}"
    assert opex >= 0, f"OPEX negativo: {opex}"
    net = annual_savings - opex
    if net <= 0:
        return float("inf")
    return capex / net


def calc_npv(
    capex: float,
    annual_savings: float,
    opex: float,
    discount_rate: float = 0.05,
    years: int = 10,
) -> float:
    """Calculate NPV (Net Present Value) [EUR].

    NPV = -CAPEX + Σ (savings - opex) / (1+r)^t per t=1..years
    """
    net_annual = annual_savings - opex
    cashflows = [-capex] + [net_annual] * years
    return float(npf.npv(discount_rate, cashflows))


def calc_irr(capex: float, annual_savings: float, opex: float, years: int = 10) -> float | None:
    """Calculate IRR (Internal Rate of Return) [%].

    Returns None if IRR is not computable (always negative cashflow).
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
    opex_multiplier: float = 1.0,
    install_multiplier: float = 1.0,
) -> EconomicResult:
    """Full economic analysis for a TechRecommendation.

    Args:
        rec: Technology recommendation
        energy_price_EUR_kWh: Energy price [€/kWh]
        discount_rate: Discount rate for NPV
        years: Time horizon [years]
        opex_multiplier: Multiplier on default OPEX (1.0 = default from costs.json)
        install_multiplier: Multiplier on default installation factor (1.0 = default)

    Returns:
        EconomicResult with all economic parameters
    """
    tech_id = rec.technology.id
    Q_kW = rec.Q_recovered_kW

    # Costs
    investment = estimate_total_investment(tech_id, Q_kW)
    capex = investment["capex"]
    # Apply installation multiplier: scale the installation overhead
    base_inst_factor = investment["installation_factor"]
    adj_inst_factor = 1.0 + (base_inst_factor - 1.0) * install_multiplier
    total_inv = round(capex["medio"] * adj_inst_factor, 0)
    opex = round(estimate_opex(tech_id, capex["medio"]) * opex_multiplier, 0)

    # Savings: use the savings already calculated in the recommendation
    annual_savings = rec.savings_EUR

    # Economic calculations
    net_annual = annual_savings - opex
    payback = calc_payback(total_inv, annual_savings, opex)
    npv = calc_npv(total_inv, annual_savings, opex, discount_rate, years)
    irr = calc_irr(total_inv, annual_savings, opex, years)

    # Cumulative cashflow for charts
    cumulative = [-total_inv]
    for t in range(1, years + 1):
        cumulative.append(cumulative[-1] + net_annual / (1 + discount_rate) ** t)

    # Fail-fast: short payback but very negative NPV = probable error
    # (simple payback doesn't discount, NPV does — slight divergence is ok)
    if payback < years * 0.5 and npv < -total_inv * 0.1:
        assert False, (
            f"Inconsistenza: payback={payback:.1f}yr << horizon/2={years / 2}yr "
            f"ma NPV={npv:.0f} molto negativo (>{total_inv * 0.1:.0f}). "
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
    """Economic comparison with and without White Certificates (TEE)."""

    base: EconomicResult  # Without incentives
    tee: TEEResult  # TEE detail
    npv_con_tee: float  # NPV with incentive [€]
    payback_con_tee: float  # Payback with incentive [years]
    irr_con_tee: float | None  # IRR with incentive [%]
    cumulative_con_tee: list[float]  # Cumulative cashflow with incentive


def economic_analysis_with_tee(
    econ: EconomicResult,
    prezzo_tee: float = 250.0,
    eta_riferimento: float = 0.90,
    discount_rate: float = 0.05,
) -> EconomicComparison:
    """Recalculate NPV/payback/IRR including White Certificates (TEE) revenue.

    TEE last 7 years (heat recovery useful life). Annual revenue is added
    to net benefit during those years, then drops to zero.

    Args:
        econ: Base economic result (without incentives)
        prezzo_tee: TEE price [€/TEE]
        eta_riferimento: Reference boiler efficiency
        discount_rate: Discount rate for NPV

    Returns:
        EconomicComparison with comparison details
    """
    rec = econ.tech_recommendation
    tee_result = calc_tee(rec.E_recovered_MWh, prezzo_tee, eta_riferimento)

    capex = econ.total_investment_EUR
    savings = econ.annual_savings_EUR
    opex = econ.opex_EUR_anno
    years = econ.horizon_years
    net_base = savings - opex

    # Annual cashflow: base + TEE revenue (only for TEE useful life = 7 years)
    cashflows_con_tee = [-capex]
    for t in range(1, years + 1):
        tee_ricavo = tee_result.ricavo_per_anno[t - 1] if t <= tee_result.vita_utile else 0.0
        cashflows_con_tee.append(net_base + tee_ricavo)

    # NPV with TEE
    npv_con_tee = float(npf.npv(discount_rate, cashflows_con_tee))

    # Payback with TEE (simple, uses average TEE revenue over first years)
    # For consistency with base payback (undiscounted), use net_base + average_revenue
    net_con_tee_medio = net_base + tee_result.ricavo_medio_anno
    if net_con_tee_medio > 0:
        payback_con_tee = capex / net_con_tee_medio
    else:
        payback_con_tee = float("inf")

    # IRR with TEE
    try:
        irr_val = float(npf.irr(cashflows_con_tee))
        if irr_val != irr_val or irr_val < -1:
            irr_con_tee = None
        else:
            irr_con_tee = round(irr_val * 100, 1)
    except Exception:
        irr_con_tee = None

    # Discounted cumulative cashflow (for chart)
    cumulative = [cashflows_con_tee[0]]
    for t in range(1, years + 1):
        cumulative.append(cumulative[-1] + cashflows_con_tee[t] / (1 + discount_rate) ** t)

    return EconomicComparison(
        base=econ,
        tee=tee_result,
        npv_con_tee=round(npv_con_tee, 0),
        payback_con_tee=round(payback_con_tee, 1),
        irr_con_tee=irr_con_tee,
        cumulative_con_tee=cumulative,
    )


@dataclass
class IncentiveSummary:
    """Economic summary with all incentives applied."""

    base: EconomicResult
    # CAPEX incentive (generic)
    capex_incentive: CapexIncentiveResult | None
    npv_con_capex_inc: float | None
    payback_con_capex_inc: float | None
    irr_con_capex_inc: float | None
    # TEE (optional, Italy only)
    tee: TEEResult | None
    npv_con_tee: float | None
    payback_con_tee: float | None
    # Combined (reduced CAPEX + TEE)
    npv_combinato: float | None
    payback_combinato: float | None


def economic_analysis_with_incentives(
    econ: EconomicResult,
    capex_riduzione_pct: float = 0.0,
    nome_incentivo: str = "Tax credit / Grant",
    tee_enabled: bool = False,
    prezzo_tee: float = 250.0,
    eta_riferimento: float = 0.90,
    discount_rate: float = 0.05,
) -> IncentiveSummary:
    """Recalculate NPV/payback with optional incentives (CAPEX and/or TEE).

    Args:
        econ: Base economic result
        capex_riduzione_pct: CAPEX reduction % from incentive [0-100]
        nome_incentivo: CAPEX incentive name
        tee_enabled: If True, also calculate TEE (Italy)
        prezzo_tee: TEE price [€/TEE]
        eta_riferimento: Reference boiler efficiency
        discount_rate: Discount rate

    Returns:
        IncentiveSummary with all scenarios
    """
    capex = econ.total_investment_EUR
    savings = econ.annual_savings_EUR
    opex = econ.opex_EUR_anno
    years = econ.horizon_years
    net_base = savings - opex

    # ── CAPEX incentive (generic) ──
    capex_inc = None
    npv_capex = None
    payback_capex = None
    irr_capex = None

    if capex_riduzione_pct > 0:
        capex_inc = calc_capex_incentive(capex, capex_riduzione_pct, nome_incentivo)
        capex_netto = capex_inc.capex_netto
        npv_capex = round(calc_npv(capex_netto, savings, opex, discount_rate, years), 0)
        payback_capex = round(calc_payback(capex_netto, savings, opex), 1)
        irr_capex = calc_irr(capex_netto, savings, opex, years)

    # ── TEE ──
    tee_result = None
    npv_tee = None
    payback_tee = None

    if tee_enabled:
        rec = econ.tech_recommendation
        tee_result = calc_tee(rec.E_recovered_MWh, prezzo_tee, eta_riferimento)

        # Cashflow con TEE (CAPEX originale + ricavi TEE)
        cashflows_tee = [-capex]
        for t in range(1, years + 1):
            tee_r = tee_result.ricavo_per_anno[t - 1] if t <= tee_result.vita_utile else 0.0
            cashflows_tee.append(net_base + tee_r)
        npv_tee = round(float(npf.npv(discount_rate, cashflows_tee)), 0)

        net_con_tee = net_base + tee_result.ricavo_medio_anno
        payback_tee = round(capex / net_con_tee if net_con_tee > 0 else float("inf"), 1)

    # ── Combined (reduced CAPEX + TEE) ──
    npv_comb = None
    payback_comb = None

    if capex_riduzione_pct > 0 and tee_enabled and tee_result is not None:
        capex_netto = capex_inc.capex_netto
        cashflows_comb = [-capex_netto]
        for t in range(1, years + 1):
            tee_r = tee_result.ricavo_per_anno[t - 1] if t <= tee_result.vita_utile else 0.0
            cashflows_comb.append(net_base + tee_r)
        npv_comb = round(float(npf.npv(discount_rate, cashflows_comb)), 0)

        net_con_tee = net_base + tee_result.ricavo_medio_anno
        payback_comb = round(capex_netto / net_con_tee if net_con_tee > 0 else float("inf"), 1)

    return IncentiveSummary(
        base=econ,
        capex_incentive=capex_inc,
        npv_con_capex_inc=npv_capex,
        payback_con_capex_inc=payback_capex,
        irr_con_capex_inc=irr_capex,
        tee=tee_result,
        npv_con_tee=npv_tee,
        payback_con_tee=payback_tee,
        npv_combinato=npv_comb,
        payback_combinato=payback_comb,
    )
