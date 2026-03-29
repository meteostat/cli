"""Tests for command modules using mocked Meteostat API."""

from dataclasses import dataclass, field
from unittest.mock import patch

import pandas as pd


@dataclass
class MockStation:
    id: str = "10637"
    name: str = "Frankfurt Airport"
    country: str = "DE"
    region: str = "HE"
    latitude: float = 50.0264
    longitude: float = 8.5431
    elevation: int = 112
    timezone: str = "Europe/Berlin"
    identifiers: dict = field(default_factory=lambda: {"wmo": "10637", "icao": "EDDF"})


class MockTimeSeries:
    """Mock for meteostat.TimeSeries."""

    def __init__(self, df=None):
        self._df = df
        self.empty = df is None or df.empty

    def fetch(self, sources=False, **kwargs):
        return self._df


class TestStationCommand:
    """Test the station metadata command."""

    def test_station_found(self, invoke):
        """Station command returns metadata for a known station."""
        mock_station = MockStation()
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = mock_station
            result = invoke("station", "10637")
            assert result.exit_code == 0
            assert "Frankfurt" in result.output

    def test_station_not_found(self, invoke):
        """Station command exits 1 for unknown station."""
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = None
            result = invoke("station", "99999")
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_station_alias_s(self, invoke):
        """Alias 's' works the same as 'station'."""
        mock_station = MockStation()
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = mock_station
            result = invoke("s", "10637")
            assert result.exit_code == 0

    def test_station_bbox_invalid_count(self, invoke):
        """Station --bbox with wrong number of values exits 2."""
        result = invoke("station", "--bbox", "1,2,3")
        assert result.exit_code == 2

    def test_station_bbox_invalid_float(self, invoke):
        """Station --bbox with non-numeric values exits 2 with a clear error."""
        result = invoke("station", "--bbox", "abc,1,2,3")
        assert result.exit_code == 2
        assert "numeric" in result.output or "float" in result.output.lower()


class TestNearbyCommand:
    """Test the nearby stations command."""

    def test_nearby_basic(self, invoke):
        """Nearby command returns stations near coordinates."""
        df = pd.DataFrame(
            {
                "name": ["Frankfurt Airport"],
                "country": ["DE"],
                "distance": [1234.5],
            },
            index=pd.Index(["10637"], name="id"),
        )
        with patch("meteostat.stations") as mock_stations:
            mock_stations.nearby.return_value = df
            with patch("meteostat.Point"):
                result = invoke("nearby", "50.1109", "8.6821")
                assert result.exit_code == 0
                assert "Frankfurt" in result.output


