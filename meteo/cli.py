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


STATION_EPILOG = (
    "Contributor commands: add, edit, delete, validate, duplicates, build. "
    "Run 'meteo station COMMAND --help' for details."
)


def _register_commands() -> None:
    """Register all command modules with the Typer app."""
    from meteo.commands.config import config_cmd
    from meteo.commands.contrib.add import add_cmd
    from meteo.commands.contrib.build import build_cmd
    from meteo.commands.contrib.delete import delete_cmd
    from meteo.commands.contrib.duplicates import duplicates_cmd
    from meteo.commands.contrib.edit import edit_cmd
    from meteo.commands.contrib.validate import validate_cmd
    from meteo.commands.daily import daily_cmd, daily_cmd_alias
    from meteo.commands.hourly import hourly_cmd, hourly_cmd_alias
    from meteo.commands.inventory import inventory_cmd, inventory_cmd_alias
    from meteo.commands.monthly import monthly_cmd, monthly_cmd_alias
    from meteo.commands.nearby import nearby_cmd
    from meteo.commands.normals import normals_cmd, normals_cmd_alias
    from meteo.commands.station import LookupCommand, StationGroup, station_cmd

    station_app = typer.Typer(cls=StationGroup)
    station_app.command(
        StationGroup.default_command,
        cls=LookupCommand,
        hidden=True,
        epilog=STATION_EPILOG,
    )(station_cmd)
    station_app.command("add")(add_cmd)
    station_app.command("edit")(edit_cmd)
    station_app.command("delete")(delete_cmd)
    station_app.command("validate")(validate_cmd)
    station_app.command("duplicates")(duplicates_cmd)
    station_app.command("build")(build_cmd)

    app.command("config")(config_cmd)
    app.add_typer(station_app, name="station", help=station_cmd.__doc__)
    app.add_typer(station_app, name="s", hidden=True)
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
