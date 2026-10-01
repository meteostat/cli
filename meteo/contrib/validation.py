"""Validation of station records.

Requires the ``contrib`` extra (jsonschema and pycountry).
"""

import copy
import functools
import json
import urllib.request
import zoneinfo
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer

from meteo.contrib.repo import ID_PATTERN, index_identifiers, order_keys, serialize

SCHEMA_URL = (
    "https://raw.githubusercontent.com/meteostat/weather-stations/"
    "refs/heads/main/schema.json"
)


@dataclass
class Report:
    """Validation result of a single station."""

    station_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


@functools.cache
def _fetch_schema() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(SCHEMA_URL, timeout=30) as response:
            return json.load(response)
    except (OSError, ValueError) as exc:
        typer.echo(f"Error: Could not load schema from {SCHEMA_URL}: {exc}", err=True)
        raise typer.Exit(1) from None


def load_schema() -> dict[str, Any]:
    """Load the station schema from the upstream weather-stations repository."""
    return copy.deepcopy(_fetch_schema())


def _quote(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _schema_message(error: Any) -> str:
    """Format a jsonschema validation error."""
    path = ".".join(str(p) for p in error.absolute_path)
    schema = error.schema
    if (
        error.validator in ("minimum", "maximum")
        and "minimum" in schema
        and "maximum" in schema
    ):
        message = (
            f"{error.instance} is out of range "
            f"({schema['minimum']} to {schema['maximum']})"
        )
    else:
        message = error.message
    return f"{path}: {message}" if path else message


class Validator:
    """Validate stations against the schema and the rest of the directory."""

    def __init__(self, stations: dict[str, dict[str, Any]]) -> None:
        try:
            import jsonschema
            import pycountry
        except ImportError:
            typer.echo(
                "Error: Additional dependencies are required for this command. "
                'Install with: uv tool install "meteostat-cli[contrib]"',
                err=True,
            )
            raise typer.Exit(1) from None

        self._pycountry = pycountry
        self._schema = jsonschema.Draft7Validator(load_schema())
        self._timezones = zoneinfo.available_timezones()
        self._identifiers = index_identifiers(stations)

    def validate_file(self, path: Path) -> Report:
        """Validate a station file, including its formatting."""
        report = Report(path.stem)
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, ValueError) as exc:
            report.errors.append(f"Invalid JSON: {exc}")
            return report

        report = self.validate(path.stem, data)
        if isinstance(data, dict) and serialize(data) != raw.rstrip():
            report.warnings.append("File is not formatted consistently")
        return report

    def validate(self, station_id: str, data: Any) -> Report:
        """Validate station data which is stored under the given ID."""
        report = Report(station_id)
        errors = report.errors

        if not ID_PATTERN.match(station_id):
            errors.append(f"File name {_quote(station_id)} is not a valid Meteostat ID")

        errors.extend(_schema_message(e) for e in self._schema.iter_errors(data))
        if not isinstance(data, dict):
            return report

        if "id" in data and data["id"] != station_id:
            errors.append(f"id: {_quote(data['id'])} does not match the file name")

        names = data.get("name")
        if isinstance(names, dict):
            for lang, name in names.items():
                if not isinstance(name, str):
                    continue
                if name != name.strip():
                    errors.append(
                        f"name.{lang}: {_quote(name)} has leading or trailing spaces"
                    )
                if name[:1].islower():
                    errors.append(f"name.{lang}: {_quote(name)} should be capitalized")

        country = data.get("country")
        region = data.get("region")
        if isinstance(country, str):
            if self._pycountry.countries.get(alpha_2=country) is None:
                errors.append(
                    f"country: {_quote(country)} is not a valid ISO 3166-1 alpha-2 code"
                )
            elif (
                isinstance(region, str)
                and self._pycountry.subdivisions.get(code=f"{country}-{region}") is None
            ):
                errors.append(
                    f"region: {_quote(region)} is not a valid "
                    f"ISO 3166-2 subdivision of {country}"
                )

        timezone = data.get("timezone")
        if isinstance(timezone, str) and timezone not in self._timezones:
            errors.append(f"timezone: {_quote(timezone)} is not a valid IANA time zone")

        identifiers = data.get("identifiers")
        if isinstance(identifiers, dict):
            for key, value in identifiers.items():
                others = self._identifiers.get((key, str(value)), set()) - {station_id}
                if others:
                    errors.append(
                        f"identifiers.{key}: {_quote(value)} is also used by "
                        + ", ".join(sorted(others))
                    )

        return report


def _remove_additional_properties(data: Any, schema: dict[str, Any]) -> None:
    """Remove properties which the schema does not allow, recursively."""
    if not isinstance(data, dict):
        return
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        for key in [key for key in data if key not in properties]:
            del data[key]
    for key, subschema in properties.items():
        if key in data:
            _remove_additional_properties(data[key], subschema)


def fix_station(
    station_id: str, data: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    """Fix common formatting issues of a station record."""
    data = copy.deepcopy(data)
    _remove_additional_properties(data, schema)

    if ID_PATTERN.match(station_id):
        data["id"] = station_id

    for key in ("country", "region", "timezone"):
        if isinstance(data.get(key), str):
            data[key] = data[key].strip()
    for key in ("country", "region"):
        if isinstance(data.get(key), str):
            data[key] = data[key].upper()

    names = data.get("name")
    if isinstance(names, dict):
        for lang, name in names.items():
            if isinstance(name, str):
                name = name.strip()
                names[lang] = name[:1].upper() + name[1:]

    identifiers = data.get("identifiers")
    if isinstance(identifiers, dict):
        for key, value in identifiers.items():
            if isinstance(value, int | str) and not isinstance(value, bool):
                identifiers[key] = str(value).strip()
        data["identifiers"] = dict(sorted(identifiers.items()))

    location = data.get("location")
    if isinstance(location, dict):
        elevation = location.get("elevation")
        if isinstance(elevation, float) and elevation.is_integer():
            location["elevation"] = int(elevation)

    return order_keys(data)


def read_and_fix(path: Path, schema: dict[str, Any]) -> bool:
    """Fix a station file in place. Returns whether the file was changed."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    fixed = serialize(fix_station(path.stem, data, schema))
    if fixed == raw:
        return False
    path.write_text(fixed, encoding="utf-8")
    return True
