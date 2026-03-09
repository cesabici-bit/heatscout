"""Rigenera il golden file delle snapshot.

Eseguire SOLO dopo aver verificato manualmente che i nuovi valori
sono corretti (review umana obbligatoria).

Usage:
    python tests/update_snapshots.py
"""

import json
import sys
from pathlib import Path

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from heatscout.core.examples import load_example
from heatscout.core.stream_analyzer import analyze_stream
from heatscout.core.technology_selector import select_technologies
from heatscout.core.economics import economic_analysis

EXAMPLES = [
    "birrificio", "cartiera", "caseificio", "ceramica", "chimica",
    "complesso_multi_stream", "data_center", "fonderia", "tessile", "vetreria",
]

SNAPSHOTS_PATH = Path(__file__).parent / "snapshots" / "golden_examples.json"


def generate_snapshots() -> dict:
    all_snapshots = {}
    for ex_id in EXAMPLES:
        streams, meta = load_example(ex_id)
        T_amb = meta.get("T_ambient", 25)
        snapshot = {
            "metadata": meta,
            "n_streams": len(streams),
            "analyses": [],
            "recommendations": [],
            "economics": [],
        }
        for s in streams:
            snapshot["analyses"].append(analyze_stream(s, T_amb))
            recs = select_technologies(s)
            for r in recs:
                snapshot["recommendations"].append({
                    "stream": r.stream_name,
                    "tech_id": r.technology.id,
                    "Q_available_kW": r.Q_available_kW,
                    "Q_recovered_kW": r.Q_recovered_kW,
                    "E_recovered_MWh": r.E_recovered_MWh,
                    "efficiency": r.efficiency,
                    "savings_EUR": r.savings_EUR,
                })
                econ = economic_analysis(r)
                snapshot["economics"].append({
                    "stream": r.stream_name,
                    "tech_id": r.technology.id,
                    "capex_EUR": econ.capex_EUR,
                    "payback_years": econ.payback_years,
                    "npv_EUR": econ.npv_EUR,
                    "irr_pct": econ.irr_pct,
                })
        all_snapshots[ex_id] = snapshot
    return all_snapshots


if __name__ == "__main__":
    print("ATTENZIONE: stai rigenerando le snapshot golden.")
    print("Questo deve essere fatto SOLO dopo review umana dei nuovi valori.")
    resp = input("Continuare? (y/N): ")
    if resp.lower() != "y":
        print("Annullato.")
        sys.exit(0)

    data = generate_snapshots()
    with open(SNAPSHOTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    total_recs = sum(len(v["recommendations"]) for v in data.values())
    print(f"Salvate {len(data)} snapshot con {total_recs} raccomandazioni totali.")
    print(f"File: {SNAPSHOTS_PATH}")
