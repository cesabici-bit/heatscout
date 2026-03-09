"""Snapshot test: verifica che l'output dei 10 esempi non cambi.

Se un test fallisce, significa che una modifica al codice ha cambiato
i risultati numerici. Questo forza una review umana prima di aggiornare
il golden file.

Per aggiornare le snapshot dopo una modifica INTENZIONALE:
    python tests/update_snapshots.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from heatscout.core.economics import economic_analysis
from heatscout.core.examples import load_example
from heatscout.core.stream_analyzer import analyze_stream
from heatscout.core.technology_selector import select_technologies

SNAPSHOTS_PATH = Path(__file__).parent / "snapshots" / "golden_examples.json"

EXAMPLES = [
    "birrificio",
    "cartiera",
    "caseificio",
    "ceramica",
    "chimica",
    "complesso_multi_stream",
    "data_center",
    "fonderia",
    "tessile",
    "vetreria",
]

# Tolleranza relativa per confronti numerici (0.1% — cattura regressioni
# ma tollera differenze minime da floating point / versioni CoolProp)
REL_TOL = 1e-3


@pytest.fixture(scope="module")
def golden_data() -> dict:
    with open(SNAPSHOTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _assert_close(actual, expected, label: str):
    """Confronta due valori numerici con tolleranza relativa."""
    if expected is None and actual is None:
        return
    if expected is None or actual is None:
        pytest.fail(f"{label}: expected={expected}, actual={actual}")
    if expected == 0:
        assert actual == pytest.approx(0, abs=0.1), f"{label}: expected~0, got {actual}"
    else:
        assert actual == pytest.approx(expected, rel=REL_TOL), (
            f"{label}: expected={expected}, actual={actual}"
        )


@pytest.mark.parametrize("example_id", EXAMPLES)
class TestSnapshotAnalysis:
    """Verifica che analyze_stream produca gli stessi risultati della golden file."""

    def test_stream_count(self, example_id, golden_data):
        streams, meta = load_example(example_id)
        expected = golden_data[example_id]
        assert len(streams) == expected["n_streams"]

    def test_thermal_analysis(self, example_id, golden_data):
        streams, meta = load_example(example_id)
        T_amb = meta.get("T_ambient", 25)
        expected_analyses = golden_data[example_id]["analyses"]

        for i, stream in enumerate(streams):
            actual = analyze_stream(stream, T_amb)
            exp = expected_analyses[i]
            label = f"{example_id}/{stream.name}"

            _assert_close(actual["Q_kW"], exp["Q_kW"], f"{label}/Q_kW")
            _assert_close(actual["E_MWh_anno"], exp["E_MWh_anno"], f"{label}/E_MWh_anno")
            _assert_close(actual["Ex_kW"], exp["Ex_kW"], f"{label}/Ex_kW")
            assert actual["T_class"] == exp["T_class"], f"{label}/T_class"


@pytest.mark.parametrize("example_id", EXAMPLES)
class TestSnapshotRecommendations:
    """Verifica che le raccomandazioni tecnologiche non cambino."""

    def test_recommendation_count(self, example_id, golden_data):
        streams, _ = load_example(example_id)
        expected_recs = golden_data[example_id]["recommendations"]

        actual_recs = []
        for s in streams:
            actual_recs.extend(select_technologies(s))

        assert len(actual_recs) == len(expected_recs), (
            f"{example_id}: expected {len(expected_recs)} recs, got {len(actual_recs)}"
        )

    def test_recommendation_values(self, example_id, golden_data):
        streams, _ = load_example(example_id)
        expected_recs = golden_data[example_id]["recommendations"]

        actual_recs = []
        for s in streams:
            actual_recs.extend(select_technologies(s))

        for i, (act, exp) in enumerate(zip(actual_recs, expected_recs)):
            label = f"{example_id}/rec[{i}]/{exp['tech_id']}"
            assert act.technology.id == exp["tech_id"], f"{label}: tech mismatch"
            _assert_close(act.Q_recovered_kW, exp["Q_recovered_kW"], f"{label}/Q_rec")
            _assert_close(act.savings_EUR, exp["savings_EUR"], f"{label}/savings")


@pytest.mark.parametrize("example_id", EXAMPLES)
class TestSnapshotEconomics:
    """Verifica che i risultati economici non cambino."""

    def test_economic_values(self, example_id, golden_data):
        streams, _ = load_example(example_id)
        expected_econs = golden_data[example_id]["economics"]

        actual_econs = []
        for s in streams:
            recs = select_technologies(s)
            for r in recs:
                actual_econs.append(economic_analysis(r))

        assert len(actual_econs) == len(expected_econs), (
            f"{example_id}: expected {len(expected_econs)} econ results"
        )

        for i, (act, exp) in enumerate(zip(actual_econs, expected_econs)):
            label = f"{example_id}/econ[{i}]/{exp['tech_id']}"
            _assert_close(act.capex_EUR, exp["capex_EUR"], f"{label}/capex")
            _assert_close(act.payback_years, exp["payback_years"], f"{label}/payback")
            _assert_close(act.npv_EUR, exp["npv_EUR"], f"{label}/npv")
            _assert_close(act.irr_pct, exp["irr_pct"], f"{label}/irr")
