"""Modelli di efficienza per tecnologie di recupero calore.

Ogni funzione è documentata con la formula e la fonte bibliografica.
"""

from __future__ import annotations


def he_effectiveness(T_hot_in: float, T_cold_in: float, he_type: str = "gas_gas") -> float:
    """Effectiveness di uno scambiatore di calore (ε = Q_reale / Q_max).

    Formula semplificata basata sul tipo di scambiatore:
    - gas-gas: ε = 0.50 - 0.75 (tipicamente ~0.65)
    - gas-liquido: ε = 0.55 - 0.80 (tipicamente ~0.70)
    - liquido-liquido: ε = 0.60 - 0.85 (tipicamente ~0.75)

    L'effectiveness dipende dal NTU e dal rapporto Cmin/Cmax,
    ma qui usiamo valori tipici per una stima di primo livello.

    Fonte: Incropera, Fundamentals of Heat and Mass Transfer, Ch. 11

    Args:
        T_hot_in: Temperatura ingresso lato caldo [°C]
        T_cold_in: Temperatura ingresso lato freddo [°C]
        he_type: "gas_gas", "gas_liquid", "liquid_liquid"

    Returns:
        effectiveness ε (0-1)
    """
    base = {
        "gas_gas": 0.62,
        "gas_liquid": 0.68,
        "liquid_liquid": 0.75,
    }.get(he_type, 0.65)

    # Bonus per delta T grande (più facile raggiungere alta ε)
    delta_T = abs(T_hot_in - T_cold_in)
    if delta_T > 200:
        base += 0.05
    elif delta_T < 30:
        base -= 0.05

    return max(0.40, min(0.85, base))


def heat_pump_cop(T_source: float, T_sink: float, eta_carnot: float = 0.45) -> float:
    """COP di una pompa di calore.

    COP = η_Carnot × T_sink_K / (T_sink_K - T_source_K)

    dove η_Carnot = 0.40-0.50 è il rapporto tra COP reale e COP di Carnot.

    Fonte: ASHRAE Handbook HVAC Systems and Equipment, Ch. 8

    Args:
        T_source: Temperatura sorgente fredda [°C]
        T_sink: Temperatura di mandata [°C]
        eta_carnot: Frazione del COP di Carnot (default 0.50)

    Returns:
        COP (sempre ≥ 1.5)
    """
    T_source_K = T_source + 273.15
    T_sink_K = T_sink + 273.15

    if T_sink_K <= T_source_K:
        return 10.0  # Non serve pompa di calore, ma ritorniamo COP alto

    cop_carnot = T_sink_K / (T_sink_K - T_source_K)
    cop_real = eta_carnot * cop_carnot

    return max(1.5, min(6.0, cop_real))


def orc_efficiency(T_source: float, T_sink: float = 30.0, eta_fraction: float = 0.45) -> float:
    """Efficienza di un ciclo ORC (Organic Rankine Cycle).

    η_ORC = η_fraction × η_Carnot = η_fraction × (1 - T_sink_K / T_source_K)

    η_fraction = 0.40-0.50 per ORC commerciali.

    Fonte: Quoilin et al., "Techno-economic survey of ORC systems",
           Renewable & Sustainable Energy Reviews, 2013

    Args:
        T_source: Temperatura sorgente calda [°C]
        T_sink: Temperatura di condensazione [°C]
        eta_fraction: Frazione del rendimento di Carnot

    Returns:
        Efficienza elettrica (0-0.25)
    """
    T_source_K = T_source + 273.15
    T_sink_K = T_sink + 273.15

    if T_source_K <= T_sink_K:
        return 0.0

    eta_carnot = 1 - T_sink_K / T_source_K
    eta_orc = eta_fraction * eta_carnot

    return max(0.0, min(0.25, eta_orc))


def preheating_savings(T_exhaust: float, T_air_in: float = 20.0,
                       T_air_out: float | None = None,
                       effectiveness: float = 0.60) -> float:
    """Percentuale di risparmio combustibile dal pre-riscaldamento aria.

    L'aria comburente viene pre-riscaldata dai fumi, riducendo il
    combustibile necessario per raggiungere la temperatura di processo.

    savings ≈ (T_air_out - T_air_in) / T_fiamma × 100%

    Con T_fiamma ≈ 1800°C per gas naturale.

    Fonte: Baukal, "Industrial Combustion Pollution and Control", Ch. 6

    Args:
        T_exhaust: Temperatura fumi [°C]
        T_air_in: Temperatura aria ambiente [°C]
        T_air_out: Temperatura aria pre-riscaldata [°C] (se None, calcolata da effectiveness)
        effectiveness: Effectiveness dello scambiatore (default 0.60)

    Returns:
        Percentuale di risparmio combustibile (0-30%)
    """
    if T_air_out is None:
        T_air_out = T_air_in + effectiveness * (T_exhaust - T_air_in)

    T_flame = 1800.0  # °C, temperatura di fiamma adiabatica gas naturale
    savings_pct = (T_air_out - T_air_in) / T_flame * 100

    return max(0.0, min(30.0, savings_pct))
