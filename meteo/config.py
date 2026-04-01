"""Configuration management for the Meteostat CLI.

Handles loading/saving CLI configuration from cli.yml, applying Meteostat
library config overrides, and type coercion between YAML and Python values.
"""

import json
from pathlib import Path
from typing import Any, get_args, get_origin

import typer
import yaml

# CLI-specific config keys (not part of Meteostat library config)
CLI_CONFIG_KEYS = {
    "interpolation_radius": 25000,
    "interpolation_station_count": 10,
    "humanize": True,
}


def _get_config_dir() -> Path:
    """Get the CLI config directory path."""
    return Path(typer.get_app_dir("meteostat"))


def _get_config_path() -> Path:
    """Get the CLI config file path."""
    return _get_config_dir() / "cli.yml"


def load_config() -> dict[str, Any]:
    """Load configuration from cli.yml."""
    path = _get_config_path()
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        typer.echo(
            f"Warning: Could not parse config file {path}: {exc}. Using defaults.",
            err=True,
        )
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict[str, Any]) -> None:
    """Save configuration to cli.yml."""
    path = _get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=True)


def get_meteostat_config_keys() -> dict[str, Any]:
    """Discover all Meteostat config options at runtime.

    Uses both __annotations__ and class-level attributes from the Config class
    to catch annotated AND unannotated attributes.
    """
    from meteostat.api.config import Config

    keys: dict[str, Any] = {}

    # Collect from class hierarchy annotations
    for cls in Config.__mro__:
        for attr_name, _ in getattr(cls, "__annotations__", {}).items():
            if not attr_name.startswith("_") and attr_name != "prefix":
                keys[attr_name] = getattr(Config, attr_name, None)

    # Also scan class-level attributes (catches unannotated ones)
    for attr_name in vars(Config):
        if attr_name.startswith("_") or attr_name == "prefix":
            continue
        val = getattr(Config, attr_name)
        if callable(val) and not isinstance(val, (list, dict)):
            continue
        if attr_name not in keys:
            keys[attr_name] = val

    return keys


def get_config_type(key: str) -> type | None:
    """Get the type annotation for a Meteostat config key."""
    from meteostat.api.config import Config

    for cls in Config.__mro__:
        annotations = getattr(cls, "__annotations__", {})
        if key in annotations:
            ann = annotations[key]
            origin = get_origin(ann)
            if origin is not None:
                # Handle Optional[X] -> extract X
                args = get_args(ann)
                if type(None) in args:
                    # Optional type - get the non-None type
                    non_none = [a for a in args if a is not type(None)]
                    if non_none:
                        return non_none[0]
                return origin
            return ann
    return None


def coerce_value(key: str, value: str) -> Any:
    """Coerce a string value to the appropriate Python type for a config key.

    Uses the Config class annotations to determine the target type.
    """
    if key in CLI_CONFIG_KEYS:
        # CLI-specific keys use their default type
        default = CLI_CONFIG_KEYS[key]
        target_type: type | None = type(default)
    else:
        target_type = get_config_type(key)

    if target_type is None:
        # No annotation found — try JSON parsing, fall back to string
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value

    if target_type is bool:
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"Cannot convert '{value}' to bool")

    if target_type is int:
        return int(value)

    if target_type is float:
        return float(value)

    if target_type is str:
        return value

    if target_type in (list, dict):
        return json.loads(value)

    # Fallback: try JSON, then string
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value


def format_value(value: Any) -> str:
    """Format a Python value for display."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    if value is None:
        return "null"
    return str(value)


def apply_config() -> None:
    """Load CLI config and apply Meteostat library config overrides.

    Called during app startup (before any command runs).
    """
    import meteostat as ms

    data = load_config()
    ms_keys = get_meteostat_config_keys()

    for key, value in data.items():
        if key in ms_keys:
            setattr(ms.config, key, value)
