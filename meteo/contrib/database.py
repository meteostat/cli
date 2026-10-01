"""Build a SQLite database from station files."""

import sqlite3
from pathlib import Path
from typing import Any

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


def _describe(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        return f"Missing property {exc}"
    return f"Could not be written: {exc}"
