"""Test per stream_analyzer: potenza termica e energia annuale."""

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.stream_analyzer import calc_annual_energy, calc_thermal_power


class TestCalcThermalPower:
    """Test di calcolo potenza termica con valori noti."""

    def test_acqua_90_60(self):
        """Acqua 90→60°C, 1 kg/s → ~125 kW.

        cp acqua a 75°C ≈ 4.19 kJ/kgK
        Q = 1.0 × 4.19 × 30 ≈ 125.7 kW
        """
        s = ThermalStream(
            name="Acqua calda",
            fluid_type="acqua",
            T_in=90,
            T_out=60,
            mass_flow=1.0,
            hours_per_day=8,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        Q = calc_thermal_power(s)
        assert 120 < Q < 130, f"Q={Q:.1f} kW, atteso ~125 kW"

    def test_aria_400_200(self):
        """Aria 400→200°C, 0.5 kg/s → ~103 kW.

        cp aria a 300°C ≈ 1.03 kJ/kgK
        Q = 0.5 × 1.03 × 200 ≈ 103 kW
        """
        s = ThermalStream(
            name="Aria calda",
            fluid_type="aria",
            T_in=400,
            T_out=200,
            mass_flow=0.5,
            hours_per_day=16,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        Q = calc_thermal_power(s)
        assert 95 < Q < 115, f"Q={Q:.1f} kW, atteso ~103 kW"

    def test_fumi_gas_naturale_500_200(self):
        """Fumi gas naturale 500→200°C, 2 kg/s.

        cp medio ≈ 1.10 kJ/kgK
        Q = 2.0 × 1.10 × 300 ≈ 660 kW
        """
        s = ThermalStream(
            name="Fumi forno",
            fluid_type="fumi_gas_naturale",
            T_in=500,
            T_out=200,
            mass_flow=2.0,
            hours_per_day=16,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        Q = calc_thermal_power(s)
        assert 600 < Q < 750, f"Q={Q:.1f} kW, atteso ~660 kW"

    def test_olio_diatermico_250_100(self):
        """Olio diatermico 250→100°C, 0.8 kg/s.

        cp medio ≈ 1.68 + 0.00164*175 ≈ 1.97 kJ/kgK
        Q = 0.8 × 1.97 × 150 ≈ 236 kW
        """
        s = ThermalStream(
            name="Olio caldo",
            fluid_type="olio_diatermico",
            T_in=250,
            T_out=100,
            mass_flow=0.8,
            hours_per_day=24,
            days_per_year=330,
            stream_type=StreamType.HOT_WASTE,
        )
        Q = calc_thermal_power(s)
        assert 220 < Q < 260, f"Q={Q:.1f} kW, atteso ~236 kW"

    def test_cold_demand_acqua(self):
        """Acqua riscaldata da 15 a 60°C, 0.5 kg/s → ~94 kW."""
        s = ThermalStream(
            name="ACS",
            fluid_type="acqua",
            T_in=15,
            T_out=60,
            mass_flow=0.5,
            hours_per_day=8,
            days_per_year=250,
            stream_type=StreamType.COLD_DEMAND,
        )
        Q = calc_thermal_power(s)
        assert 90 < Q < 100, f"Q={Q:.1f} kW, atteso ~94 kW"

    def test_azoto_alta_T(self):
        """Azoto 600→300°C, 1 kg/s.

        cp azoto ≈ 1.06 kJ/kgK
        Q = 1.0 × 1.06 × 300 ≈ 318 kW
        """
        s = ThermalStream(
            name="N2 caldo",
            fluid_type="azoto",
            T_in=600,
            T_out=300,
            mass_flow=1.0,
            hours_per_day=24,
            days_per_year=365,
            stream_type=StreamType.HOT_WASTE,
        )
        Q = calc_thermal_power(s)
        assert 300 < Q < 340, f"Q={Q:.1f} kW, atteso ~318 kW"


class TestCalcAnnualEnergy:
    """Test energia annuale."""

    def test_annual_energy_acqua(self):
        """125 kW × 8 h × 250 d / 1000 = 250 MWh/anno."""
        s = ThermalStream(
            name="Acqua calda",
            fluid_type="acqua",
            T_in=90,
            T_out=60,
            mass_flow=1.0,
            hours_per_day=8,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        E = calc_annual_energy(s)
        assert 240 < E < 260, f"E={E:.1f} MWh/anno, atteso ~250"

    def test_annual_energy_continuous(self):
        """Stream continuo 24/7: ore annue = 8760."""
        s = ThermalStream(
            name="Aria calda",
            fluid_type="aria",
            T_in=400,
            T_out=200,
            mass_flow=0.5,
            hours_per_day=24,
            days_per_year=365,
            stream_type=StreamType.HOT_WASTE,
        )
        E = calc_annual_energy(s)
        Q = calc_thermal_power(s)
        expected = Q * 8760 / 1000
        assert abs(E - expected) < 0.1
