"""Validate stations command for the Meteostat CLI."""

import typer

from meteo.commands.contrib import REPO_HELP, echo_report, plural
from meteo.contrib.repo import (
    changed_station_ids,
    load_stations,
    resolve_repo,
    station_files,
    station_path,
)
from meteo.contrib.validation import Report, Validator, load_schema, read_and_fix


def validate_cmd(
    station_ids: list[str] | None = typer.Argument(
        None, help="Station IDs to validate. Validates all stations if omitted."
    ),
    changed: bool = typer.Option(
        False,
        "--changed",
        help="Only validate stations changed compared to main (requires Git).",
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Automatically fix issues where possible."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only print stations with errors or warnings."
    ),
    repo: str | None = typer.Option(None, "--repo", help=REPO_HELP),
) -> None:
    """Check station records for errors."""
    repo_path = resolve_repo(repo)

    if station_ids or changed:
        ids = {station_id.upper() for station_id in station_ids or []}
        if changed:
            ids.update(changed_station_ids(repo_path))
        if not ids:
            typer.echo("No changed stations.")
            return
        paths = [station_path(repo_path, station_id) for station_id in sorted(ids)]
    else:
        paths = list(station_files(repo_path))

    fixed = 0
    if fix:
        schema = load_schema()
        fixed = sum(read_and_fix(path, schema) for path in paths if path.is_file())

    validator = Validator(load_stations(repo_path))

    invalid = errors = warnings = 0
    for path in paths:
        if path.is_file():
            report = validator.validate_file(path)
        else:
            report = Report(path.stem, errors=["Station not found"])
        echo_report(report, quiet)
        invalid += not report.valid
        errors += len(report.errors)
        warnings += len(report.warnings)

    typer.echo()
    if fix:
        typer.echo(f"Fixed {plural(fixed, 'station')}")
    details = ", ".join(
        plural(count, word)
        for count, word in ((errors, "error"), (warnings, "warning"))
        if count
    )
    details = f" ({details})" if details else ""
    if invalid:
        typer.echo(f"{invalid} of {plural(len(paths), 'station')} invalid{details}")
        raise typer.Exit(1)
    prefix = "All " if len(paths) > 1 else ""
    typer.echo(f"{prefix}{plural(len(paths), 'station')} valid{details}")
