"""Access to a local clone of the weather stations repository."""

import json
import random
import re
import string
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import typer

from meteo.config import load_config

STATIONS_DIR = "stations"
ID_PATTERN = re.compile(r"^[A-Z0-9$]{5}$")
ID_ALPHABET = string.ascii_uppercase + string.digits

# Canonical order of top-level properties in a station file
KEY_ORDER = (
    "id",
    "active",
    "name",
    "country",
    "region",
    "identifiers",
    "location",
    "timezone",
)


def is_repo(path: Path) -> bool:
    """Check whether a directory looks like a stations repository."""
    return (path / STATIONS_DIR).is_dir()


def resolve_repo(repo: str | None) -> Path:
    """Resolve the stations repository from --repo, config or the working directory."""
    configured = load_config().get("stations_repo")
    source = repo or configured

    if source:
        path = Path(source).expanduser().resolve()
        if not is_repo(path):
            typer.echo(
                f"Error: '{path}' is not a stations repository "
                f"(no '{STATIONS_DIR}' directory found).",
                err=True,
            )
            raise typer.Exit(2)
        return path

    cwd = Path.cwd()
    if is_repo(cwd):
        return cwd

    typer.echo(
        "Error: No stations repository found. Pass --repo or set it with "
        "'meteo config stations_repo PATH'.",
        err=True,
    )
    raise typer.Exit(2)


def station_path(repo: Path, station_id: str) -> Path:
    """Get the file path of a station."""
    return repo / STATIONS_DIR / f"{station_id}.json"


def station_files(repo: Path) -> Iterator[Path]:
    """Iterate over all station files in the repository."""
    yield from sorted((repo / STATIONS_DIR).glob("*.json"))


def require_station(repo: Path, station_id: str) -> Path:
    """Get the file path of an existing station or exit with an error."""
    path = station_path(repo, station_id.upper())
    if not path.is_file():
        typer.echo(
            f"Error: Station '{station_id}' not found in {repo / STATIONS_DIR}.",
            err=True,
        )
        raise typer.Exit(1)
    return path


def serialize(data: dict[str, Any]) -> str:
    """Serialize station data the same way as the files in the repository."""
    return json.dumps(data, indent=4, ensure_ascii=False)


def read_station(path: Path) -> dict[str, Any]:
    """Read and parse a station file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_station(path: Path, data: dict[str, Any]) -> None:
    """Write station data to a file."""
    path.write_text(serialize(data), encoding="utf-8")


def load_stations(repo: Path) -> dict[str, dict[str, Any]]:
    """Load all parseable stations, keyed by their file name."""
    stations = {}
    for path in station_files(repo):
        try:
            data = read_station(path)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            stations[path.stem] = data
    return stations


def index_identifiers(
    stations: dict[str, dict[str, Any]],
) -> dict[tuple[str, str], set[str]]:
    """Map each (key, value) identifier to the stations using it."""
    index: dict[tuple[str, str], set[str]] = {}
    for station_id, data in stations.items():
        identifiers = data.get("identifiers")
        if not isinstance(identifiers, dict):
            continue
        for key, value in identifiers.items():
            index.setdefault((key, str(value)), set()).add(station_id)
    return index


def order_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Sort top-level properties in canonical order, keeping unknown ones last."""
    known = {key: data[key] for key in KEY_ORDER if key in data}
    return known | {key: value for key, value in data.items() if key not in known}


def generate_id(repo: Path) -> str:
    """Generate a random, unused Meteostat ID.

    Numeric IDs are reserved for stations with a WMO ID, so generated IDs
    always contain at least one letter.
    """
    while True:
        candidate = "".join(random.choices(ID_ALPHABET, k=5))
        if candidate.isdigit() or station_path(repo, candidate).exists():
            continue
        return candidate


def changed_station_ids(repo: Path) -> list[str]:
    """List stations which were changed compared to the main branch."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    try:
        for ref in ("main", "origin/main"):
            try:
                base = git("merge-base", ref, "HEAD").strip()
                break
            except subprocess.CalledProcessError:
                continue
        else:
            typer.echo("Error: Could not find a 'main' branch to compare to.", err=True)
            raise typer.Exit(2)
        # Committed and uncommitted changes, plus new files
        changed = git(
            "diff", "--name-only", "--diff-filter=d", base, "--", STATIONS_DIR
        ).splitlines()
        changed += git(
            "ls-files", "--others", "--exclude-standard", "--", STATIONS_DIR
        ).splitlines()
    except FileNotFoundError:
        typer.echo("Error: --changed requires Git to be installed.", err=True)
        raise typer.Exit(2) from None

    return sorted({Path(f).stem for f in changed if f.endswith(".json")})
