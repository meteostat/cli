"""Shared utilities for the Meteostat CLI.

Provides date parsing, station/coordinate disambiguation, output formatting,
and common option patterns shared across time-series commands.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import typer

from meteo.config import CLI_CONFIG_KEYS, load_config

# Mapping of file extensions to format names
EXT_FORMAT_MAP = {
    ".csv": "csv",
    ".json": "json",
    ".xlsx": "xlsx",
    ".parquet": "parquet",
    ".png": "png",
    ".svg": "svg",
}


def parse_date(value: str | None, is_end: bool = False) -> date | datetime | None:
    """Parse a date string in various formats.

    Supports: YYYY-MM-DD, YYYY-MM, YYYY, YYYY-MM-DDTHH:MM:SSZ
    For YYYY-MM: if is_end, uses last day of month.
    For YYYY: if is_end, uses Dec 31.
    Returns a datetime when the input contains a time component (ISO 8601 with T).
    """
    if value is None:
        return None

    try:
        # ISO 8601 with time component
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        parts = value.split("-")

        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))

        if len(parts) == 2:
            year, month = int(parts[0]), int(parts[1])
            if is_end:
                # Last day of the month
                if month == 12:
                    return date(year, 12, 31)
                return date(year, month + 1, 1) - timedelta(days=1)
            return date(year, month, 1)

        if len(parts) == 1:
            year = int(parts[0])
            if is_end:
                return date(year, 12, 31)
            return date(year, 1, 1)

        raise typer.BadParameter(f"Invalid date format: {value}")
    except ValueError:
        # Normalize numeric/date parsing errors to a clean CLI error
        raise typer.BadParameter(f"Invalid date format: {value}") from None


def parse_datetime(value: str | None, is_end: bool = False) -> datetime | None:
    """Parse a date string and return a datetime object."""
    result = parse_date(value, is_end)
    if result is None:
        return None
    if isinstance(result, datetime):
        return result
    return datetime(result.year, result.month, result.day)


def resolve_station_or_point(
    *stations: str,
) -> (
    tuple[Literal["station"], str]
    | tuple[Literal["stations"], list[Any]]
    | tuple[Literal["point"], float, float]
):
    """Disambiguate station ID(s) vs lat/lon coordinates.

    Returns:
        ("station", id), ("stations", [id, ...]), or ("point", lat, lon)
    """
    if len(stations) == 1 and "," in stations[0]:
        parts = stations[0].split(",", 1)
        try:
            lat_f = float(parts[0])
            lon_f = float(parts[1])
        except ValueError:
            raise typer.BadParameter(f"Invalid coordinates: {stations[0]}") from None
        if not (-90 <= lat_f <= 90):
            raise typer.BadParameter(
                f"Latitude must be between -90 and 90, got {lat_f}"
            )
        if not (-180 <= lon_f <= 180):
            raise typer.BadParameter(
                f"Longitude must be between -180 and 180, got {lon_f}"
            )
        return ("point", lat_f, lon_f)

    if len(stations) == 1:
        return ("station", stations[0])

    return ("stations", list(stations))


def get_interpolation_radius() -> int:
    """Get the configured interpolation radius for coordinate-based queries."""
    data = load_config()
    key = "interpolation_radius"
    if key in data:
        return int(data[key])
    return CLI_CONFIG_KEYS["interpolation_radius"]


def get_interpolation_station_count() -> int:
    """Get the configured station count limit for coordinate-based queries."""
    data = load_config()
    key = "interpolation_station_count"
    if key in data:
        return int(data[key])
    return CLI_CONFIG_KEYS["interpolation_station_count"]


def detect_format(fmt: str | None, output: str | None) -> str:
    """Detect the output format from explicit flag or file extension."""
    if fmt is not None:
        return fmt

    if output is not None:
        ext = Path(output).suffix.lower()
        if ext in EXT_FORMAT_MAP:
            return EXT_FORMAT_MAP[ext]

    return "text"


def output_df(
    df: pd.DataFrame | None,
    fmt: str,
    output: str | None = None,
    no_header: bool = False,
    plot_params: dict | None = None,
    show_all: bool = False,
) -> None:
    """Output a DataFrame in the specified format.

    Handles CSV, JSON, XLSX, Parquet output, and PNG/SVG plotting.
    When fmt is "text" and show_all is False (default), uses Pandas'
    standard truncated display. Pass show_all=True (--all flag) to
    print the full table.
    """
    if df is None or df.empty:
        typer.echo("No data available.", err=True)
        raise typer.Exit(1)

    if fmt in ("png", "svg"):
        if output is None:
            typer.echo(
                f"Error: {fmt.upper()} format requires --output to specify a file path.",
                err=True,
            )
            raise typer.Exit(2)
        from meteo.plotting import plot_dataframe

        plot_dataframe(df, output, fmt, **(plot_params or {}))
        return

    if fmt == "text":
        if show_all:
            text = df.to_string(max_rows=None, max_cols=None)
        else:
            text = df.to_string(
                max_rows=pd.get_option("display.max_rows"),
                max_cols=pd.get_option("display.max_columns"),
            )
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(text + "\n")
        else:
            sys.stdout.write(text + "\n")

    elif fmt == "csv":
        text = df.reset_index().to_csv(index=False, header=not no_header)
        assert text is not None
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(text)
        else:
            sys.stdout.write(text)

    elif fmt == "json":
        text = df.reset_index().to_json(orient="records", indent=2, date_format="iso")
        assert text is not None
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(text)
        else:
            sys.stdout.write(text)
            sys.stdout.write("\n")

    elif fmt == "xlsx":
        if output is None:
            typer.echo(
                "Error: XLSX format requires --output to specify a file path.",
                err=True,
            )
            raise typer.Exit(2)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        try:
            df.reset_index().to_excel(output, index=False)
        except ImportError:
            typer.echo(
                "Error: openpyxl is required for XLSX output. "
                "Install with: pip install openpyxl",
                err=True,
            )
            raise typer.Exit(1) from None

    elif fmt == "parquet":
        if output is None:
            typer.echo(
                "Error: Parquet format requires --output to specify a file path.",
                err=True,
            )
            raise typer.Exit(2)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_parquet(output, index=True)
        except ImportError:
            typer.echo(
                "Error: pyarrow is required for Parquet output. "
                "Install with: pip install pyarrow",
                err=True,
            )
            raise typer.Exit(1) from None

    else:
        typer.echo(f"Error: Unknown format '{fmt}'.", err=True)
        raise typer.Exit(2)


def apply_no_cache() -> None:
    """Disable Meteostat cache for the current request."""
    import meteostat as ms

    ms.config.cache_enable = False


def apply_no_models() -> None:
    """Exclude model data for the current request."""
    import meteostat as ms

    ms.config.include_model_data = False


def parse_parameters(value: str | None) -> list | None:
    """Parse comma-separated parameter names into Parameter enums."""
    if value is None:
        return None
    from meteostat.enumerations import Parameter

    params = []
    for name in value.split(","):
        name = name.strip().upper()
        try:
            params.append(Parameter[name])
        except KeyError:
            # Try by value (lowercase)
            try:
                params.append(Parameter(name.lower()))
            except ValueError:
                typer.echo(
                    f"Error: Unknown parameter '{name}'.",
                    err=True,
                )
                raise typer.Exit(2) from None
    return params


def parse_providers(value: str | None) -> list | None:
    """Parse comma-separated provider names into Provider enums."""
    if value is None:
        return None
    from meteostat.enumerations import Provider

    providers = []
    for name in value.split(","):
        name = name.strip()
        try:
            providers.append(Provider[name.upper()])
        except KeyError:
            try:
                providers.append(Provider(name.lower()))
            except ValueError:
                typer.echo(
                    f"Error: Unknown provider '{name}'.",
                    err=True,
                )
                raise typer.Exit(2) from None
    return providers


def fetch_timeseries(
    granularity: str,
    stations: list[str],
    start: str | None = None,
    end: str | None = None,
    timezone: str | None = None,
    parameters: str | None = None,
    providers: str | None = None,
    no_models: bool = False,
    with_sources: bool = False,
    no_cache: bool = False,
    fmt: str | None = None,
    output: str | None = None,
    no_header: bool = False,
    show_all: bool = False,
    agg: str | None = None,
) -> None:
    """Shared logic for hourly/daily/monthly/normals time-series commands."""
    import meteostat as ms

    if no_cache:
        apply_no_cache()
    if no_models:
        apply_no_models()

    resolved = resolve_station_or_point(*stations)
    # Always pass station IDs as a list so the API returns a station-indexed
    # MultiIndex DataFrame, ensuring --agg always shows the station ID.
    if resolved[0] == "station":
        resolved: tuple[Literal["stations"], list[Any]] = ("stations", [resolved[1]])
    param_list = parse_parameters(parameters)
    provider_list = parse_providers(providers)

    # Build kwargs for the API call
    kwargs: dict = {}
    if param_list is not None:
        kwargs["parameters"] = param_list
    if provider_list is not None:
        kwargs["providers"] = provider_list

    # Select the API function and parse dates appropriately
    if granularity == "normals":
        try:
            start_val = int(start) if start else 1991
            end_val = int(end) if end else 2020
        except ValueError:
            raise typer.BadParameter(
                "Start and end for normals must be a 4-digit year (e.g. 1991)."
            ) from None
        if not (1000 <= start_val <= 9999) or not (1000 <= end_val <= 9999):
            raise typer.BadParameter(
                "Start and end for normals must be a 4-digit year (e.g. 1991)."
            )
        if start_val > end_val:
            raise typer.BadParameter(
                f"Start year ({start_val}) must be before end year ({end_val})."
            )
        if resolved[0] == "station" or resolved[0] == "stations":
            ts = ms.normals(resolved[1], start_val, end_val, **kwargs)
        else:
            point = ms.Point(resolved[1], resolved[2])
            radius = get_interpolation_radius()
            nearby = ms.stations.nearby(
                point, radius=radius, limit=get_interpolation_station_count()
            )
            if nearby.empty:
                typer.echo(
                    "No weather stations found within the specified radius.",
                    err=True,
                )
                raise typer.Exit(1)
            ts = ms.normals(nearby, start_val, end_val, **kwargs)
            ts = ms.interpolate(ts, point)
    else:
        api_fn = getattr(ms, granularity)

        if granularity == "hourly":
            default_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            default_end = datetime.now().strftime("%Y-%m-%d")
            start_dt = parse_datetime(start or default_start)
            end_dt = parse_datetime(end or default_end, is_end=True)
            if start_dt and end_dt and start_dt > end_dt:
                raise typer.BadParameter(
                    f"Start date ({start_dt.date()}) must be before end date ({end_dt.date()})."
                )
            extra_kwargs: dict = {}
            if timezone:
                extra_kwargs["timezone"] = timezone
            if resolved[0] == "station" or resolved[0] == "stations":
                ts = api_fn(
                    resolved[1],
                    start_dt,
                    end_dt,
                    **extra_kwargs,
                    **kwargs,
                )
            else:
                point = ms.Point(resolved[1], resolved[2])
                radius = get_interpolation_radius()
                nearby = ms.stations.nearby(
                    point, radius=radius, limit=get_interpolation_station_count()
                )
                if nearby.empty:
                    typer.echo(
                        "No weather stations found within the specified radius.",
                        err=True,
                    )
                    raise typer.Exit(1)
                ts = api_fn(
                    nearby,
                    start_dt,
                    end_dt,
                    **extra_kwargs,
                    **kwargs,
                )
                ts = ms.interpolate(ts, point)
        else:
            # daily/monthly
            if granularity == "daily":
                default_start = (datetime.now() - timedelta(days=30)).strftime(
                    "%Y-%m-%d"
                )
            else:
                default_start = (datetime.now() - timedelta(days=365)).strftime(
                    "%Y-%m-%d"
                )
            default_end = datetime.now().strftime("%Y-%m-%d")
            start_dt = parse_datetime(start or default_start)
            end_dt = parse_datetime(end or default_end, is_end=True)
            if start_dt and end_dt and start_dt > end_dt:
                raise typer.BadParameter(
                    f"Start date ({start_dt.date()}) must be before end date ({end_dt.date()})."
                )
            if resolved[0] == "station" or resolved[0] == "stations":
                ts = api_fn(resolved[1], start_dt, end_dt, **kwargs)
            else:
                point = ms.Point(resolved[1], resolved[2])
                radius = get_interpolation_radius()
                nearby = ms.stations.nearby(
                    point, radius=radius, limit=get_interpolation_station_count()
                )
                if nearby.empty:
                    typer.echo(
                        "No weather stations found within the specified radius.",
                        err=True,
                    )
                    raise typer.Exit(1)
                ts = api_fn(nearby, start_dt, end_dt, **kwargs)
                ts = ms.interpolate(ts, point)

    # Determine humanize setting (CLI config, default True)
    config_data = load_config()
    humanize = config_data.get("humanize", CLI_CONFIG_KEYS["humanize"])

    # Fetch the DataFrame
    df = ts.fetch(sources=with_sources, humanize=humanize)

    if df is None or df.empty:
        typer.echo("No data available.", err=True)
        raise typer.Exit(1)

    # Apply aggregation if requested
    if agg is not None:
        try:
            if "station" in df.index.names:
                df = df.groupby(level="station").agg(agg)
            else:
                result = df.agg(agg)
                df = result.to_frame().T if isinstance(result, pd.Series) else result
        except (AttributeError, TypeError, ValueError) as exc:
            typer.echo(f"Error: Invalid aggregation function '{agg}': {exc}", err=True)
            raise typer.Exit(2) from None

    # Determine output format
    actual_fmt = detect_format(fmt, output)

    output_df(df, actual_fmt, output, no_header, None, show_all)
