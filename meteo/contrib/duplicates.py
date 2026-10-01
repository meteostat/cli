"""Detection of potential duplicate stations."""

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations
from typing import Any

from meteo.contrib.repo import index_identifiers

EARTH_RADIUS = 6_371_000  # meters
NAME_SIMILARITY = 0.8


@dataclass
class Duplicate:
    """A pair of potentially duplicate stations."""

    station_a: str
    station_b: str
    distance: int | None
    reasons: list[str]


def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in meters (Haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS * math.asin(math.sqrt(a))


def _normalize(name: str) -> str:
    return re.sub(r"[\W_]+", " ", name.lower()).strip()


def similar_names(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Check whether two stations have a similar name in any common language."""
    names_a, names_b = a.get("name"), b.get("name")
    if not isinstance(names_a, dict) or not isinstance(names_b, dict):
        return False
    for lang in names_a.keys() & names_b.keys():
        x, y = _normalize(str(names_a[lang])), _normalize(str(names_b[lang]))
        if not x or not y:
            continue
        if x in y or y in x or SequenceMatcher(None, x, y).ratio() >= NAME_SIMILARITY:
            return True
    return False


def _coords(data: dict[str, Any]) -> tuple[float, float] | None:
    location = data.get("location")
    if not isinstance(location, dict):
        return None
    lat, lon = location.get("latitude"), location.get("longitude")
    if not isinstance(lat, int | float) or not isinstance(lon, int | float):
        return None
    return float(lat), float(lon)


def _shared_identifiers(
    stations: dict[str, dict[str, Any]],
) -> dict[tuple[str, str], list[str]]:
    """Map pairs of stations to the identifier keys they share."""
    shared: dict[tuple[str, str], list[str]] = {}
    for (key, _), ids in index_identifiers(stations).items():
        for pair in combinations(sorted(ids), 2):
            shared.setdefault(pair, []).append(key)
    return shared


def _nearby_pairs(
    stations: dict[str, dict[str, Any]], radius: float
) -> dict[tuple[str, str], float]:
    """Find all pairs of stations within the given radius (in meters)."""
    points = sorted(
        (coords, station_id)
        for station_id, data in stations.items()
        if (coords := _coords(data)) is not None
    )
    # Latitude difference which corresponds to the radius
    max_dlat = math.degrees(radius / EARTH_RADIUS)

    pairs = {}
    for i, ((lat1, lon1), id1) in enumerate(points):
        for (lat2, lon2), id2 in points[i + 1 :]:
            if lat2 - lat1 > max_dlat:
                break
            dist = distance(lat1, lon1, lat2, lon2)
            if dist <= radius:
                pairs[tuple(sorted((id1, id2)))] = dist
    return pairs


def find_duplicates(
    stations: dict[str, dict[str, Any]],
    radius: float = 1000,
    ids: set[str] | None = None,
) -> list[Duplicate]:
    """Find potential duplicates.

    Two stations are potential duplicates if they share an identifier, or if
    they are within ``radius`` meters of each other and have similar names.
    If ``ids`` is given, only duplicates involving those stations are returned.
    """
    shared = _shared_identifiers(stations)
    nearby = _nearby_pairs(stations, radius)

    duplicates = []
    for pair in sorted(shared.keys() | nearby.keys()):
        if ids is not None and not ids.intersection(pair):
            continue
        a, b = (stations[station_id] for station_id in pair)
        reasons = sorted(set(shared.get(pair, [])))
        if pair in nearby:
            reasons.append("location")
        if similar_names(a, b):
            reasons.append("name")
        if pair not in shared and "name" not in reasons:
            continue
        coords_a, coords_b = _coords(a), _coords(b)
        dist = (
            round(distance(*coords_a, *coords_b))
            if coords_a is not None and coords_b is not None
            else None
        )
        duplicates.append(Duplicate(*pair, dist, reasons))
    return duplicates
