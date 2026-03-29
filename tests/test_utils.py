"""Tests for utility functions."""

import re
from datetime import date, datetime
from io import StringIO
from unittest.mock import patch

import pandas as pd
import pytest
import typer

from meteo.utils import (
    detect_format,
    output_df,
    parse_date,
    parse_datetime,
    resolve_station_or_point,
)


class TestParseDate:
    """Test date parsing in various formats."""

    def test_full_date(self):
        assert parse_date("2020-01-15") == date(2020, 1, 15)

    def test_year_month_start(self):
        assert parse_date("2020-03") == date(2020, 3, 1)

    def test_year_month_end(self):
        assert parse_date("2020-03", is_end=True) == date(2020, 3, 31)

    def test_year_month_end_december(self):
        assert parse_date("2020-12", is_end=True) == date(2020, 12, 31)

    def test_year_start(self):
        assert parse_date("2020") == date(2020, 1, 1)

    def test_year_end(self):
        assert parse_date("2020", is_end=True) == date(2020, 12, 31)

    def test_none(self):
        assert parse_date(None) is None

    def test_iso_with_time(self):
        result = parse_date("2020-01-15T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2020
        assert result.month == 1
        assert result.day == 15

    def test_invalid_date_string(self):
        """Non-date strings raise BadParameter."""
        with pytest.raises(typer.BadParameter, match="Invalid date format"):
            parse_date("not-a-date")

    def test_invalid_month(self):
        """Month 13 raises BadParameter."""
        with pytest.raises(typer.BadParameter, match="Invalid date format"):
            parse_date("2020-13-01")

    def test_invalid_day(self):
        """Day 32 raises BadParameter."""
        with pytest.raises(typer.BadParameter, match="Invalid date format"):
            parse_date("2020-01-32")


class TestParseDatetime:
    """Test datetime parsing."""

    def test_returns_datetime(self):
        result = parse_datetime("2020-01-15")
        assert isinstance(result, datetime)
        assert result == datetime(2020, 1, 15)

    def test_none(self):
        assert parse_datetime(None) is None


class TestResolveStationOrPoint:
    """Test station vs coordinate disambiguation."""

    def test_station_id(self):
        result = resolve_station_or_point("10637")
        assert result == ("station", "10637")

    def test_coordinates(self):
        result = resolve_station_or_point("50.1109,8.6821")
        assert result[0] == "point"
        assert result[1] == pytest.approx(50.1109)
        assert result[2] == pytest.approx(8.6821)

    def test_negative_coordinates(self):
        result = resolve_station_or_point("-33.8688,151.2093")
        assert result[0] == "point"
        assert result[1] == pytest.approx(-33.8688)

    def test_two_numeric_args_treated_as_stations(self):
        """Two numeric args are always treated as station IDs, not coordinates."""
        result = resolve_station_or_point("100.0", "8.0")
        assert result == ("stations", ["100.0", "8.0"])

    def test_two_numeric_args_treated_as_stations_2(self):
        """Two numeric args are always treated as station IDs, not coordinates."""
        result = resolve_station_or_point("50.0", "200.0")
        assert result == ("stations", ["50.0", "200.0"])

    def test_two_station_ids_treated_as_stations(self):
        """Two non-numeric args are treated as station IDs."""
        result = resolve_station_or_point("abc", "def")
        assert result == ("stations", ["abc", "def"])

    def test_two_numeric_station_ids(self):
        """Two large numeric station IDs (e.g. WMO IDs) are treated as station IDs."""
        result = resolve_station_or_point("10637", "10635")
        assert result == ("stations", ["10637", "10635"])

    def test_comma_separated_single_arg(self):
        """Single arg with comma is parsed as lat,lon."""
        result = resolve_station_or_point("50.1109,8.6821")
        assert result[0] == "point"
        assert result[1] == pytest.approx(50.1109)
        assert result[2] == pytest.approx(8.6821)

    def test_comma_separated_invalid(self):
        """Single arg with comma but invalid coords raises BadParameter."""
        with pytest.raises(typer.BadParameter):
            resolve_station_or_point("abc,8.6")

    def test_three_station_ids(self):
        """Three station IDs are returned as ('stations', [...])."""
        result = resolve_station_or_point("10637", "10729", "10500")
        assert result[0] == "stations"
        assert result[1] == ["10637", "10729", "10500"]


class TestDetectFormat:
    """Test format auto-detection."""

    def test_explicit_format(self):
        assert detect_format("json", None) == "json"

    def test_from_extension_csv(self):
        assert detect_format(None, "output.csv") == "csv"

    def test_from_extension_json(self):
        assert detect_format(None, "output.json") == "json"

    def test_from_extension_xlsx(self):
        assert detect_format(None, "output.xlsx") == "xlsx"

    def test_from_extension_parquet(self):
        assert detect_format(None, "output.parquet") == "parquet"

    def test_from_extension_png(self):
        assert detect_format(None, "output.png") == "png"

    def test_from_extension_svg(self):
        assert detect_format(None, "output.svg") == "svg"

    def test_default_text(self):
        assert detect_format(None, None) == "text"

    def test_explicit_overrides_extension(self):
        assert detect_format("json", "output.csv") == "json"


class TestOutputDf:
    """Test output_df text format truncation and --all flag."""

    def _make_large_df(self, n=100):
        """Create a DataFrame with n rows."""
        return pd.DataFrame(
            {"value": range(n)},
            index=pd.RangeIndex(n, name="idx"),
        )

    def test_text_default_truncates(self):
        """Default text output truncates large DataFrames."""
        df = self._make_large_df(200)
        buf = StringIO()
        with patch("sys.stdout", buf):
            output_df(df, "text")
        text = buf.getvalue()
        # Pandas default max_rows is 60; output should contain ".." truncation
        lines = text.strip().split("\n")
        # Should NOT contain all 200 data rows (+ header line)
        assert len(lines) < 200

    def test_text_show_all(self):
        """--all flag prints every row."""
        df = self._make_large_df(200)
        buf = StringIO()
        with patch("sys.stdout", buf):
            output_df(df, "text", show_all=True)
        text = buf.getvalue()
        # All 200 data rows should appear - count lines matching the full
        # "<index>  <value>" pattern to avoid false positives from substring matches
        lines = text.strip().split("\n")
        data_lines = [line for line in lines if re.match(r"^\d+\s+\d+\s*$", line)]
        assert len(data_lines) == 200

    def test_text_small_df_unchanged(self):
        """Small DataFrames display fully even without --all."""
        df = self._make_large_df(5)
        buf = StringIO()
        with patch("sys.stdout", buf):
            output_df(df, "text")
        text = buf.getvalue()
        # All 5 rows should appear
        assert "0" in text
        assert "4" in text

    def test_show_all_ignored_for_csv(self):
        """show_all has no effect on CSV format."""
        df = self._make_large_df(5)
        buf = StringIO()
        with patch("sys.stdout", buf):
            output_df(df, "csv", show_all=True)
        text = buf.getvalue()
        assert "value" in text

    def test_empty_df_exits(self):
        """Empty DataFrame exits with code 1."""
        df = pd.DataFrame()
        with pytest.raises(typer.Exit):
            output_df(df, "text")

    def test_none_df_exits(self):
        """None DataFrame exits with code 1."""
        with pytest.raises(typer.Exit):
            output_df(None, "text")

    def test_xlsx_without_output_exits(self):
        """XLSX format without output path exits with code 2."""
        df = pd.DataFrame({"value": [1]})
        with pytest.raises(typer.Exit):
            output_df(df, "xlsx")

    def test_parquet_without_output_exits(self):
        """Parquet format without output path exits with code 2."""
        df = pd.DataFrame({"value": [1]})
        with pytest.raises(typer.Exit):
            output_df(df, "parquet")

    def test_png_without_output_exits(self):
        """PNG format without output path exits with code 2."""
        df = pd.DataFrame({"value": [1]})
        with pytest.raises(typer.Exit):
            output_df(df, "png")

    def test_unknown_format_exits(self):
        """Unknown format exits with code 2."""
        df = pd.DataFrame({"value": [1]})
        with pytest.raises(typer.Exit):
            output_df(df, "xyz")

    def test_csv_output(self):
        """CSV format outputs correct text."""
        df = pd.DataFrame(
            {"tavg": [10.5], "tmin": [5.0]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        buf = StringIO()
        with patch("sys.stdout", buf):
            output_df(df, "csv")
        text = buf.getvalue()
        assert "tavg" in text
        assert "10.5" in text

    def test_csv_no_header(self):
        """CSV output with no_header omits the header row."""
        df = pd.DataFrame(
            {"tavg": [10.5]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        buf = StringIO()
        with patch("sys.stdout", buf):
            output_df(df, "csv", no_header=True)
        text = buf.getvalue()
        assert "tavg" not in text
        assert "10.5" in text

    def test_json_output(self):
        """JSON format outputs valid JSON."""
        import json

        df = pd.DataFrame(
            {"tavg": [10.5]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        buf = StringIO()
        with patch("sys.stdout", buf):
            output_df(df, "json")
        text = buf.getvalue()
        parsed = json.loads(text)
        assert isinstance(parsed, list)
        assert parsed[0]["tavg"] == pytest.approx(10.5)


class TestPlotDataframe:
    """Tests for plot_dataframe edge cases."""

    def test_partial_nan_columns_plot_succeeds(self, tmp_path):
        """Partial NaN columns are skipped; non-NaN columns are plotted successfully."""
        import numpy as np

        from meteo.plotting import plot_dataframe

        df = pd.DataFrame(
            {"temp": [np.nan, np.nan], "prcp": [1.0, 2.0]},
            index=pd.date_range("2024-01-01", periods=2),
        )
        out = str(tmp_path / "out.png")
        # Should not raise — prcp has real data
        plot_dataframe(df, out, "png")
        assert (tmp_path / "out.png").exists()

    def test_all_nan_columns_exits(self, tmp_path):
        """All-NaN DataFrame raises typer.Exit rather than saving a silent empty chart."""
        import numpy as np

        from meteo.plotting import plot_dataframe

        df = pd.DataFrame(
            {"temp": [np.nan, np.nan], "prcp": [np.nan, np.nan]},
            index=pd.date_range("2024-01-01", periods=2),
        )
        out = str(tmp_path / "out.png")
        with pytest.raises(typer.Exit):
            plot_dataframe(df, out, "png")
        # File must NOT have been created
        assert not (tmp_path / "out.png").exists()

    def test_non_numeric_columns_excluded(self, tmp_path):
        """Non-numeric (string) columns are excluded from the plot."""
        from meteo.plotting import plot_dataframe

        df = pd.DataFrame(
            {"temp": [1.0, 2.0], "label": ["foo", "bar"]},
            index=pd.date_range("2024-01-01", periods=2),
        )
        out = str(tmp_path / "out.png")
        # Should succeed: temp is numeric, label is excluded silently
        plot_dataframe(df, out, "png")
        assert (tmp_path / "out.png").exists()

    def test_single_row_dataframe_plots(self, tmp_path):
        """Single-row DataFrame is plotted without error."""
        from meteo.plotting import plot_dataframe

        df = pd.DataFrame(
            {"temp": [10.0]},
            index=pd.date_range("2024-01-01", periods=1),
        )
        out = str(tmp_path / "out.png")
        plot_dataframe(df, out, "png")
        assert (tmp_path / "out.png").exists()
