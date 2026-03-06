"""Proprietà termofisiche dei fluidi via CoolProp e correlazioni custom."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import CoolProp.CoolProp as CP

# ── Caricamento database fluidi ──────────────────────────────────────────────

_FLUIDS_PATH = Path(__file__).parent.parent / "data" / "fluids.json"


@lru_cache(maxsize=1)
def _load_fluids_db() -> dict:
    with open(_FLUIDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {fluid["id"]: fluid for fluid in data["fluids"]}


def get_fluid_info(fluid_id: str) -> dict:
    """Ritorna le informazioni di un fluido dal database."""
    db = _load_fluids_db()
    if fluid_id not in db:
        raise ValueError(
            f"Fluido '{fluid_id}' non trovato. Disponibili: {list(db.keys())}"
        )
    return db[fluid_id]


# ── Correlazioni custom per fluidi non-CoolProp ─────────────────────────────


def _cp_fumi_gas_naturale(T_celsius: float) -> float:
    """Cp fumi gas naturale [kJ/kgK].

    Correlazione polinomiale basata su composizione tipica
    (71% N2, 15% CO2, 12% H2O, 2% O2).
    Valida per T = 50-1200°C.
    Fonte: Incropera, Fundamentals of Heat and Mass Transfer, Table A.4
    """
    T = T_celsius
    return 1.005 + 1.79e-4 * T + 2.22e-7 * T**2 - 6.94e-11 * T**3


def _cp_fumi_gasolio(T_celsius: float) -> float:
    """Cp fumi gasolio [kJ/kgK].

    Composizione tipica: 73% N2, 13% CO2, 10% H2O, 4% O2.
    Leggermente inferiore ai fumi gas naturale (meno H2O).
    """
    T = T_celsius
    return 1.000 + 1.65e-4 * T + 2.10e-7 * T**2 - 6.50e-11 * T**3


def _cp_olio_diatermico(T_celsius: float) -> float:
    """Cp olio diatermico [kJ/kgK].

    Correlazione lineare tipica per oli sintetici (Therminol 66, Dowtherm A).
    Valida per T = 20-350°C.
    Fonte: dati produttore Therminol 66.
    """
    return 1.68 + 0.00164 * T_celsius


def _cp_glicole_etilenico_30(T_celsius: float) -> float:
    """Cp glicole etilenico 30% vol [kJ/kgK].

    Miscela acqua-glicole. Cp diminuisce rispetto ad acqua pura.
    Valida per T = -15 to 110°C.
    Fonte: ASHRAE Handbook, Fundamentals.
    """
    return 3.50 + 0.0012 * T_celsius


# Mappa fluidi custom → funzione cp(T)
_CUSTOM_CP = {
    "fumi_gas_naturale": _cp_fumi_gas_naturale,
    "fumi_gasolio": _cp_fumi_gasolio,
    "olio_diatermico": _cp_olio_diatermico,
    "glicole_etilenico_30": _cp_glicole_etilenico_30,
}

# Densità approssimative per fluidi custom [kg/m3]
_CUSTOM_DENSITY = {
    "fumi_gas_naturale": lambda T: 1.1 * 273.15 / (T + 273.15),
    "fumi_gasolio": lambda T: 1.15 * 273.15 / (T + 273.15),
    "olio_diatermico": lambda T: 1020 - 0.63 * T,
    "glicole_etilenico_30": lambda T: 1042 - 0.5 * T,
}


# ── Funzioni pubbliche ──────────────────────────────────────────────────────


def get_cp(fluid_id: str, T_celsius: float, P: float = 101325) -> float:
    """Calore specifico a pressione costante [kJ/kgK].

    Args:
        fluid_id: ID fluido dal database
        T_celsius: Temperatura [°C]
        P: Pressione [Pa], default 1 atm

    Returns:
        cp in kJ/kgK
    """
    if fluid_id in _CUSTOM_CP:
        return _CUSTOM_CP[fluid_id](T_celsius)

    info = get_fluid_info(fluid_id)
    coolprop_name = info["coolprop_name"]
    if coolprop_name is None:
        raise ValueError(f"Fluido '{fluid_id}' non ha nome CoolProp né correlazione custom")

    T_K = T_celsius + 273.15
    # CoolProp ritorna in J/kgK, convertiamo in kJ/kgK
    return CP.PropsSI("Cpmass", "T", T_K, "P", P, coolprop_name) / 1000.0


def get_density(fluid_id: str, T_celsius: float, P: float = 101325) -> float:
    """Densità [kg/m3].

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
    """Proprietà termofisiche complete.

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
