"""Find duplicate stations command for the Meteostat CLI."""

import pandas as pd
import typer

from meteo.commands.contrib import REPO_HELP
from meteo.contrib.duplicates import find_duplicates
from meteo.contrib.repo import load_stations, resolve_repo
from meteo.utils import detect_format, output_df


def duplicates_cmd(
    station_ids: list[str] | None = typer.Option(
        None, "--id", help="Only report duplicates of the given station (repeatable)."
    ),
    country: str | None = typer.Option(
        None, "--country", "-c", help="Only check stations in the given country."
    ),
    radius: int = typer.Option(
        1000, "--radius", "-r", help="Maximum distance in meters for location matches."
    ),
    fmt: str | None = typer.Option(None, "--format", "-f", help="Output format."),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path."),
    no_header: bool = typer.Option(
        False, "--no-header", help="Omit header row from CSV output."
    ),
    show_all: bool = typer.Option(
        False, "--all", "-A", help="Print full table instead of truncated display."
    ),
    repo: str | None = typer.Option(None, "--repo", help=REPO_HELP),
) -> None:
    """Find potential duplicate stations."""
    repo_path = resolve_repo(repo)
    stations = load_stations(repo_path)

    if country:
        stations = {
            station_id: data
            for station_id, data in stations.items()
            if str(data.get("country", "")).upper() == country.upper()
        }

    ids = {station_id.upper() for station_id in station_ids} if station_ids else None
    duplicates = find_duplicates(stations, radius=radius, ids=ids)

    if not duplicates:
        typer.echo("No potential duplicates found.", err=True)
        return

    df = pd.DataFrame(
        [
            {
                "station_a": dup.station_a,
                "station_b": dup.station_b,
                "distance": dup.distance,
                "reasons": ", ".join(dup.reasons),
            }
            for dup in duplicates
        ]
    ).set_index(["station_a", "station_b"])

    actual_fmt = detect_format(fmt, output)
    output_df(df, actual_fmt, output, no_header, show_all=show_all)
    raise typer.Exit(1)
