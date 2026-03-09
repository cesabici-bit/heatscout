"""Database delle tecnologie di recupero calore."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_TECH_PATH = Path(__file__).parent.parent / "data" / "technologies.json"


@dataclass
class Technology:
    """Rappresenta una tecnologia di recupero calore."""

    id: str
    name: str
    description: str
    T_min: float  # °C
    T_max: float  # °C
    Q_min: float  # kW
    Q_max: float  # kW
    efficiency_range: tuple[float, float]
    lifetime_years: int
    applicable_fluids: list[str]
    pros: list[str]
    cons: list[str]

    def is_compatible(self, T_mean: float, Q_kW: float, fluid_type: str = "") -> bool:
        """Verifica se la tecnologia è compatibile con lo stream.

        Args:
            T_mean: Temperatura media dello stream [°C]
            Q_kW: Potenza termica dello stream [kW]
            fluid_type: ID fluido (opzionale, per check compatibilità)
        """
        if not (self.T_min <= T_mean <= self.T_max):
            return False
        if not (self.Q_min <= Q_kW <= self.Q_max):
            return False
        if fluid_type and self.applicable_fluids:
            if fluid_type not in self.applicable_fluids:
                return False
        return True

    @property
    def efficiency_typical(self) -> float:
        """Efficienza tipica (media del range)."""
        return (self.efficiency_range[0] + self.efficiency_range[1]) / 2


@lru_cache(maxsize=1)
def load_technologies() -> list[Technology]:
    """Carica tutte le tecnologie dal database JSON."""
    with open(_TECH_PATH, encoding="utf-8") as f:
        data = json.load(f)

    techs = []
    for t in data["technologies"]:
        techs.append(
            Technology(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                T_min=t["T_min"],
                T_max=t["T_max"],
                Q_min=t["Q_min"],
                Q_max=t["Q_max"],
                efficiency_range=tuple(t["efficiency_range"]),
                lifetime_years=t["lifetime_years"],
                applicable_fluids=t.get("applicable_fluids", []),
                pros=t.get("pros", []),
                cons=t.get("cons", []),
            )
        )
    return techs
