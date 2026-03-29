"""Daily time series command for the Meteostat CLI."""

from typing import Annotated

import typer

from meteo.utils import fetch_timeseries


def _daily(
    stations: Annotated[
        list[str],
        typer.Argument(
            help="Station ID(s), or coordinates as lat,lon (e.g. 48.1,11.6)."
        ),
    ],
    start: str | None = typer.Option(
        None, "--start", "-s", help="Start date (YYYY-MM-DD, YYYY-MM, or YYYY)."
    ),
    end: str | None = typer.Option(None, "--end", "-e", help="End date."),
    parameters: str | None = typer.Option(
        None, "--parameters", "-p", help="Comma-separated list of parameters."
    ),
    providers: str | None = typer.Option(
        None, "--providers", "-P", help="Comma-separated list of providers."
    ),
    no_models: bool = typer.Option(False, "--no-models", help="Exclude model data."),
    with_sources: bool = typer.Option(
        False, "--with-sources", "-S", help="Include data source information."
    ),
    fmt: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Output format (csv, json, xlsx, parquet, png, svg).",
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path."),
    no_header: bool = typer.Option(
        False, "--no-header", help="Omit header row from CSV output."
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable caching."),
    show_all: bool = typer.Option(
        False, "--all", "-A", help="Print full table instead of truncated display."
    ),
    agg: str | None = typer.Option(
        None,
        "--agg",
        help="Aggregation function to apply via pandas .agg() (e.g. mean, sum, min, max).",
    ),
) -> None:
    """Fetch daily weather data."""
    fetch_timeseries(
        granularity="daily",
        stations=stations,
        start=start,
        end=end,
        parameters=parameters,
        providers=providers,
        no_models=no_models,
        with_sources=with_sources,
        no_cache=no_cache,
        fmt=fmt,
        output=output,
        no_header=no_header,
        show_all=show_all,
        agg=agg,
    )


# Expose for registration in cli.py
daily_cmd = _daily
daily_cmd_alias = _daily
