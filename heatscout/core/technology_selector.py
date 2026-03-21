"""Heat recovery technology selection algorithm."""

from __future__ import annotations

from dataclasses import dataclass

from heatscout.core.stream import ThermalStream
from heatscout.core.stream_analyzer import calc_thermal_power
from heatscout.knowledge.efficiency_models import (
    he_effectiveness,
    heat_pump_cop,
    orc_efficiency,
    preheating_savings,
)
from heatscout.knowledge.tech_database import Technology, load_technologies


@dataclass
class TechRecommendation:
    """Recommendation of a technology for a specific stream."""

    technology: Technology
    stream_name: str
    Q_available_kW: float  # Thermal power of the stream
    Q_recovered_kW: float  # Recoverable power with this technology
    E_recovered_MWh: float  # Annual recoverable energy
    efficiency: float  # Technology efficiency/COP
    savings_EUR: float  # Estimated annual savings
    is_heat_pump: bool = False  # True if heat pump (COP > 1)

    @property
    def recovery_fraction(self) -> float:
        """Fraction of recovered heat relative to available."""
        if self.Q_available_kW <= 0:
            return 0
        return self.Q_recovered_kW / self.Q_available_kW


def _calc_efficiency_for_tech(tech: Technology, stream: ThermalStream) -> float:
    """Calculate the specific efficiency of the technology for the given stream."""

    if tech.id == "recuperatore_gas_gas":
        return he_effectiveness(stream.T_in, 20, "gas_gas")

    elif tech.id == "economizzatore_gas_liquido":
        return he_effectiveness(stream.T_in, 20, "gas_liquid")

    elif tech.id == "scambiatore_liquido_liquido":
        return he_effectiveness(stream.T_in, 20, "liquid_liquid")

    elif tech.id == "caldaia_recupero":
        return he_effectiveness(stream.T_in, 100, "gas_liquid") * 0.90

    elif tech.id == "pompa_calore_aria_acqua":
        return heat_pump_cop(stream.T_mean, 60)  # Produce acqua a 60°C

    elif tech.id == "pompa_calore_acqua_acqua":
        return heat_pump_cop(stream.T_mean, 60)  # Produce acqua a 60°C

    elif tech.id == "orc":
        return orc_efficiency(stream.T_mean, 30)

    elif tech.id == "preriscaldamento_aria":
        return preheating_savings(stream.T_in) / 100.0

    else:
        return tech.efficiency_typical


def select_technologies(
    stream: ThermalStream,
    energy_price_EUR_kWh: float = 0.08,
    T_sink: float = 60.0,
) -> list[TechRecommendation]:
    """Select compatible technologies for a stream, sorted by savings.

    Args:
        stream: ThermalStream to analyze
        energy_price_EUR_kWh: Thermal energy price [€/kWh]
        T_sink: Temperature of recovered heat usage [°C]

    Returns:
        List of TechRecommendation sorted by savings_EUR descending
    """
    Q_kW = calc_thermal_power(stream)
    technologies = load_technologies()

    recommendations = []

    for tech in technologies:
        # Check compatibility
        if not tech.is_compatible(stream.T_mean, Q_kW, stream.fluid_type):
            continue

        # Calculate specific efficiency
        eff = _calc_efficiency_for_tech(tech, stream)
        is_hp = tech.id in ("pompa_calore_aria_acqua", "pompa_calore_acqua_acqua")
        is_orc = tech.id == "orc"

        if is_hp:
            # For heat pumps: Q_recovered = Q_available (at given COP)
            # Savings are on heat produced: Q_out = Q_source + W_el
            # where W_el = Q_out / COP. Savings = Q_out - W_el (cost)
            cop = eff
            Q_source = Q_kW * 0.85  # 85% del calore disponibile catturato
            Q_out = Q_source * cop / (cop - 1)  # Calore utile prodotto
            Q_recovered = Q_out
            E_recovered = Q_recovered * stream.annual_hours / 1000
            # Costo elettrico: W_el = Q_out / COP
            W_el_kW = Q_out / cop
            # Risparmio netto = valore calore prodotto - costo elettricità
            elec_price = energy_price_EUR_kWh * 2.5  # Prezzo elettrico ≈ 2.5× termico
            savings = (
                Q_recovered * energy_price_EUR_kWh - W_el_kW * elec_price
            ) * stream.annual_hours
        elif is_orc:
            # ORC produces electricity
            Q_recovered = Q_kW * eff  # kW elettrici
            E_recovered = Q_recovered * stream.annual_hours / 1000  # MWh elettrici
            elec_price = energy_price_EUR_kWh * 2.5
            savings = E_recovered * 1000 * elec_price  # Valore elettricità prodotta
        else:
            # Heat exchangers: direct recovery
            Q_recovered = Q_kW * eff
            E_recovered = Q_recovered * stream.annual_hours / 1000
            savings = E_recovered * 1000 * energy_price_EUR_kWh

        if Q_recovered <= 0 or savings <= 0:
            continue

        recommendations.append(
            TechRecommendation(
                technology=tech,
                stream_name=stream.name,
                Q_available_kW=round(Q_kW, 1),
                Q_recovered_kW=round(Q_recovered, 1),
                E_recovered_MWh=round(E_recovered, 1),
                efficiency=round(eff, 3),
                savings_EUR=round(savings, 0),
                is_heat_pump=is_hp,
            )
        )

    # Sort by savings descending
    recommendations.sort(key=lambda r: r.savings_EUR, reverse=True)
    return recommendations
