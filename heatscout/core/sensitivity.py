"""Sensitivity analysis: how economic indicators change with parameters.

Module 1: Energy price sensitivity (payback, NPV, IRR vs price).
Module 2: Tornado chart — one-at-a-time ±20% on multiple parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from heatscout.core.economics import (
    EconomicResult,
    calc_irr,
    calc_npv,
    calc_payback,
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

        points.append(
            SensitivityPoint(
                param_value=round(price, 4),
                param_label=f"€ {price:.3f}/kWh",
                payback_years=round(pb, 1) if pb < 100 else float("inf"),
                npv_EUR=round(npv, 0),
                irr_pct=irr,
            )
        )

    return points


# ── Module 2: Tornado chart ─────────────────────────────────────────────────


@dataclass
class TornadoBar:
    """One bar in a tornado chart (one parameter)."""

    param_name: str
    base_npv: float
    npv_low: float  # NPV when parameter is at -variation
    npv_high: float  # NPV when parameter is at +variation
    swing: float  # |npv_high - npv_low| — used for sorting


def tornado_analysis(
    econ,
    base_price: float,
    variation_pct: float = 20.0,
    discount_rate: float = 0.05,
    years: int = 10,
) -> list[TornadoBar]:
    """One-at-a-time sensitivity: NPV impact of ±variation_pct on key parameters.

    Parameters varied (one at a time, others held at base):
    - Energy price (scales savings linearly)
    - CAPEX (scales total_investment_EUR)
    - Operating hours (scales savings linearly)
    - Technology efficiency (scales savings linearly)

    Assumption: one-at-a-time (no interactions). Declared in UI.

    Args:
        econ: Base economic result (needs total_investment_EUR, annual_savings_EUR, opex_EUR_anno)
        base_price: Base energy price [€/kWh]
        variation_pct: Variation as % (20 = ±20%)
        discount_rate: Discount rate for NPV
        years: Analysis horizon

    Returns:
        List of TornadoBar sorted by swing (largest impact first)
    """
    assert variation_pct > 0, f"Variation must be positive: {variation_pct}"

    capex = econ.total_investment_EUR
    savings = econ.annual_savings_EUR
    opex = econ.opex_EUR_anno

    base_npv = calc_npv(capex, savings, opex, discount_rate, years)

    lo = 1 - variation_pct / 100
    hi = 1 + variation_pct / 100

    bars = []

    # 1. Energy price → scales savings only
    npv_lo = calc_npv(capex, savings * lo, opex, discount_rate, years)
    npv_hi = calc_npv(capex, savings * hi, opex, discount_rate, years)
    bars.append(TornadoBar("Energy price", base_npv, npv_lo, npv_hi, abs(npv_hi - npv_lo)))

    # 2. CAPEX → scales investment and opex (opex ∝ capex)
    npv_lo = calc_npv(capex * lo, savings, opex * lo, discount_rate, years)
    npv_hi = calc_npv(capex * hi, savings, opex * hi, discount_rate, years)
    # Higher CAPEX → lower NPV, so swap lo/hi for correct bar direction
    bars.append(TornadoBar("CAPEX", base_npv, npv_hi, npv_lo, abs(npv_hi - npv_lo)))

    # 3. Operating hours → scales savings AND opex (more hours = more wear)
    npv_lo = calc_npv(capex, savings * lo, opex * lo, discount_rate, years)
    npv_hi = calc_npv(capex, savings * hi, opex * hi, discount_rate, years)
    bars.append(TornadoBar("Operating hours", base_npv, npv_lo, npv_hi, abs(npv_hi - npv_lo)))

    # 4. Technology efficiency → scales savings only (capex/opex unchanged)
    npv_lo = calc_npv(capex, savings * lo, opex, discount_rate, years)
    npv_hi = calc_npv(capex, savings * hi, opex, discount_rate, years)
    bars.append(TornadoBar("Efficiency", base_npv, npv_lo, npv_hi, abs(npv_hi - npv_lo)))

    # Sort by swing (most impactful first)
    bars.sort(key=lambda b: b.swing, reverse=True)

    return bars
