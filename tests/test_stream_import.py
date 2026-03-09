"""Test per import stream da CSV/Excel."""

import pytest
import pandas as pd
from io import BytesIO

from heatscout.report.stream_import import import_streams, generate_template, MAX_STREAMS


class TestGenerateTemplate:

    def test_returns_bytes(self):
        tpl = generate_template()
        assert isinstance(tpl, bytes)
        assert len(tpl) > 50

    def test_template_is_valid_csv(self):
        tpl = generate_template()
        df = pd.read_csv(BytesIO(tpl), encoding="utf-8-sig")
        assert len(df) == 2
        assert "name" in df.columns
        assert "T_in" in df.columns

    def test_template_reimportable(self):
        """Template can be imported back without errors."""
        tpl = generate_template()
        streams = import_streams(tpl, "template.csv")
        assert len(streams) == 2
        assert streams[0]["name"] == "Flue gas furnace"


class TestImportCSV:

    def _make_csv(self, rows: list[dict]) -> bytes:
        df = pd.DataFrame(rows)
        return df.to_csv(index=False).encode("utf-8")

    def test_basic_import(self):
        csv = self._make_csv([{
            "name": "S1", "fluid_type": "acqua",
            "T_in": 80, "T_out": 40,
            "mass_flow": 1.0, "hours_per_day": 16, "days_per_year": 300,
            "stream_type": "hot_waste",
        }])
        streams = import_streams(csv, "test.csv")
        assert len(streams) == 1
        assert streams[0]["name"] == "S1"
        assert streams[0]["T_in"] == 80.0

    def test_alias_columns(self):
        """Accepts Italian column names."""
        csv = self._make_csv([{
            "nome": "S1", "fluido": "acqua",
            "t_ingresso": 80, "t_uscita": 40,
            "portata": 1.0, "ore": 16, "giorni": 300,
            "tipo": "hot_waste",
        }])
        streams = import_streams(csv, "test.csv")
        assert len(streams) == 1
        assert streams[0]["T_in"] == 80.0

    def test_multiple_streams(self):
        rows = [
            {"name": f"S{i}", "fluid_type": "acqua",
             "T_in": 80, "T_out": 40, "mass_flow": 1.0,
             "hours_per_day": 16, "days_per_year": 300,
             "stream_type": "hot_waste"}
            for i in range(5)
        ]
        streams = import_streams(self._make_csv(rows), "test.csv")
        assert len(streams) == 5

    def test_too_many_streams(self):
        rows = [
            {"name": f"S{i}", "fluid_type": "acqua",
             "T_in": 80, "T_out": 40, "mass_flow": 1.0,
             "hours_per_day": 16, "days_per_year": 300,
             "stream_type": "hot_waste"}
            for i in range(MAX_STREAMS + 1)
        ]
        with pytest.raises(ValueError, match="Too many"):
            import_streams(self._make_csv(rows), "test.csv")

    def test_missing_column(self):
        csv = self._make_csv([{"name": "S1", "T_in": 80}])
        with pytest.raises(ValueError, match="Missing required"):
            import_streams(csv, "test.csv")

    def test_empty_file(self):
        csv = b"name,fluid_type,T_in,T_out,mass_flow,hours_per_day,days_per_year,stream_type\n"
        with pytest.raises(ValueError, match="empty"):
            import_streams(csv, "test.csv")

    def test_invalid_data(self):
        csv = self._make_csv([{
            "name": "S1", "fluid_type": "acqua",
            "T_in": "not_a_number", "T_out": 40,
            "mass_flow": 1.0, "hours_per_day": 16, "days_per_year": 300,
            "stream_type": "hot_waste",
        }])
        with pytest.raises(ValueError, match="invalid data"):
            import_streams(csv, "test.csv")


class TestImportExcel:

    def test_xlsx_import(self):
        """Import from .xlsx file."""
        df = pd.DataFrame([{
            "name": "Excel stream", "fluid_type": "acqua",
            "T_in": 90, "T_out": 50, "mass_flow": 2.0,
            "hours_per_day": 20, "days_per_year": 350,
            "stream_type": "hot_waste",
        }])
        buf = BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        streams = import_streams(buf.getvalue(), "test.xlsx")
        assert len(streams) == 1
        assert streams[0]["name"] == "Excel stream"
        assert streams[0]["T_in"] == 90.0

    def test_exported_file_reimportable(self):
        """A file exported by HeatScout can be re-imported as streams."""
        # Generate an export-like Excel
        df = pd.DataFrame([
            {"Name": "S1", "Type": "hot_waste", "Fluid": "acqua",
             "T_in (°C)": 80, "T_out (°C)": 40,
             "mass_flow": 1.0, "hours_per_day": 16, "days_per_year": 300,
             "stream_type": "hot_waste"},
        ])
        buf = BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        streams = import_streams(buf.getvalue(), "export.xlsx")
        assert len(streams) == 1
