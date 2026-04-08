"""Nearby stations command for the Meteostat CLI."""

import typer

from meteo.utils import detect_format, output_df


def nearby_cmd(
    coords: str = typer.Argument(..., help="Coordinates as lat,lon (e.g. 48.1,11.6)."),
    limit: int = typer.Option(5, "--limit", "-l", help="Maximum number of stations."),
    radius: int | None = typer.Option(None, "--radius", "-r", help="Search radius in meters."),
    fmt: str | None = typer.Option(
        None, "--format", "-f", help="Output format (csv, json, xlsx, parquet)."
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path."),
    no_header: bool = typer.Option(
        False, "--no-header", help="Omit header row from CSV output."
    ),
    show_all: bool = typer.Option(
        False, "--all", "-A", help="Print full table instead of truncated display."
    ),
) -> None:
    """Find weather stations near a location."""
    import meteostat as ms

    parts = coords.split(",", 1)
    if len(parts) != 2:
        typer.echo("Error: Coordinates must be in lat,lon format (e.g. 48.1,11.6).", err=True)
        raise typer.Exit(2)
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        typer.echo(f"Error: Invalid coordinates: {coords}", err=True)
        raise typer.Exit(2) from None
    if not (-90 <= lat <= 90):
        raise typer.BadParameter(f"Latitude must be between -90 and 90, got {lat}")
    if not (-180 <= lon <= 180):
        raise typer.BadParameter(f"Longitude must be between -180 and 180, got {lon}")

    point = ms.Point(lat, lon)
    df = ms.stations.nearby(point, radius=radius or 40_075_000, limit=limit)

    actual_fmt = detect_format(fmt, output)
    output_df(df, actual_fmt, output, no_header, show_all=show_all)