class TestHourlyCommand:
    """Test the hourly data command."""

    def test_hourly_help(self, invoke):
        result = invoke("hourly", "--help")
        assert result.exit_code == 0
        assert "--start" in result.output

    def test_hourly_station(self, invoke):
        """Hourly command fetches data for a station."""
        df = pd.DataFrame(
            {"temp": [5.0, 6.0], "prcp": [0.0, 1.2]},
            index=pd.DatetimeIndex(
                ["2020-01-01 00:00", "2020-01-01 01:00"], name="time"
            ),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.hourly", return_value=mock_ts), patch("meteostat.config"):
            result = invoke("hourly", "10637", "-s", "2020-01-01", "-e", "2020-01-02")
            assert result.exit_code == 0
            assert "temp" in result.output


class TestDailyCommand:
    """Test the daily data command."""

    def test_daily_help(self, invoke):
        result = invoke("daily", "--help")
        assert result.exit_code == 0

    def test_daily_station(self, invoke):
        """Daily command fetches data for a station."""
        df = pd.DataFrame(
            {"tavg": [10.5], "tmin": [5.0], "tmax": [15.0]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke("daily", "10637", "-s", "2020-01-01", "-e", "2020-01-02")
            assert result.exit_code == 0
            assert "tavg" in result.output


class TestMonthlyCommand:
    """Test the monthly data command."""

    def test_monthly_help(self, invoke):
        result = invoke("monthly", "--help")
        assert result.exit_code == 0

    def test_monthly_station(self, invoke):
        """Monthly command fetches data for a station."""
        df = pd.DataFrame(
            {"tavg": [10.5, 11.2], "prcp": [55.0, 60.1]},
            index=pd.DatetimeIndex(["2020-01-01", "2020-02-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with (
            patch("meteostat.monthly", return_value=mock_ts),
            patch("meteostat.config"),
        ):
            result = invoke("monthly", "10637", "-s", "2020-01", "-e", "2020-02")
            assert result.exit_code == 0
            assert "tavg" in result.output


class TestNormalsCommand:
    """Test the normals data command."""

    def test_normals_help(self, invoke):
        result = invoke("normals", "--help")
        assert result.exit_code == 0

    def test_normals_station(self, invoke):
        """Normals command fetches data for a station."""
        df = pd.DataFrame(
            {"tavg": [0.5, 2.3, 6.1]},
            index=pd.Index([1, 2, 3], name="month"),
        )
        mock_ts = MockTimeSeries(df)

        with (
            patch("meteostat.normals", return_value=mock_ts),
            patch("meteostat.config"),
        ):
            result = invoke("normals", "10637", "-s", "1991", "-e", "2020")
            assert result.exit_code == 0
            assert "tavg" in result.output

    def test_normals_invalid_year_format(self, invoke):
        """Normals command exits with error for non-integer start/end."""
        result = invoke("normals", "10637", "--start", "2020-01")
        assert result.exit_code != 0
        assert result.output != ""

    def test_normals_invalid_year_string(self, invoke):
        """Normals command exits with error for non-numeric year."""
        result = invoke("normals", "10637", "--start", "abc")
        assert result.exit_code != 0

    def test_normals_year_out_of_range(self, invoke):
        """Normals command exits with error for out-of-range year (e.g., 5-digit)."""
        result = invoke("normals", "10637", "--start", "19910", "--end", "2020")
        assert result.exit_code != 0

    def test_normals_year_negative(self, invoke):
        """Normals command exits with error for negative year."""
        result = invoke("normals", "10637", "--start", "-1991", "--end", "2020")
        assert result.exit_code != 0


class TestInventoryCommand:
    """Test the inventory command."""

    def test_inventory_help(self, invoke):
        result = invoke("inventory", "--help")
        assert result.exit_code == 0

    def test_inventory_no_data(self, invoke):
        """Inventory command exits 1 when no inventory data is found."""
        import pandas as pd

        class MockInventory:
            df = pd.DataFrame()

        with patch("meteostat.stations") as mock_stations:
            mock_stations.inventory.return_value = MockInventory()
            result = invoke("inventory", "99999")
            assert result.exit_code == 1
            assert "No inventory data" in result.output


class TestAllFlag:
    """Test that --all / -A flag is accepted by all DataFrame-outputting commands."""

    def test_station_all_flag(self, invoke):
        """Station command accepts --all flag."""
        mock_station = MockStation()
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = mock_station
            result = invoke("station", "10637", "--all")
            assert result.exit_code == 0
            assert "Frankfurt" in result.output

    def test_station_all_short_flag(self, invoke):
        """Station command accepts -A short flag."""
        mock_station = MockStation()
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = mock_station
            result = invoke("station", "10637", "-A")
            assert result.exit_code == 0

    def test_nearby_all_flag(self, invoke):
        """Nearby command accepts --all flag."""
        df = pd.DataFrame(
            {
                "name": ["Frankfurt Airport"],
                "country": ["DE"],
                "distance": [1234.5],
            },
            index=pd.Index(["10637"], name="id"),
        )
        with patch("meteostat.stations") as mock_stations:
            mock_stations.nearby.return_value = df
            with patch("meteostat.Point"):
                result = invoke("nearby", "50.1109", "8.6821", "--all")
                assert result.exit_code == 0

    def test_hourly_all_flag(self, invoke):
        """Hourly command accepts --all flag."""
        df = pd.DataFrame(
            {"temp": [5.0, 6.0], "prcp": [0.0, 1.2]},
            index=pd.DatetimeIndex(
                ["2020-01-01 00:00", "2020-01-01 01:00"], name="time"
            ),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.hourly", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "hourly", "10637", "-s", "2020-01-01", "-e", "2020-01-02", "--all"
            )
            assert result.exit_code == 0

    def test_daily_all_flag(self, invoke):
        """Daily command accepts --all flag."""
        df = pd.DataFrame(
            {"tavg": [10.5], "tmin": [5.0], "tmax": [15.0]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily", "10637", "-s", "2020-01-01", "-e", "2020-01-02", "--all"
            )
            assert result.exit_code == 0

    def test_normals_all_flag(self, invoke):
        """Normals command accepts --all flag."""
        df = pd.DataFrame(
            {"tavg": [0.5, 2.3, 6.1]},
            index=pd.Index([1, 2, 3], name="month"),
        )
        mock_ts = MockTimeSeries(df)

        with (
            patch("meteostat.normals", return_value=mock_ts),
            patch("meteostat.config"),
        ):
            result = invoke("normals", "10637", "-s", "1991", "-e", "2020", "--all")
            assert result.exit_code == 0

    def test_all_flag_in_help(self, invoke):
        """--all flag appears in help for all data commands."""
        for cmd in [
            "station",
            "stations",
            "nearby",
            "inventory",
            "hourly",
            "daily",
            "monthly",
            "normals",
        ]:
            result = invoke(cmd, "--help")
            assert result.exit_code == 0
            assert "--all" in result.output, f"--all not in {cmd} help"


class TestOutputFormats:
    """Test --format and --no-header options on data commands."""

    def test_daily_csv_format(self, invoke):
        """Daily command outputs valid CSV with --format csv."""
        df = pd.DataFrame(
            {"tavg": [10.5], "tmin": [5.0], "tmax": [15.0]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--format",
                "csv",
            )
            assert result.exit_code == 0
            assert "tavg" in result.output
            assert "10.5" in result.output

    def test_daily_csv_no_header(self, invoke):
        """Daily command with --no-header omits CSV header row."""
        df = pd.DataFrame(
            {"tavg": [10.5]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--format",
                "csv",
                "--no-header",
            )
            assert result.exit_code == 0
            assert "tavg" not in result.output
            assert "10.5" in result.output

    def test_daily_json_format(self, invoke):
        """Daily command outputs JSON with --format json."""
        df = pd.DataFrame(
            {"tavg": [10.5]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--format",
                "json",
            )
            assert result.exit_code == 0
            assert "tavg" in result.output

    def test_daily_xlsx_without_output_exits(self, invoke):
        """XLSX format without --output exits with code 2."""
        df = pd.DataFrame(
            {"tavg": [10.5]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--format",
                "xlsx",
            )
            assert result.exit_code == 2
            assert "XLSX" in result.output

    def test_daily_png_without_output_exits(self, invoke):
        """PNG format without --output exits with code 2."""
        df = pd.DataFrame(
            {"tavg": [10.5]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--format",
                "png",
            )
            assert result.exit_code == 2
            assert "PNG" in result.output

    def test_daily_unknown_format_exits(self, invoke):
        """Unknown format exits with code 2."""
        df = pd.DataFrame(
            {"tavg": [10.5]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--format",
                "xyz",
            )
            assert result.exit_code == 2

    def test_station_csv_format(self, invoke):
        """Station command outputs valid CSV with --format csv."""
        mock_station = MockStation()
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = mock_station
            result = invoke("station", "10637", "--format", "csv")
            assert result.exit_code == 0
            assert "10637" in result.output

    def test_station_csv_no_header(self, invoke):
        """Station command with --no-header omits CSV header."""
        mock_station = MockStation()
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = mock_station
            result = invoke("station", "10637", "--format", "csv", "--no-header")
            assert result.exit_code == 0
            # Header fields should be absent; data should be present
            assert "name" not in result.output
            assert "Frankfurt" in result.output


class TestStationFilters:
    """Test station listing with various filters."""

    def _mock_df(self):
        return pd.DataFrame(
            {
                "name": ["Frankfurt Airport"],
                "country": ["DE"],
                "region": ["HE"],
                "latitude": [50.0264],
                "longitude": [8.5431],
                "elevation": [112],
                "timezone": ["Europe/Berlin"],
            },
            index=pd.Index(["10637"], name="id"),
        )

    def test_station_list_no_args(self, invoke):
        """Station command with no station_id lists all stations."""
        with patch("meteostat.stations") as ms:
            ms.query.return_value = self._mock_df()
            result = invoke("station")
            assert result.exit_code == 0
            assert "Frankfurt" in result.output

    def test_station_filter_country(self, invoke):
        """Station --country filter passes correctly."""
        with patch("meteostat.stations") as ms:
            ms.query.return_value = self._mock_df()
            result = invoke("station", "--country", "DE")
            assert result.exit_code == 0
            assert ms.query.called

    def test_station_filter_name(self, invoke):
        """Station --name filter passes correctly."""
        with patch("meteostat.stations") as ms:
            ms.query.return_value = self._mock_df()
            result = invoke("station", "--name", "Frankfurt")
            assert result.exit_code == 0

    def test_station_sql(self, invoke):
        """Station --sql passes raw SQL to query."""
        with patch("meteostat.stations") as ms:
            ms.query.return_value = self._mock_df()
            result = invoke("station", "--sql", "SELECT * FROM stations LIMIT 1")
            assert result.exit_code == 0

    def test_station_no_results(self, invoke):
        """Station with no results exits with code 1."""
        with patch("meteostat.stations") as ms:
            ms.query.return_value = pd.DataFrame()
            result = invoke("station", "--country", "ZZ")
            assert result.exit_code == 1


class TestNearbyEdgeCases:
    """Test nearby command edge cases."""

    def test_nearby_no_results(self, invoke):
        """Nearby command exits 1 when no stations found."""
        with patch("meteostat.stations") as ms, patch("meteostat.Point"):
            ms.nearby.return_value = pd.DataFrame()
            result = invoke("nearby", "50.1109", "8.6821")
            assert result.exit_code == 1
            assert "No data" in result.output

    def test_nearby_csv_format(self, invoke):
        """Nearby command outputs CSV with --format csv."""
        df = pd.DataFrame(
            {"name": ["Frankfurt Airport"], "distance": [1234.5]},
            index=pd.Index(["10637"], name="id"),
        )
        with patch("meteostat.stations") as ms, patch("meteostat.Point"):
            ms.nearby.return_value = df
            result = invoke("nearby", "50.1109", "8.6821", "--format", "csv")
            assert result.exit_code == 0
            assert "name" in result.output

    def test_nearby_invalid_latitude(self, invoke):
        """Nearby command exits 2 when latitude is out of range."""
        result = invoke("nearby", "200", "8.6821")
        assert result.exit_code == 2
        assert "Latitude" in result.output

    def test_nearby_invalid_longitude(self, invoke):
        """Nearby command exits 2 when longitude is out of range."""
        result = invoke("nearby", "50.1109", "200")
        assert result.exit_code == 2
        assert "Longitude" in result.output


class TestInvalidParameters:
    """Test commands with invalid --parameters and --providers."""

    def test_daily_invalid_parameter(self, invoke):
        """Invalid --parameters exits with code 2 and an error message."""
        result = invoke(
            "daily",
            "10637",
            "-s",
            "2020-01-01",
            "-e",
            "2020-01-02",
            "--parameters",
            "NOT_A_PARAM",
        )
        assert result.exit_code == 2
        assert "Unknown parameter" in result.output

    def test_daily_invalid_provider(self, invoke):
        """Invalid --providers exits with code 2 and an error message."""
        result = invoke(
            "daily",
            "10637",
            "-s",
            "2020-01-01",
            "-e",
            "2020-01-02",
            "--providers",
            "NOT_A_PROVIDER",
        )
        assert result.exit_code == 2
        assert "Unknown provider" in result.output

    def test_hourly_invalid_parameter(self, invoke):
        """Hourly invalid --parameters exits with code 2."""
        result = invoke(
            "hourly",
            "10637",
            "-s",
            "2020-01-01",
            "-e",
            "2020-01-02",
            "--parameters",
            "BADPARAM",
        )
        assert result.exit_code == 2

    def test_monthly_invalid_parameter(self, invoke):
        """Monthly invalid --parameters exits with code 2."""
        result = invoke(
            "monthly",
            "10637",
            "-s",
            "2020-01",
            "-e",
            "2020-12",
            "--parameters",
            "NOT_A_PARAM",
        )
        assert result.exit_code == 2
        assert "Unknown parameter" in result.output

    def test_monthly_invalid_provider(self, invoke):
        """Monthly invalid --providers exits with code 2."""
        result = invoke(
            "monthly",
            "10637",
            "-s",
            "2020-01",
            "-e",
            "2020-12",
            "--providers",
            "NOT_A_PROVIDER",
        )
        assert result.exit_code == 2
        assert "Unknown provider" in result.output

    def test_normals_invalid_parameter(self, invoke):
        """Normals invalid --parameters exits with code 2."""
        result = invoke(
            "normals",
            "10637",
            "-s",
            "1991",
            "-e",
            "2020",
            "--parameters",
            "NOT_A_PARAM",
        )
        assert result.exit_code == 2
        assert "Unknown parameter" in result.output

    def test_normals_invalid_provider(self, invoke):
        """Normals invalid --providers exits with code 2."""
        result = invoke(
            "normals",
            "10637",
            "-s",
            "1991",
            "-e",
            "2020",
            "--providers",
            "NOT_A_PROVIDER",
        )
        assert result.exit_code == 2
        assert "Unknown provider" in result.output


class TestDateRangeValidation:
    """Test that start > end is rejected with a clear error."""

    def test_daily_start_after_end(self, invoke):
        """Daily command exits non-zero when start is after end."""
        result = invoke("daily", "10637", "-s", "2020-12-31", "-e", "2020-01-01")
        assert result.exit_code != 0
        assert "Start date" in result.output or "start" in result.output.lower()

    def test_hourly_start_after_end(self, invoke):
        """Hourly command exits non-zero when start is after end."""
        result = invoke("hourly", "10637", "-s", "2020-12-31", "-e", "2020-01-01")
        assert result.exit_code != 0

    def test_monthly_start_after_end(self, invoke):
        """Monthly command exits non-zero when start is after end."""
        result = invoke("monthly", "10637", "-s", "2020-12", "-e", "2020-01")
        assert result.exit_code != 0

    def test_normals_start_after_end(self, invoke):
        """Normals command exits non-zero when start year is after end year."""
        result = invoke("normals", "10637", "-s", "2020", "-e", "1991")
        assert result.exit_code != 0
        assert "Start year" in result.output or "start" in result.output.lower()


class TestInventoryEdgeCases:
    """Test inventory command edge cases."""

    def test_inventory_invalid_granularity(self, invoke):
        """Inventory with unknown --granularity exits with code 2."""
        import pandas as pd

        class MockInventory:
            df = pd.DataFrame(
                {
                    "station": ["10637"],
                    "provider": ["dwd_daily"],
                    "parameter": ["tavg"],
                    "start": ["2020-01-01"],
                    "end": ["2020-12-31"],
                }
            )

        with patch("meteostat.stations") as ms:
            ms.inventory.return_value = MockInventory()
            result = invoke("inventory", "10637", "--granularity", "weekly")
            assert result.exit_code == 2
            assert "Unknown granularity" in result.output

    def test_inventory_invalid_parameter(self, invoke):
        """Inventory with invalid --parameters exits with code 2."""
        import pandas as pd

        class MockInventory:
            df = pd.DataFrame(
                {
                    "station": ["10637"],
                    "provider": ["dwd_daily"],
                    "parameter": ["tavg"],
                    "start": ["2020-01-01"],
                    "end": ["2020-12-31"],
                }
            )

        with patch("meteostat.stations") as ms:
            ms.inventory.return_value = MockInventory()
            result = invoke("inventory", "10637", "--parameters", "BADPARAM")
            assert result.exit_code == 2


class TestAggParameter:
    """Test the --agg aggregation parameter."""

    def test_agg_valid(self, invoke):
        """--agg with a valid function aggregates rows."""
        df = pd.DataFrame(
            {"tavg": [10.0, 12.0], "tmin": [5.0, 6.0]},
            index=pd.DatetimeIndex(["2020-01-01", "2020-01-02"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--agg",
                "mean",
            )
            assert result.exit_code == 0
            # mean of [10.0, 12.0] = 11.0
            assert "11.0" in result.output

    def test_agg_single_station_includes_station_id(self, invoke):
        """--agg on a single station always shows the station ID in output."""
        df = pd.DataFrame(
            {"tavg": [10.0, 12.0]},
            index=pd.MultiIndex.from_tuples(
                [
                    ("10637", pd.Timestamp("2020-01-01")),
                    ("10637", pd.Timestamp("2020-01-02")),
                ],
                names=["station", "time"],
            ),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--agg",
                "max",
            )
            assert result.exit_code == 0
            assert "10637" in result.output

    def test_agg_multiple_stations_includes_station_id(self, invoke):
        """--agg on multiple stations groups by station and shows all station IDs."""
        df = pd.DataFrame(
            {"tavg": [10.0, 12.0, 8.0, 9.0]},
            index=pd.MultiIndex.from_tuples(
                [
                    ("10637", pd.Timestamp("2020-01-01")),
                    ("10637", pd.Timestamp("2020-01-02")),
                    ("10635", pd.Timestamp("2020-01-01")),
                    ("10635", pd.Timestamp("2020-01-02")),
                ],
                names=["station", "time"],
            ),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "10635",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--agg",
                "max",
            )
            assert result.exit_code == 0
            assert "10637" in result.output
            assert "10635" in result.output

    def test_agg_invalid_exits_nonzero(self, invoke):
        """--agg with an invalid function exits with a non-zero code."""
        df = pd.DataFrame(
            {"tavg": [10.0]},
            index=pd.DatetimeIndex(["2020-01-01"], name="time"),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.daily", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "daily",
                "10637",
                "-s",
                "2020-01-01",
                "-e",
                "2020-01-02",
                "--agg",
                "not_a_real_function",
            )
            assert result.exit_code != 0


class TestMultipleStations:
    """Test passing multiple station IDs to time-series commands."""

    def test_hourly_two_station_ids(self, invoke):
        """Two numeric station IDs are treated as station IDs, not coordinates."""
        df = pd.DataFrame(
            {"temp": [5.0, 6.0]},
            index=pd.MultiIndex.from_tuples(
                [
                    ("10637", pd.Timestamp("2020-01-01 00:00")),
                    ("10635", pd.Timestamp("2020-01-01 00:00")),
                ],
                names=["station", "time"],
            ),
        )
        mock_ts = MockTimeSeries(df)

        with patch("meteostat.hourly", return_value=mock_ts), patch("meteostat.config"):
            result = invoke(
                "hourly", "10637", "10635", "-s", "2020-01-01", "-e", "2020-01-02"
            )
            assert result.exit_code == 0
            assert "temp" in result.output
