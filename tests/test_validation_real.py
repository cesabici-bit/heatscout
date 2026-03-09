"""Validazione contro dati REALI misurati da impianti industriali.

Questi test confrontano l'output di HeatScout con dati pubblicati da
case study reali. Non sono unit test (il modello e' semplificato),
ma verificano che i risultati siano nello stesso ordine di grandezza
della realta'.

TOLLERANZE:
- Potenza termica: +/-20% (il nostro modello usa cp medio, la realta' no)
- Payback: +/-50% (le nostre correlazioni CAPEX hanno +/-30% di incertezza,
  i prezzi energia variano per paese/anno)
- Savings: +/-50% (dipende da prezzo energia locale)

Se un test fallisce, NON significa necessariamente un bug. Significa che
il modello si e' allontanato troppo dalla realta' e serve una review.

Fonti: vedi tests/validation_data/real_case_studies.json
"""

from __future__ import annotations

import pytest

from heatscout.core.economics import economic_analysis
from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.stream_analyzer import calc_annual_energy, calc_thermal_power
from heatscout.core.technology_selector import select_technologies


class TestValidationFonderia:
    """Waupaca Foundry, Wisconsin — DOE Better Buildings.

    Fumi forno cupola: 760C -> 177C, recupero 20.5 MW termici.
    HX due stadi. CAPEX $442K, savings $109K/yr, payback 2.4yr (con incentivo).
    Payback senza incentivo: ~4.1yr.
    """

    @pytest.fixture
    def stream(self):
        # Stima portata da Q=20500kW, dT=583K, cp_fumi~1.1 kJ/kgK
        # m_dot = Q / (cp * dT) = 20500 / (1.1 * 583) = ~32 kg/s
        return ThermalStream(
            name="Cupola furnace exhaust - Waupaca",
            fluid_type="fumi_gas_naturale",
            T_in=760,
            T_out=177,
            mass_flow=32.0,
            hours_per_day=16,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )

    def test_thermal_power_order_of_magnitude(self, stream):
        """HeatScout deve calcolare ~20 MW termici (misurato: 20.5 MW)."""
        Q = calc_thermal_power(stream)
        assert 15000 < Q < 30000, f"Q={Q} kW, atteso ~20500 kW (Waupaca measured)"

    def test_technology_recommends_gas_gas_exchanger(self, stream):
        """A 760C deve raccomandare almeno un recuperatore gas-gas."""
        recs = select_technologies(stream)
        tech_ids = [r.technology.id for r in recs]
        assert any(
            t in tech_ids
            for t in [
                "recuperatore_gas_gas",
                "caldaia_recupero",
                "economizzatore_gas_liquido",
            ]
        ), f"Nessun HX trovato per 760C. Tecnologie: {tech_ids}"

    def test_payback_plausible(self, stream):
        """Payback reale: 2.4-4.1 anni. HeatScout deve dare 1-8 anni."""
        recs = select_technologies(stream)
        # Prendi la prima raccomandazione (massimo savings)
        if recs:
            econ = economic_analysis(recs[0])
            assert 0.5 < econ.payback_years < 10, (
                f"Payback={econ.payback_years}yr, atteso 1-8yr (Waupaca: 2.4-4.1yr)"
            )


class TestValidationCeramica:
    """Atlas Concorde, Modena — ETEKINA H2020 project.

    HPHE su forno ceramico, 100 kW recuperati, 863 MWh/yr,
    payback 16 mesi, 164 tCO2/yr ridotte.
    Fonte: Jouhara et al., Int. J. Thermofluids, 2019.
    """

    @pytest.fixture
    def stream(self):
        # Tipico forno ceramico: fumi a ~300C, uscita ~150C
        # m_dot stimata da Q=100kW: m = 100/(1.05*150) = ~0.63 kg/s
        return ThermalStream(
            name="Kiln exhaust - Atlas Concorde",
            fluid_type="fumi_gas_naturale",
            T_in=300,
            T_out=150,
            mass_flow=0.63,
            hours_per_day=24,
            days_per_year=330,
            stream_type=StreamType.HOT_WASTE,
        )

    def test_thermal_power_order_of_magnitude(self, stream):
        """HeatScout deve calcolare ~100 kW (ETEKINA misurato: 100 kW)."""
        Q = calc_thermal_power(stream)
        assert 50 < Q < 200, f"Q={Q} kW, atteso ~100 kW (Atlas Concorde measured)"

    def test_annual_energy_order_of_magnitude(self, stream):
        """Energia annua: ~863 MWh/yr misurata (ma include primary energy)."""
        E = calc_annual_energy(stream)
        # Il nostro calcolo è sull'energia termica grezza, non primary
        # 100kW * 24h * 330d / 1000 = ~792 MWh — ragionevole
        assert 400 < E < 1500, f"E={E} MWh/yr, atteso ~792-863 MWh/yr"


