"""Test per modelli di efficienza delle tecnologie."""

import pytest

from heatscout.knowledge.efficiency_models import (
    he_effectiveness,
    heat_pump_cop,
    orc_efficiency,
    preheating_savings,
)


class TestHeatExchangerEffectiveness:
    def test_gas_gas_typical(self):
        """Effectiveness scambiatore gas-gas ≈ 0.6-0.7."""
        eff = he_effectiveness(400, 20, "gas_gas")
        assert 0.55 < eff < 0.75

    def test_liquid_liquid_typical(self):
        """Effectiveness scambiatore liquido-liquido ≈ 0.7-0.85."""
        eff = he_effectiveness(90, 20, "liquid_liquid")
        assert 0.65 < eff < 0.85

    def test_effectiveness_range(self):
        """Effectiveness sempre in [0.40, 0.85]."""
        for T_hot in [50, 100, 300, 600]:
            for he_type in ["gas_gas", "gas_liquid", "liquid_liquid"]:
                eff = he_effectiveness(T_hot, 20, he_type)
                assert 0.40 <= eff <= 0.85, f"ε({T_hot}, {he_type}) = {eff}"


class TestHeatPumpCOP:
    def test_cop_60_80(self):
        """COP pompa di calore 60°C→80°C ≈ 4-6.

        Con lift di soli 20°C, il COP è elevato (vicino al cap).
        Fonte: AIT, "Le pompe di calore", COP tipici.
        """
        cop = heat_pump_cop(60, 80)
        assert 3.5 < cop <= 6.0, f"COP(60→80) = {cop}"

    def test_cop_30_60(self):
        """COP pompa di calore 30°C→60°C ≈ 3-6."""
        cop = heat_pump_cop(30, 60)
        assert 3.0 < cop <= 6.0, f"COP(30→60) = {cop}"

    def test_cop_decreases_with_lift(self):
        """COP diminuisce quando la differenza T_sink - T_source aumenta."""
        cop_small = heat_pump_cop(40, 50)  # lift = 10°C
        cop_large = heat_pump_cop(40, 80)  # lift = 40°C
        assert cop_small > cop_large

    def test_cop_always_above_1(self):
        """COP ≥ 1.5 per qualsiasi configurazione ragionevole."""
        for T_source in [20, 30, 40, 50, 60]:
            for T_sink in [50, 60, 70, 80]:
                if T_sink > T_source:
                    cop = heat_pump_cop(T_source, T_sink)
                    assert cop >= 1.5, f"COP({T_source}→{T_sink}) = {cop}"


class TestORCEfficiency:
    def test_orc_from_150(self):
        """η ORC da 150°C ≈ 8-12%.

        Fonte: Quoilin et al. (2013), Fig. 4
        """
        eta = orc_efficiency(150, 30)
        assert 0.06 < eta < 0.15, f"η_ORC(150°C) = {eta:.3f}"

    def test_orc_from_300(self):
        """η ORC da 300°C ≈ 14-20%."""
        eta = orc_efficiency(300, 30)
        assert 0.12 < eta < 0.22, f"η_ORC(300°C) = {eta:.3f}"

    def test_orc_increases_with_temperature(self):
        """η ORC aumenta con T_source."""
        eta_low = orc_efficiency(100, 30)
        eta_high = orc_efficiency(300, 30)
        assert eta_high > eta_low

    def test_orc_zero_below_sink(self):
        """η ORC = 0 se T_source ≤ T_sink."""
        assert orc_efficiency(30, 30) == 0.0
        assert orc_efficiency(20, 30) == 0.0


class TestPreheatingSavings:
    def test_savings_400C(self):
        """Pre-riscaldamento con fumi a 400°C → ~10-15% risparmio."""
        savings = preheating_savings(400, 20)
        assert 8 < savings < 20, f"Savings(400°C) = {savings:.1f}%"

    def test_savings_increases_with_T(self):
        """Più alta la T dei fumi, più si risparmia."""
        s_low = preheating_savings(200)
        s_high = preheating_savings(600)
        assert s_high > s_low

    def test_savings_range(self):
        """Risparmio sempre in [0, 30]%."""
        for T in [100, 200, 400, 600, 800]:
            s = preheating_savings(T)
            assert 0 <= s <= 30, f"Savings({T}°C) = {s}%"
