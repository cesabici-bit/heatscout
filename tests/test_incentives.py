"""Test per il modulo Certificati Bianchi (TEE).

Ogni test ha calcoli manuali verificabili nei commenti.
Fonte normativa: DM MASE 21/07/2025
"""

import pytest

from heatscout.knowledge.incentives import (
    TEP_PER_MWH_THERMAL,
    TEE_VITA_UTILE_ANNI,
    TEE_K_PRIMA_META,
    TEE_K_SECONDA_META,
    TEE_SOGLIA_MINIMA_TEP,
    ETA_CALDAIA_RIFERIMENTO,
    calc_tee,
    TEEResult,
)


class TestCalcTEE:
    """Test calcolo Certificati Bianchi."""

    def test_esempio_fonderia_grande(self):
        """Fonderia con 2000 MWh/anno di calore recuperato.

        Calcolo manuale:
        - TEP = (2000 / 0.90) × 0.086 = 2222.2 × 0.086 = 191.11 TEP/anno
        - Sopra soglia 10 TEP → ammissibile
        - Anno 1-3 (K=1.2): TEE = 191.11 × 1.2 = 229.33 → ricavo = 229.33 × 250 = 57333
        - Anno 4-7 (K=0.8): TEE = 191.11 × 0.8 = 152.89 → ricavo = 152.89 × 250 = 38222
        - Totale 7 anni: 3 × 57333 + 4 × 38222 = 171999 + 152888 = 324887
        """
        result = calc_tee(2000.0, prezzo_tee=250.0, eta_riferimento=0.90)

        assert result.sopra_soglia is True
        assert abs(result.tep_risparmiati_anno - 191.11) < 0.5
        assert result.vita_utile == 7
        assert len(result.tee_per_anno) == 7
        assert len(result.ricavo_per_anno) == 7

        # Primi 3 anni: K = 1.2
        for i in range(3):
            assert abs(result.tee_per_anno[i] - 229.33) < 0.5

        # Ultimi 4 anni: K = 0.8
        for i in range(3, 7):
            assert abs(result.tee_per_anno[i] - 152.89) < 0.5

        # Ricavo totale ~325k
        assert abs(result.ricavo_totale - 324887) < 500

    def test_esempio_medio(self):
        """Impianto medio con 500 MWh/anno.

        Calcolo manuale:
        - TEP = (500 / 0.90) × 0.086 = 555.56 × 0.086 = 47.78 TEP/anno
        - Sopra soglia → ammissibile
        - Ricavo medio/anno: ~47.78 × 250 × ((3×1.2 + 4×0.8)/7)
        -   = 47.78 × 250 × 1.017 = ~12,153
        """
        result = calc_tee(500.0, prezzo_tee=250.0)

        assert result.sopra_soglia is True
        assert abs(result.tep_risparmiati_anno - 47.78) < 0.5
        assert result.ricavo_totale > 0
        assert result.ricavo_medio_anno > 0

    def test_sotto_soglia(self):
        """Progetto piccolo: 50 MWh/anno → sotto soglia 10 TEP.

        Calcolo manuale:
        - TEP = (50 / 0.90) × 0.086 = 55.56 × 0.086 = 4.78 TEP/anno
        - Sotto soglia 10 TEP → NON ammissibile
        """
        result = calc_tee(50.0)

        assert result.sopra_soglia is False
        assert abs(result.tep_risparmiati_anno - 4.78) < 0.5
        # Calcola comunque i ricavi (l'utente vede "non ammissibile")
        assert result.ricavo_totale > 0

    def test_soglia_esatta(self):
        """Verifica soglia: 10 TEP = (E / 0.90) × 0.086 → E = 10 / 0.086 × 0.90 = 104.65 MWh."""
        result_sotto = calc_tee(104.0)
        result_sopra = calc_tee(105.0)

        assert result_sotto.sopra_soglia is False
        assert result_sopra.sopra_soglia is True


