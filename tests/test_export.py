"""Test per export Excel (.xlsx).

Verifica che il file generato sia valido e contenga i dati attesi.
"""

import pytest
import pandas as pd
from io import BytesIO

from heatscout.core.stream import ThermalStream, StreamType
from heatscout.core.heat_balance import FactoryHeatBalance
from heatscout.core.technology_selector import select_technologies
from heatscout.core.economics import economic_analysis, economic_analysis_with_incentives
from heatscout.report.excel_export import export_to_excel


@pytest.fixture
def fonderia_data():
    """Setup completo esempio fonderia: summary, econ_results, incentive_summaries."""
    hb = FactoryHeatBalance(factory_name="Fonderia Test", T_ambient=25.0)
    hb.add_stream(ThermalStream(
        name="Fumi forno",
        fluid_type="fumi_gas_naturale",
        T_in=400.0, T_out=180.0,
        mass_flow=2.0,
        hours_per_day=16.0, days_per_year=300.0,
        stream_type=StreamType.HOT_WASTE,
    ))
    hb.add_stream(ThermalStream(
        name="Acqua raffreddamento",
        fluid_type="acqua",
        T_in=60.0, T_out=35.0,
        mass_flow=1.5,
        hours_per_day=16.0, days_per_year=300.0,
        stream_type=StreamType.HOT_WASTE,
    ))
    hb.calculate()
    summary = hb.summary()

    econ_results = []
    for stream in hb.streams:
        if stream.stream_type != StreamType.HOT_WASTE:
            continue
        recs = select_technologies(stream, energy_price_EUR_kWh=0.08)
        for rec in recs:
            econ = economic_analysis(rec, energy_price_EUR_kWh=0.08)
            econ_results.append(econ)

    # Incentivi
    summaries = []
    for econ in econ_results:
        s = economic_analysis_with_incentives(
            econ, capex_riduzione_pct=30.0, nome_incentivo="Test Grant",
            tee_enabled=True, prezzo_tee=250.0,
        )
        summaries.append(s)

    return summary, econ_results, summaries


class TestExcelExport:
    """Test generazione file Excel."""

    def test_returns_bytes(self, fonderia_data):
        """Export ritorna bytes non vuoti."""
        summary, econ_results, summaries = fonderia_data
        xlsx = export_to_excel(summary, econ_results, summaries)
        assert isinstance(xlsx, bytes)
        assert len(xlsx) > 1000  # un xlsx valido è almeno qualche KB

    def test_has_three_sheets(self, fonderia_data):
        """Il file ha esattamente 3 fogli."""
        summary, econ_results, summaries = fonderia_data
        xlsx = export_to_excel(summary, econ_results, summaries)
        xls = pd.ExcelFile(BytesIO(xlsx), engine="openpyxl")
        assert set(xls.sheet_names) == {"Streams", "Technologies", "Economics"}

    def test_streams_sheet_content(self, fonderia_data):
        """Foglio Streams contiene tutti gli stream con colonne corrette."""
        summary, econ_results, summaries = fonderia_data
        xlsx = export_to_excel(summary, econ_results, summaries)
        df = pd.read_excel(BytesIO(xlsx), sheet_name="Streams", engine="openpyxl")

        assert len(df) == 2  # 2 stream
        assert "Name" in df.columns
        assert "T_in (°C)" in df.columns
        assert "Thermal power (kW)" in df.columns
        assert "Annual energy (MWh/yr)" in df.columns
        # Valori positivi
        assert (df["Thermal power (kW)"] > 0).all()
        assert (df["Annual energy (MWh/yr)"] > 0).all()

    def test_technologies_sheet_content(self, fonderia_data):
        """Foglio Technologies ha le colonne economiche."""
        summary, econ_results, summaries = fonderia_data
        xlsx = export_to_excel(summary, econ_results, summaries)
        df = pd.read_excel(BytesIO(xlsx), sheet_name="Technologies", engine="openpyxl")

        assert len(df) == len(econ_results)
        assert "CAPEX (€)" in df.columns
        assert "Annual savings (€/yr)" in df.columns
        assert "Total investment (€)" in df.columns
        # CAPEX min < medio < max
        assert (df["CAPEX min (€)"] <= df["CAPEX (€)"]).all()
        assert (df["CAPEX (€)"] <= df["CAPEX max (€)"]).all()

    def test_economics_sheet_with_incentives(self, fonderia_data):
        """Foglio Economics include colonne incentivo."""
        summary, econ_results, summaries = fonderia_data
        xlsx = export_to_excel(summary, econ_results, summaries)
        df = pd.read_excel(BytesIO(xlsx), sheet_name="Economics", engine="openpyxl")

        assert len(df) == len(econ_results)
        assert "Payback (yr)" in df.columns
        assert "NPV 10yr (€)" in df.columns
        # Colonne incentivo CAPEX
        assert "CAPEX reduction (%)" in df.columns
        assert "CAPEX net (€)" in df.columns
        # Colonne TEE
        assert "TEP/yr" in df.columns
        assert "TEE revenue/yr (€)" in df.columns
        # Colonne combinato
        assert "NPV combined (€)" in df.columns

    def test_economics_sheet_without_incentives(self, fonderia_data):
        """Senza incentivi, colonne extra non presenti."""
        summary, econ_results, _ = fonderia_data
        xlsx = export_to_excel(summary, econ_results, incentive_summaries=None)
        df = pd.read_excel(BytesIO(xlsx), sheet_name="Economics", engine="openpyxl")

        assert "Payback (yr)" in df.columns
        assert "CAPEX reduction (%)" not in df.columns
        assert "TEP/yr" not in df.columns

    def test_values_match_econ_results(self, fonderia_data):
        """I valori nel foglio Economics corrispondono a quelli calcolati."""
        summary, econ_results, summaries = fonderia_data
        xlsx = export_to_excel(summary, econ_results, summaries)
        df = pd.read_excel(BytesIO(xlsx), sheet_name="Economics", engine="openpyxl")

        for i, econ in enumerate(econ_results):
            assert df.loc[i, "Investment (€)"] == round(econ.total_investment_EUR, 0)
            assert df.loc[i, "Payback (yr)"] == econ.payback_years
            assert df.loc[i, "NPV 10yr (€)"] == round(econ.npv_EUR, 0)
