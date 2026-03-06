"""Correlazioni di costo per tecnologie di recupero calore."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_COSTS_PATH = Path(__file__).parent.parent / "data" / "costs.json"


@lru_cache(maxsize=1)
def _load_costs() -> dict:
    with open(_COSTS_PATH, encoding="utf-8") as f:
        return json.load(f)["costs"]


def estimate_capex(tech_id: str, Q_kW: float) -> dict:
    """Stima CAPEX per una tecnologia.

    Formula: CAPEX = a × Q^b [EUR]

    Args:
        tech_id: ID della tecnologia
        Q_kW: Potenza termica recuperabile [kW]

    Returns:
        dict con min, medio, max in EUR
    """
    costs = _load_costs()
    if tech_id not in costs:
        raise ValueError(f"Tecnologia '{tech_id}' non ha correlazione di costo")

    c = costs[tech_id]
    capex_mid = c["capex_a"] * Q_kW ** c["capex_b"]
    capex_min = c["capex_a_min"] * Q_kW ** c["capex_b"]
    capex_max = c["capex_a_max"] * Q_kW ** c["capex_b"]

    return {
        "min": round(capex_min, 0),
        "medio": round(capex_mid, 0),
        "max": round(capex_max, 0),
    }


def estimate_opex(tech_id: str, capex: float) -> float:
    """Stima OPEX annuo [EUR/anno] come percentuale del CAPEX.

    Args:
        tech_id: ID della tecnologia
        capex: CAPEX in EUR

    Returns:
        OPEX in EUR/anno
    """
    costs = _load_costs()
    if tech_id not in costs:
        raise ValueError(f"Tecnologia '{tech_id}' non ha correlazione di costo")

    return round(capex * costs[tech_id]["opex_pct"], 0)


def estimate_total_investment(tech_id: str, Q_kW: float) -> dict:
    """Stima investimento totale (CAPEX + installazione).

    Args:
        tech_id: ID della tecnologia
        Q_kW: Potenza termica [kW]

    Returns:
        dict con CAPEX, installazione, totale (min/medio/max)
    """
    costs = _load_costs()
    if tech_id not in costs:
        raise ValueError(f"Tecnologia '{tech_id}' non ha correlazione di costo")

    capex = estimate_capex(tech_id, Q_kW)
    inst_factor = costs[tech_id]["installation_factor"]

    return {
        "capex": capex,
        "installation_factor": inst_factor,
        "total_min": round(capex["min"] * inst_factor, 0),
        "total_medio": round(capex["medio"] * inst_factor, 0),
        "total_max": round(capex["max"] * inst_factor, 0),
    }