class TestTEEProperties:
    """Test proprietà invarianti dei TEE."""

    def test_coefficiente_k_neutro_su_vita(self):
        """Il coefficiente K è circa neutro sulla vita intera.

        (3 × 1.2 + 4 × 0.8) / 7 ≈ 1.017
        """
        k_medio = (3 * TEE_K_PRIMA_META + 4 * TEE_K_SECONDA_META) / TEE_VITA_UTILE_ANNI
        assert abs(k_medio - 1.0) < 0.05  # quasi neutro

    def test_ricavo_monotono_crescente_con_energia(self):
        """Più energia recuperata → più TEE → più ricavo."""
        r1 = calc_tee(100.0)
        r2 = calc_tee(500.0)
        r3 = calc_tee(2000.0)

        assert r1.ricavo_totale < r2.ricavo_totale < r3.ricavo_totale

    def test_ricavo_monotono_crescente_con_prezzo(self):
        """Prezzo TEE più alto → più ricavo."""
        r1 = calc_tee(500.0, prezzo_tee=150.0)
        r2 = calc_tee(500.0, prezzo_tee=250.0)
        r3 = calc_tee(500.0, prezzo_tee=350.0)

        assert r1.ricavo_totale < r2.ricavo_totale < r3.ricavo_totale

    def test_primi_anni_piu_redditizi(self):
        """Con K=1.2 i primi anni rendono più degli ultimi."""
        result = calc_tee(500.0)

        assert result.ricavo_per_anno[0] > result.ricavo_per_anno[-1]

    def test_conversione_tep_coerente(self):
        """1 MWh_th = 0.086 TEP (fattore ARERA)."""
        assert abs(TEP_PER_MWH_THERMAL - 0.086) < 0.001

    def test_vita_utile_7_anni(self):
        """Vita utile recupero calore = 7 anni (DM MASE 2025)."""
        assert TEE_VITA_UTILE_ANNI == 7

    def test_eta_riferimento_range(self):
        """Rendimento caldaia plausibile."""
        result_90 = calc_tee(500.0, eta_riferimento=0.90)
        result_80 = calc_tee(500.0, eta_riferimento=0.80)

        # Caldaia meno efficiente → più combustibile risparmiato → più TEP
        assert result_80.tep_risparmiati_anno > result_90.tep_risparmiati_anno


class TestTEEFailFast:
    """Test fail-fast assertions."""

    def test_energia_negativa(self):
        with pytest.raises(AssertionError):
            calc_tee(-100.0)

    def test_eta_fuori_range(self):
        with pytest.raises(AssertionError):
            calc_tee(500.0, eta_riferimento=0.3)
        with pytest.raises(AssertionError):
            calc_tee(500.0, eta_riferimento=1.5)

    def test_prezzo_zero(self):
        with pytest.raises(AssertionError):
            calc_tee(500.0, prezzo_tee=0.0)

    def test_prezzo_negativo(self):
        with pytest.raises(AssertionError):
            calc_tee(500.0, prezzo_tee=-10.0)


