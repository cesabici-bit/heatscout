"""Modello dati per stream termici industriali."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StreamType(str, Enum):
    HOT_WASTE = "hot_waste"
    COLD_DEMAND = "cold_demand"


@dataclass
class ThermalStream:
    """Rappresenta un flusso termico industriale (caldo di scarto o domanda fredda).

    Attributes:
        name: Nome identificativo dello stream (es. "Fumi forno fusione")
        fluid_type: Tipo di fluido (chiave per lookup in fluids.json)
        T_in: Temperatura di ingresso [°C]
        T_out: Temperatura di uscita [°C]
        mass_flow: Portata massica [kg/s]
        hours_per_day: Ore di funzionamento al giorno
        days_per_year: Giorni di funzionamento all'anno
        stream_type: hot_waste (calore da recuperare) o cold_demand (domanda termica)
        pressure: Pressione operativa [Pa], default 101325 (1 atm)
        notes: Note aggiuntive opzionali
    """

    name: str
    fluid_type: str
    T_in: float
    T_out: float
    mass_flow: float
    hours_per_day: float
    days_per_year: float
    stream_type: StreamType
    pressure: float = 101325.0
    notes: str = ""

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Valida i parametri dello stream."""
        if not self.name or not self.name.strip():
            raise ValueError("Il nome dello stream non può essere vuoto")

        if not self.fluid_type or not self.fluid_type.strip():
            raise ValueError("Il tipo di fluido non può essere vuoto")

        # Temperatura minima: zero assoluto
        if self.T_in <= -273.15:
            raise ValueError(
                f"T_in={self.T_in}°C è sotto lo zero assoluto (-273.15°C)"
            )
        if self.T_out <= -273.15:
            raise ValueError(
                f"T_out={self.T_out}°C è sotto lo zero assoluto (-273.15°C)"
            )

        if self.T_in == self.T_out:
            raise ValueError(
                f"T_in e T_out sono uguali ({self.T_in}°C): nessun scambio termico"
            )

        # Per hot_waste: T_in > T_out (il fluido si raffredda)
        if self.stream_type == StreamType.HOT_WASTE and self.T_in < self.T_out:
            raise ValueError(
                f"Stream hot_waste: T_in ({self.T_in}°C) deve essere > T_out ({self.T_out}°C)"
            )

        # Per cold_demand: T_out > T_in (il fluido si scalda)
        if self.stream_type == StreamType.COLD_DEMAND and self.T_out < self.T_in:
            raise ValueError(
                f"Stream cold_demand: T_out ({self.T_out}°C) deve essere > T_in ({self.T_in}°C)"
            )

        if self.mass_flow <= 0:
            raise ValueError(f"mass_flow={self.mass_flow} kg/s deve essere > 0")

        if not (0 < self.hours_per_day <= 24):
            raise ValueError(
                f"hours_per_day={self.hours_per_day} deve essere tra 0 e 24"
            )

        if not (0 < self.days_per_year <= 366):
            raise ValueError(
                f"days_per_year={self.days_per_year} deve essere tra 0 e 366"
            )

        if self.pressure <= 0:
            raise ValueError(f"pressure={self.pressure} Pa deve essere > 0")

    @property
    def delta_T(self) -> float:
        """Differenza di temperatura assoluta [°C]."""
        return abs(self.T_in - self.T_out)

    @property
    def T_mean(self) -> float:
        """Temperatura media dello stream [°C]."""
        return (self.T_in + self.T_out) / 2

    @property
    def annual_hours(self) -> float:
        """Ore di funzionamento annuali."""
        return self.hours_per_day * self.days_per_year

    def to_dict(self) -> dict:
        """Serializza lo stream in un dizionario."""
        return {
            "name": self.name,
            "fluid_type": self.fluid_type,
            "T_in": self.T_in,
            "T_out": self.T_out,
            "mass_flow": self.mass_flow,
            "hours_per_day": self.hours_per_day,
            "days_per_year": self.days_per_year,
            "stream_type": self.stream_type.value,
            "pressure": self.pressure,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ThermalStream:
        """Crea un ThermalStream da un dizionario."""
        data = data.copy()
        if isinstance(data.get("stream_type"), str):
            data["stream_type"] = StreamType(data["stream_type"])
        return cls(**data)
