"""Topographic metrics for Moon/Mars targets, identical to the Earth pipeline.

The Earth candidates (services/earth/clients/opentopo.py) sample a 7x7 grid at
120 m spacing (bilinear DEM values) and derive relative relief (max-min),
centre slope (four cardinal neighbours) and roughness (sample std. dev.).
These functions reproduce that geometry on a spherical body so S_T compares
the same quantities. Kept separate from earth/ because both services are
deployed and tested as independent packages.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

GRID_N = 7
SPACING_M = 120.0


def grid_points(
    lat: float, lon: float, radius_m: float, n: int = GRID_N, spacing_m: float = SPACING_M
) -> List[Tuple[float, float]]:
    """n x n grid of (lat, lon) in degrees, centred on the target, on a sphere of radius_m."""
    dlat = math.degrees(spacing_m / radius_m)
    coslat = max(0.05, abs(math.cos(math.radians(lat))))
    dlon = math.degrees(spacing_m / (radius_m * coslat))
    half = n // 2
    return [
        (lat + iy * dlat, lon + ix * dlon)
        for iy in range(-half, half + 1)
        for ix in range(-half, half + 1)
    ]


def bilinear(window: Sequence[Sequence[Optional[float]]], fx: float, fy: float) -> Optional[float]:
    """Bilinear value at fractional (fx, fy) inside a 2-D window of cell values."""
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    corners = (
        window[y0][x0], window[y0][x0 + 1],
        window[y0 + 1][x0], window[y0 + 1][x0 + 1],
    )
    if any(c is None for c in corners):
        return None
    z00, z10, z01, z11 = corners
    top = z00 * (1 - tx) + z10 * tx
    bottom = z01 * (1 - tx) + z11 * tx
    return top * (1 - ty) + bottom * ty


def terrain_metrics(elevations: Sequence[Optional[float]], n: int = GRID_N, spacing_m: float = SPACING_M) -> Dict[str, Optional[float]]:
    """Same definitions as earth/clients/opentopo.py::terrain_metrics."""
    if len(elevations) != n * n:
        raise ValueError("expected %s elevations, got %s" % (n * n, len(elevations)))
    valid = [z for z in elevations if z is not None]
    if len(valid) < 5:
        return {"elevation_m": elevations[(n * n) // 2], "relative_relief_m": None,
                "slope_deg": None, "roughness_m": None, "n_valid": len(valid)}
    mean = sum(valid) / len(valid)
    roughness = math.sqrt(sum((z - mean) ** 2 for z in valid) / (len(valid) - 1))
    c = n // 2

    def at(ix: int, iy: int) -> Optional[float]:
        return elevations[iy * n + ix]

    zc, zn, zs, ze, zw = at(c, c), at(c, c + 1), at(c, c - 1), at(c + 1, c), at(c - 1, c)
    slope = None
    if all(v is not None for v in (zc, zn, zs, ze, zw)):
        dx = 2.0 * spacing_m
        dzdx = (ze - zw) / dx
        dzdy = (zn - zs) / dx
        slope = math.degrees(math.atan(math.hypot(dzdx, dzdy)))
    return {
        "elevation_m": zc,
        "relative_relief_m": max(valid) - min(valid),
        "slope_deg": slope,
        "roughness_m": roughness,
        "n_valid": len(valid),
    }


def sample_grid(
    points: Sequence[Tuple[float, float]],
    to_pixel: Callable[[float, float], Tuple[float, float]],
    read_window: Callable[[int, int, int, int], List[List[Optional[float]]]],
) -> List[Optional[float]]:
    """Bilinear DEM values at each (lat, lon), reading one window that covers the grid."""
    pix = [to_pixel(lat, lon) for lat, lon in points]
    col0 = int(math.floor(min(p[0] for p in pix)))
    row0 = int(math.floor(min(p[1] for p in pix)))
    col1 = int(math.floor(max(p[0] for p in pix))) + 2
    row1 = int(math.floor(max(p[1] for p in pix))) + 2
    window = read_window(col0, row0, col1 - col0, row1 - row0)
    return [bilinear(window, px - col0, py - row0) for px, py in pix]
