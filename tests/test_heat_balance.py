"""Test per exergia, classificazione temperatura e FactoryHeatBalance."""

import pytest

from heatscout.core.heat_balance import FactoryHeatBalance
from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.stream_analyzer import (
    calc_exergy,
    calc_thermal_power,
    classify_temperature,
)


class TestClassifyTemperature:
    def test_alta(self):
        assert classify_temperature(300) == "alta"
        assert classify_temperature(500) == "alta"

    def test_media(self):
        assert classify_temperature(80) == "media"
        assert classify_temperature(150) == "media"
        assert classify_temperature(250) == "media"

    def test_bassa(self):
        assert classify_temperature(50) == "bassa"
        assert classify_temperature(79) == "bassa"


class TestCalcExergy:
    def test_exergy_high_temp(self):
        """Fumi 500°C: exergia alta (Carnot factor ~0.53)."""
        s = ThermalStream(
            name="Fumi",
            fluid_type="fumi_gas_naturale",
            T_in=500,
            T_out=200,
            mass_flow=1.0,
            hours_per_day=16,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        Q = calc_thermal_power(s)
        Ex = calc_exergy(s, T_ambient=25)
        # T_mean = 350°C = 623 K, T_amb = 298 K
        # Carnot = 1 - 298/623 = 0.522
        assert Ex > 0
        assert Ex < Q  # exergia sempre < energia
        assert Ex / Q > 0.45  # Carnot factor alto per fumi caldi

    def test_exergy_low_temp(self):
        """Acqua 45°C: exergia bassa (Carnot factor ~0.06)."""
        s = ThermalStream(
            name="Acqua tiepida",
            fluid_type="acqua",
            T_in=45,
            T_out=30,
            mass_flow=2.0,
            hours_per_day=8,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        Ex = calc_exergy(s, T_ambient=25)
        Q = calc_thermal_power(s)
        assert Ex > 0
        assert Ex / Q < 0.10  # Carnot factor molto basso

    def test_exergy_high_much_greater_than_low(self):
        """Exergia fumi 500°C >> exergia acqua 45°C."""
        fumi = ThermalStream(
            name="Fumi",
            fluid_type="fumi_gas_naturale",
            T_in=500,
            T_out=200,
            mass_flow=1.0,
            hours_per_day=16,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        acqua = ThermalStream(
            name="Acqua",
            fluid_type="acqua",
            T_in=45,
            T_out=30,
            mass_flow=1.0,
            hours_per_day=8,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        Ex_fumi = calc_exergy(fumi)
        Ex_acqua = calc_exergy(acqua)
        assert Ex_fumi > 10 * Ex_acqua


class TestFactoryHeatBalance:
    def _make_test_factory(self) -> FactoryHeatBalance:
        """Crea una fabbrica di test con 3 stream (alta/media/bassa T)."""
        hb = FactoryHeatBalance(factory_name="Test Factory", T_ambient=25)

        hb.add_stream(
            ThermalStream(
                name="Fumi forno",
                fluid_type="fumi_gas_naturale",
                T_in=500,
                T_out=200,
                mass_flow=1.0,
                hours_per_day=16,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )
        )
        hb.add_stream(
            ThermalStream(
                name="Vapore flash",
                fluid_type="aria",
                T_in=150,
                T_out=80,
                mass_flow=0.5,
                hours_per_day=16,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )
        )
        hb.add_stream(
            ThermalStream(
                name="Acqua raffreddam.",
                fluid_type="acqua",
                T_in=55,
                T_out=30,
                mass_flow=2.0,
                hours_per_day=16,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )
        )
        return hb

    def test_calculate_returns_results(self):
        hb = self._make_test_factory()
        results = hb.calculate()
        assert len(results) == 3
        assert all("Q_kW" in r for r in results)

    def test_summary_totals(self):
        hb = self._make_test_factory()
        s = hb.summary()
        assert s["n_streams"] == 3
        assert s["n_hot_waste"] == 3
        assert s["total_waste_kW"] > 0
        assert s["total_waste_MWh_anno"] > 0

    def test_summary_temperature_classes(self):
        hb = self._make_test_factory()
        s = hb.summary()
        by_class = s["by_temperature_class"]
        # Fumi: T_mean=350 → alta
        assert by_class["alta"]["count"] == 1
        # Vapore flash: T_mean=115 → media
        assert by_class["media"]["count"] == 1
        # Acqua: T_mean=42.5 → bassa
        assert by_class["bassa"]["count"] == 1

    def test_estimate_energy_input(self):
        hb = self._make_test_factory()
        hb.estimate_energy_input(efficiency=0.85)
        s = hb.summary()
        assert s["energy_input_kW"] is not None
        assert s["energy_input_kW"] > s["total_waste_kW"]
        assert s["waste_pct_of_input"] == pytest.approx(15.0, abs=0.1)

    def test_set_energy_input_gas(self):
        hb = self._make_test_factory()
        # 100,000 Sm3/anno di gas naturale → ~959,000 kWh/anno → ~109 kW
        hb.set_energy_input("gas_naturale", 100_000, "Sm3/anno")
        s = hb.summary()
        assert s["energy_input_kW"] is not None
        assert 100 < s["energy_input_kW"] < 120
