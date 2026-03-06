"""Test per il modello dati ThermalStream."""

import pytest

from heatscout.core.stream import StreamType, ThermalStream


class TestThermalStreamCreation:
    """Test di creazione corretta di ThermalStream."""

    def test_create_hot_waste_stream(self):
        s = ThermalStream(
            name="Fumi forno",
            fluid_type="fumi_gas_naturale",
            T_in=400,
            T_out=150,
            mass_flow=0.5,
            hours_per_day=16,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        assert s.name == "Fumi forno"
        assert s.delta_T == 250
        assert s.T_mean == 275

    def test_create_cold_demand_stream(self):
        s = ThermalStream(
            name="Acqua processo",
            fluid_type="acqua",
            T_in=15,
            T_out=60,
            mass_flow=1.0,
            hours_per_day=8,
            days_per_year=300,
            stream_type=StreamType.COLD_DEMAND,
        )
        assert s.T_in < s.T_out
        assert s.annual_hours == 2400

    def test_annual_hours_calculation(self):
        s = ThermalStream(
            name="Test",
            fluid_type="acqua",
            T_in=90,
            T_out=60,
            mass_flow=1.0,
            hours_per_day=24,
            days_per_year=365,
            stream_type=StreamType.HOT_WASTE,
        )
        assert s.annual_hours == 8760


class TestThermalStreamValidation:
    """Test di validazione input."""

    def test_reject_empty_name(self):
        with pytest.raises(ValueError, match="nome"):
            ThermalStream(
                name="",
                fluid_type="acqua",
                T_in=90,
                T_out=60,
                mass_flow=1.0,
                hours_per_day=8,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )

    def test_reject_below_absolute_zero(self):
        with pytest.raises(ValueError, match="zero assoluto"):
            ThermalStream(
                name="Test",
                fluid_type="acqua",
                T_in=-300,
                T_out=20,
                mass_flow=1.0,
                hours_per_day=8,
                days_per_year=250,
                stream_type=StreamType.COLD_DEMAND,
            )

    def test_reject_negative_mass_flow(self):
        with pytest.raises(ValueError, match="mass_flow"):
            ThermalStream(
                name="Test",
                fluid_type="acqua",
                T_in=90,
                T_out=60,
                mass_flow=-1.0,
                hours_per_day=8,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )

    def test_reject_zero_mass_flow(self):
        with pytest.raises(ValueError, match="mass_flow"):
            ThermalStream(
                name="Test",
                fluid_type="acqua",
                T_in=90,
                T_out=60,
                mass_flow=0,
                hours_per_day=8,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )

    def test_reject_equal_temperatures(self):
        with pytest.raises(ValueError, match="uguali"):
            ThermalStream(
                name="Test",
                fluid_type="acqua",
                T_in=60,
                T_out=60,
                mass_flow=1.0,
                hours_per_day=8,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )

    def test_reject_hot_waste_wrong_direction(self):
        with pytest.raises(ValueError, match="hot_waste"):
            ThermalStream(
                name="Test",
                fluid_type="acqua",
                T_in=30,
                T_out=60,
                mass_flow=1.0,
                hours_per_day=8,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )

    def test_reject_hours_over_24(self):
        with pytest.raises(ValueError, match="hours_per_day"):
            ThermalStream(
                name="Test",
                fluid_type="acqua",
                T_in=90,
                T_out=60,
                mass_flow=1.0,
                hours_per_day=25,
                days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            )


class TestThermalStreamSerialization:
    """Test serializzazione/deserializzazione."""

    def test_to_dict_and_back(self):
        s = ThermalStream(
            name="Fumi forno",
            fluid_type="fumi_gas_naturale",
            T_in=400,
            T_out=150,
            mass_flow=0.5,
            hours_per_day=16,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        d = s.to_dict()
        s2 = ThermalStream.from_dict(d)
        assert s2.name == s.name
        assert s2.T_in == s.T_in
        assert s2.stream_type == s.stream_type

    def test_from_dict_with_string_type(self):
        d = {
            "name": "Test",
            "fluid_type": "acqua",
            "T_in": 90,
            "T_out": 60,
            "mass_flow": 1.0,
            "hours_per_day": 8,
            "days_per_year": 250,
            "stream_type": "hot_waste",
        }
        s = ThermalStream.from_dict(d)
        assert s.stream_type == StreamType.HOT_WASTE