class TestCapexIncentive:
    """Test modulo incentivo generico CAPEX."""

    def test_riduzione_30_pct(self):
        """30% di 100k = 30k riduzione, netto = 70k."""
        from heatscout.knowledge.incentives import calc_capex_incentive

        r = calc_capex_incentive(100_000, 30.0, "IRA §48C")
        assert r.capex_lordo == 100_000
        assert abs(r.riduzione_EUR - 30_000) < 0.01
        assert abs(r.capex_netto - 70_000) < 0.01
        assert r.nome_incentivo == "IRA §48C"

    def test_riduzione_zero(self):
        """0% = nessuna riduzione."""
        from heatscout.knowledge.incentives import calc_capex_incentive

        r = calc_capex_incentive(100_000, 0.0)
        assert r.capex_netto == r.capex_lordo

    def test_riduzione_100_pct(self):
        """100% = investimento gratuito."""
        from heatscout.knowledge.incentives import calc_capex_incentive

        r = calc_capex_incentive(100_000, 100.0)
        assert r.capex_netto == 0.0

    def test_capex_netto_sempre_minore(self):
        """CAPEX netto <= CAPEX lordo (SEMPRE)."""
        from heatscout.knowledge.incentives import calc_capex_incentive

        for pct in [5, 15, 30, 45, 80]:
            r = calc_capex_incentive(200_000, pct)
            assert r.capex_netto <= r.capex_lordo

    def test_fail_fast_pct_fuori_range(self):
        from heatscout.knowledge.incentives import calc_capex_incentive

        with pytest.raises(AssertionError):
            calc_capex_incentive(100_000, -5.0)
        with pytest.raises(AssertionError):
            calc_capex_incentive(100_000, 150.0)

    def test_fail_fast_capex_negativo(self):
        from heatscout.knowledge.incentives import calc_capex_incentive

        with pytest.raises(AssertionError):
            calc_capex_incentive(-50_000, 30.0)


class TestIncentiveSummary:
    """Test integrazione incentivi in economics.py."""

    @pytest.fixture
    def sample_econ_result(self):
        """Crea un EconomicResult di esempio per test."""
        from heatscout.core.stream import ThermalStream, StreamType
        from heatscout.core.technology_selector import select_technologies
        from heatscout.core.economics import economic_analysis

        stream = ThermalStream(
            name="Fumi forno",
            fluid_type="fumi_gas_naturale",
            T_in=400.0,
            T_out=180.0,
            mass_flow=2.0,
            hours_per_day=16.0,
            days_per_year=300.0,
            stream_type=StreamType.HOT_WASTE,
        )
        recs = select_technologies(stream, energy_price_EUR_kWh=0.08)
        assert len(recs) > 0
        return economic_analysis(recs[0], energy_price_EUR_kWh=0.08)

    def test_solo_capex_incentive(self, sample_econ_result):
        """Con solo CAPEX reduction: NPV migliora, payback scende."""
        from heatscout.core.economics import economic_analysis_with_incentives

        s = economic_analysis_with_incentives(
            sample_econ_result, capex_riduzione_pct=30.0
        )
        assert s.npv_con_capex_inc > s.base.npv_EUR
        assert s.payback_con_capex_inc < s.base.payback_years
        assert s.tee is None  # TEE non abilitato
        assert s.npv_combinato is None

    def test_solo_tee(self, sample_econ_result):
        """Con solo TEE: NPV migliora, payback scende."""
        from heatscout.core.economics import economic_analysis_with_incentives

        s = economic_analysis_with_incentives(
            sample_econ_result, tee_enabled=True
        )
        assert s.npv_con_tee >= s.base.npv_EUR
        assert s.payback_con_tee <= s.base.payback_years
        assert s.capex_incentive is None
        assert s.npv_combinato is None

    def test_combinato(self, sample_econ_result):
        """Con entrambi: il combinato è il migliore di tutti."""
        from heatscout.core.economics import economic_analysis_with_incentives

        s = economic_analysis_with_incentives(
            sample_econ_result, capex_riduzione_pct=30.0, tee_enabled=True
        )
        # Combinato >= solo CAPEX
        assert s.npv_combinato >= s.npv_con_capex_inc
        # Combinato >= solo TEE
        assert s.npv_combinato >= s.npv_con_tee
        # Payback combinato <= base
        assert s.payback_combinato <= s.base.payback_years

    def test_nessun_incentivo(self, sample_econ_result):
        """Senza incentivi: tutti i campi opzionali sono None."""
        from heatscout.core.economics import economic_analysis_with_incentives

        s = economic_analysis_with_incentives(sample_econ_result)
        assert s.capex_incentive is None
        assert s.npv_con_capex_inc is None
        assert s.tee is None
        assert s.npv_combinato is None
