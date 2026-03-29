"""Inventory command for the Meteostat CLI."""

import typer

from meteo.utils import detect_format, output_df, parse_parameters, parse_providers


def _inventory(
    station_id: str = typer.Argument(..., help="Meteostat station ID."),
    parameters: str | None = typer.Option(
        None, "--parameters", "-p", help="Comma-separated list of parameters."
    ),
    providers: str | None = typer.Option(
        None, "--providers", "-P", help="Comma-separated list of providers."
    ),
    granularity: str | None = typer.Option(
        None,
        "--granularity",
        "-g",
        help="Granularity filter (hourly/h, daily/d, monthly/m).",
    ),
    fmt: str | None = typer.Option(None, "--format", "-f", help="Output format."),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path."),
    no_header: bool = typer.Option(
        False, "--no-header", help="Omit header row from CSV output."
    ),
    show_all: bool = typer.Option(
        False, "--all", "-A", help="Print full table instead of truncated display."
    ),
) -> None:
    """Get inventory data for a weather station."""
    import meteostat as ms
    from meteostat.enumerations import Granularity

    provider_list = parse_providers(providers)

    inv = ms.stations.inventory(station_id, providers=provider_list)

    if inv.df is None or inv.df.empty:
        typer.echo(f"No inventory data found for station '{station_id}'.", err=True)
        raise typer.Exit(1)

    df = inv.df.reset_index()

    # Filter by granularity if specified
    if granularity:
        gran_map = {
            "hourly": Granularity.HOURLY,
            "h": Granularity.HOURLY,
            "daily": Granularity.DAILY,
            "d": Granularity.DAILY,
            "monthly": Granularity.MONTHLY,
            "m": Granularity.MONTHLY,
        }
        gran = gran_map.get(granularity.lower())
        if gran is None:
            typer.echo(
                f"Error: Unknown granularity '{granularity}'. Use hourly/h, daily/d, or monthly/m.",
                err=True,
            )
            raise typer.Exit(2)
        # Filter providers that match the granularity
        from meteostat.core.providers import provider_service

        valid_providers = []
        for p in df["provider"].unique():
            try:
                spec = provider_service.get_provider(p)
                if spec and spec.granularity == gran:
                    valid_providers.append(p)
            except (KeyError, ValueError):
                pass
        df = df[df["provider"].isin(valid_providers)]

    # Filter by parameters if specified
    if parameters:
        param_list = parse_parameters(parameters)
        if param_list:
            param_values = [p.value for p in param_list]
            df = df[df["parameter"].isin(param_values)]

    if df.empty:
        typer.echo("No matching inventory data found.", err=True)
        raise typer.Exit(1)

    actual_fmt = detect_format(fmt, output)
    output_df(
        df.set_index(["station", "provider", "parameter"]),
        actual_fmt,
        output,
        no_header,
        show_all=show_all,
    )


# Expose for registration in cli.py
inventory_cmd = _inventory
inventory_cmd_alias = _inventory
