"""Tests for sensitivity analysis (energy price sweep + tornado chart)."""

from types import SimpleNamespace

import pytest

from heatscout.core.sensitivity import (
    energy_price_sensitivity,
    tornado_analysis,
)


def _make_econ(capex=100_000, savings=25_000, opex=2_000):
    """Create a minimal object with fields used by sensitivity analysis."""
    return SimpleNamespace(
        total_investment_EUR=capex,
        annual_savings_EUR=savings,
        opex_EUR_anno=opex,
    )


@pytest.fixture
def base_econ():
    """Typical economic result for testing."""
    return _make_econ()


BASE_PRICE = 0.10  # €/kWh


class TestEnergyPriceSensitivity:
    """Core sensitivity sweep tests."""

    def test_returns_correct_number_of_points(self, base_econ):
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=15)
        assert len(pts) == 15

    def test_points_sorted_by_price(self, base_econ):
        pts = energy_price_sensitivity(base_econ, BASE_PRICE)
        prices = [p.param_value for p in pts]
        assert prices == sorted(prices)

    def test_monotonic_payback_decreasing(self, base_econ):
        """Payback must decrease (or stay equal) as price rises."""
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=21)
        paybacks = [p.payback_years for p in pts]
        for i in range(1, len(paybacks)):
            assert paybacks[i] <= paybacks[i - 1], (
                f"Payback not monotonically decreasing: "
                f"price {pts[i].param_value} has payback {paybacks[i]} > {paybacks[i - 1]}"
            )

    def test_monotonic_npv_increasing(self, base_econ):
        """NPV must increase as price rises (higher savings)."""
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=21)
        npvs = [p.npv_EUR for p in pts]
        for i in range(1, len(npvs)):
            assert npvs[i] >= npvs[i - 1], (
                f"NPV not monotonically increasing: "
                f"price {pts[i].param_value} has NPV {npvs[i]} < {npvs[i - 1]}"
            )

    def test_near_zero_price_infinite_payback(self, base_econ):
        """When price → 0, savings → 0, payback → infinity."""
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=11, range_pct=99.0)
        # First point is near-zero price
        assert pts[0].param_value < 0.005
        assert pts[0].payback_years == float("inf")

    def test_double_price_halves_payback(self, base_econ):
        """At 2× price, payback ≈ half (since savings ∝ price, opex constant)."""
        # Use range that includes both 1× and 2× base price
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=101, range_pct=100.0)
        # Find points closest to 1× and 2× base price
        base_pt = min(pts, key=lambda p: abs(p.param_value - BASE_PRICE))
        double_pt = min(pts, key=lambda p: abs(p.param_value - 2 * BASE_PRICE))

        # With opex, payback = capex / (savings - opex)
        # At 2× price: savings doubles, so payback < half (opex is constant)
        # Allow 10% tolerance
        assert double_pt.payback_years < base_pt.payback_years * 0.6, (
            f"Payback at 2× price ({double_pt.payback_years}) should be roughly "
            f"half of base ({base_pt.payback_years})"
        )

    def test_base_price_in_sweep(self, base_econ):
        """Base price should be included (or very close) in the sweep."""
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=15)
        closest = min(pts, key=lambda p: abs(p.param_value - BASE_PRICE))
        assert abs(closest.param_value - BASE_PRICE) < 0.01

    def test_param_label_format(self, base_econ):
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=5)
        for p in pts:
            assert p.param_label.startswith("€")
            assert "/kWh" in p.param_label

    def test_irr_present_when_profitable(self, base_econ):
        """At high prices, IRR should be calculable."""
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=11)
        # Last point has highest price → most profitable
        assert pts[-1].irr_pct is not None
        assert pts[-1].irr_pct > 0


class TestSensitivityEdgeCases:
    """Edge cases and input validation."""

    def test_minimum_points(self, base_econ):
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=3)
        assert len(pts) == 3

    def test_narrow_range(self, base_econ):
        pts = energy_price_sensitivity(base_econ, BASE_PRICE, n_points=5, range_pct=5.0)
        prices = [p.param_value for p in pts]
        assert min(prices) >= BASE_PRICE * 0.94
        assert max(prices) <= BASE_PRICE * 1.06

    def test_rejects_zero_base_price(self, base_econ):
        with pytest.raises(AssertionError, match="positive"):
            energy_price_sensitivity(base_econ, 0.0)

    def test_rejects_negative_base_price(self, base_econ):
        with pytest.raises(AssertionError, match="positive"):
            energy_price_sensitivity(base_econ, -0.05)

    def test_rejects_too_few_points(self, base_econ):
        with pytest.raises(AssertionError, match="at least 3"):
            energy_price_sensitivity(base_econ, BASE_PRICE, n_points=2)

    def test_zero_savings_base(self):
        """If base savings are 0, all sweep points should have inf payback."""
        econ = _make_econ(capex=50_000, savings=0, opex=1_000)
        pts = energy_price_sensitivity(econ, BASE_PRICE, n_points=5)
        for p in pts:
            assert p.payback_years == float("inf")


class TestTornadoAnalysis:
    """Tornado chart (one-at-a-time sensitivity)."""

    def test_returns_four_bars(self, base_econ):
        bars = tornado_analysis(base_econ, BASE_PRICE)
        assert len(bars) == 4

    def test_bars_sorted_by_swing(self, base_econ):
        bars = tornado_analysis(base_econ, BASE_PRICE)
        swings = [b.swing for b in bars]
        assert swings == sorted(swings, reverse=True)

    def test_all_bars_have_nonzero_swing(self, base_econ):
        bars = tornado_analysis(base_econ, BASE_PRICE)
        for b in bars:
            assert b.swing > 0, f"{b.param_name} has zero swing"

    def test_base_npv_consistent(self, base_econ):
        bars = tornado_analysis(base_econ, BASE_PRICE)
        # All bars should share the same base NPV
        base = bars[0].base_npv
        for b in bars:
            assert b.base_npv == base

    def test_energy_price_bar_present(self, base_econ):
        bars = tornado_analysis(base_econ, BASE_PRICE)
        names = [b.param_name for b in bars]
        assert "Energy price" in names

    def test_capex_bar_direction(self, base_econ):
        """Higher CAPEX → lower NPV, so npv_low should be below base."""
        bars = tornado_analysis(base_econ, BASE_PRICE)
        capex_bar = next(b for b in bars if b.param_name == "CAPEX")
        assert capex_bar.npv_low < capex_bar.base_npv

    def test_param_names(self, base_econ):
        bars = tornado_analysis(base_econ, BASE_PRICE)
        names = {b.param_name for b in bars}
        assert names == {"Energy price", "CAPEX", "Operating hours", "Efficiency"}

    def test_rejects_zero_variation(self, base_econ):
        with pytest.raises(AssertionError, match="positive"):
            tornado_analysis(base_econ, BASE_PRICE, variation_pct=0.0)
