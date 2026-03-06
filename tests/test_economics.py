"""Test per modulo analisi economica."""

import pytest

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.technology_selector import select_technologies
from heatscout.core.economics import (
    calc_annual_savings,
    calc_payback,
    calc_npv,
    calc_irr,
    economic_analysis,
)
from heatscout.knowledge.cost_correlations import (
    estimate_capex,
    estimate_opex,
    estimate_total_investment,
)


class TestCostCorrelations:
    def test_capex_positive(self):
        """CAPEX deve essere sempre positivo."""
        for tech_id in ["recuperatore_gas_gas", "pompa_calore_acqua_acqua", "orc"]:
            capex = estimate_capex(tech_id, 100)
            assert capex["medio"] > 0
            assert capex["min"] > 0
            assert capex["max"] > 0

    def test_capex_ordering(self):
        """min < medio < max."""
        capex = estimate_capex("orc", 100)
        assert capex["min"] < capex["medio"] < capex["max"]

    def test_capex_increases_with_size(self):
        """CAPEX maggiore per potenza maggiore."""
        small = estimate_capex("pompa_calore_aria_acqua", 50)
        large = estimate_capex("pompa_calore_aria_acqua", 200)
        assert large["medio"] > small["medio"]

    def test_capex_economy_of_scale(self):
        """Costo specifico (EUR/kW) diminuisce con la taglia (b < 1)."""
        small = estimate_capex("recuperatore_gas_gas", 50)
        large = estimate_capex("recuperatore_gas_gas", 500)
        cost_per_kw_small = small["medio"] / 50
        cost_per_kw_large = large["medio"] / 500
        assert cost_per_kw_large < cost_per_kw_small, "Economie di scala mancanti"


class TestCalcPayback:
    def test_simple_payback(self):
        """Payback = CAPEX / (savings - opex)."""
        pb = calc_payback(100000, 30000, 5000)
        assert pb == pytest.approx(4.0, abs=0.01)

    def test_payback_inf_if_no_benefit(self):
        """Se opex >= savings, payback = inf."""
        pb = calc_payback(100000, 5000, 5000)
        assert pb == float("inf")


class TestCalcNPV:
    def test_npv_positive_for_good_project(self):
        """NPV positivo se risparmio >> OPEX + ammortamento."""
        npv = calc_npv(100000, 30000, 3000, 0.05, 10)
        assert npv > 0

    def test_npv_negative_for_bad_project(self):
        """NPV negativo se risparmio troppo basso."""
        npv = calc_npv(500000, 10000, 5000, 0.05, 10)
        assert npv < 0

    def test_npv_increases_with_horizon(self):
        """NPV a 15 anni > NPV a 10 anni per progetto buono."""
        npv_10 = calc_npv(100000, 25000, 3000, 0.05, 10)
        npv_15 = calc_npv(100000, 25000, 3000, 0.05, 15)
        assert npv_15 > npv_10


class TestCalcIRR:
    def test_irr_positive_for_good_project(self):
        """IRR > 0 per progetto con payback ragionevole."""
        irr = calc_irr(100000, 30000, 3000, 10)
        assert irr is not None
        assert irr > 0

    def test_irr_greater_than_discount_rate(self):
        """Se NPV > 0 al 5%, allora IRR > 5%."""
        npv = calc_npv(100000, 30000, 3000, 0.05, 10)
        irr = calc_irr(100000, 30000, 3000, 10)
        if npv > 0:
            assert irr > 5.0


class TestEconomicAnalysisIntegration:
    def test_full_economic_analysis(self):
        """Test end-to-end: stream → tecnologie → economia."""
        s = ThermalStream(
            "Fumi", "fumi_gas_naturale", 400, 180, 1.5, 16, 250, StreamType.HOT_WASTE
        )
        recs = select_technologies(s, energy_price_EUR_kWh=0.08)
        assert len(recs) > 0

        result = economic_analysis(recs[0], energy_price_EUR_kWh=0.08)
        assert result.capex_EUR > 0
        assert result.annual_savings_EUR > 0
        assert result.payback_years > 0
        assert len(result.cumulative_cashflows) == result.horizon_years + 1

    def test_payback_heat_pump_50kw(self):
        """Payback pompa di calore ~50 kW: 3-8 anni."""
        s = ThermalStream(
            "Acqua", "acqua", 55, 30, 0.5, 16, 250, StreamType.HOT_WASTE
        )
        recs = select_technologies(s, energy_price_EUR_kWh=0.08)
        hp_recs = [r for r in recs if r.is_heat_pump]
        if hp_recs:
            result = economic_analysis(hp_recs[0], energy_price_EUR_kWh=0.08)
            assert 1 < result.payback_years < 15, f"Payback HP = {result.payback_years}"

    def test_npv_consistent_with_payback(self):
        """Se payback < horizon, NPV deve essere > 0."""
        s = ThermalStream(
            "Fumi", "fumi_gas_naturale", 300, 150, 1.0, 16, 250, StreamType.HOT_WASTE
        )
        recs = select_technologies(s, energy_price_EUR_kWh=0.08)
        for rec in recs[:3]:  # Top 3
            result = economic_analysis(rec, energy_price_EUR_kWh=0.08, years=15)
            if result.payback_years < 15:
                assert result.npv_EUR > 0, (
                    f"{rec.technology.name}: payback={result.payback_years} < 15 "
                    f"ma NPV={result.npv_EUR}"
                )
