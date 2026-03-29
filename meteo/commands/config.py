"""Configuration command for the Meteostat CLI."""

import typer

from meteo.config import (
    CLI_CONFIG_KEYS,
    coerce_value,
    format_value,
    get_meteostat_config_keys,
    load_config,
    save_config,
)


def config_cmd(
    key: str | None = typer.Argument(None, help="Configuration key (dot notation)."),
    value: str | None = typer.Argument(None, help="Value to set."),
    list_all: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all configuration values.",
    ),
) -> None:
    """Get or set Meteostat configuration values."""
    if list_all:
        _list_config()
        return

    if key is None:
        typer.echo("Error: Provide a config key, or use --list.", err=True)
        raise typer.Exit(2)

    if value is None:
        # Get mode
        _get_config(key)
    else:
        # Set mode
        _set_config(key, value)


def _list_config() -> None:
    """List all configuration keys with their current values."""
    import meteostat as ms

    ms_keys = get_meteostat_config_keys()
    saved = load_config()

    # Meteostat library keys
    for attr, default in sorted(ms_keys.items()):
        current = saved.get(attr, getattr(ms.config, attr, default))
        typer.echo(f"{attr} = {format_value(current)}")

    # CLI-specific keys
    for attr, default in sorted(CLI_CONFIG_KEYS.items()):
        current = saved.get(attr, default)
        typer.echo(f"{attr} = {format_value(current)}")


def _get_config(key: str) -> None:
    """Get and display a single config value."""
    import meteostat as ms

    saved = load_config()
    ms_keys = get_meteostat_config_keys()

    if key in saved:
        typer.echo(format_value(saved[key]))
    elif key in ms_keys:
        typer.echo(format_value(getattr(ms.config, key, ms_keys[key])))
    elif key in CLI_CONFIG_KEYS:
        typer.echo(format_value(CLI_CONFIG_KEYS[key]))
    else:
        typer.echo(f"Error: Unknown config key '{key}'.", err=True)
        raise typer.Exit(2)


def _set_config(key: str, value: str) -> None:
    """Set a config value and persist it."""
    ms_keys = get_meteostat_config_keys()

    if key not in ms_keys and key not in CLI_CONFIG_KEYS:
        typer.echo(f"Error: Unknown config key '{key}'.", err=True)
        raise typer.Exit(2)

    try:
        coerced = coerce_value(key, value)
    except (ValueError, TypeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None

    data = load_config()
    data[key] = coerced
    save_config(data)
    typer.echo(f"{key} = {format_value(coerced)}")
