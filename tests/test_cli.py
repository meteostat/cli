"""Tests for the CLI entry point and global options."""

from meteo import __version__


def test_help(invoke):
    """Test that --help exits successfully and shows usage."""
    result = invoke("--help")
    assert result.exit_code == 0
    assert "Access weather and climate data" in result.output


def test_version(invoke):
    """Test that --version shows the version string."""
    result = invoke("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_args_shows_help(invoke):
    """Test that running with no args shows usage info."""
    result = invoke()
    assert result.exit_code == 0 or result.exit_code == 2
    assert "Usage" in result.output or "Commands" in result.output


def test_unknown_command(invoke):
    """Test that unknown commands exit with error."""
    result = invoke("nonexistent")
    assert result.exit_code != 0


def test_command_help_station(invoke):
    """Test that 'station --help' works."""
    result = invoke("station", "--help")
    assert result.exit_code == 0
    assert "Station ID" in result.output or "station" in result.output.lower()


def test_command_help_hourly(invoke):
    """Test that 'hourly --help' works."""
    result = invoke("hourly", "--help")
    assert result.exit_code == 0


def test_command_help_daily(invoke):
    """Test that 'daily --help' works."""
    result = invoke("daily", "--help")
    assert result.exit_code == 0


def test_command_help_monthly(invoke):
    """Test that 'monthly --help' works."""
    result = invoke("monthly", "--help")
    assert result.exit_code == 0


def test_command_help_normals(invoke):
    """Test that 'normals --help' works."""
    result = invoke("normals", "--help")
    assert result.exit_code == 0


def test_command_help_config(invoke):
    """Test that 'config --help' works."""
    result = invoke("config", "--help")
    assert result.exit_code == 0


def test_command_help_stations(invoke):
    """Test that 'stations --help' works."""
    result = invoke("stations", "--help")
    assert result.exit_code == 0


def test_command_help_nearby(invoke):
    """Test that 'nearby --help' works."""
    result = invoke("nearby", "--help")
    assert result.exit_code == 0


def test_command_help_inventory(invoke):
    """Test that 'inventory --help' works."""
    result = invoke("inventory", "--help")
    assert result.exit_code == 0


def test_alias_h(invoke):
    """Test that alias 'h' resolves to hourly."""
    result = invoke("h", "--help")
    assert result.exit_code == 0


def test_alias_d(invoke):
    """Test that alias 'd' resolves to daily."""
    result = invoke("d", "--help")
    assert result.exit_code == 0


def test_alias_m(invoke):
    """Test that alias 'm' resolves to monthly."""
    result = invoke("m", "--help")
    assert result.exit_code == 0


def test_alias_n(invoke):
    """Test that alias 'n' resolves to normals."""
    result = invoke("n", "--help")
    assert result.exit_code == 0


def test_alias_s(invoke):
    """Test that alias 's' resolves to station."""
    result = invoke("s", "--help")
    assert result.exit_code == 0


def test_alias_i(invoke):
    """Test that alias 'i' resolves to inventory."""
    result = invoke("i", "--help")
    assert result.exit_code == 0
