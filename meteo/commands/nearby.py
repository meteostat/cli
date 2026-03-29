"""Nearby stations command for the Meteostat CLI."""

import typer

from meteo.utils import detect_format, output_df


def nearby_cmd(
    lat: float = typer.Argument(..., help="Latitude."),
    lon: float = typer.Argument(..., help="Longitude."),
    limit: int = typer.Option(5, "--limit", "-l", help="Maximum number of stations."),
    radius: int = typer.Option(5000, "--radius", "-r", help="Search radius in meters."),
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

    if not (-90 <= lat <= 90):
        typer.echo(f"Error: Latitude must be between -90 and 90, got {lat}.", err=True)
        raise typer.Exit(2)
    if not (-180 <= lon <= 180):
        typer.echo(
            f"Error: Longitude must be between -180 and 180, got {lon}.", err=True
        )
        raise typer.Exit(2)

    point = ms.Point(lat, lon)
    df = ms.stations.nearby(point, radius=radius, limit=limit)

    actual_fmt = detect_format(fmt, output)
    output_df(df, actual_fmt, output, no_header, show_all=show_all)
