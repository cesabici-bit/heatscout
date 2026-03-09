"""CHECKPOINT CRITICI — Verifica di sanità fisica.

Questi test verificano che i calcoli siano fisicamente plausibili,
NON solo che il codice funzioni. Servono per catturare:
1. Errori di unità (kJ vs kW, °C vs K, etc.)
2. Correlazioni sbagliate (cp fuori range)
3. Errori logici (exergia > energia termica)
4. Valori fuori scala (potenze negative, COP > Carnot, etc.)

Ogni test ha un VALORE DI RIFERIMENTO MANUALE calcolato con fonti esterne.
"""

from heatscout.core.fluid_properties import get_cp, get_density
from heatscout.core.heat_balance import FactoryHeatBalance
from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.stream_analyzer import (
    calc_annual_energy,
    calc_exergy,
    calc_thermal_power,
)

# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT 1: Proprietà fluidi — confronto con valori tabulati
# Fonte: Engineering Toolbox, Perry's Chemical Engineers' Handbook
# ═══════════════════════════════════════════════════════════════════════════════


class TestFluidPropertiesSanity:
    """Verifica cp e densità contro valori noti da letteratura."""

    def test_cp_acqua_20C(self):
        """cp acqua a 20°C = 4.182 kJ/kgK (Engineering Toolbox)."""
        cp = get_cp("acqua", 20)
        assert 4.15 < cp < 4.20, f"cp acqua 20°C = {cp}, atteso ~4.18"

    def test_cp_acqua_80C(self):
        """cp acqua a 80°C = 4.197 kJ/kgK."""
        cp = get_cp("acqua", 80)
        assert 4.15 < cp < 4.25, f"cp acqua 80°C = {cp}, atteso ~4.20"

    def test_cp_aria_20C(self):
        """cp aria a 20°C = 1.005 kJ/kgK."""
        cp = get_cp("aria", 20)
        assert 0.99 < cp < 1.02, f"cp aria 20°C = {cp}, atteso ~1.005"

    def test_cp_aria_400C(self):
        """cp aria a 400°C = 1.068 kJ/kgK (Engineering Toolbox)."""
        cp = get_cp("aria", 400)
        assert 1.04 < cp < 1.10, f"cp aria 400°C = {cp}, atteso ~1.07"

    def test_cp_fumi_gas_200C(self):
        """cp fumi gas naturale a 200°C ≈ 1.04-1.08 kJ/kgK."""
        cp = get_cp("fumi_gas_naturale", 200)
        assert 1.00 < cp < 1.15, f"cp fumi 200°C = {cp}, atteso ~1.05"

    def test_cp_fumi_gas_500C(self):
        """cp fumi gas naturale a 500°C ≈ 1.10-1.18 kJ/kgK."""
        cp = get_cp("fumi_gas_naturale", 500)
        assert 1.05 < cp < 1.25, f"cp fumi 500°C = {cp}, atteso ~1.12"

    def test_density_acqua_20C(self):
        """rho acqua 20°C = 998 kg/m3."""
        rho = get_density("acqua", 20)
        assert 990 < rho < 1005, f"rho acqua 20°C = {rho}, atteso ~998"

    def test_density_aria_20C(self):
        """rho aria 20°C a 1atm = 1.204 kg/m3."""
        rho = get_density("aria", 20)
        assert 1.15 < rho < 1.25, f"rho aria 20°C = {rho}, atteso ~1.20"

    def test_cp_always_positive(self):
        """cp deve essere SEMPRE positivo per qualsiasi fluido/temperatura."""
        test_cases = [
            ("acqua", 10),
            ("acqua", 90),
            ("aria", 20),
            ("aria", 600),
            ("fumi_gas_naturale", 100),
            ("fumi_gas_naturale", 800),
            ("olio_diatermico", 50),
            ("olio_diatermico", 300),
            ("azoto", 20),
            ("azoto", 500),
            ("co2", 20),
            ("co2", 400),
        ]
        for fluid, T in test_cases:
            cp = get_cp(fluid, T)
            assert cp > 0, f"cp({fluid}, {T}°C) = {cp} — DEVE essere > 0"

    def test_cp_reasonable_range(self):
        """cp per tutti i fluidi deve stare in un range ragionevole (0.5 - 5 kJ/kgK)."""
        test_cases = [
            ("acqua", 50),
            ("aria", 200),
            ("fumi_gas_naturale", 400),
            ("olio_diatermico", 200),
            ("azoto", 300),
            ("co2", 200),
        ]
        for fluid, T in test_cases:
            cp = get_cp(fluid, T)
            assert 0.5 < cp < 5.0, f"cp({fluid}, {T}°C) = {cp} — fuori range [0.5, 5.0]"


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT 2: Potenza termica — calcoli manuali verificabili
# ═══════════════════════════════════════════════════════════════════════════════


