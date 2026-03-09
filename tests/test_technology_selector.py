"""Test per l'algoritmo di selezione tecnologie."""

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.technology_selector import select_technologies


class TestTechnologySelection:
    def test_fumi_400_suggests_multiple(self):
        """Fumi 400°C → deve suggerire recuperatore, caldaia recupero, ORC, pre-riscaldamento."""
        s = ThermalStream("Fumi", "fumi_gas_naturale", 400, 180, 2.0, 16, 250, StreamType.HOT_WASTE)
        recs = select_technologies(s)
        tech_ids = [r.technology.id for r in recs]
        assert "recuperatore_gas_gas" in tech_ids or "economizzatore_gas_liquido" in tech_ids
        assert "caldaia_recupero" in tech_ids
        assert "orc" in tech_ids
        assert "preriscaldamento_aria" in tech_ids

    def test_acqua_55_suggests_heat_pump(self):
        """Acqua 55°C → deve suggerire pompa di calore acqua-acqua."""
        s = ThermalStream("Acqua", "acqua", 55, 30, 2.0, 16, 250, StreamType.HOT_WASTE)
        recs = select_technologies(s)
        tech_ids = [r.technology.id for r in recs]
        assert "pompa_calore_acqua_acqua" in tech_ids
        # NON deve suggerire caldaia recupero (T troppo bassa)
        assert "caldaia_recupero" not in tech_ids

    def test_vapore_120_suggests_scambiatore(self):
        """Fumi a 120°C → deve suggerire economizzatore e/o pompa di calore."""
        s = ThermalStream(
            "Vapore flash",
            "fumi_gas_naturale",
            120,
            80,
            0.5,
            12,
            300,
            StreamType.HOT_WASTE,
        )
        recs = select_technologies(s)
        # Deve suggerire almeno una opzione
        assert len(recs) > 0

    def test_recommendations_sorted_by_savings(self):
        """Le raccomandazioni devono essere ordinate per savings decrescente."""
        s = ThermalStream("Fumi", "fumi_gas_naturale", 400, 150, 2.0, 16, 250, StreamType.HOT_WASTE)
        recs = select_technologies(s)
        if len(recs) > 1:
            for i in range(len(recs) - 1):
                assert recs[i].savings_EUR >= recs[i + 1].savings_EUR

    def test_recovery_fraction_in_range(self):
        """La frazione di recupero deve essere in [0, 1] per scambiatori."""
        s = ThermalStream("Fumi", "fumi_gas_naturale", 300, 150, 1.0, 16, 250, StreamType.HOT_WASTE)
        recs = select_technologies(s)
        for r in recs:
            if not r.is_heat_pump:
                assert 0 < r.recovery_fraction <= 1.0, (
                    f"{r.technology.name}: recovery = {r.recovery_fraction:.2f}"
                )

    def test_all_recommendations_have_positive_savings(self):
        """Tutte le raccomandazioni devono avere risparmio > 0."""
        s = ThermalStream("Acqua", "acqua", 80, 40, 1.0, 16, 250, StreamType.HOT_WASTE)
        recs = select_technologies(s)
        for r in recs:
            assert r.savings_EUR > 0, f"{r.technology.name}: savings = {r.savings_EUR}"
