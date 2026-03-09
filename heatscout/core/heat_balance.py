"""Bilancio termico di fabbrica: aggregazione e riepilogo."""

from __future__ import annotations

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.stream_analyzer import analyze_stream, calc_thermal_power


class FactoryHeatBalance:
    """Bilancio termico complessivo di una fabbrica.

    Aggrega più ThermalStream e calcola totali, breakdown per
    classificazione di temperatura, e percentuali.
    """

    def __init__(self, factory_name: str = "", T_ambient: float = 25.0):
        self.factory_name = factory_name
        self.T_ambient = T_ambient
        self._streams: list[ThermalStream] = []
        self._results: list[dict] | None = None

        # Input energetico (opzionale)
        self._energy_input_kW: float | None = None
        self._energy_input_source: str = ""

    def add_stream(self, stream: ThermalStream):
        """Aggiunge uno stream al bilancio."""
        self._streams.append(stream)
        self._results = None  # invalida cache

    @property
    def streams(self) -> list[ThermalStream]:
        return list(self._streams)

    def set_energy_input(self, fuel_type: str, consumption: float, unit: str):
        """Imposta input energetico diretto.

        Args:
            fuel_type: Tipo combustibile ("gas_naturale", "gasolio", "elettrico")
            consumption: Consumo nel periodo
            unit: Unità ("Sm3/anno", "kWh/anno", "MWh/anno", "tep/anno")
        """
        # Conversioni a kW medio annuo (assumendo 8760 h/anno)
        conversions = {
            "Sm3/anno": {"gas_naturale": 9.59},  # kWh/Sm3 (PCI gas naturale)
            "kWh/anno": {"_any": 1.0},
            "MWh/anno": {"_any": 1000.0},
            "tep/anno": {"_any": 11630.0},  # kWh/tep
        }

        if unit not in conversions:
            raise ValueError(
                f"Unità '{unit}' non supportata. Disponibili: {list(conversions.keys())}"
            )

        conv = conversions[unit]
        factor = conv.get(fuel_type, conv.get("_any"))
        if factor is None:
            raise ValueError(f"Conversione non disponibile per {fuel_type} in {unit}")

        energy_kWh_anno = consumption * factor
        self._energy_input_kW = energy_kWh_anno / 8760.0
        self._energy_input_source = f"{consumption} {unit} ({fuel_type})"
        self._results = None

    def estimate_energy_input(self, efficiency: float = 0.85):
        """Stima l'input energetico come somma scarti / (1-efficiency).

        L'idea: se la fabbrica ha efficienza 85%, il calore di scarto è il 15%
        mancante, quindi input = scarto / (1 - 0.85).
        In realtà è più complesso, ma serve come stima di primo livello.
        """
        total_waste_kW = sum(
            calc_thermal_power(s) for s in self._streams if s.stream_type == StreamType.HOT_WASTE
        )
        if total_waste_kW > 0 and 0 < efficiency < 1:
            self._energy_input_kW = total_waste_kW / (1.0 - efficiency)
        else:
            self._energy_input_kW = None
        self._energy_input_source = f"Stimato (efficienza={efficiency * 100:.0f}%)"
        self._results = None

    def calculate(self) -> list[dict]:
        """Calcola l'analisi per tutti gli stream.

        Returns:
            Lista di dict con risultati per ogni stream
        """
        self._results = [analyze_stream(s, self.T_ambient) for s in self._streams]
        return self._results

    def summary(self) -> dict:
        """Riepilogo complessivo del bilancio termico.

        Returns:
            dict con totali, percentuali, breakdown per stream e per classe T.
        """
        if self._results is None:
            self.calculate()

        results = self._results

        # Totali per tipo stream
        hot_waste = [r for r in results if r["stream_type"] == "hot_waste"]
        cold_demand = [r for r in results if r["stream_type"] == "cold_demand"]

        total_waste_kW = sum(r["Q_kW"] for r in hot_waste)
        total_waste_MWh = sum(r["E_MWh_anno"] for r in hot_waste)
        total_waste_Ex = sum(r["Ex_kW"] for r in hot_waste)

        total_demand_kW = sum(r["Q_kW"] for r in cold_demand)
        total_demand_MWh = sum(r["E_MWh_anno"] for r in cold_demand)

        # Breakdown per classe temperatura (solo hot_waste)
        by_class = {"alta": [], "media": [], "bassa": []}
        for r in hot_waste:
            by_class[r["T_class"]].append(r)

        class_summary = {}
        for cls, streams in by_class.items():
            class_summary[cls] = {
                "count": len(streams),
                "Q_kW": sum(r["Q_kW"] for r in streams),
                "E_MWh_anno": sum(r["E_MWh_anno"] for r in streams),
                "pct_of_waste": (
                    sum(r["Q_kW"] for r in streams) / total_waste_kW * 100
                    if total_waste_kW > 0
                    else 0
                ),
            }

        summary = {
            "factory_name": self.factory_name,
            "T_ambient": self.T_ambient,
            "n_streams": len(results),
            "n_hot_waste": len(hot_waste),
            "n_cold_demand": len(cold_demand),
            "total_waste_kW": round(total_waste_kW, 1),
            "total_waste_MWh_anno": round(total_waste_MWh, 1),
            "total_waste_exergy_kW": round(total_waste_Ex, 1),
            "total_demand_kW": round(total_demand_kW, 1),
            "total_demand_MWh_anno": round(total_demand_MWh, 1),
            "by_temperature_class": class_summary,
            "stream_results": results,
            "energy_input_kW": self._energy_input_kW,
            "energy_input_source": self._energy_input_source,
        }

        # Percentuale di scarto rispetto all'input (se disponibile)
        if self._energy_input_kW and self._energy_input_kW > 0:
            summary["waste_pct_of_input"] = round(total_waste_kW / self._energy_input_kW * 100, 1)
        else:
            summary["waste_pct_of_input"] = None

        return summary
