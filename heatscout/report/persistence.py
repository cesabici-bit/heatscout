"""Save/Load analysis configuration as JSON.

Schema version 1.0: stores all user inputs needed to reproduce an analysis.
"""

from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = "1.0"


def save_analysis(
    factory_name: str,
    T_ambient: float,
    energy_price: float,
    streams: list[dict],
    incentive_params: dict | None = None,
    discount_rate: float = 0.05,
    horizon_years: int = 10,
    opex_multiplier: float = 1.0,
    install_multiplier: float = 1.0,
) -> str:
    """Serialize analysis inputs to JSON string.

    Args:
        factory_name: Plant name
        T_ambient: Ambient temperature [°C]
        energy_price: Energy price [€/kWh]
        streams: List of stream dicts (same format as streams_input in UI)
        incentive_params: Optional incentive configuration
        discount_rate: Discount rate for NPV (0-1)
        horizon_years: Analysis horizon in years

    Returns:
        JSON string (indented, human-readable)
    """
    # Convert stream_type enum to string for JSON
    serialized_streams = []
    for s in streams:
        ss = dict(s)
        st = ss.get("stream_type")
        if hasattr(st, "value"):
            ss["stream_type"] = st.value
        elif hasattr(st, "name"):
            ss["stream_type"] = st.name.lower()
        serialized_streams.append(ss)

    data: dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "factory_name": factory_name,
        "T_ambient": T_ambient,
        "energy_price": energy_price,
        "discount_rate": discount_rate,
        "horizon_years": horizon_years,
        "opex_multiplier": opex_multiplier,
        "install_multiplier": install_multiplier,
        "streams": serialized_streams,
    }

    if incentive_params:
        data["incentives"] = incentive_params

    return json.dumps(data, indent=2, ensure_ascii=False)


def load_analysis(json_str: str) -> dict:
    """Deserialize analysis inputs from JSON string.

    Args:
        json_str: JSON string (from save_analysis or file upload)

    Returns:
        dict with keys: version, factory_name, T_ambient, energy_price,
        streams (list of dicts), incentives (optional dict)

    Raises:
        ValueError: if JSON is invalid or missing required fields
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    # Validate required fields
    required = ["version", "factory_name", "T_ambient", "energy_price", "streams"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Validate streams
    if not isinstance(data["streams"], list) or len(data["streams"]) == 0:
        raise ValueError("'streams' must be a non-empty list")

    stream_fields = {"name", "fluid_type", "T_in", "T_out", "mass_flow",
                     "hours_per_day", "days_per_year", "stream_type"}
    for i, s in enumerate(data["streams"]):
        missing_s = stream_fields - set(s.keys())
        if missing_s:
            raise ValueError(f"Stream {i+1} missing fields: {missing_s}")

    return data
