"""Pinch Analysis: Problem Table Algorithm, Composite Curves, Grand Composite Curve.

Implements the Linnhoff method for heat integration targeting:
- Minimum hot utility (QH_min) and cold utility (QC_min)
- Maximum process-to-process heat recovery
- Pinch point identification

Supports temperature-dependent cp via get_cp() (trapezoidal average per interval).

References:
    - Linnhoff B., Flower J.R. (1978). Synthesis of heat exchanger networks.
      AIChE Journal, 24(4), 633-642.
    - Smith R. (2005). Chemical Process Design and Integration. Wiley.
    - Kemp I.C. (2007). Pinch Analysis and Process Integration. Elsevier.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from heatscout.core.fluid_properties import get_cp
from heatscout.core.stream import StreamType, ThermalStream

# ── Data Models ──────────────────────────────────────────────────────────


@dataclass
class PinchStream:
    """A stream prepared for pinch analysis with shifted temperatures."""

    name: str
    is_hot: bool
    T_supply: float  # °C, original supply temperature
    T_target: float  # °C, original target temperature
    T_supply_shifted: float  # °C, shifted by ±dT_min/2
    T_target_shifted: float  # °C, shifted by ±dT_min/2
    fluid_type: str
    mass_flow: float  # kg/s
    pressure: float  # Pa

    @property
    def T_shifted_max(self) -> float:
        return max(self.T_supply_shifted, self.T_target_shifted)

    @property
    def T_shifted_min(self) -> float:
        return min(self.T_supply_shifted, self.T_target_shifted)


@dataclass
class TemperatureInterval:
    """One interval in the Problem Table."""

    T_upper: float  # °C (shifted temperature)
    T_lower: float  # °C (shifted temperature)
    hot_CP_total: float  # kW/K (sum of hot stream CPs in this interval)
    cold_CP_total: float  # kW/K (sum of cold stream CPs in this interval)
    delta_H: float  # kW (net heat surplus: positive = hot surplus)


@dataclass
class PinchResult:
    """Complete result of Pinch Analysis."""

    dT_min: float  # °C, minimum approach temperature used
    pinch_T_hot: float  # °C, pinch temperature (hot side)
    pinch_T_cold: float  # °C, pinch temperature (cold side)
    QH_min: float  # kW, minimum hot utility
    QC_min: float  # kW, minimum cold utility
    max_recovery: float  # kW, maximum process-to-process heat recovery

    # Problem Table data
    intervals: list[TemperatureInterval] = field(default_factory=list)
    cascade: list[float] = field(default_factory=list)  # kW, adjusted heat cascade
    shifted_temperatures: list[float] = field(default_factory=list)  # sorted desc

    # Composite Curves (actual temperatures, cumulative enthalpy)
    hot_composite_T: list[float] = field(default_factory=list)  # °C
    hot_composite_H: list[float] = field(default_factory=list)  # kW
    cold_composite_T: list[float] = field(default_factory=list)  # °C
    cold_composite_H: list[float] = field(default_factory=list)  # kW

    # Grand Composite Curve
    gcc_T: list[float] = field(default_factory=list)  # °C (shifted)
    gcc_H: list[float] = field(default_factory=list)  # kW (net heat flow)

    # Show-your-work
    streams_used: list[PinchStream] = field(default_factory=list)


# ── Core Algorithm ───────────────────────────────────────────────────────


def pinch_analysis(
    streams: list[ThermalStream],
    dT_min: float = 10.0,
) -> PinchResult:
    """Run Pinch Analysis on a set of hot and cold streams.

    Args:
        streams: List of ThermalStream objects (must contain at least 1 hot and 1 cold).
        dT_min: Minimum approach temperature [°C]. Must be > 0.

    Returns:
        PinchResult with utility targets, pinch point, and data for plotting.

    Raises:
        ValueError: If streams are missing hot or cold, or dT_min <= 0.
    """
    if dT_min <= 0:
        raise ValueError(f"dT_min must be > 0, got {dT_min}")

    hot_streams = [s for s in streams if s.stream_type == StreamType.HOT_WASTE]
    cold_streams = [s for s in streams if s.stream_type == StreamType.COLD_DEMAND]

    if not hot_streams:
        raise ValueError("Pinch analysis requires at least 1 hot stream (HOT_WASTE)")
    if not cold_streams:
        raise ValueError("Pinch analysis requires at least 1 cold stream (COLD_DEMAND)")

    half_dt = dT_min / 2.0

    # Step 1: Classify and shift temperatures
    pinch_streams = _prepare_streams(streams, half_dt)

    # Step 2: Collect unique shifted temperature boundaries, sorted descending
    shifted_temps = _collect_shifted_temperatures(pinch_streams)

    # Step 3: Build interval table with variable cp
    intervals = _build_intervals(pinch_streams, shifted_temps, half_dt)

    # Step 4: Heat cascade → pinch point, utility targets
    cascade, QH_min, QC_min, pinch_idx = _heat_cascade(intervals, shifted_temps)

    pinch_T_shifted = shifted_temps[pinch_idx]
    pinch_T_hot = pinch_T_shifted + half_dt
    pinch_T_cold = pinch_T_shifted - half_dt

    # Max recovery (computed from interval data for consistency)
    total_hot_interval = sum(iv.hot_CP_total * (iv.T_upper - iv.T_lower) for iv in intervals)
    max_recovery = total_hot_interval - QC_min

    # Step 5: Composite curves
    hot_T, hot_H, cold_T, cold_H = _build_composite_curves(pinch_streams, half_dt, QH_min)

    # Step 6: Grand Composite Curve
    gcc_T = list(shifted_temps)
    gcc_H = list(cascade)

    # Step 7: Assertions (fail-fast)
    _validate_results(QH_min, QC_min, cascade, pinch_idx, intervals)

    return PinchResult(
        dT_min=dT_min,
        pinch_T_hot=round(pinch_T_hot, 2),
        pinch_T_cold=round(pinch_T_cold, 2),
        QH_min=round(QH_min, 2),
        QC_min=round(QC_min, 2),
        max_recovery=round(max_recovery, 2),
        intervals=intervals,
        cascade=cascade,
        shifted_temperatures=list(shifted_temps),
        hot_composite_T=hot_T,
        hot_composite_H=hot_H,
        cold_composite_T=cold_T,
        cold_composite_H=cold_H,
        gcc_T=gcc_T,
        gcc_H=gcc_H,
        streams_used=pinch_streams,
    )


# ── Internal Functions ───────────────────────────────────────────────────


def _prepare_streams(streams: list[ThermalStream], half_dt: float) -> list[PinchStream]:
    """Convert ThermalStreams to PinchStreams with shifted temperatures."""
    result = []
    for s in streams:
        is_hot = s.stream_type == StreamType.HOT_WASTE
        if is_hot:
            T_supply = s.T_in  # hot enters hot
            T_target = s.T_out  # hot leaves cooler
            T_supply_shifted = T_supply - half_dt
            T_target_shifted = T_target - half_dt
        else:
            T_supply = s.T_in  # cold enters cold
            T_target = s.T_out  # cold leaves hotter
            T_supply_shifted = T_supply + half_dt
            T_target_shifted = T_target + half_dt

        result.append(
            PinchStream(
                name=s.name,
                is_hot=is_hot,
                T_supply=T_supply,
                T_target=T_target,
                T_supply_shifted=T_supply_shifted,
                T_target_shifted=T_target_shifted,
                fluid_type=s.fluid_type,
                mass_flow=s.mass_flow,
                pressure=s.pressure,
            )
        )
    return result


def _collect_shifted_temperatures(pinch_streams: list[PinchStream]) -> list[float]:
    """Collect all unique shifted temperature boundaries, sorted descending."""
    temps = set()
    for s in pinch_streams:
        temps.add(s.T_supply_shifted)
        temps.add(s.T_target_shifted)
    result = sorted(temps, reverse=True)
    assert len(result) >= 2, f"Need at least 2 temperature boundaries, got {len(result)}"
    return result


def _avg_cp(fluid_type: str, T1: float, T2: float, pressure: float) -> float:
    """Average cp at two temperatures [kJ/kgK]."""
    cp1 = get_cp(fluid_type, T1, pressure)
    cp2 = get_cp(fluid_type, T2, pressure)
    return (cp1 + cp2) / 2.0


def _stream_active_in_interval(s: PinchStream, T_upper: float, T_lower: float) -> bool:
    """Check if a stream spans the given shifted temperature interval."""
    return s.T_shifted_max >= T_upper and s.T_shifted_min <= T_lower


def _build_intervals(
    pinch_streams: list[PinchStream],
    shifted_temps: list[float],
    half_dt: float,
) -> list[TemperatureInterval]:
    """Build the Problem Table intervals with variable cp."""
    intervals = []
    for i in range(len(shifted_temps) - 1):
        T_upper = shifted_temps[i]
        T_lower = shifted_temps[i + 1]
        dT = T_upper - T_lower

        hot_CP_total = 0.0
        cold_CP_total = 0.0

        for s in pinch_streams:
            if not _stream_active_in_interval(s, T_upper, T_lower):
                continue

            # Convert shifted T back to actual T for cp lookup
            if s.is_hot:
                T_actual_upper = T_upper + half_dt
                T_actual_lower = T_lower + half_dt
            else:
                T_actual_upper = T_upper - half_dt
                T_actual_lower = T_lower - half_dt

            cp_avg = _avg_cp(s.fluid_type, T_actual_upper, T_actual_lower, s.pressure)
            CP = s.mass_flow * cp_avg  # kW/K

            if s.is_hot:
                hot_CP_total += CP
            else:
                cold_CP_total += CP

        delta_H = (hot_CP_total - cold_CP_total) * dT
        intervals.append(
            TemperatureInterval(
                T_upper=T_upper,
                T_lower=T_lower,
                hot_CP_total=round(hot_CP_total, 4),
                cold_CP_total=round(cold_CP_total, 4),
                delta_H=round(delta_H, 4),
            )
        )
    return intervals


def _heat_cascade(
    intervals: list[TemperatureInterval],
    shifted_temps: list[float],
) -> tuple[list[float], float, float, int]:
    """Compute the heat cascade and find pinch point.

    Returns:
        (adjusted_cascade, QH_min, QC_min, pinch_index)
    """
    # Infeasible cascade (starting with QH = 0)
    raw_cascade = [0.0]
    for iv in intervals:
        raw_cascade.append(raw_cascade[-1] + iv.delta_H)

    # QH_min = amount needed to make all cascade values non-negative
    min_val = min(raw_cascade)
    QH_min = max(0.0, -min_val)

    # Adjusted (feasible) cascade
    cascade = [round(c + QH_min, 4) for c in raw_cascade]

    # QC_min = last value in adjusted cascade
    QC_min = cascade[-1]

    # Pinch = where cascade is zero (or closest to zero)
    pinch_idx = cascade.index(min(cascade))

    return cascade, round(QH_min, 4), round(QC_min, 4), pinch_idx


def _build_composite_curves(
    pinch_streams: list[PinchStream],
    half_dt: float,
    QH_min: float,
) -> tuple[list[float], list[float], list[float], list[float]]:
    """Build hot and cold composite curves (actual T vs cumulative H).

    Returns:
        (hot_T, hot_H, cold_T, cold_H)
    """
    hot_streams = [s for s in pinch_streams if s.is_hot]
    cold_streams = [s for s in pinch_streams if not s.is_hot]

    hot_T, hot_H = _single_composite(hot_streams, half_dt, is_hot=True)
    cold_T, cold_H = _single_composite(cold_streams, half_dt, is_hot=False)

    # Shift cold composite by QH_min so curves align correctly
    cold_H = [h + QH_min for h in cold_H]

    return hot_T, hot_H, cold_T, cold_H


def _single_composite(
    streams: list[PinchStream],
    half_dt: float,
    is_hot: bool,
) -> tuple[list[float], list[float]]:
    """Build a single composite curve (hot or cold).

    Returns:
        (temperatures_ascending, cumulative_enthalpy)
    """
    if not streams:
        return [], []

    # Collect actual temperature boundaries
    temps = set()
    for s in streams:
        temps.add(s.T_supply)
        temps.add(s.T_target)
    temps_sorted = sorted(temps)  # ascending

    # Accumulate enthalpy from lowest T upward
    T_out = [temps_sorted[0]]
    H_out = [0.0]
    cumulative = 0.0

    for i in range(len(temps_sorted) - 1):
        T_low = temps_sorted[i]
        T_high = temps_sorted[i + 1]
        dT = T_high - T_low

        total_CP = 0.0
        for s in streams:
            T_min_actual = min(s.T_supply, s.T_target)
            T_max_actual = max(s.T_supply, s.T_target)
            if T_max_actual >= T_high and T_min_actual <= T_low:
                cp_avg = _avg_cp(s.fluid_type, T_low, T_high, s.pressure)
                total_CP += s.mass_flow * cp_avg

        cumulative += total_CP * dT
        T_out.append(T_high)
        H_out.append(round(cumulative, 4))

    return T_out, H_out


def _validate_results(
    QH_min: float,
    QC_min: float,
    cascade: list[float],
    pinch_idx: int,
    intervals: list[TemperatureInterval],
) -> None:
    """Fail-fast assertions on pinch analysis results."""
    TOL = 1.0  # kW tolerance (accounts for cp averaging differences)

    assert QH_min >= -TOL, f"QH_min={QH_min:.2f} kW is negative"
    assert QC_min >= -TOL, f"QC_min={QC_min:.2f} kW is negative"

    assert cascade[pinch_idx] < TOL, (
        f"Cascade at pinch index {pinch_idx} = {cascade[pinch_idx]:.2f} kW, expected ≈ 0"
    )

    # Energy balance from interval data (consistent with PTA computation):
    # sum(delta_H) = total_hot_interval - total_cold_interval
    # QH_min + sum(delta_H) = QC_min  (cascade: starts at QH, ends at QC)
    total_delta_H = sum(iv.delta_H for iv in intervals)
    balance_error = abs(QH_min + total_delta_H - QC_min)
    assert balance_error < TOL, (
        f"Energy balance violated: QH({QH_min:.1f}) + sum_dH({total_delta_H:.1f}) = "
        f"{QH_min + total_delta_H:.1f}, QC={QC_min:.1f}, error={balance_error:.2f} kW"
    )
