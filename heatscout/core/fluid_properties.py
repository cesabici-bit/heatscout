"""Thermophysical fluid properties via CoolProp and custom correlations."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import CoolProp.CoolProp as CP

# ── Load fluid database ──────────────────────────────────────────────────────

_FLUIDS_PATH = Path(__file__).parent.parent / "data" / "fluids.json"


@lru_cache(maxsize=1)
def _load_fluids_db() -> dict:
    with open(_FLUIDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {fluid["id"]: fluid for fluid in data["fluids"]}


def get_fluid_info(fluid_id: str) -> dict:
    """Return fluid information from the database."""
    db = _load_fluids_db()
    if fluid_id not in db:
        raise ValueError(f"Fluid '{fluid_id}' not found. Available: {list(db.keys())}")
    return db[fluid_id]


# ── Custom correlations for non-CoolProp fluids ─────────────────────────────


def _cp_fumi_gas_naturale(T_celsius: float) -> float:
    """Cp natural gas flue gas [kJ/kgK].

    Polynomial correlation based on typical composition
    (71% N2, 15% CO2, 12% H2O, 2% O2).
    Valid for T = 50-1200°C.
    Source: Incropera, Fundamentals of Heat and Mass Transfer, Table A.4
    """
    T = T_celsius
    return 1.005 + 1.79e-4 * T + 2.22e-7 * T**2 - 6.94e-11 * T**3


def _cp_fumi_gasolio(T_celsius: float) -> float:
    """Cp diesel flue gas [kJ/kgK].

    Typical composition: 73% N2, 13% CO2, 10% H2O, 4% O2.
    Slightly lower than natural gas flue gas (less H2O).
    """
    T = T_celsius
    return 1.000 + 1.65e-4 * T + 2.10e-7 * T**2 - 6.50e-11 * T**3


def _cp_olio_diatermico(T_celsius: float) -> float:
    """Cp thermal oil [kJ/kgK].

    Typical linear correlation for synthetic oils (Therminol 66, Dowtherm A).
    Valid for T = 20-350°C.
    Source: Therminol 66 manufacturer data.
    """
    return 1.68 + 0.00164 * T_celsius


def _cp_glicole_etilenico_30(T_celsius: float) -> float:
    """Cp ethylene glycol 30% vol [kJ/kgK].

    Water-glycol mixture. Cp decreases compared to pure water.
    Valid for T = -15 to 110°C.
    Source: ASHRAE Handbook, Fundamentals.
    """
    return 3.50 + 0.0012 * T_celsius


# Custom fluid map → cp(T) function
_CUSTOM_CP = {
    "fumi_gas_naturale": _cp_fumi_gas_naturale,
    "fumi_gasolio": _cp_fumi_gasolio,
    "olio_diatermico": _cp_olio_diatermico,
    "glicole_etilenico_30": _cp_glicole_etilenico_30,
}

# Approximate densities for custom fluids [kg/m3]
_CUSTOM_DENSITY = {
    "fumi_gas_naturale": lambda T: 1.1 * 273.15 / (T + 273.15),
    "fumi_gasolio": lambda T: 1.15 * 273.15 / (T + 273.15),
    "olio_diatermico": lambda T: 1020 - 0.63 * T,
    "glicole_etilenico_30": lambda T: 1042 - 0.5 * T,
}


# ── Public functions ────────────────────────────────────────────────────────


def get_cp(fluid_id: str, T_celsius: float, P: float = 101325) -> float:
    """Specific heat at constant pressure [kJ/kgK].

    Args:
        fluid_id: ID fluido dal database
        T_celsius: Temperatura [°C]
        P: Pressione [Pa], default 1 atm

    Returns:
        cp in kJ/kgK
    """
    if fluid_id in _CUSTOM_CP:
        cp = _CUSTOM_CP[fluid_id](T_celsius)
    else:
        info = get_fluid_info(fluid_id)
        coolprop_name = info["coolprop_name"]
        if coolprop_name is None:
            raise ValueError(f"Fluido '{fluid_id}' non ha nome CoolProp né correlazione custom")
        T_K = T_celsius + 273.15
        # CoolProp returns in J/kgK, convert to kJ/kgK
        cp = CP.PropsSI("Cpmass", "T", T_K, "P", P, coolprop_name) / 1000.0

    assert 0.1 < cp < 15, (
        f"cp={cp:.3f} kJ/kgK fuori range plausibile "
        f"per {fluid_id} a {T_celsius}°C. "
        f"Range atteso: 0.1-15 kJ/kgK (aria~1.0, acqua~4.2, glicole~3.5)"
    )
    return cp


def get_density(fluid_id: str, T_celsius: float, P: float = 101325) -> float:
    """Density [kg/m3].

    Args:
        fluid_id: ID fluido dal database
        T_celsius: Temperatura [°C]
        P: Pressione [Pa]

    Returns:
        densità in kg/m3
    """
    if fluid_id in _CUSTOM_DENSITY:
        return _CUSTOM_DENSITY[fluid_id](T_celsius)

    info = get_fluid_info(fluid_id)
    coolprop_name = info["coolprop_name"]
    if coolprop_name is None:
        raise ValueError(f"Fluido '{fluid_id}' non ha nome CoolProp né correlazione custom")

    T_K = T_celsius + 273.15
    return CP.PropsSI("Dmass", "T", T_K, "P", P, coolprop_name)


def get_properties(fluid_id: str, T_celsius: float, P: float = 101325) -> dict:
    """Complete thermophysical properties.

    Returns:
        dict con cp [kJ/kgK], rho [kg/m3], mu [Pa.s], k [W/mK]
        (mu e k solo per fluidi CoolProp)
    """
    result = {
        "cp_kJ_kgK": get_cp(fluid_id, T_celsius, P),
        "rho_kg_m3": get_density(fluid_id, T_celsius, P),
        "mu_Pa_s": None,
        "k_W_mK": None,
    }

    info = get_fluid_info(fluid_id)
    coolprop_name = info["coolprop_name"]
    if coolprop_name is not None:
        T_K = T_celsius + 273.15
        try:
            result["mu_Pa_s"] = CP.PropsSI("viscosity", "T", T_K, "P", P, coolprop_name)
            result["k_W_mK"] = CP.PropsSI("conductivity", "T", T_K, "P", P, coolprop_name)
        except Exception:
            pass  # Alcune proprietà non disponibili per tutti i fluidi/fasi

    return result
