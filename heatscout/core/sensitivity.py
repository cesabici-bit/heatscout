"""Sensitivity analysis: how economic indicators change with parameters.

Module 1: Energy price sensitivity (payback, NPV, IRR vs price).
"""

from __future__ import annotations

from dataclasses import dataclass

from heatscout.core.economics import (
    EconomicResult,
    calc_payback,
    calc_npv,
    calc_irr,
)


@dataclass
class SensitivityPoint:
    """Single point in a sensitivity sweep."""

    param_value: float
    param_label: str
    payback_years: float
    npv_EUR: float
    irr_pct: float | None


def energy_price_sensitivity(
    econ: EconomicResult,
    base_price: float,
    n_points: int = 15,
    range_pct: float = 50.0,
    discount_rate: float = 0.05,
    years: int = 10,
) -> list[SensitivityPoint]:
    """Sweep energy price ± range_pct and recalculate economics.

    Savings scale linearly with energy price (validated assumption:
    savings = Q_recovered × hours × price, so savings ∝ price).

    Args:
        econ: Base economic result at base_price
        base_price: Energy price used in the base analysis [€/kWh]
        n_points: Number of sweep points (odd recommended for symmetry)
        range_pct: Range as % of base price (50 = sweep from 50% to 150%)
        discount_rate: Discount rate for NPV
        years: Analysis horizon

    Returns:
        List of SensitivityPoint sorted by param_value
    """
    assert base_price > 0, f"Base price must be positive: {base_price}"
    assert n_points >= 3, f"Need at least 3 points: {n_points}"

    capex = econ.total_investment_EUR
    opex = econ.opex_EUR_anno
    base_savings = econ.annual_savings_EUR

    # Price range
    lo = base_price * (1 - range_pct / 100)
    hi = base_price * (1 + range_pct / 100)
    lo = max(lo, 0.001)  # avoid zero/negative

    prices = [lo + (hi - lo) * i / (n_points - 1) for i in range(n_points)]

    points = []
    for price in prices:
        # Scale savings linearly with price
        scale = price / base_price
        savings = base_savings * scale

        pb = calc_payback(capex, savings, opex)
        npv = calc_npv(capex, savings, opex, discount_rate, years)
        irr = calc_irr(capex, savings, opex, years)

        points.append(SensitivityPoint(
            param_value=round(price, 4),
            param_label=f"€ {price:.3f}/kWh",
            payback_years=round(pb, 1) if pb < 100 else float("inf"),
            npv_EUR=round(npv, 0),
            irr_pct=irr,
        ))

    return points
