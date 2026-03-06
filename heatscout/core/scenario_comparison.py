"""Confronto scenari: combinazioni diverse di tecnologie."""

from __future__ import annotations

from dataclasses import dataclass

from heatscout.core.economics import EconomicResult


@dataclass
class Scenario:
    """Un scenario = una combinazione di tecnologie selezionate."""

    name: str
    econ_results: list[EconomicResult]

    @property
    def total_capex(self) -> float:
        return sum(e.total_investment_EUR for e in self.econ_results)

    @property
    def total_savings_annual(self) -> float:
        return sum(e.annual_savings_EUR for e in self.econ_results)

    @property
    def total_npv(self) -> float:
        return sum(e.npv_EUR for e in self.econ_results)

    @property
    def average_payback(self) -> float:
        paybacks = [e.payback_years for e in self.econ_results if e.payback_years < 50]
        if not paybacks:
            return float("inf")
        return sum(paybacks) / len(paybacks)

    @property
    def best_payback(self) -> float:
        paybacks = [e.payback_years for e in self.econ_results]
        return min(paybacks) if paybacks else float("inf")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "n_technologies": len(self.econ_results),
            "total_capex_EUR": round(self.total_capex, 0),
            "total_savings_annual_EUR": round(self.total_savings_annual, 0),
            "total_npv_EUR": round(self.total_npv, 0),
            "average_payback_years": round(self.average_payback, 1),
            "best_payback_years": round(self.best_payback, 1),
        }


def compare_scenarios(scenarios: list[Scenario]) -> list[dict]:
    """Confronta una lista di scenari.

    Returns:
        Lista di dict con metriche per ogni scenario, ordinata per NPV decrescente.
    """
    results = [s.to_dict() for s in scenarios]
    results.sort(key=lambda r: r["total_npv_EUR"], reverse=True)

    # Aggiungi ranking
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results