class TestThermalPowerSanity:
    """Verifica potenza termica contro calcoli manuali."""

    def test_acqua_benchmark_1(self):
        """BENCHMARK: Acqua 90→60°C, 1 kg/s.

        Calcolo manuale:
          cp_medio ≈ 4.19 kJ/kgK (media cp(90) e cp(60))
          Q = 1.0 × 4.19 × 30 = 125.7 kW

        Fonte verifica: qualsiasi manuale di termodinamica.
        """
        s = ThermalStream("BM1", "acqua", 90, 60, 1.0, 8, 250, StreamType.HOT_WASTE)
        Q = calc_thermal_power(s)
        assert 120 < Q < 132, f"Q = {Q:.2f} kW — atteso 125.7 ± 6"

    def test_aria_benchmark_2(self):
        """BENCHMARK: Aria 400→200°C, 0.5 kg/s.

        Calcolo manuale:
          cp_medio ≈ 1.04 kJ/kgK
          Q = 0.5 × 1.04 × 200 = 104 kW
        """
        s = ThermalStream("BM2", "aria", 400, 200, 0.5, 16, 250, StreamType.HOT_WASTE)
        Q = calc_thermal_power(s)
        assert 95 < Q < 115, f"Q = {Q:.2f} kW — atteso ~104"

    def test_power_proportional_to_mass_flow(self):
        """INVARIANTE: Q deve essere proporzionale alla portata."""
        s1 = ThermalStream("test1", "acqua", 90, 60, 1.0, 8, 250, StreamType.HOT_WASTE)
        s2 = ThermalStream("test2", "acqua", 90, 60, 2.0, 8, 250, StreamType.HOT_WASTE)
        Q1 = calc_thermal_power(s1)
        Q2 = calc_thermal_power(s2)
        assert abs(Q2 / Q1 - 2.0) < 0.001, f"Q2/Q1 = {Q2 / Q1:.4f}, atteso 2.0"

    def test_power_proportional_to_delta_T(self):
        """INVARIANTE: Q approssimativamente proporzionale a deltaT (se cp ≈ costante)."""
        s1 = ThermalStream("test1", "acqua", 90, 60, 1.0, 8, 250, StreamType.HOT_WASTE)
        s2 = ThermalStream("test2", "acqua", 90, 30, 1.0, 8, 250, StreamType.HOT_WASTE)
        Q1 = calc_thermal_power(s1)  # deltaT = 30
        Q2 = calc_thermal_power(s2)  # deltaT = 60
        ratio = Q2 / Q1
        # Cp acqua varia poco, quindi il rapporto dovrebbe essere ~2.0
        assert 1.9 < ratio < 2.1, f"Q2/Q1 = {ratio:.3f}, atteso ~2.0"

    def test_power_always_positive(self):
        """INVARIANTE: La potenza termica deve essere SEMPRE positiva."""
        cases = [
            ("acqua", 90, 30, 1.0, StreamType.HOT_WASTE),
            ("aria", 500, 100, 0.5, StreamType.HOT_WASTE),
            ("acqua", 15, 60, 1.0, StreamType.COLD_DEMAND),
        ]
        for fluid, Tin, Tout, m, stype in cases:
            s = ThermalStream("test", fluid, Tin, Tout, m, 8, 250, stype)
            Q = calc_thermal_power(s)
            assert Q > 0, f"Q({fluid}, {Tin}→{Tout}) = {Q} — DEVE essere > 0"


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT 3: Exergia — leggi della termodinamica
# ═══════════════════════════════════════════════════════════════════════════════