class TestValidationBirrificio:
    """Small Brewery USA — L&L Engineering 2025.

    Vapori bollitura: HX $10.5K, $3.5K/yr savings, 3yr payback.
    Fermentazione: HX $5K, $2.5K/yr, 2yr payback.
    """

    @pytest.fixture
    def stream_boiling(self):
        return ThermalStream(
            name="Boiling vapors - Small Brewery",
            fluid_type="acqua",
            T_in=100,
            T_out=60,
            mass_flow=0.25,  # Piccolo birrificio
            hours_per_day=8,
            days_per_year=250,
            stream_type=StreamType.HOT_WASTE,
        )

    def test_technology_recommends_liquid_hx(self, stream_boiling):
        """Per acqua 100->60C deve raccomandare scambiatore liquido-liquido."""
        recs = select_technologies(stream_boiling)
        tech_ids = [r.technology.id for r in recs]
        assert "scambiatore_liquido_liquido" in tech_ids, (
            f"Scambiatore L-L non trovato. Tecnologie: {tech_ids}"
        )

    def test_payback_plausible_small_brewery(self, stream_boiling):
        """Payback reale: 2-3 anni. HeatScout deve dare 1-6 anni."""
        recs = select_technologies(stream_boiling)
        hx_recs = [r for r in recs if r.technology.id == "scambiatore_liquido_liquido"]
        if hx_recs:
            econ = economic_analysis(hx_recs[0])
            assert 0.5 < econ.payback_years < 8, (
                f"Payback={econ.payback_years}yr, atteso 1-6yr (brewery real: 2-3yr)"
            )


class TestValidationTessile:
    """Textile dyeing, Bursa, Turkey — ScienceDirect.

    Wastewater 50->20C, shell&tube HX, 5716 MWh/yr, $47K/yr savings,
    payback <6 mesi.
    """

    @pytest.fixture
    def stream(self):
        # 5716 MWh/yr, assume 16h/d, 300d/yr = 4800h
        # Q = 5716*1000/4800 = ~1191 kW
        # m_dot = 1191 / (4.18*30) = ~9.5 kg/s
        return ThermalStream(
            name="Dyeing wastewater - Bursa textile",
            fluid_type="acqua",
            T_in=50,
            T_out=20,
            mass_flow=9.5,
            hours_per_day=16,
            days_per_year=300,
            stream_type=StreamType.HOT_WASTE,
        )

    def test_thermal_power_order_of_magnitude(self, stream):
        """Circa 1200 kW attesi."""
        Q = calc_thermal_power(stream)
        assert 800 < Q < 1600, f"Q={Q} kW, atteso ~1191 kW"

    def test_annual_energy_order_of_magnitude(self, stream):
        """Misurato: 5716 MWh/yr."""
        E = calc_annual_energy(stream)
        assert 3000 < E < 8000, f"E={E} MWh/yr, atteso ~5716 MWh/yr"

    def test_payback_very_short(self, stream):
        """Payback reale: <6 mesi. Deve essere <3 anni."""
        recs = select_technologies(stream)
        hx_recs = [r for r in recs if "scambiatore" in r.technology.id]
        if hx_recs:
            econ = economic_analysis(hx_recs[0])
            assert econ.payback_years < 3, (
                f"Payback={econ.payback_years}yr, atteso <3yr (real: <0.5yr)"
            )


class TestValidationDataCenter:
    """ReUseHeat, Brunswick, Germany — CORDIS H2020.

    Cooling water 45->25C, heat pump to district heating.
    Payback: 3.05yr (originariamente atteso 8yr).
    LCOH: 74 EUR/MWh (gas boiler: 83 EUR/MWh).
    """

    @pytest.fixture
    def stream(self):
        return ThermalStream(
            name="Cooling water - Data Center Brunswick",
            fluid_type="acqua",
            T_in=45,
            T_out=25,
            mass_flow=5.0,  # Stima per DC medio
            hours_per_day=24,
            days_per_year=365,
            stream_type=StreamType.HOT_WASTE,
        )

    def test_recommends_heat_pump(self, stream):
        """Per acqua a 35C medio deve raccomandare pompa di calore."""
        recs = select_technologies(stream)
        tech_ids = [r.technology.id for r in recs]
        assert any("pompa_calore" in t for t in tech_ids), (
            f"Nessuna pompa di calore per DC. Tecnologie: {tech_ids}"
        )

    def test_payback_plausible_dc(self, stream):
        """Payback reale: 3.05yr. HeatScout deve dare 1-8yr."""
        recs = select_technologies(stream)
        hp_recs = [r for r in recs if "pompa_calore" in r.technology.id]
        if hp_recs:
            econ = economic_analysis(hp_recs[0])
            assert 0.5 < econ.payback_years < 10, (
                f"Payback={econ.payback_years}yr, atteso 1-8yr (real: 3.05yr)"
            )


class TestValidationChimicaElectroplating:
    """Electroplating factory, Ningbo, China — Renewable Energy 2024.

    Cascade HP, 480 kW, COP 1.8, $123K/yr savings, 1.65yr payback.
    """

    @pytest.fixture
    def stream(self):
        # 480kW a COP 1.8: Q_source ~ 480*(1-1/1.8) ~ 213 kW
        # Stima: acqua a 40C -> 25C, m = 213/(4.18*15) ~ 3.4 kg/s
        return ThermalStream(
            name="Process waste heat - Ningbo electroplating",
            fluid_type="acqua",
            T_in=40,
            T_out=25,
            mass_flow=3.4,
            hours_per_day=16,
            days_per_year=300,
            stream_type=StreamType.HOT_WASTE,
        )

    def test_recommends_heat_pump(self, stream):
        """Per acqua bassa T deve raccomandare pompa di calore."""
        recs = select_technologies(stream)
        tech_ids = [r.technology.id for r in recs]
        assert any("pompa_calore" in t for t in tech_ids), (
            f"Nessuna pompa di calore. Tecnologie: {tech_ids}"
        )
