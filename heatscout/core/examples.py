"""Caricamento esempi preconfigurati."""

from __future__ import annotations

import json
from pathlib import Path

from heatscout.core.stream import ThermalStream

EXAMPLES_DIR = Path(__file__).parent.parent / "data" / "examples"


def list_examples() -> list[dict]:
    """Lista esempi disponibili con nome e descrizione."""
    examples = []
    for p in sorted(EXAMPLES_DIR.glob("*.json")):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        examples.append({
            "id": p.stem,
            "name": data["name"],
            "description": data.get("description", ""),
            "n_streams": len(data["streams"]),
        })
    return examples


def load_example(name: str) -> tuple[list[ThermalStream], dict]:
    """Carica un esempio e ritorna lista di ThermalStream + metadata.

    Args:
        name: nome del file senza estensione (es. "fonderia")

    Returns:
        (lista di ThermalStream, dict con name, description, T_ambient)
    """
    path = EXAMPLES_DIR / f"{name}.json"
    if not path.exists():
        available = [p.stem for p in EXAMPLES_DIR.glob("*.json")]
        raise FileNotFoundError(
            f"Esempio '{name}' non trovato. Disponibili: {available}"
        )

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    streams = [ThermalStream.from_dict(s) for s in data["streams"]]
    metadata = {
        "name": data["name"],
        "description": data.get("description", ""),
        "T_ambient": data.get("T_ambient", 25),
    }
    return streams, metadata
