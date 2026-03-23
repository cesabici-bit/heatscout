"""Factory heat balance: aggregation and summary."""

from __future__ import annotations

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.stream_analyzer import analyze_stream, calc_thermal_power


class FactoryHeatBalance:
    """Overall factory heat balance.

    Aggregates multiple ThermalStreams and computes totals, breakdown by
    temperature classification, and percentages.
    """

    def __init__(self, factory_name: str = "", T_ambient: float = 25.0):
        self.factory_name = factory_name
        self.T_ambient = T_ambient
        self._streams: list[ThermalStream] = []
        self._results: list[dict] | None = None

        # Energy input (optional)
        self._energy_input_kW: float | None = None
        self._energy_input_source: str = ""

    def add_stream(self, stream: ThermalStream):
        """Add a stream to the balance."""
        self._streams.append(stream)
        self._results = None  # invalidate cache

    @property
    def streams(self) -> list[ThermalStream]:
        return list(self._streams)

    def set_energy_input(self, fuel_type: str, consumption: float, unit: str):
        """Set direct energy input.

        Args:
            fuel_type: Fuel type ("gas_naturale", "gasolio", "elettrico")
            consumption: Consumption in the period
            unit: Unit ("Sm3/anno", "kWh/anno", "MWh/anno", "tep/anno")
        """
        # Conversions to average annual kW (assuming 8760 h/year)
        conversions = {
            "Sm3/anno": {"gas_naturale": 9.59},  # kWh/Sm3 (natural gas LHV)
            "kWh/anno": {"_any": 1.0},
            "MWh/anno": {"_any": 1000.0},
            "tep/anno": {"_any": 11630.0},  # kWh/tep
        }

        if unit not in conversions:
            raise ValueError(f"Unit '{unit}' not supported. Available: {list(conversions.keys())}")

        conv = conversions[unit]
        factor = conv.get(fuel_type, conv.get("_any"))
        if factor is None:
            raise ValueError(f"Conversion not available for {fuel_type} in {unit}")

        energy_kWh_anno = consumption * factor
        self._energy_input_kW = energy_kWh_anno / 8760.0
        self._energy_input_source = f"{consumption} {unit} ({fuel_type})"
        self._results = None

    def estimate_energy_input(self, efficiency: float = 0.85):
        """Estimate energy input as total waste heat / (1 - efficiency).

        The idea: if the factory has 85% efficiency, waste heat is the missing 15%,
        so input = waste / (1 - 0.85).
        In reality it's more complex, but serves as a first-order estimate.
        """
        total_waste_kW = sum(
            calc_thermal_power(s) for s in self._streams if s.stream_type == StreamType.HOT_WASTE
        )
        if total_waste_kW > 0 and 0 < efficiency < 1:
            self._energy_input_kW = total_waste_kW / (1.0 - efficiency)
        else:
            self._energy_input_kW = None
        self._energy_input_source = f"Estimated (efficiency={efficiency * 100:.0f}%)"
        self._results = None

    def calculate(self) -> list[dict]:
        """Compute the analysis for all streams.

        Returns:
            List of dicts with results for each stream.
        """
        self._results = [analyze_stream(s, self.T_ambient) for s in self._streams]
        return self._results

    def summary(self) -> dict:
        """Overall heat balance summary.

        Returns:
            Dict with totals, percentages, breakdown by stream and temperature class.
        """
        if self._results is None:
            self.calculate()

        results = self._results

        # Totals by stream type
        hot_waste = [r for r in results if r["stream_type"] == "hot_waste"]
        cold_demand = [r for r in results if r["stream_type"] == "cold_demand"]

        total_waste_kW = sum(r["Q_kW"] for r in hot_waste)
        total_waste_MWh = sum(r["E_MWh_anno"] for r in hot_waste)
        total_waste_Ex = sum(r["Ex_kW"] for r in hot_waste)

        total_demand_kW = sum(r["Q_kW"] for r in cold_demand)
        total_demand_MWh = sum(r["E_MWh_anno"] for r in cold_demand)

        # Breakdown by temperature class (hot_waste only)
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

        # Waste percentage relative to input (if available)
        if self._energy_input_kW and self._energy_input_kW > 0:
            summary["waste_pct_of_input"] = round(total_waste_kW / self._energy_input_kW * 100, 1)
        else:
            summary["waste_pct_of_input"] = None

        return summary

    def pinch_analysis(self, dT_min: float = 10.0):
        """Run Pinch Analysis on this factory's streams.

        Requires at least 1 hot (HOT_WASTE) and 1 cold (COLD_DEMAND) stream.

        Args:
            dT_min: Minimum approach temperature [°C], default 10.

        Returns:
            PinchResult with utility targets, pinch point, and plotting data.

        Raises:
            ValueError: If missing hot or cold streams, or dT_min <= 0.
        """
        from heatscout.core.pinch import pinch_analysis  # lazy import

        hot = [s for s in self._streams if s.stream_type == StreamType.HOT_WASTE]
        cold = [s for s in self._streams if s.stream_type == StreamType.COLD_DEMAND]
        if not hot:
            raise ValueError("Pinch analysis requires at least 1 hot stream (HOT_WASTE)")
        if not cold:
            raise ValueError("Pinch analysis requires at least 1 cold stream (COLD_DEMAND)")
        return pinch_analysis(self._streams, dT_min)
