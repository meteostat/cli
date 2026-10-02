"""Add station command for the Meteostat CLI."""

import re
from typing import Any

import typer

from meteo.commands.contrib import REPO_HELP, echo_report
from meteo.contrib.duplicates import find_duplicates
from meteo.contrib.repo import (
    generate_id,
    load_stations,
    resolve_repo,
    serialize,
    station_path,
    write_station,
)
from meteo.contrib.validation import Validator

LOCALIZED_NAME = re.compile(r"^([a-z]{2})=(.+)$")


def parse_names(values: list[str]) -> dict[str, str]:
    """Parse --name values. `LANG=NAME` sets a localized name, anything else English."""
    names = {}
    for value in values:
        match = LOCALIZED_NAME.match(value)
        lang, name = match.groups() if match else ("en", value)
        names[lang] = name.strip()
    return names


def parse_identifiers(values: list[str]) -> dict[str, str]:
    """Parse KEY=VALUE identifiers."""
    identifiers = {}
    for value in values:
        key, sep, ident = value.partition("=")
        if not sep or not key.strip() or not ident.strip():
            raise typer.BadParameter(
                f"Identifiers must be KEY=VALUE, got '{value}'.", param_hint="--id"
            )
        identifiers[key.strip().lower()] = ident.strip()
    return identifiers


def add_cmd(
    name: list[str] | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Station name. Use LANG=NAME for a localized name (repeatable).",
    ),
    country: str | None = typer.Option(
        None, "--country", "-c", help="ISO 3166-1 alpha-2 country code."
    ),
    region: str | None = typer.Option(
        None, "--region", help="ISO 3166-2 state or region code."
    ),
    lat: float | None = typer.Option(None, "--lat", help="Latitude."),
    lon: float | None = typer.Option(None, "--lon", help="Longitude."),
    elevation: int | None = typer.Option(
        None, "--elevation", "-e", help="Elevation in meters."
    ),
    timezone: str | None = typer.Option(
        None, "--timezone", "-t", help="IANA time zone (e.g. Europe/Berlin)."
    ),
    identifier: list[str] | None = typer.Option(
        None,
        "--id",
        "-i",
        help="Station identifier as KEY=VALUE, e.g. wmo=10637 (repeatable).",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Don't prompt. Fail on missing properties and skip duplicate confirmation.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the resulting JSON without writing any file."
    ),
    repo: str | None = typer.Option(None, "--repo", help=REPO_HELP),
) -> None:
    """Add a new weather station."""
    repo_path = resolve_repo(repo)

    names = parse_names(name or [])
    identifiers = parse_identifiers(identifier or [])

    if yes:
        missing = [
            option
            for option, value in (
                ("--name", names.get("en")),
                ("--country", country),
                ("--lat", lat),
                ("--lon", lon),
                ("--elevation", elevation),
                ("--timezone", timezone),
            )
            if value is None
        ]
        if missing:
            typer.echo(f"Error: Missing option(s): {', '.join(missing)}", err=True)
            raise typer.Exit(2)
    else:
        if "en" not in names:
            names["en"] = typer.prompt("Name (English)").strip()
        if country is None:
            country = typer.prompt("Country (ISO 3166-1 alpha-2)")
        if region is None:
            region = typer.prompt(
                "Region (ISO 3166-2, optional)", default="", show_default=False
            )
        if lat is None:
            lat = typer.prompt("Latitude", type=float)
        if lon is None:
            lon = typer.prompt("Longitude", type=float)
        if elevation is None:
            elevation = typer.prompt("Elevation (m)", type=int)
        if timezone is None:
            timezone = typer.prompt("Time zone (e.g. Europe/Berlin)")
        if not identifier:
            value = typer.prompt(
                "Identifiers (KEY=VALUE, comma-separated, optional)",
                default="",
                show_default=False,
            )
            identifiers = parse_identifiers(
                [item for item in value.split(",") if item.strip()]
            )

    station_id = generate_id(repo_path)
    data: dict[str, Any] = {
        "id": station_id,
        "name": dict(sorted(names.items())),
        "country": (country or "").strip().upper(),
        "region": region.strip().upper() if region and region.strip() else None,
        "identifiers": identifiers,
        "location": {"latitude": lat, "longitude": lon, "elevation": elevation},
        "timezone": (timezone or "").strip(),
    }

    stations = load_stations(repo_path)
    report = Validator(stations).validate(station_id, data)
    if not report.valid:
        echo_report(report)
        raise typer.Exit(1)

    stations[station_id] = data
    duplicates = find_duplicates(stations, ids={station_id})
    if duplicates:
        typer.echo("Potential duplicates:", err=True)
        for dup in duplicates:
            other = dup.station_b if dup.station_a == station_id else dup.station_a
            other_name = stations[other].get("name", {}).get("en", "")
            dist = f"{dup.distance} m, " if dup.distance is not None else ""
            typer.echo(
                f"  {other}  {other_name} ({dist}{', '.join(dup.reasons)})",
                err=True,
            )
        if not yes and not dry_run:
            typer.confirm("Create station anyway?", abort=True, err=True)

    if dry_run:
        typer.echo(serialize(data))
        return

    path = station_path(repo_path, station_id)
    write_station(path, data)
    typer.echo(f"Created station {station_id} ({path.relative_to(repo_path)})")
