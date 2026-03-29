"""Station command for the Meteostat CLI."""

import pandas as pd
import typer

from meteo.utils import detect_format, output_df


def station_cmd(
    station_id: str | None = typer.Argument(
        None, help="Meteostat station ID. If omitted, lists stations."
    ),
    country: str | None = typer.Option(
        None, "--country", "-c", help="ISO 3166-1 alpha-2 country code."
    ),
    state: str | None = typer.Option(None, "--state", help="State or region code."),
    name: str | None = typer.Option(
        None, "--name", "-n", help="Station name (partial match)."
    ),
    sql: str | None = typer.Option(None, "--sql", help="Arbitrary SQL query."),
    wmo: str | None = typer.Option(None, "--wmo", "-w", help="WMO station ID."),
    icao: str | None = typer.Option(None, "--icao", "-i", help="ICAO station ID."),
    iata: str | None = typer.Option(None, "--iata", help="IATA station ID."),
    national: str | None = typer.Option(
        None, "--national", "-N", help="National station ID."
    ),
    bbox: str | None = typer.Option(
        None, "--bbox", help="Bounding box (lon_min,lat_min,lon_max,lat_max)."
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
    """Get metadata for a weather station, or list stations with optional filters."""
    import meteostat as ms

    actual_fmt = detect_format(fmt, output)

    if station_id is not None:
        meta = ms.stations.meta(station_id)

        if meta is None:
            typer.echo(f"Error: Station '{station_id}' not found.", err=True)
            raise typer.Exit(1)

        data = {
            "id": meta.id,
            "name": meta.name,
            "country": meta.country,
            "region": meta.region,
            "latitude": meta.latitude,
            "longitude": meta.longitude,
            "elevation": meta.elevation,
            "timezone": meta.timezone,
        }
        for key, value in meta.identifiers.items():
            data[key] = value

        df = pd.DataFrame([data]).set_index("id")

        if actual_fmt == "text" and output is None:
            from rich.console import Console
            from rich.table import Table

            table = Table(show_header=False, show_lines=True, padding=(0, 2, 0, 0))
            table.add_column(style="bold")
            table.add_column()
            for field, value in data.items():
                display = str(value) if value is not None else ""
                if field == "elevation" and value is not None:
                    display = f"{value} m"
                table.add_row(field, display)
            Console().print(table)
        else:
            output_df(df, actual_fmt, output, no_header, show_all=show_all)
    else:
        if sql:
            df = ms.stations.query(sql, index_col="id")
        else:
            conditions: list[str] = []
            params: list[str] = []

            if country:
                conditions.append("`stations`.`country` = ?")
                params.append(country.upper())

            if state:
                conditions.append("`stations`.`region` = ?")
                params.append(state.upper())

            if name:
                conditions.append("`names`.`name` LIKE ?")
                params.append(f"%{name}%")

            if wmo:
                conditions.append(
                    "`stations`.`id` IN (SELECT `station` FROM `identifiers` WHERE `key` = 'wmo' AND `value` LIKE ?)"
                )
                params.append(f"%{wmo.upper()}%")

            if icao:
                conditions.append(
                    "`stations`.`id` IN (SELECT `station` FROM `identifiers` WHERE `key` = 'icao' AND `value` LIKE ?)"
                )
                params.append(f"%{icao.upper()}%")

            if iata:
                conditions.append(
                    "`stations`.`id` IN (SELECT `station` FROM `identifiers` WHERE `key` = 'iata' AND `value` LIKE ?)"
                )
                params.append(f"%{iata.upper()}%")

            if national:
                conditions.append(
                    "`stations`.`id` IN (SELECT `station` FROM `identifiers` WHERE `key` = 'national' AND `value` LIKE ?)"
                )
                params.append(f"%{national.upper()}%")

            if bbox:
                parts = bbox.split(",")
                if len(parts) != 4:
                    typer.echo(
                        "Error: --bbox requires 4 comma-separated values: lon_min,lat_min,lon_max,lat_max",
                        err=True,
                    )
                    raise typer.Exit(2)
                try:
                    lon_min_f, lat_min_f, lon_max_f, lat_max_f = (
                        float(p) for p in parts
                    )
                except ValueError:
                    typer.echo(
                        "Error: --bbox values must be numeric floats.",
                        err=True,
                    )
                    raise typer.Exit(2) from None
                conditions.append("`stations`.`longitude` >= ?")
                params.append(str(lon_min_f))
                conditions.append("`stations`.`latitude` >= ?")
                params.append(str(lat_min_f))
                conditions.append("`stations`.`longitude` <= ?")
                params.append(str(lon_max_f))
                conditions.append("`stations`.`latitude` <= ?")
                params.append(str(lat_max_f))

            query = """
                SELECT
                    `stations`.`id`,
                    `names`.`name`,
                    `stations`.`country`,
                    `stations`.`region`,
                    `stations`.`latitude`,
                    `stations`.`longitude`,
                    `stations`.`elevation`,
                    `stations`.`timezone`
                FROM `stations`
                LEFT JOIN `names` ON `stations`.`id` = `names`.`station`
                    AND `names`.`language` = 'en'
            """

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY `stations`.`id`"

            df = ms.stations.query(
                query, index_col="id", params=tuple(params) if params else None
            )

        output_df(df, actual_fmt, output, no_header, show_all=show_all)
