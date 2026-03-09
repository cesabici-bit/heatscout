"""Import stream data from CSV or Excel files.

Expected columns (case-insensitive, flexible naming):
- name: stream name
- fluid / fluid_type: fluid identifier (must match fluids.json)
- T_in / t_in: inlet temperature [°C]
- T_out / t_out: outlet temperature [°C]
- mass_flow / flow: mass flow rate [kg/s]
- hours / hours_per_day: operating hours per day
- days / days_per_year: operating days per year
- type / stream_type: "hot_waste" or "cold_demand"
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

# Column name aliases (lowercase key → canonical name)
_ALIASES: dict[str, list[str]] = {
    "name": ["name", "stream_name", "nome"],
    "fluid_type": ["fluid_type", "fluid", "fluido"],
    "T_in": ["t_in", "tin", "t_ingresso", "inlet_temp", "t_in_(°c)", "t_in_(c)"],
    "T_out": ["t_out", "tout", "t_uscita", "outlet_temp", "t_out_(°c)", "t_out_(c)"],
    "mass_flow": ["mass_flow", "flow", "portata", "mass_flow_kg_s"],
    "hours_per_day": ["hours_per_day", "hours", "ore", "ore_giorno", "h_day"],
    "days_per_year": ["days_per_year", "days", "giorni", "giorni_anno", "d_year"],
    "stream_type": ["stream_type", "type", "tipo"],
}

MAX_STREAMS = 50


def generate_template() -> bytes:
    """Generate a CSV template with example data.

    Returns:
        UTF-8 encoded CSV bytes with BOM for Excel compatibility.
    """
    df = pd.DataFrame(
        [
            {
                "name": "Flue gas furnace",
                "fluid_type": "fumi_gas_naturale",
                "T_in": 400.0,
                "T_out": 180.0,
                "mass_flow": 2.0,
                "hours_per_day": 16.0,
                "days_per_year": 300.0,
                "stream_type": "hot_waste",
            },
            {
                "name": "Cooling water",
                "fluid_type": "acqua",
                "T_in": 60.0,
                "T_out": 35.0,
                "mass_flow": 1.5,
                "hours_per_day": 16.0,
                "days_per_year": 300.0,
                "stream_type": "hot_waste",
            },
        ]
    )
    # BOM for Excel to recognize UTF-8
    return b"\xef\xbb\xbf" + df.to_csv(index=False).encode("utf-8")


def import_streams(file_bytes: bytes, filename: str) -> list[dict]:
    """Import streams from CSV or Excel file.

    Args:
        file_bytes: Raw file content
        filename: Original filename (used to detect format)

    Returns:
        List of stream dicts ready for ThermalStream construction

    Raises:
        ValueError: if file is invalid, too large, or missing required columns
    """
    # Read file
    try:
        if filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
        else:
            # Try UTF-8, fallback to Latin-1 (Excel italiano)
            try:
                df = pd.read_csv(BytesIO(file_bytes), encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(BytesIO(file_bytes), encoding="latin-1")
    except Exception as e:
        raise ValueError(f"Cannot read file: {e}") from e

    if len(df) == 0:
        raise ValueError("File is empty")
    if len(df) > MAX_STREAMS:
        raise ValueError(f"Too many streams ({len(df)}). Maximum is {MAX_STREAMS}.")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Map aliases to canonical names
    col_map = {}
    for canonical, aliases in _ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                col_map[alias] = canonical
                break

    df = df.rename(columns=col_map)

    # Check required columns
    required = {
        "name",
        "fluid_type",
        "T_in",
        "T_out",
        "mass_flow",
        "hours_per_day",
        "days_per_year",
        "stream_type",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Available: {list(df.columns)}")

    # Convert to list of dicts
    streams = []
    for idx, row in df.iterrows():
        try:
            st_type = str(row["stream_type"]).strip().lower()
            streams.append(
                {
                    "name": str(row["name"]).strip(),
                    "fluid_type": str(row["fluid_type"]).strip(),
                    "T_in": float(row["T_in"]),
                    "T_out": float(row["T_out"]),
                    "mass_flow": float(row["mass_flow"]),
                    "hours_per_day": float(row["hours_per_day"]),
                    "days_per_year": float(row["days_per_year"]),
                    "stream_type": st_type,
                }
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Row {idx + 2}: invalid data — {e}") from e

    return streams
