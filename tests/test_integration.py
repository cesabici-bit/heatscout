"""Integration test end-to-end — Task 3F.2.

Verifica il workflow completo: stream -> HeatBalance -> summary ->
technology selection -> economic analysis. Nessuna eccezione non gestita.
"""

from __future__ import annotations

import pytest

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.heat_balance import FactoryHeatBalance
from heatscout.core.technology_selector import select_technologies
from heatscout.core.economics import economic_analysis
from heatscout.core.examples import load_example
from heatscout.report.executive_summary import generate_executive_summary
from heatscout.plotting.sankey import create_sankey


def _run_full_workflow(streams, factory_name="Test", T_ambient=25.0,
                       energy_price=0.08):
    """Esegue il workflow completo e ritorna (summary, econ_results, hb)."""
    hb = FactoryHeatBalance(factory_name=factory_name, T_ambient=T_ambient)
    for s in streams:
        hb.add_stream(s)
    hb.estimate_energy_input(efficiency=0.85)

    summary = hb.summary()
    assert summary["n_streams"] == len(streams)

    all_econ = []
    for stream in hb.streams:
        if stream.stream_type != StreamType.HOT_WASTE:
            continue
        recs = select_technologies(stream, energy_price_EUR_kWh=energy_price)
        for rec in recs:
            econ = economic_analysis(rec, energy_price_EUR_kWh=energy_price,
                                     discount_rate=0.05, years=10)
            all_econ.append(econ)

    return summary, all_econ, hb


class TestWorkflowCompleto:
    """1. Workflow completo da stream singolo a summary + economia."""

    def test_single_stream_full_pipeline(self):
        stream = ThermalStream(
            name="Fumi test",
            fluid_type="fumi_gas_naturale",
            T_in=400, T_out=150,
            mass_flow=2.0,
            hours_per_day=16, days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        summary, econ_results, hb = _run_full_workflow([stream])

        assert summary["n_hot_waste"] == 1
        assert summary["total_waste_kW"] > 0
        assert summary["total_waste_MWh_anno"] > 0
        assert summary["total_waste_exergy_kW"] > 0
        assert summary["energy_input_kW"] is not None
        assert len(summary["stream_results"]) == 1
        assert len(econ_results) > 0

        # Ogni risultato economico ha campi validi
        for e in econ_results:
            assert e.capex_EUR > 0
            assert e.annual_savings_EUR > 0
            assert e.payback_years > 0
            assert e.npv_EUR is not None

        # Executive summary non crasha
        text = generate_executive_summary(summary, econ_results, 0.08)
        assert len(text) > 100

        # Sankey non crasha
        fig = create_sankey(hb, "Test")
        assert fig is not None


class TestEsempioFonderia:
    """2. Esempio 'fonderia' end-to-end."""

    def test_fonderia_full_pipeline(self):
        streams, meta = load_example("fonderia")
        assert len(streams) >= 1

        summary, econ_results, hb = _run_full_workflow(
            streams,
            factory_name=meta["name"],
            T_ambient=meta.get("T_ambient", 25.0),
        )

        assert summary["n_hot_waste"] >= 1
        assert summary["total_waste_kW"] > 0
        assert len(econ_results) > 0

        # Fonderia ha fumi ad alta T, deve trovare recuperatori
        best = min(econ_results, key=lambda e: e.payback_years)
        assert best.payback_years < 20

        # Sankey e summary non crashano
        fig = create_sankey(hb, meta["name"])
        assert fig is not None
        text = generate_executive_summary(summary, econ_results, 0.08)
        assert "kW" in text or "MWh" in text


class TestMultiStream:
    """3. Multi-stream (5 stream misti)."""

    def test_five_streams_pipeline(self):
        streams = [
            ThermalStream(
                name="Fumi forno", fluid_type="fumi_gas_naturale",
                T_in=500, T_out=200, mass_flow=1.5,
                hours_per_day=16, days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            ),
            ThermalStream(
                name="Acqua raffreddamento", fluid_type="acqua",
                T_in=60, T_out=30, mass_flow=3.0,
                hours_per_day=16, days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            ),
            ThermalStream(
                name="Aria compressa", fluid_type="aria",
                T_in=120, T_out=40, mass_flow=0.5,
                hours_per_day=16, days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            ),
            ThermalStream(
                name="Olio diatermico", fluid_type="olio_diatermico",
                T_in=250, T_out=150, mass_flow=1.0,
                hours_per_day=16, days_per_year=250,
                stream_type=StreamType.HOT_WASTE,
            ),
            ThermalStream(
                name="Riscaldamento processo", fluid_type="acqua",
                T_in=20, T_out=60, mass_flow=2.0,
                hours_per_day=16, days_per_year=250,
                stream_type=StreamType.COLD_DEMAND,
            ),
        ]

        summary, econ_results, hb = _run_full_workflow(streams)

        assert summary["n_streams"] == 5
        assert summary["n_hot_waste"] == 4
        assert summary["n_cold_demand"] == 1
        assert summary["total_waste_kW"] > 0
        assert len(econ_results) > 0

        # Temperatura classes devono avere almeno 2 classi non-vuote
        by_class = summary["by_temperature_class"]
        non_empty = sum(1 for c in by_class.values() if c["count"] > 0)
        assert non_empty >= 2


class TestEdgeCaseSmallPower:
    """4. Edge case: stream ~1 kW (molto piccolo)."""

    def test_tiny_stream_no_crash(self):
        stream = ThermalStream(
            name="Micro stream", fluid_type="acqua",
            T_in=50, T_out=40, mass_flow=0.025,
            hours_per_day=8, days_per_year=200,
            stream_type=StreamType.HOT_WASTE,
        )
        summary, econ_results, _ = _run_full_workflow([stream])

        assert summary["total_waste_kW"] > 0
        assert summary["total_waste_kW"] < 10  # Deve essere piccolo
        # Potrebbe non trovare tecnologie economiche, ma non deve crashare


class TestEdgeCaseHighTemp:
    """5. Edge case: T = 800°C (molto alta)."""

    def test_800C_stream_no_crash(self):
        stream = ThermalStream(
            name="Fumi altissima T", fluid_type="fumi_gas_naturale",
            T_in=800, T_out=200, mass_flow=2.0,
            hours_per_day=16, days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )
        summary, econ_results, _ = _run_full_workflow([stream])

        assert summary["total_waste_kW"] > 0
        assert summary["by_temperature_class"]["alta"]["count"] == 1
        assert len(econ_results) > 0

        # A 800°C ci devono essere tecnologie ad alta T
        for e in econ_results:
            assert e.capex_EUR > 0
            assert e.payback_years > 0
