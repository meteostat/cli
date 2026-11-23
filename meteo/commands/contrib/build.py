"""Build station database command for the Meteostat CLI."""

from enum import StrEnum
from pathlib import Path

import typer

from meteo.commands.contrib import REPO_HELP, echo_report, plural
from meteo.contrib.database import build_database, build_parquet
from meteo.contrib.repo import load_stations, resolve_repo, station_files
from meteo.contrib.validation import Validator


class Format(StrEnum):
    sqlite = "sqlite"
    parquet = "parquet"


BUILDERS = {Format.sqlite: build_database, Format.parquet: build_parquet}
DEFAULT_FILES = {Format.sqlite: "stations.db", Format.parquet: "stations.parquet"}


def build_cmd(
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stations.db or stations.parquet in the repository root).",
    ),
    fmt: Format = typer.Option(
        Format.sqlite, "--format", "-f", help="Output format.", case_sensitive=False
    ),
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="Don't validate stations before building."
    ),
    repo: str | None = typer.Option(None, "--repo", help=REPO_HELP),
) -> None:
    """Build a SQLite database or Parquet file from the station files."""
    repo_path = resolve_repo(repo)
    output_path = (
        Path(output).expanduser() if output else repo_path / DEFAULT_FILES[fmt]
    )
    stations = load_stations(repo_path)

    skipped = 0
    if not skip_validation:
        validator = Validator(stations)
        for path in station_files(repo_path):
            report = validator.validate_file(path)
            if not report.valid:
                echo_report(report, quiet=True)
                stations.pop(path.stem, None)
                skipped += 1

    count, failed = BUILDERS[fmt](stations, output_path)
    for station_id, reason in failed:
        typer.echo(f"{typer.style('✗', fg='red')} {station_id}  {reason}")

    skipped += len(failed)
    summary = f"Built {output_path} with {plural(count, 'station')}"
    if skipped:
        summary += f" ({skipped} skipped)"
    typer.echo(summary)
