"""Test per Save/Load analysis (JSON persistence).

Round-trip: save → load → same inputs.
"""

import json

import pytest

from heatscout.core.stream import StreamType
from heatscout.report.persistence import SCHEMA_VERSION, load_analysis, save_analysis

SAMPLE_STREAMS = [
    {
        "name": "Fumi forno",
        "fluid_type": "fumi_gas_naturale",
        "T_in": 400.0,
        "T_out": 180.0,
        "mass_flow": 2.0,
        "hours_per_day": 16.0,
        "days_per_year": 300.0,
        "stream_type": StreamType.HOT_WASTE,
    },
    {
        "name": "Acqua raffreddamento",
        "fluid_type": "acqua",
        "T_in": 60.0,
        "T_out": 35.0,
        "mass_flow": 1.5,
        "hours_per_day": 16.0,
        "days_per_year": 300.0,
        "stream_type": StreamType.COLD_DEMAND,
    },
]


class TestSaveAnalysis:
    """Test serializzazione."""

    def test_returns_valid_json(self):
        result = save_analysis("Fonderia", 25.0, 0.08, SAMPLE_STREAMS)
        data = json.loads(result)  # must not raise
        assert isinstance(data, dict)

    def test_has_version(self):
        result = save_analysis("Test", 25.0, 0.08, SAMPLE_STREAMS)
        data = json.loads(result)
        assert data["version"] == SCHEMA_VERSION

    def test_has_all_fields(self):
        result = save_analysis("MyPlant", 20.0, 0.10, SAMPLE_STREAMS)
        data = json.loads(result)
        assert data["factory_name"] == "MyPlant"
        assert data["T_ambient"] == 20.0
        assert data["energy_price"] == 0.10
        assert len(data["streams"]) == 2

    def test_stream_type_serialized_as_string(self):
        result = save_analysis("Test", 25.0, 0.08, SAMPLE_STREAMS)
        data = json.loads(result)
        # Enum should be serialized as string, not object
        for s in data["streams"]:
            assert isinstance(s["stream_type"], str)

    def test_includes_incentives(self):
        inc = {"capex_reduction_pct": 30, "tee_enabled": True}
        result = save_analysis("Test", 25.0, 0.08, SAMPLE_STREAMS, inc)
        data = json.loads(result)
        assert "incentives" in data
        assert data["incentives"]["capex_reduction_pct"] == 30

    def test_no_incentives_when_none(self):
        result = save_analysis("Test", 25.0, 0.08, SAMPLE_STREAMS)
        data = json.loads(result)
        assert "incentives" not in data

    def test_readable_format(self):
        """JSON is indented (human-readable)."""
        result = save_analysis("Test", 25.0, 0.08, SAMPLE_STREAMS)
        assert "\n" in result
        assert "  " in result


class TestLoadAnalysis:
    """Test deserializzazione."""

    def test_round_trip(self):
        """save → load → same values (±0.01%)."""
        saved = save_analysis("Fonderia Test", 25.0, 0.08, SAMPLE_STREAMS)
        loaded = load_analysis(saved)

        assert loaded["factory_name"] == "Fonderia Test"
        assert loaded["T_ambient"] == 25.0
        assert loaded["energy_price"] == 0.08
        assert len(loaded["streams"]) == 2

        for orig, restored in zip(SAMPLE_STREAMS, loaded["streams"]):
            assert restored["name"] == orig["name"]
            assert restored["fluid_type"] == orig["fluid_type"]
            assert abs(restored["T_in"] - orig["T_in"]) < 0.01
            assert abs(restored["T_out"] - orig["T_out"]) < 0.01
            assert abs(restored["mass_flow"] - orig["mass_flow"]) < 0.01
            assert abs(restored["hours_per_day"] - orig["hours_per_day"]) < 0.01
            assert abs(restored["days_per_year"] - orig["days_per_year"]) < 0.01

    def test_round_trip_with_incentives(self):
        inc = {"capex_reduction_pct": 30, "tee_enabled": True, "tee_price": 250}
        saved = save_analysis("Test", 25.0, 0.08, SAMPLE_STREAMS, inc)
        loaded = load_analysis(saved)
        assert loaded["incentives"]["capex_reduction_pct"] == 30
        assert loaded["incentives"]["tee_enabled"] is True

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_analysis("not json {{{")

    def test_missing_fields(self):
        with pytest.raises(ValueError, match="Missing required"):
            load_analysis('{"version": "1.0"}')

    def test_empty_streams(self):
        with pytest.raises(ValueError, match="non-empty"):
            load_analysis(
                json.dumps(
                    {
                        "version": "1.0",
                        "factory_name": "X",
                        "T_ambient": 25,
                        "energy_price": 0.08,
                        "streams": [],
                    }
                )
            )

    def test_stream_missing_field(self):
        with pytest.raises(ValueError, match="missing fields"):
            load_analysis(
                json.dumps(
                    {
                        "version": "1.0",
                        "factory_name": "X",
                        "T_ambient": 25,
                        "energy_price": 0.08,
                        "streams": [{"name": "S1"}],
                    }
                )
            )


class TestRoundTripReproducibility:
    """Test che il round-trip produce gli stessi risultati di analisi."""

    def test_analysis_reproducible(self):
        """save → load → re-analyze → same NPV/payback."""

        # Prima analisi
        streams = SAMPLE_STREAMS[:1]  # solo primo stream
        saved = save_analysis("Test", 25.0, 0.08, streams)
        loaded = load_analysis(saved)

        # Ricostruisci stream e analizza
        results_1 = _analyze(SAMPLE_STREAMS[:1])
        results_2 = _analyze(loaded["streams"])

        assert len(results_1) == len(results_2)
        for r1, r2 in zip(results_1, results_2):
            assert r1.payback_years == r2.payback_years
            assert abs(r1.npv_EUR - r2.npv_EUR) < 1  # ±1€


def _analyze(stream_dicts):
    """Helper: analizza una lista di stream dict, ritorna EconomicResult."""
    from heatscout.core.economics import economic_analysis
    from heatscout.core.stream import StreamType, ThermalStream
    from heatscout.core.technology_selector import select_technologies

    results = []
    for sd in stream_dicts:
        st_type = sd["stream_type"]
        if isinstance(st_type, str):
            st_type = StreamType.HOT_WASTE if "hot" in st_type.lower() else StreamType.COLD_DEMAND
        if st_type != StreamType.HOT_WASTE:
            continue
        stream = ThermalStream(
            name=sd["name"],
            fluid_type=sd["fluid_type"],
            T_in=sd["T_in"],
            T_out=sd["T_out"],
            mass_flow=sd["mass_flow"],
            hours_per_day=sd["hours_per_day"],
            days_per_year=sd["days_per_year"],
            stream_type=st_type,
        )
        recs = select_technologies(stream, energy_price_EUR_kWh=0.08)
        for rec in recs:
            results.append(economic_analysis(rec, energy_price_EUR_kWh=0.08))
    return results
