"""Operational accessibility of Earth sites: roads, aerodromes, population.

Pure functions over local files (no network). Used by scripts/ingest_accessibility.py.

Definitions (all distances are straight-line geodesic on WGS84, not travel distance):
* dist_road_km       nearest road segment of a roads layer (SEDAC gROADS v1).
* dist_airport_km    nearest open aerodrome with a runway (OurAirports small/medium/large_airport).
* dist_airport_scheduled_km  same, restricted to aerodromes with scheduled service.
* population_50km    sum of population-count cells whose centre is within 50 km (SEDAC GPWv4 r11).

These describe how reachable an Earth site is. They are NOT similarity to a Moon/Mars
site and never enter TASI (see docs/propuestas/practicidad.md).
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

WGS84 = "EPSG:4326"
EARTH_RADIUS_KM = 6371.0088  # mean radius, only used to size search windows
RUNWAY_TYPES = ("small_airport", "medium_airport", "large_airport")
ROAD_SEARCH_RADII_KM = (100.0, 400.0, 1500.0, 5000.0)
POPULATION_RADIUS_KM = 50.0
BBOX_MARGIN = 1.05
AIRPORT_SHORTLIST = 25

# ---- practicality index P (proposal, see docs/propuestas/practicidad.md) ----
P_WEIGHTS = {"road": 0.35, "airport": 0.25, "population": 0.20, "altitude": 0.20}
P_ROAD_KM = (1.0, 300.0)            # full score at or below, zero at or above
P_AIRPORT_KM = (25.0, 1000.0)
P_POPULATION = (100.0, 100000.0)    # zero at or below, full score at or above
P_ALTITUDE_M = (2500.0, 5500.0)     # full score at or below, zero at or above


def to_local_km(lat0: float, lon0: float, lats: Sequence[float], lons: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
    """Project points to an azimuthal-equidistant plane centred on (lat0, lon0), in km.

    On this projection the distance from the origin to any point is the WGS84 geodesic
    distance, which is the only property the callers rely on.
    """
    from rasterio.warp import transform

    aeqd = "+proj=aeqd +lat_0=%.8f +lon_0=%.8f +datum=WGS84 +units=m +no_defs" % (lat0, lon0)
    xs, ys = transform(WGS84, aeqd, list(map(float, lons)), list(map(float, lats)))
    return np.asarray(xs, dtype="float64") / 1000.0, np.asarray(ys, dtype="float64") / 1000.0


def geodesic_km(lat0: float, lon0: float, lat: float, lon: float) -> float:
    x, y = to_local_km(lat0, lon0, [lat], [lon])
    return float(math.hypot(x[0], y[0]))


def bboxes_for_radius(lat: float, lon: float, radius_km: float) -> List[Tuple[float, float, float, float]]:
    """Lon/lat boxes (minx, miny, maxx, maxy) that contain the circle; split at the antimeridian."""
    ang = min(math.pi, radius_km * BBOX_MARGIN / EARTH_RADIUS_KM)
    dlat = math.degrees(ang)
    south, north = max(-90.0, lat - dlat), min(90.0, lat + dlat)
    reaches_pole = lat + dlat >= 90.0 or lat - dlat <= -90.0
    ratio = math.sin(ang) / max(math.cos(math.radians(lat)), 1e-12)
    if reaches_pole or ang >= math.pi / 2 or ratio >= 1.0:
        return [(-180.0, south, 180.0, north)]
    dlon = math.degrees(math.asin(ratio))
    west, east = lon - dlon, lon + dlon
    if west < -180.0:
        return [(-180.0, south, east, north), (west + 360.0, south, 180.0, north)]
    if east > 180.0:
        return [(west, south, 180.0, north), (-180.0, south, east - 360.0, north)]
    return [(west, south, east, north)]


def min_distance_to_polylines(x: np.ndarray, y: np.ndarray, part: np.ndarray) -> Tuple[Optional[float], Optional[int]]:
    """Distance from the origin to the nearest segment of a set of polylines.

    x, y are vertex coordinates; `part` tells which polyline each vertex belongs to
    (consecutive vertices with the same value form a segment). Returns (distance, part id).
    """
    if len(x) == 0:
        return None, None
    best = np.hypot(x, y)
    idx = int(np.argmin(best))
    dist, owner = float(best[idx]), int(part[idx])
    if len(x) < 2:
        return dist, owner
    same = part[:-1] == part[1:]
    ax, ay = x[:-1][same], y[:-1][same]
    dx, dy = x[1:][same] - ax, y[1:][same] - ay
    if len(ax) == 0:
        return dist, owner
    length2 = dx * dx + dy * dy
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(length2 > 0, -(ax * dx + ay * dy) / length2, 0.0)
    t = np.clip(t, 0.0, 1.0)
    seg = np.hypot(ax + t * dx, ay + t * dy)
    j = int(np.argmin(seg))
    if float(seg[j]) < dist:
        return float(seg[j]), int(part[:-1][same][j])
    return dist, owner


def _read_roads(path: Path, layer: Optional[str], bbox: Tuple[float, float, float, float], columns: Sequence[str]):
    import pyogrio
    import shapely

    _, _, wkb, fields = pyogrio.raw.read(str(path), layer=layer, bbox=bbox, columns=list(columns))
    geoms = shapely.from_wkb(wkb)
    lines, owner = shapely.get_parts(geoms, return_index=True)
    coords, line_idx = shapely.get_coordinates(lines, return_index=True)
    return coords, line_idx, owner, fields


def nearest_road(
    path: Path, lat: float, lon: float, layer: Optional[str] = None,
    radii_km: Sequence[float] = ROAD_SEARCH_RADII_KM, columns: Sequence[str] = (),
) -> Optional[Dict[str, Any]]:
    """Nearest road segment within the growing search windows, or None if there is none.

    A hit only counts when it lies inside the search radius, so a nearer road outside
    the window cannot be missed.
    """
    for radius in radii_km:
        best: Optional[Dict[str, Any]] = None
        for bbox in bboxes_for_radius(lat, lon, radius):
            coords, line_idx, owner, fields = _read_roads(path, layer, bbox, columns)
            if len(coords) == 0:
                continue
            x, y = to_local_km(lat, lon, coords[:, 1], coords[:, 0])
            dist, line = min_distance_to_polylines(x, y, line_idx)
            if dist is None or (best and best["distance_km"] <= dist):
                continue
            feature = int(owner[line])
            attrs = {name: _plain(values[feature]) for name, values in zip(columns, fields)}
            best = {"distance_km": dist, "attributes": attrs, "search_radius_km": radius}
        if best and best["distance_km"] <= radius:
            return best
    return None


def _plain(value: Any) -> Any:
    return value.item() if hasattr(value, "item") else value


def load_airports(csv_path: Path) -> List[Dict[str, Any]]:
    """Open aerodromes with a runway from an OurAirports airports.csv."""
    out = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["type"] not in RUNWAY_TYPES:
                continue
            try:
                lat, lon = float(row["latitude_deg"]), float(row["longitude_deg"])
            except (TypeError, ValueError):
                continue
            out.append({
                "ident": row["ident"], "name": row["name"], "type": row["type"], "lat": lat, "lon": lon,
                "scheduled": row.get("scheduled_service") == "yes", "country": row.get("iso_country"),
            })
    return out


def nearest_airport(airports: Sequence[Dict[str, Any]], lat: float, lon: float, scheduled_only: bool = False) -> Optional[Dict[str, Any]]:
    pool = [a for a in airports if a["scheduled"]] if scheduled_only else list(airports)
    if not pool:
        return None
    lats = np.radians([a["lat"] for a in pool])
    lons = np.radians([a["lon"] for a in pool])
    lat0, lon0 = math.radians(lat), math.radians(lon)
    hav = np.sin((lats - lat0) / 2) ** 2 + np.cos(lat0) * np.cos(lats) * np.sin((lons - lon0) / 2) ** 2
    order = np.argsort(hav)[:AIRPORT_SHORTLIST]  # spherical shortlist, exact geodesic below
    shortlist = [pool[i] for i in order]
    x, y = to_local_km(lat, lon, [a["lat"] for a in shortlist], [a["lon"] for a in shortlist])
    dist = np.hypot(x, y)
    j = int(np.argmin(dist))
    return {**shortlist[j], "distance_km": float(dist[j])}


def population_within(tif_path: Path, lat: float, lon: float, radius_km: float = POPULATION_RADIUS_KM) -> Dict[str, Any]:
    """Sum a population-count raster over cells whose centre is within radius_km.

    Returns value None when no cell inside the circle has data (e.g. Antarctica, open ocean).
    """
    import rasterio
    from rasterio.windows import from_bounds

    total, valid, cells = 0.0, 0, 0
    with rasterio.open(tif_path) as src:
        nodata = src.nodata
        for west, south, east, north in bboxes_for_radius(lat, lon, radius_km):
            west, east = max(west, src.bounds.left), min(east, src.bounds.right)
            south, north = max(south, src.bounds.bottom), min(north, src.bounds.top)
            if west >= east or south >= north:
                continue
            window = from_bounds(west, south, east, north, src.transform).round_offsets().round_lengths()
            data = src.read(1, window=window).astype("float64")
            if data.size == 0:
                continue
            transform = src.window_transform(window)
            rows, cols = np.indices(data.shape)
            xs = transform.c + (cols + 0.5) * transform.a
            ys = transform.f + (rows + 0.5) * transform.e
            x, y = to_local_km(lat, lon, ys.ravel(), xs.ravel())
            inside = (np.hypot(x, y) <= radius_km).reshape(data.shape)
            has_data = np.isfinite(data) & (data >= 0)
            if nodata is not None:
                has_data &= data != nodata
            cells += int(inside.sum())
            valid += int((inside & has_data).sum())
            total += float(data[inside & has_data].sum())
    return {"value": total if valid else None, "valid_cells": valid, "cells": cells}


def _falling(value: float, full: float, zero: float) -> float:
    """1 at or below `full`, 0 at or above `zero`, log-linear in between."""
    if value <= full:
        return 1.0
    if value >= zero:
        return 0.0
    return (math.log(zero) - math.log(value)) / (math.log(zero) - math.log(full))


def practicality_index(
    dist_road_km: Optional[float], dist_airport_km: Optional[float],
    population_50km: Optional[float], elevation_m: Optional[float],
) -> Dict[str, Any]:
    """Proposed practicality index P (0-100) with per-term scores and coverage.

    Weights are renormalised over the terms that have data (same policy as TASI).
    """
    scores: Dict[str, Optional[float]] = {
        "road": None if dist_road_km is None else _falling(dist_road_km, *P_ROAD_KM),
        "airport": None if dist_airport_km is None else _falling(dist_airport_km, *P_AIRPORT_KM),
        "population": None if population_50km is None else 1.0 - _falling(max(population_50km, 1e-9), *P_POPULATION),
        "altitude": None,
    }
    if elevation_m is not None:
        low, high = P_ALTITUDE_M
        scores["altitude"] = min(1.0, max(0.0, (high - elevation_m) / (high - low)))
    weight = sum(P_WEIGHTS[k] for k, v in scores.items() if v is not None)
    if weight == 0:
        return {"P": None, "scores": scores, "coverage": 0.0}
    total = sum(P_WEIGHTS[k] * v for k, v in scores.items() if v is not None)
    return {"P": 100.0 * total / weight, "scores": scores, "coverage": weight / sum(P_WEIGHTS.values())}