class TestExergySanity:
    """Verifica che l'exergia rispetti i vincoli termodinamici."""

    def test_exergy_less_than_energy(self):
        """LEGGE: Exergia ≤ Energia termica (secondo principio)."""
        cases = [
            ("acqua", 90, 60, 1.0),
            ("aria", 500, 200, 0.5),
            ("fumi_gas_naturale", 400, 150, 1.0),
        ]
        for fluid, Tin, Tout, m in cases:
            s = ThermalStream("test", fluid, Tin, Tout, m, 8, 250, StreamType.HOT_WASTE)
            Q = calc_thermal_power(s)
            Ex = calc_exergy(s, T_ambient=25)
            assert Ex <= Q, f"Ex ({Ex:.1f}) > Q ({Q:.1f}) per {fluid} — VIOLA secondo principio!"

    def test_exergy_positive_above_ambient(self):
        """Se T_stream > T_ambiente, l'exergia deve essere positiva."""
        s = ThermalStream("test", "acqua", 90, 60, 1.0, 8, 250, StreamType.HOT_WASTE)
        Ex = calc_exergy(s, T_ambient=25)
        assert Ex > 0, f"Ex = {Ex} per T_mean=75°C > T_amb=25°C — deve essere > 0"

    def test_exergy_increases_with_temperature(self):
        """INVARIANTE: A parità di Q, exergia maggiore per temperature più alte."""
        # Compariamo due stream con Q simile ma T diverse
        s_hot = ThermalStream("hot", "aria", 500, 200, 0.35, 8, 250, StreamType.HOT_WASTE)
        s_warm = ThermalStream("warm", "acqua", 90, 60, 1.0, 8, 250, StreamType.HOT_WASTE)
        Ex_hot = calc_exergy(s_hot)
        Ex_warm = calc_exergy(s_warm)
        # L'exergia del flusso ad alta T deve essere relativamente più alta
        Q_hot = calc_thermal_power(s_hot)
        Q_warm = calc_thermal_power(s_warm)
        ratio_hot = Ex_hot / Q_hot
        ratio_warm = Ex_warm / Q_warm
        assert ratio_hot > ratio_warm, "Qualità exergetica deve essere maggiore ad alta T"

    def test_carnot_factor_range(self):
        """Il fattore di Carnot deve essere in [0, 1) per T > T_ambiente."""
        for T_mean in [40, 80, 150, 300, 500, 800]:
            T_amb = 25
            carnot = 1 - (T_amb + 273.15) / (T_mean + 273.15)
            assert 0 <= carnot < 1, f"Carnot({T_mean}°C) = {carnot} — fuori range!"


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT 4: Energia annuale — ordini di grandezza
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnnualEnergySanity:
    """Verifica che le energie annuali siano nell'ordine di grandezza giusto."""

    def test_annual_energy_order_of_magnitude(self):
        """100 kW per 8000 h/anno = 800 MWh/anno."""
        s = ThermalStream("test", "acqua", 90, 60, 1.0, 24, 365, StreamType.HOT_WASTE)
        Q = calc_thermal_power(s)
        E = calc_annual_energy(s)
        expected = Q * 8760 / 1000  # kW × h / 1000 = MWh
        assert abs(E - expected) < 1, f"E = {E}, expected = {expected}"

    def test_energy_consistent_with_power(self):
        """E [MWh] = Q [kW] × ore_annue / 1000."""
        s = ThermalStream("test", "aria", 300, 100, 0.5, 16, 250, StreamType.HOT_WASTE)
        Q = calc_thermal_power(s)
        E = calc_annual_energy(s)
        expected = Q * 16 * 250 / 1000
        assert abs(E - expected) / expected < 0.001


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT 5: Heat Balance — conservazione dell'energia
# ═══════════════════════════════════════════════════════════════════════════════


class TestHeatBalanceSanity:
    """Verifica conservazione energia nel bilancio."""

    def test_sum_equals_total(self):
        """La somma delle Q per stream deve uguale al totale."""
        hb = FactoryHeatBalance("Test", 25)
        hb.add_stream(
            ThermalStream("S1", "fumi_gas_naturale", 500, 200, 1.0, 16, 250, StreamType.HOT_WASTE)
        )
        hb.add_stream(ThermalStream("S2", "acqua", 60, 30, 2.0, 16, 250, StreamType.HOT_WASTE))
        hb.add_stream(ThermalStream("S3", "aria", 150, 80, 0.5, 16, 250, StreamType.HOT_WASTE))

        summary = hb.summary()
        sum_Q = sum(r["Q_kW"] for r in summary["stream_results"])
        assert abs(sum_Q - summary["total_waste_kW"]) < 0.5, "Somma stream ≠ totale"

    def test_class_percentages_sum_to_100(self):
        """Le percentuali per classe T devono sommare a ~100%."""
        hb = FactoryHeatBalance("Test", 25)
        hb.add_stream(
            ThermalStream("S1", "fumi_gas_naturale", 500, 200, 1.0, 16, 250, StreamType.HOT_WASTE)
        )
        hb.add_stream(ThermalStream("S2", "acqua", 60, 30, 2.0, 16, 250, StreamType.HOT_WASTE))
        hb.add_stream(ThermalStream("S3", "aria", 150, 80, 0.5, 16, 250, StreamType.HOT_WASTE))

        summary = hb.summary()
        total_pct = sum(
            summary["by_temperature_class"][cls]["pct_of_waste"]
            for cls in ["alta", "media", "bassa"]
        )
        assert abs(total_pct - 100) < 0.1, f"Percentuali classi: {total_pct}%, atteso 100%"

    def test_estimated_input_greater_than_waste(self):
        """Se l'efficienza < 100%, l'input stimato DEVE essere > scarto."""
        hb = FactoryHeatBalance("Test", 25)
        hb.add_stream(ThermalStream("S1", "acqua", 90, 60, 1.0, 16, 250, StreamType.HOT_WASTE))
        hb.estimate_energy_input(efficiency=0.85)
        summary = hb.summary()
        assert summary["energy_input_kW"] > summary["total_waste_kW"]
