"""Build a SQLite database or Parquet file from station files."""

import sqlite3
from pathlib import Path
from typing import Any

import typer

TABLES_SQL = """
CREATE TABLE `stations` (
  `id` char(5) NOT NULL PRIMARY KEY,
  `country` varchar(2) DEFAULT NULL,
  `region` varchar(5) DEFAULT NULL,
  `latitude` float(8,4) DEFAULT NULL,
  `longitude` float(8,4) DEFAULT NULL,
  `elevation` int(4) DEFAULT NULL,
  `timezone` varchar(30) DEFAULT NULL
);

CREATE TABLE `names` (
  `station` char(5) NOT NULL,
  `language` char(2) NOT NULL,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`station`, `language`)
);

CREATE TABLE `identifiers` (
  `station` char(5) NOT NULL,
  `key` varchar(255) NOT NULL,
  `value` varchar(255) NOT NULL,
  PRIMARY KEY (`station`, `key`)
);
"""


def build_database(
    stations: dict[str, dict[str, Any]], output: Path
) -> tuple[int, list[tuple[str, str]]]:
    """Write stations to a new SQLite database at ``output``.

    Inactive stations are left out, like in the official database. The file is
    only replaced once the database was built successfully.

    Returns the number of stations written and a list of (id, reason) for
    stations which could not be written.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(f"{output.name}.tmp")
    tmp.unlink(missing_ok=True)

    count = 0
    failed: list[tuple[str, str]] = []
    conn = sqlite3.connect(tmp, isolation_level=None)
    try:
        conn.executescript(TABLES_SQL)
        conn.execute("BEGIN")
        for station_id, data in stations.items():
            if data.get("active", True) is False:
                continue
            # Roll back partial inserts of stations which can't be written
            conn.execute("SAVEPOINT station")
            try:
                _insert(conn, data)
                count += 1
            except (KeyError, TypeError, AttributeError, sqlite3.Error) as exc:
                conn.execute("ROLLBACK TO station")
                failed.append((station_id, _describe(exc)))
            conn.execute("RELEASE station")
        conn.execute("COMMIT")
    finally:
        conn.close()

    tmp.replace(output)
    return count, failed


def _insert(conn: sqlite3.Connection, data: dict[str, Any]) -> None:
    station_id = data["id"]
    location = data["location"]
    conn.execute(
        "INSERT INTO `stations` VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            station_id,
            data["country"],
            data.get("region"),
            location["latitude"],
            location["longitude"],
            location["elevation"],
            data["timezone"],
        ),
    )
    conn.executemany(
        "INSERT INTO `names` VALUES (?, ?, ?)",
        [(station_id, lang, name) for lang, name in data["name"].items()],
    )
    conn.executemany(
        "INSERT INTO `identifiers` VALUES (?, ?, ?)",
        [(station_id, key, value) for key, value in data["identifiers"].items()],
    )


def build_parquet(
    stations: dict[str, dict[str, Any]], output: Path
) -> tuple[int, list[tuple[str, str]]]:
    """Write stations to a Parquet file at ``output``.

    One row per station, sorted by ID. ``name`` holds the English name,
    ``names`` the names in other languages and ``identifiers`` all identifiers,
    so new languages or identifier keys don't change the schema. Inactive
    stations are left out, like in the SQLite database.

    Returns the number of stations written and a list of (id, reason) for
    stations which could not be written.
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        typer.echo(
            "Error: Additional dependencies are required for Parquet output. "
            'Install with: uv tool install "meteostat-cli[contrib]"',
            err=True,
        )
        raise typer.Exit(1) from None

    text_map = pa.map_(pa.string(), pa.string())
    schema = pa.schema(
        [
            pa.field("id", pa.string(), nullable=False),
            pa.field("name", pa.string(), nullable=False),
            pa.field("names", text_map),
            pa.field("country", pa.string()),
            pa.field("region", pa.string()),
            pa.field("latitude", pa.float64()),
            pa.field("longitude", pa.float64()),
            pa.field("elevation", pa.int16()),
            pa.field("timezone", pa.string()),
            pa.field("identifiers", text_map),
        ]
    )

    rows: list[dict[str, Any]] = []
    failed: list[tuple[str, str]] = []
    for station_id in sorted(stations):
        data = stations[station_id]
        if data.get("active", True) is False:
            continue
        try:
            rows.append(_parquet_row(data))
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            failed.append((station_id, _describe(exc)))

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(f"{output.name}.tmp")
    table = pa.Table.from_pylist(rows, schema=schema)
    # One row group; dictionary encoding only pays off for the repetitive
    # columns. The file is written once and downloaded often, so compress hard.
    pq.write_table(
        table,
        tmp,
        compression="zstd",
        compression_level=19,
        use_dictionary=["country", "region", "timezone"],
        row_group_size=len(rows) or None,
    )
    tmp.replace(output)
    return len(rows), failed


def _parquet_row(data: dict[str, Any]) -> dict[str, Any]:
    names = dict(data["name"])
    name = names.pop("en")
    location = data["location"]
    elevation = location["elevation"]
    if elevation is not None and not -32768 <= elevation <= 32767:
        raise ValueError(f"Elevation {elevation} out of range")
    row = {
        "id": str(data["id"]),
        "name": str(name),
        "names": _pairs(names),
        "country": data["country"],
        "region": data.get("region"),
        "latitude": _float(location["latitude"]),
        "longitude": _float(location["longitude"]),
        "elevation": None if elevation is None else int(elevation),
        "timezone": data["timezone"],
        "identifiers": _pairs(data["identifiers"]),
    }
    for key in ("country", "region", "timezone"):
        if row[key] is not None and not isinstance(row[key], str):
            raise TypeError(f"{key} must be a string")
    return row


def _pairs(mapping: dict[str, Any]) -> list[tuple[str, str]] | None:
    """Sorted (key, value) pairs of a map column; None if there are none."""
    return [(str(k), str(v)) for k, v in sorted(mapping.items())] or None


def _float(value: Any) -> float | None:
    return None if value is None else float(value)


def _describe(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        return f"Missing property {exc}"
    return f"Could not be written: {exc}"
