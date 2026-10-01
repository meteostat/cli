"""Edit station command for the Meteostat CLI."""

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import typer

from meteo.commands.contrib import REPO_HELP, echo_report
from meteo.contrib.repo import (
    load_stations,
    require_station,
    resolve_repo,
    serialize,
    write_station,
)
from meteo.contrib.validation import Report, Validator, load_schema


def schema_types(schema: dict[str, Any], key: str) -> set[str]:
    """Get the allowed JSON types of a property in dot notation."""
    node = schema
    for part in key.split("."):
        properties = node.get("properties", {})
        if part in properties:
            node = properties[part]
        elif isinstance(node.get("additionalProperties"), dict):
            node = node["additionalProperties"]
        else:
            return set()
    types = node.get("type", [])
    return {types} if isinstance(types, str) else set(types)


def parse_value(value: str, types: set[str]) -> Any:
    """Convert a --set value to the type expected by the schema."""
    if value == "null" and "null" in types:
        return None
    if "string" in types:
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


def _check_key(key: str, option: str) -> None:
    if not key or "" in key.split("."):
        raise typer.BadParameter(f"Invalid property '{key}'.", param_hint=option)
    if key.split(".")[0] == "id":
        raise typer.BadParameter(
            "The Meteostat ID cannot be changed.", param_hint=option
        )


def set_property(data: dict[str, Any], key: str, value: Any) -> None:
    """Set a property using dot notation, creating objects as needed."""
    *parents, last = key.split(".")
    node = data
    for part in parents:
        node = node.setdefault(part, {})
        if not isinstance(node, dict):
            raise typer.BadParameter(f"'{part}' is not an object.", param_hint="--set")
    node[last] = value


def unset_property(data: dict[str, Any], key: str) -> None:
    """Remove a property using dot notation."""
    *parents, last = key.split(".")
    node: Any = data
    for part in parents:
        node = node.get(part) if isinstance(node, dict) else None
    if not isinstance(node, dict) or last not in node:
        raise typer.BadParameter(f"Property '{key}' is not set.", param_hint="--unset")
    del node[last]


def launch_editor(text: str, filename: str, editor: str | None) -> str:
    """Open text in an editor and return the edited text."""
    command = (
        editor
        or os.environ.get("VISUAL")
        or os.environ.get("EDITOR")
        or ("notepad" if os.name == "nt" else "vi")
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / filename
        path.write_text(text, encoding="utf-8")
        try:
            subprocess.run(
                [*shlex.split(command, posix=os.name != "nt"), str(path)], check=True
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            typer.echo(f"Error: Could not run editor '{command}': {exc}", err=True)
            raise typer.Exit(1) from None
        return path.read_text(encoding="utf-8")


def edit_cmd(
    station_id: str = typer.Argument(..., help="Meteostat station ID."),
    set_: list[str] | None = typer.Option(
        None,
        "--set",
        "-s",
        help="Set a property as KEY=VALUE using dot notation (repeatable).",
    ),
    unset: list[str] | None = typer.Option(
        None, "--unset", "-u", help="Remove an optional property (repeatable)."
    ),
    editor: str | None = typer.Option(
        None, "--editor", help="Editor command to use instead of $VISUAL/$EDITOR."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the resulting JSON without writing the file."
    ),
    repo: str | None = typer.Option(None, "--repo", help=REPO_HELP),
) -> None:
    """Edit an existing weather station."""
    repo_path = resolve_repo(repo)
    path = require_station(repo_path, station_id)
    station_id = path.stem
    raw = path.read_text(encoding="utf-8")
    validator = Validator(load_stations(repo_path))

    if set_ or unset:
        try:
            data = json.loads(raw)
        except ValueError as exc:
            typer.echo(f"Error: {path.name} contains invalid JSON: {exc}", err=True)
            raise typer.Exit(1) from None
        schema = load_schema()
        for item in set_ or []:
            key, sep, value = item.partition("=")
            if not sep:
                raise typer.BadParameter(
                    f"Expected KEY=VALUE, got '{item}'.", param_hint="--set"
                )
            _check_key(key, "--set")
            set_property(data, key, parse_value(value, schema_types(schema, key)))
        for key in unset or []:
            _check_key(key, "--unset")
            unset_property(data, key)

        report = validator.validate(station_id, data)
        if not report.valid:
            echo_report(report)
            raise typer.Exit(1)
    else:
        text = raw
        while True:
            edited = launch_editor(text, path.name, editor)
            if edited.strip() == raw.strip():
                typer.echo("No changes.")
                return
            try:
                data = json.loads(edited)
                report = validator.validate(station_id, data)
            except ValueError as exc:
                report = Report(station_id, errors=[f"Invalid JSON: {exc}"])
            if report.valid:
                break
            echo_report(report)
            if not typer.confirm("Re-open the editor?", default=True):
                typer.echo("Changes discarded.")
                raise typer.Exit(1)
            text = edited

    if dry_run:
        typer.echo(serialize(data))
        return

    write_station(path, data)
    typer.echo(f"Updated station {station_id} ({path.relative_to(repo_path)})")
