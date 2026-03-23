"""Tests for Pinch Analysis (Problem Table Algorithm).

Test levels:
    L1: Unit tests — shifted temps, intervals, cascade mechanics
    L2: Domain sanity — hand-calculated 4-stream example with verified values
    L3: Property-based — Hypothesis invariants (energy balance, monotonicity)
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from heatscout.core.pinch import (
    _collect_shifted_temperatures,
    _prepare_streams,
    pinch_analysis,
)
from heatscout.core.stream import StreamType, ThermalStream

# ── Fixtures ─────────────────────────────────────────────────────────────


def _make_stream(
    name: str,
    stream_type: StreamType,
    T_in: float,
    T_out: float,
    mass_flow: float,
    fluid: str = "acqua",
) -> ThermalStream:
    """Helper to create ThermalStream with default operating hours."""
    return ThermalStream(
        name=name,
        fluid_type=fluid,
        T_in=T_in,
        T_out=T_out,
        mass_flow=mass_flow,
        hours_per_day=8,
        days_per_year=250,
        stream_type=stream_type,
    )


def four_stream_water():
    """Classic 4-stream example using water.

    Hand-calculated with CONSTANT CP (textbook approach, dT_min=10):
        H1: Hot, 170→60°C, CP=3.0 kW/K → m=0.716 kg/s (at cp≈4.19)
        H2: Hot, 150→30°C, CP=1.5 kW/K → m=0.358 kg/s
        C1: Cold, 20→135°C, CP=2.0 kW/K → m=0.477 kg/s
        C2: Cold, 80→140°C, CP=4.0 kW/K → m=0.955 kg/s

    Constant-CP hand calculation (Step 1-4):
        Shifted: H1: 165→55, H2: 145→25, C1: 25→140, C2: 85→145
        Boundaries desc: [165, 145, 140, 85, 55, 25]
        Intervals:
          [165→145]: hot_CP=2.0, cold_CP=0 → dH=+40
          [145→140]: hot_CP=5.5, cold_CP=4.0 → dH=+7.5
          [140→85]:  hot_CP=4.5, cold_CP=6.0 → dH=-82.5
          [85→55]:   hot_CP=4.5, cold_CP=2.0 → dH=+75
          [55→25]:   hot_CP=1.5, cold_CP=2.0 → dH=-15
        Raw cascade: [0, 40, 47.5, -35, 40, 25]
        QH_min = 35, cascade adj: [35, 75, 82.5, 0, 75, 60]
        QC_min = 60, Pinch at shifted T=85 → hot=90, cold=80

    NOTE: With variable cp (CoolProp water), results differ by ~5-10%
    because cp(water) varies from 4.18 to 4.37 kJ/kgK over 20-170°C.
    The pinch LOCATION (90°C/80°C) is robust to cp variation.
    """
    return [
        _make_stream("H1", StreamType.HOT_WASTE, 170, 60, 0.716),
        _make_stream("H2", StreamType.HOT_WASTE, 150, 30, 0.358),
        _make_stream("C1", StreamType.COLD_DEMAND, 20, 135, 0.477),
        _make_stream("C2", StreamType.COLD_DEMAND, 80, 140, 0.955),
    ]


def two_stream_simple():
    """Minimal 2-stream example (1 hot, 1 cold)."""
    return [
        _make_stream("H1", StreamType.HOT_WASTE, 200, 100, 0.5),
        _make_stream("C1", StreamType.COLD_DEMAND, 50, 150, 0.5),
    ]


# ── L1: Unit Tests ──────────────────────────────────────────────────────


class TestL1ShiftedTemperatures:
    """L1: Verify temperature shifting mechanics."""

    def test_hot_stream_shifted_down(self):
        """Hot streams are shifted DOWN by dT_min/2."""
        streams = [_make_stream("H1", StreamType.HOT_WASTE, 200, 100, 1.0)]
        prepared = _prepare_streams(streams, half_dt=5.0)
        s = prepared[0]
        assert s.is_hot is True
        assert s.T_supply_shifted == 195.0  # 200 - 5
        assert s.T_target_shifted == 95.0  # 100 - 5

    def test_cold_stream_shifted_up(self):
        """Cold streams are shifted UP by dT_min/2."""
        streams = [_make_stream("C1", StreamType.COLD_DEMAND, 50, 150, 1.0)]
        prepared = _prepare_streams(streams, half_dt=5.0)
        s = prepared[0]
        assert s.is_hot is False
        assert s.T_supply_shifted == 55.0  # 50 + 5
        assert s.T_target_shifted == 155.0  # 150 + 5

    def test_shifted_temps_sorted_descending(self):
        """Shifted temperatures collected and sorted descending."""
        streams = four_stream_water()
        prepared = _prepare_streams(streams, half_dt=5.0)
        temps = _collect_shifted_temperatures(prepared)
        assert temps == sorted(temps, reverse=True)
        assert len(temps) >= 2

    def test_interval_count(self):
        """N unique shifted temps produce N-1 intervals."""
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        n_temps = len(result.shifted_temperatures)
        n_intervals = len(result.intervals)
        assert n_intervals == n_temps - 1


class TestL1Cascade:
    """L1: Verify cascade mechanics."""

    def test_cascade_length(self):
        """Cascade has N+1 entries for N intervals."""
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert len(result.cascade) == len(result.intervals) + 1

    def test_cascade_first_is_QH_min(self):
        """First entry in adjusted cascade equals QH_min."""
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert result.cascade[0] == pytest.approx(result.QH_min, abs=0.1)

    def test_cascade_last_is_QC_min(self):
        """Last entry in adjusted cascade equals QC_min."""
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert result.cascade[-1] == pytest.approx(result.QC_min, abs=0.1)

    def test_pinch_at_zero(self):
        """Cascade has a zero at the pinch point."""
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert min(result.cascade) == pytest.approx(0.0, abs=0.1)


class TestL1Validation:
    """L1: Input validation."""

    def test_no_hot_streams_raises(self):
        with pytest.raises(ValueError, match="hot stream"):
            pinch_analysis(
                [_make_stream("C1", StreamType.COLD_DEMAND, 20, 100, 1.0)],
                dT_min=10.0,
            )

    def test_no_cold_streams_raises(self):
        with pytest.raises(ValueError, match="cold stream"):
            pinch_analysis(
                [_make_stream("H1", StreamType.HOT_WASTE, 200, 100, 1.0)],
                dT_min=10.0,
            )

    def test_zero_dT_min_raises(self):
        with pytest.raises(ValueError, match="dT_min"):
            pinch_analysis(four_stream_water(), dT_min=0.0)

    def test_negative_dT_min_raises(self):
        with pytest.raises(ValueError, match="dT_min"):
            pinch_analysis(four_stream_water(), dT_min=-5.0)


class TestL1CompositeCurves:
    """L1: Composite curve structure."""

    def test_hot_composite_ascending_T(self):
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert result.hot_composite_T == sorted(result.hot_composite_T)

    def test_cold_composite_ascending_T(self):
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert result.cold_composite_T == sorted(result.cold_composite_T)

    def test_hot_composite_ascending_H(self):
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        for i in range(1, len(result.hot_composite_H)):
            assert result.hot_composite_H[i] >= result.hot_composite_H[i - 1]

    def test_cold_composite_ascending_H(self):
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        for i in range(1, len(result.cold_composite_H)):
            assert result.cold_composite_H[i] >= result.cold_composite_H[i - 1]

    def test_composites_start_at_zero_or_QH(self):
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert result.hot_composite_H[0] == pytest.approx(0.0, abs=0.1)
        assert result.cold_composite_H[0] == pytest.approx(result.QH_min, abs=1.0)


class TestL1GCC:
    """L1: Grand Composite Curve structure."""

    def test_gcc_same_length_as_cascade(self):
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert len(result.gcc_T) == len(result.gcc_H)
        assert len(result.gcc_T) == len(result.cascade)

    def test_gcc_touches_zero(self):
        """GCC must touch zero at pinch."""
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert min(result.gcc_H) == pytest.approx(0.0, abs=0.1)


# ── L2: Domain Sanity — Hand-Calculated Oracle ──────────────────────────


class TestL2FourStreamExample:
    """L2: 4-stream pinch analysis verified by hand calculation.

    The hand calculation uses CONSTANT CP (textbook standard).
    Our algorithm uses variable cp (CoolProp water), so results differ
    by ~5-10%. The PINCH LOCATION is robust. Utility targets are within
    tolerance for screening purposes.

    # SOURCE: Hand calculation (Problem Table Algorithm, Linnhoff 1978)
    #   Verified step-by-step in four_stream_water() docstring.
    #   Reference methodology: Smith R., "Chemical Process Design and
    #   Integration", Wiley 2005, Chapter 16.
    """

    def test_pinch_location(self):
        """Pinch temperature is robust to cp variation.

        # SOURCE: Hand calc with constant CP → pinch at shifted T=85°C
        #   → T_hot=90°C, T_cold=80°C (dT_min=10°C)
        """
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert result.pinch_T_hot == pytest.approx(90.0, abs=1.0)
        assert result.pinch_T_cold == pytest.approx(80.0, abs=1.0)
        assert result.pinch_T_hot - result.pinch_T_cold == pytest.approx(10.0, abs=0.01)

    def test_utility_targets_order_of_magnitude(self):
        """Utility targets within expected range.

        # SOURCE: Hand calc (constant CP): QH_min=35 kW, QC_min=60 kW
        #   With variable cp: expect within ±50% (cp varies 4.18-4.37)
        """
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert 10 < result.QH_min < 60, f"QH_min={result.QH_min}"
        assert 30 < result.QC_min < 100, f"QC_min={result.QC_min}"

    def test_max_recovery_positive(self):
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert result.max_recovery > 0

    def test_interval_count_matches_boundaries(self):
        """4 streams with 8 shifted T boundaries → up to 7 intervals.
        With duplicates removed, expect 5-6 intervals."""
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        assert 4 <= len(result.intervals) <= 7

    def test_energy_balance(self):
        """First Law: QH_min + sum(interval delta_H) ≈ QC_min.

        # SOURCE: First Law of Thermodynamics (energy conservation)
        #   The cascade starts at QH_min, each interval adds/removes heat,
        #   and must end at QC_min.
        """
        result = pinch_analysis(four_stream_water(), dT_min=10.0)
        total_delta_H = sum(iv.delta_H for iv in result.intervals)
        lhs = result.QH_min + total_delta_H
        assert lhs == pytest.approx(result.QC_min, abs=1.0), (
            f"Energy balance: QH({result.QH_min:.1f}) + sum_dH({total_delta_H:.1f})"
            f" = {lhs:.1f} vs QC={result.QC_min:.1f}"
        )


class TestL2TwoStreamSimple:
    """L2: Minimal 2-stream case — easy to verify by inspection.

    # SOURCE: Hand calculation (trivial case)
    #   H1: 200→100°C, m=0.5 kg/s, cp≈4.18 → Q_hot ≈ 209 kW
    #   C1: 50→150°C, m=0.5 kg/s, cp≈4.19 → Q_cold ≈ 209.5 kW
    #   dT_min=10: pinch is either at hot outlet or cold outlet
    """

    def test_runs_without_error(self):
        result = pinch_analysis(two_stream_simple(), dT_min=10.0)
        assert result.QH_min >= 0
        assert result.QC_min >= 0

    def test_pinch_T_separation(self):
        result = pinch_analysis(two_stream_simple(), dT_min=10.0)
        assert result.pinch_T_hot - result.pinch_T_cold == pytest.approx(10.0, abs=0.01)


# ── L3: Property-Based Tests (Hypothesis) ───────────────────────────────


@st.composite
def pinch_stream_pair(draw):
    """Generate a valid pair of 1 hot + 1 cold stream for pinch analysis."""
    # Hot stream: T_in > T_out, using water
    hot_T_in = draw(st.floats(min_value=80, max_value=200, allow_nan=False))
    hot_T_out = draw(st.floats(min_value=25, max_value=hot_T_in - 10, allow_nan=False))
    hot_mass = draw(st.floats(min_value=0.1, max_value=5.0, allow_nan=False))

    # Cold stream: T_out > T_in, using water
    cold_T_in = draw(st.floats(min_value=10, max_value=80, allow_nan=False))
    cold_T_out = draw(st.floats(min_value=cold_T_in + 10, max_value=200, allow_nan=False))
    cold_mass = draw(st.floats(min_value=0.1, max_value=5.0, allow_nan=False))

    dT_min = draw(st.floats(min_value=1.0, max_value=30.0, allow_nan=False))

    return (
        [
            _make_stream("H1", StreamType.HOT_WASTE, hot_T_in, hot_T_out, hot_mass),
            _make_stream("C1", StreamType.COLD_DEMAND, cold_T_in, cold_T_out, cold_mass),
        ],
        dT_min,
    )


class TestL3PropertyBased:
    """L3: Pinch analysis invariants hold for any valid input."""

    @given(data=pinch_stream_pair())
    @settings(max_examples=100, deadline=5000)
    def test_non_negative_utilities(self, data):
        """QH_min >= 0 and QC_min >= 0 for any valid input."""
        streams, dT_min = data
        result = pinch_analysis(streams, dT_min)
        assert result.QH_min >= -0.1, f"QH_min={result.QH_min}"
        assert result.QC_min >= -0.1, f"QC_min={result.QC_min}"

    @given(data=pinch_stream_pair())
    @settings(max_examples=100, deadline=5000)
    def test_pinch_temperature_separation(self, data):
        """pinch_T_hot - pinch_T_cold == dT_min always."""
        streams, dT_min = data
        result = pinch_analysis(streams, dT_min)
        assert result.pinch_T_hot - result.pinch_T_cold == pytest.approx(
            dT_min, abs=0.01
        )

    @given(data=pinch_stream_pair())
    @settings(max_examples=100, deadline=5000)
    def test_max_recovery_bounded(self, data):
        """Max recovery cannot exceed total hot duty (from intervals)."""
        streams, dT_min = data
        result = pinch_analysis(streams, dT_min)
        total_hot_interval = sum(
            iv.hot_CP_total * (iv.T_upper - iv.T_lower) for iv in result.intervals
        )
        total_cold_interval = sum(
            iv.cold_CP_total * (iv.T_upper - iv.T_lower) for iv in result.intervals
        )
        assert result.max_recovery <= total_hot_interval + 1.0
        assert result.max_recovery <= total_cold_interval + 1.0

    @given(data=pinch_stream_pair())
    @settings(max_examples=100, deadline=5000)
    def test_cascade_has_zero(self, data):
        """Adjusted cascade must contain a value ≈ 0 (pinch)."""
        streams, dT_min = data
        result = pinch_analysis(streams, dT_min)
        assert min(result.cascade) < 1.0


class TestL3Monotonicity:
    """L3: Increasing dT_min increases utility requirements."""

    def test_QH_min_increases_with_dT_min(self):
        """Larger dT_min → larger QH_min (monotonic, non-strict)."""
        streams = four_stream_water()
        results = [pinch_analysis(streams, dT_min=dt) for dt in [5, 10, 15, 20, 25]]
        QH_values = [r.QH_min for r in results]
        for i in range(1, len(QH_values)):
            assert QH_values[i] >= QH_values[i - 1] - 0.5, (
                f"QH_min not monotonic: dT={5*(i)}→{QH_values[i-1]:.1f}, "
                f"dT={5*(i+1)}→{QH_values[i]:.1f}"
            )

    def test_total_utility_increases_with_dT_min(self):
        """Larger dT_min → larger total utility need (QH+QC).

        NOTE: Individual QH_min/QC_min may not be strictly monotone with
        variable cp (pinch can jump location). But QH+QC always increases.
        """
        streams = four_stream_water()
        results = [pinch_analysis(streams, dT_min=dt) for dt in [5, 10, 15, 20, 25]]
        totals = [r.QH_min + r.QC_min for r in results]
        for i in range(1, len(totals)):
            assert totals[i] >= totals[i - 1] - 2.0, (
                f"Total utility not monotonic: dT={5*(i)}→{totals[i-1]:.1f}, "
                f"dT={5*(i+1)}→{totals[i]:.1f}"
            )
