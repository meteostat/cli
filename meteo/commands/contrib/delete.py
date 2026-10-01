"""Delete station command for the Meteostat CLI."""

import typer

from meteo.commands.contrib import REPO_HELP, print_station
from meteo.contrib.repo import read_station, require_station, resolve_repo


def delete_cmd(
    station_id: str = typer.Argument(..., help="Meteostat station ID."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the confirmation prompt."
    ),
    repo: str | None = typer.Option(None, "--repo", help=REPO_HELP),
) -> None:
    """Remove a weather station."""
    repo_path = resolve_repo(repo)
    path = require_station(repo_path, station_id)

    if not yes:
        try:
            print_station(read_station(path))
        except ValueError:
            typer.echo(f"Warning: {path.name} contains invalid JSON.", err=True)
        typer.confirm(f"Delete station {path.stem}?", abort=True)

    path.unlink()
    typer.echo(f"Deleted station {path.stem} ({path.relative_to(repo_path)})")
