"""Geometry and lookups for the lunar south pole (pure functions, no network).

* Polar stereographic projection on the 1737.4 km sphere, true at the pole, as used
  by the LOLA polar GDRs (LDEM_80S_20M, AVGVISIB_*) and the Diviner polar products.
* A 7x7 grid at 120 m laid out in local east/north metres through great-circle
  destinations, so it stays valid at -89.7 deg where a lat/lon grid degenerates.
* Binary search over the fixed-width ASCII tables of the Diviner polar cumulative
  product (PCP), sorted by (x, y), read with HTTP range requests.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

MOON_RADIUS_M = 1737400.0
PCP_RECORD_BYTES = 59
PCP_HEADER_RECORDS = 1
PCP_PIXEL_M = 240.0
PCP_COLUMN_ROWS = 3600  # rows that cover one x column (<= ~2 900 occur) in a single range read


def polar_xy_south(lat: float, lon: float, radius_m: float = MOON_RADIUS_M) -> Tuple[float, float]:
    """Metres (x east at lon 0 -> +y) in south polar stereographic, true at the pole."""
    rho = 2.0 * radius_m * math.tan(math.radians(90.0 + lat) / 2.0)
    lam = math.radians(lon)
    return rho * math.sin(lam), rho * math.cos(lam)


def destination(lat: float, lon: float, east_m: float, north_m: float, radius_m: float = MOON_RADIUS_M) -> Tuple[float, float]:
    """Point reached moving east_m / north_m (local tangent offsets) along a great circle."""
    dist = math.hypot(east_m, north_m)
    if dist == 0.0:
        return lat, lon
    bearing = math.atan2(east_m, north_m)
    ang = dist / radius_m
    phi1, lam1 = math.radians(lat), math.radians(lon)
    sin_phi2 = math.sin(phi1) * math.cos(ang) + math.cos(phi1) * math.sin(ang) * math.cos(bearing)
    phi2 = math.asin(max(-1.0, min(1.0, sin_phi2)))
    lam2 = lam1 + math.atan2(
        math.sin(bearing) * math.sin(ang) * math.cos(phi1),
        math.cos(ang) - math.sin(phi1) * sin_phi2,
    )
    return math.degrees(phi2), ((math.degrees(lam2) + 180.0) % 360.0) - 180.0


def local_grid_points(lat: float, lon: float, n: int = 7, spacing_m: float = 120.0,
                      radius_m: float = MOON_RADIUS_M) -> List[Tuple[float, float]]:
    """n x n (lat, lon) points, row-major from south-west, spaced spacing_m east/north."""
    half = n // 2
    return [
        destination(lat, lon, ix * spacing_m, iy * spacing_m, radius_m)
        for iy in range(-half, half + 1)
        for ix in range(-half, half + 1)
    ]


def lower_bound(n_rows: int, key_of: Callable[[int], float], target: float) -> int:
    """First row index in [0, n_rows) whose key >= target (rows sorted ascending by key)."""
    lo, hi = 0, n_rows
    while lo < hi:
        mid = (lo + hi) // 2
        if key_of(mid) < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def parse_pcp_line(line: str) -> Optional[Tuple[float, float, float]]:
    """(x, y, tbol_K) from one PCP record, or None if it is not a data row."""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != 5:
        return None
    try:
        return float(parts[0]), float(parts[1]), float(parts[4])
    except ValueError:
        return None


def pcp_bin_value(
    x_norm: float,
    y_norm: float,
    n_data_rows: int,
    read_rows: Callable[[int, int], Sequence[Tuple[float, float, float]]],
    pixel_m: float = PCP_PIXEL_M,
    radius_m: float = MOON_RADIUS_M,
) -> Optional[float]:
    """Tbol of the 240 m bin containing (x_norm, y_norm), or None if the bin is empty.

    read_rows(first, count) returns the parsed records [first, first + count) (data rows
    numbered from 0). The table is sorted by x then y, so we bisect on x to the start of
    the column and then read the whole column in one block.
    """
    half = (pixel_m / radius_m) / 2.0
    first_x = lambda i: read_rows(i, 1)[0][0]  # noqa: E731
    start = lower_bound(n_data_rows, first_x, x_norm - half)
    if start >= n_data_rows:
        return None
    count = min(PCP_COLUMN_ROWS, n_data_rows - start)
    block = read_rows(start, count)
    column = [r for r in block if abs(r[0] - x_norm) <= half]
    if not column:
        return None
    # a single x node lies within +-half; keep the rows of that node only
    node_x = min(column, key=lambda r: abs(r[0] - x_norm))[0]
    same = [r for r in column if r[0] == node_x]
    best = min(same, key=lambda r: abs(r[1] - y_norm))
    if abs(best[1] - y_norm) > half:
        return None
    return best[2]


def pcp_summary(values: Dict[str, Sequence[Optional[float]]]) -> Dict[str, float]:
    """Annual mean / diurnal range as the mean of the summer and winter statistics (K)."""
    from climate import diurnal_stats

    per_season = {name: diurnal_stats(v) for name, v in values.items()}
    n = len(per_season)
    return {
        "mean_K": sum(s["mean_K"] for s in per_season.values()) / n,
        "diurnal_range_K": sum(s["diurnal_range_K"] for s in per_season.values()) / n,
        "max_K": max(max(x for x in v if x is not None) for v in values.values()),
        "seasons": per_season,
    }
