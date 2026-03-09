"""Analisi termica degli stream: potenza, energia annuale, exergia."""

from __future__ import annotations

from heatscout.core.fluid_properties import get_cp
from heatscout.core.stream import ThermalStream


def calc_thermal_power(stream: ThermalStream, detailed: bool = False) -> float | dict:
    """Calcola la potenza termica dello stream [kW].

    Q = m_dot × cp_medio × |T_in - T_out|

    cp_medio è calcolato come media aritmetica tra cp(T_in) e cp(T_out).

    Args:
        stream: ThermalStream da analizzare
        detailed: se True, ritorna dict con risultato e intermedi (show-your-work)

    Returns:
        Potenza termica in kW, oppure dict con intermedi se detailed=True
    """
    cp_in = get_cp(stream.fluid_type, stream.T_in, stream.pressure)
    cp_out = get_cp(stream.fluid_type, stream.T_out, stream.pressure)
    cp_mean = (cp_in + cp_out) / 2  # kJ/kgK

    Q = stream.mass_flow * cp_mean * stream.delta_T  # kW

    assert Q >= 0, (
        f"Q={Q:.1f} kW negativo per {stream.name}: "
        f"m_dot={stream.mass_flow}, cp_mean={cp_mean:.3f}, dT={stream.delta_T}"
    )

    if detailed:
        return {
            "Q_kW": Q,
            "_steps": {
                "fluid": stream.fluid_type,
                "T_in_C": stream.T_in,
                "T_out_C": stream.T_out,
                "delta_T_K": stream.delta_T,
                "cp_at_T_in_kJ_kgK": round(cp_in, 4),
                "cp_at_T_out_kJ_kgK": round(cp_out, 4),
                "cp_mean_kJ_kgK": round(cp_mean, 4),
                "mass_flow_kg_s": stream.mass_flow,
                "formula": "Q = m_dot × cp_mean × |T_in - T_out|",
            },
        }
    return Q


def calc_annual_energy(stream: ThermalStream) -> float:
    """Calcola l'energia termica annuale [MWh/anno].

    E = Q × ore/giorno × giorni/anno / 1000

    Returns:
        Energia annuale in MWh/anno
    """
    Q_kW = calc_thermal_power(stream)
    E_MWh = Q_kW * stream.annual_hours / 1000.0
    return E_MWh


def classify_temperature(T_celsius: float) -> str:
    """Classifica la temperatura in alta/media/bassa.

    - Alta: > 250°C
    - Media: 80-250°C
    - Bassa: < 80°C
    """
    if T_celsius > 250:
        return "alta"
    elif T_celsius >= 80:
        return "media"
    else:
        return "bassa"


def calc_exergy(stream: ThermalStream, T_ambient: float = 25.0) -> float:
    """Calcola l'exergia (disponibilità termodinamica) dello stream [kW].

    Ex = Q × (1 - T_amb / T_stream_medio)

    dove le temperature sono in Kelvin.

    Args:
        stream: ThermalStream da analizzare
        T_ambient: Temperatura ambiente [°C], default 25°C

    Returns:
        Exergia in kW. Può essere negativa se T_stream < T_ambiente.
    """
    Q_kW = calc_thermal_power(stream)
    T_mean_K = stream.T_mean + 273.15
    T_amb_K = T_ambient + 273.15

    if T_mean_K <= 0:
        return 0.0

    carnot_factor = 1.0 - T_amb_K / T_mean_K
    Ex = Q_kW * carnot_factor

    assert Ex <= Q_kW + 1e-6, (
        f"Exergia ({Ex:.1f} kW) > Potenza ({Q_kW:.1f} kW): "
        f"viola 2o principio. carnot_factor={carnot_factor:.3f}, "
        f"T_mean={stream.T_mean}°C, T_amb={T_ambient}°C"
    )
    return Ex


def analyze_stream(stream: ThermalStream, T_ambient: float = 25.0) -> dict:
    """Analisi completa di un singolo stream.

    Returns:
        dict con Q_kW, E_MWh_anno, Ex_kW, T_class, quality_ratio
    """
    Q_kW = calc_thermal_power(stream)
    E_MWh = calc_annual_energy(stream)
    Ex_kW = calc_exergy(stream, T_ambient)
    T_class = classify_temperature(stream.T_mean)
    quality_ratio = Ex_kW / Q_kW if Q_kW > 0 else 0.0

    return {
        "name": stream.name,
        "stream_type": stream.stream_type.value,
        "fluid_type": stream.fluid_type,
        "T_in": stream.T_in,
        "T_out": stream.T_out,
        "T_mean": stream.T_mean,
        "Q_kW": round(Q_kW, 1),
        "E_MWh_anno": round(E_MWh, 1),
        "Ex_kW": round(Ex_kW, 1),
        "T_class": T_class,
        "quality_ratio": round(quality_ratio, 3),
    }
