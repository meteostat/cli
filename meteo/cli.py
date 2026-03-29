"""Main CLI entry point for the Meteostat CLI."""

import typer

from meteo import __version__

app = typer.Typer(
    name="meteo",
    help="Access weather and climate data through the terminal.",
    no_args_is_help=True,
    add_completion=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"meteo {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Access weather and climate data through the terminal."""
    from meteo.config import apply_config

    apply_config()


def _register_commands() -> None:
    """Register all command modules with the Typer app."""
    from meteo.commands.config import config_cmd
    from meteo.commands.daily import daily_cmd, daily_cmd_alias
    from meteo.commands.hourly import hourly_cmd, hourly_cmd_alias
    from meteo.commands.inventory import inventory_cmd, inventory_cmd_alias
    from meteo.commands.monthly import monthly_cmd, monthly_cmd_alias
    from meteo.commands.nearby import nearby_cmd
    from meteo.commands.normals import normals_cmd, normals_cmd_alias
    from meteo.commands.station import station_cmd

    app.command("config")(config_cmd)
    app.command("station")(station_cmd)
    app.command("stations")(station_cmd)
    app.command("s", hidden=True)(station_cmd)
    app.command("nearby")(nearby_cmd)
    app.command("inventory")(inventory_cmd)
    app.command("i", hidden=True)(inventory_cmd_alias)
    app.command("hourly")(hourly_cmd)
    app.command("h", hidden=True)(hourly_cmd_alias)
    app.command("daily")(daily_cmd)
    app.command("d", hidden=True)(daily_cmd_alias)
    app.command("monthly")(monthly_cmd)
    app.command("m", hidden=True)(monthly_cmd_alias)
    app.command("normals")(normals_cmd)
    app.command("n", hidden=True)(normals_cmd_alias)


_register_commands()


def main() -> None:
    """Entry point for the CLI."""
    app()
