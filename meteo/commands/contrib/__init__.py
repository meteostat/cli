"""Contributor commands for the weather stations repository."""

from typing import Any

import typer

from meteo.contrib.validation import Report

REPO_HELP = "Path to the stations repository (overrides stations_repo)."


def echo_report(report: Report, quiet: bool = False) -> None:
    """Print the validation result of a station."""
    for error in report.errors:
        typer.echo(f"{typer.style('✗', fg='red')} {report.station_id}  {error}")
    for warning in report.warnings:
        typer.echo(f"{typer.style('!', fg='yellow')} {report.station_id}  {warning}")
    if report.valid and not report.warnings and not quiet:
        typer.echo(f"{typer.style('✓', fg='green')} {report.station_id}")


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def print_station(data: dict[str, Any]) -> None:
    """Print a station record in the same way as `meteo station ID`."""
    from meteo.commands.station import print_metadata

    location = data.get("location") or {}
    names = data.get("name") or {}
    print_metadata(
        {
            "id": data.get("id"),
            "name": names.get("en"),
            "country": data.get("country"),
            "region": data.get("region"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "elevation": location.get("elevation"),
            "timezone": data.get("timezone"),
            **(data.get("identifiers") or {}),
        }
    )
