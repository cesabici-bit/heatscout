"""Property-based test: invarianti fisiche e matematiche.

Usa Hypothesis per generare input random e verificare che le leggi
della fisica siano SEMPRE rispettate, indipendentemente dall'input.
"""

from __future__ import annotations

import pytest

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.stream_analyzer import (
    calc_thermal_power,
    calc_annual_energy,
    calc_exergy,
    classify_temperature,
)
from heatscout.core.economics import calc_payback, calc_npv, calc_irr


# ── Strategie per generare input validi ──────────────────────────────────────

reasonable_temp = st.floats(min_value=-50, max_value=1200, allow_nan=False, allow_infinity=False)
positive_float = st.floats(min_value=0.001, max_value=1e6, allow_nan=False, allow_infinity=False)
mass_flow = st.floats(min_value=0.001, max_value=100, allow_nan=False, allow_infinity=False)
hours = st.floats(min_value=0.1, max_value=24, allow_nan=False, allow_infinity=False)
days = st.floats(min_value=1, max_value=366, allow_nan=False, allow_infinity=False)


@st.composite
def hot_waste_stream(draw):
    """Genera un ThermalStream hot_waste valido con fluido 'acqua'."""
    T_in = draw(st.floats(min_value=30, max_value=99, allow_nan=False, allow_infinity=False))
    T_out = draw(st.floats(min_value=5, max_value=T_in - 1, allow_nan=False, allow_infinity=False))
    return ThermalStream(
        name="test_stream",
        fluid_type="acqua",
        T_in=T_in,
        T_out=T_out,
        mass_flow=draw(mass_flow),
        hours_per_day=draw(hours),
        days_per_year=draw(days),
        stream_type=StreamType.HOT_WASTE,
    )


# ── Test invarianti termodinamiche ───────────────────────────────────────────

class TestThermalPowerProperties:

    @given(stream=hot_waste_stream())
    @settings(max_examples=200)
    def test_power_always_positive(self, stream):
        """Potenza termica deve essere > 0 per qualsiasi stream valido."""
        Q = calc_thermal_power(stream)
        assert Q > 0, f"Q={Q} per dT={stream.delta_T}, m={stream.mass_flow}"

    @given(stream=hot_waste_stream())
    @settings(max_examples=200)
    def test_energy_always_positive(self, stream):
        """Energia annuale deve essere > 0."""
        E = calc_annual_energy(stream)
        assert E > 0

    @given(stream=hot_waste_stream())
    @settings(max_examples=200)
    def test_exergy_leq_energy(self, stream):
        """Secondo principio: exergia <= energia (potenza)."""
        Q = calc_thermal_power(stream)
        Ex = calc_exergy(stream, T_ambient=25.0)
        assert Ex <= Q + 1e-6, f"Exergia ({Ex}) > Potenza ({Q}): viola 2o principio"

    @given(stream=hot_waste_stream())
    @settings(max_examples=200)
    def test_power_proportional_to_mass_flow(self, stream):
        """Raddoppiando la portata, la potenza raddoppia."""
        Q1 = calc_thermal_power(stream)
        stream2 = ThermalStream(
            name=stream.name,
            fluid_type=stream.fluid_type,
            T_in=stream.T_in,
            T_out=stream.T_out,
            mass_flow=stream.mass_flow * 2,
            hours_per_day=stream.hours_per_day,
            days_per_year=stream.days_per_year,
            stream_type=stream.stream_type,
        )
        Q2 = calc_thermal_power(stream2)
        assert Q2 == pytest.approx(Q1 * 2, rel=1e-9)


# ── Test invarianti economiche ───────────────────────────────────────────────

class TestEconomicProperties:

    @given(
        capex=st.floats(min_value=100, max_value=1e8, allow_nan=False, allow_infinity=False),
        savings=st.floats(min_value=100, max_value=1e7, allow_nan=False, allow_infinity=False),
        opex=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_payback_always_positive(self, capex, savings, opex):
        """Payback deve essere > 0 se net benefit > 0."""
        assume(savings > opex)
        pb = calc_payback(capex, savings, opex)
        assert pb > 0

    @given(
        capex=st.floats(min_value=100, max_value=1e8, allow_nan=False, allow_infinity=False),
        savings=st.floats(min_value=100, max_value=1e7, allow_nan=False, allow_infinity=False),
        opex=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_payback_increases_with_capex(self, capex, savings, opex):
        """Payback maggiore con CAPEX maggiore (a parità di savings)."""
        assume(savings > opex)
        pb1 = calc_payback(capex, savings, opex)
        pb2 = calc_payback(capex * 2, savings, opex)
        assert pb2 > pb1

    @given(
        capex=st.floats(min_value=1000, max_value=1e6, allow_nan=False, allow_infinity=False),
        savings=st.floats(min_value=500, max_value=1e6, allow_nan=False, allow_infinity=False),
        opex=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_npv_positive_when_savings_large(self, capex, savings, opex):
        """NPV positivo quando savings >> capex."""
        assume(savings - opex > capex / 3)  # ~3 anni payback
        npv = calc_npv(capex, savings, opex, discount_rate=0.05, years=10)
        assert npv > 0, f"NPV={npv} con capex={capex}, savings={savings}"

    @given(
        capex=st.floats(min_value=100, max_value=1e6, allow_nan=False, allow_infinity=False),
        savings=st.floats(min_value=100, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_irr_none_when_no_benefit(self, capex, savings):
        """IRR è None quando non c'è beneficio netto."""
        opex = savings + 100  # Forza net benefit negativo
        irr = calc_irr(capex, savings, opex)
        assert irr is None


# ── Test classificazione temperatura ─────────────────────────────────────────

class TestTemperatureClassification:

    @given(T=st.floats(min_value=251, max_value=2000, allow_nan=False, allow_infinity=False))
    def test_high_temp(self, T):
        assert classify_temperature(T) == "alta"

    @given(T=st.floats(min_value=80, max_value=250, allow_nan=False, allow_infinity=False))
    def test_medium_temp(self, T):
        assert classify_temperature(T) == "media"

    @given(T=st.floats(min_value=-50, max_value=79.99, allow_nan=False, allow_infinity=False))
    def test_low_temp(self, T):
        assert classify_temperature(T) == "bassa"
