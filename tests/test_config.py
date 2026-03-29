"""Tests for the config command and config utilities."""

from unittest.mock import patch

import pytest

from meteo.config import (
    coerce_value,
    format_value,
    load_config,
    save_config,
)


class TestCoerceValue:
    """Test type coercion for config values."""

    def test_bool_true(self):
        assert coerce_value("cache_enable", "true") is True

    def test_bool_false(self):
        assert coerce_value("cache_enable", "false") is False

    def test_bool_yes(self):
        assert coerce_value("cache_enable", "yes") is True

    def test_bool_no(self):
        assert coerce_value("cache_enable", "no") is False

    def test_bool_invalid(self):
        with pytest.raises(ValueError):
            coerce_value("cache_enable", "maybe")

    def test_cli_specific_int(self):
        result = coerce_value("interpolation_radius", "50000")
        assert result == 50000
        assert isinstance(result, int)

    def test_cli_specific_bool_false(self):
        """CLI bool keys (e.g. humanize) must coerce 'false' to False, not True."""
        result = coerce_value("humanize", "false")
        assert result is False

    def test_cli_specific_bool_true(self):
        result = coerce_value("humanize", "true")
        assert result is True


class TestFormatValue:
    """Test value formatting for display."""

    def test_bool_true(self):
        assert format_value(True) == "true"

    def test_bool_false(self):
        assert format_value(False) == "false"

    def test_none(self):
        assert format_value(None) == "null"

    def test_list(self):
        assert format_value([1, 2]) == "[1, 2]"

    def test_dict(self):
        result = format_value({"a": 1})
        assert '"a"' in result

    def test_int(self):
        assert format_value(42) == "42"

    def test_string(self):
        assert format_value("hello") == "hello"


class TestConfigPersistence:
    """Test config file load/save."""

    def test_load_empty(self, tmp_path):
        """Loading from non-existent path returns empty dict."""
        with patch("meteo.config._get_config_path", return_value=tmp_path / "cli.yml"):
            assert load_config() == {}

    def test_save_and_load(self, tmp_path):
        """Config round-trips through save/load."""
        cfg_path = tmp_path / "meteostat" / "cli.yml"
        with patch("meteo.config._get_config_path", return_value=cfg_path):
            save_config({"cache_enable": False, "cache_dir": "/tmp/test"})
            loaded = load_config()
            assert loaded["cache_enable"] is False
            assert loaded["cache_dir"] == "/tmp/test"

    def test_load_corrupted_yaml_returns_empty(self, tmp_path):
        """Corrupted config YAML returns empty dict with a warning, not a crash."""
        cfg_path = tmp_path / "cli.yml"
        cfg_path.write_text(": invalid: yaml: :: :\n")
        with patch("meteo.config._get_config_path", return_value=cfg_path):
            result = load_config()
            assert result == {}

    def test_load_non_dict_yaml_returns_empty(self, tmp_path):
        """Config file containing a non-dict YAML value returns empty dict."""
        cfg_path = tmp_path / "cli.yml"
        cfg_path.write_text("- item1\n- item2\n")
        with patch("meteo.config._get_config_path", return_value=cfg_path):
            result = load_config()
            assert result == {}


class TestConfigCommand:
    """Test the 'meteo config' CLI command."""

    def test_config_no_args(self, invoke):
        """Config with no args and no --list shows error."""
        result = invoke("config")
        assert result.exit_code == 2

    def test_config_list(self, invoke):
        """Config --list shows all keys."""
        result = invoke("config", "--list")
        assert result.exit_code == 0
        # Should show at least some known config keys
        assert "=" in result.output

    def test_config_unknown_key(self, invoke):
        """Config get for unknown key shows error."""
        result = invoke("config", "nonexistent_key")
        assert result.exit_code == 2
        assert "Unknown" in result.output

    def test_config_set_unknown_key(self, invoke):
        """Config set for unknown key shows error."""
        result = invoke("config", "nonexistent_key", "value")
        assert result.exit_code == 2

    def test_config_get_known_key(self, invoke):
        """Config get for known key shows value."""
        result = invoke("config", "cache_enable")
        assert result.exit_code == 0

    def test_config_set_and_get(self, invoke, tmp_path):
        """Config set persists and can be retrieved."""
        cfg_path = tmp_path / "meteostat" / "cli.yml"
        with patch("meteo.config._get_config_path", return_value=cfg_path):
            result = invoke("config", "cache_enable", "false")
            assert result.exit_code == 0
            assert "false" in result.output
