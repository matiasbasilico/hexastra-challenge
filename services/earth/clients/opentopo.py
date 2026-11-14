"""OpenTopoData client. Used for ASTER GDEM v3 elevations (global, including polar)."""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

OPENTOPO = "https://api.opentopodata.org/v1/{dataset}"
USER_AGENT = "HexastraAnalogos/0.1 (NASA Space Apps 2026 prototype)"
MAX_LOCATIONS = 100


def batch_elevations(
    points: Sequence[Tuple[float, float]],
    dataset: str = "aster30m",
    timeout: float = 30.0,
    pause_s: float = 1.05,
) -> List[Optional[float]]:
    """Return elevation in metres for each (lat, lon), or None if the API has no value."""
    out: List[Optional[float]] = []
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        for i in range(0, len(points), MAX_LOCATIONS):
            chunk = points[i : i + MAX_LOCATIONS]
            locs = "|".join("{:.7f},{:.7f}".format(lat, lon) for lat, lon in chunk)
            url = OPENTOPO.format(dataset=dataset)
            r = client.get(url, params={"locations": locs})
            r.raise_for_status()
            payload = r.json()
            if payload.get("status") != "OK":
                raise RuntimeError("OpenTopoData status=%s error=%s" % (payload.get("status"), payload.get("error")))
            results = payload.get("results") or []
            if len(results) != len(chunk):
                raise RuntimeError("OpenTopoData returned %s results for %s points" % (len(results), len(chunk)))
            for item in results:
                ev = item.get("elevation")
                out.append(float(ev) if ev is not None else None)
            if i + MAX_LOCATIONS < len(points):
                time.sleep(pause_s)
    return out


def grid_points(lat: float, lon: float, n: int = 7, spacing_m: float = 120.0) -> Tuple[List[Tuple[float, float]], float, float]:
    """Build an n x n grid centred on (lat, lon). Returns points, dlat, dlon in degrees."""
    dlat = spacing_m / 111320.0
    coslat = math.cos(math.radians(lat))
    # Avoid exploding spacing near the poles.
    denom = max(0.05, abs(coslat))
    dlon = spacing_m / (111320.0 * denom)
    half = n // 2
    pts = []
    for iy in range(-half, half + 1):
        for ix in range(-half, half + 1):
            pts.append((lat + iy * dlat, lon + ix * dlon))
    return pts, dlat, dlon


def terrain_metrics(elevations: Sequence[Optional[float]], n: int, spacing_m: float) -> Dict[str, Any]:
    """Relative relief, center slope and roughness from an n x n elevation grid.

    Slope uses the four cardinal neighbours of the centre cell (Horn-style
    finite differences). Relief is max-min of valid cells. Roughness is the
    sample standard deviation of valid cells. Absolute elevation is returned
    for metadata only; TASI does not use it in S_T.
    """
    if len(elevations) != n * n:
        raise ValueError("expected %s elevations, got %s" % (n * n, len(elevations)))

    def at(ix: int, iy: int) -> Optional[float]:
        # ix, iy in 0..n-1, row-major with x varying first, y from south to north
        return elevations[iy * n + ix]

    valid = [z for z in elevations if z is not None]
    if len(valid) < 5:
        return {
            "elevation_m": elevations[(n * n) // 2],
            "relative_relief_m": None,
            "slope_deg": None,
            "roughness_m": None,
            "n_valid": len(valid),
        }
    relief = max(valid) - min(valid)
    mean = sum(valid) / len(valid)
    var = sum((z - mean) ** 2 for z in valid) / (len(valid) - 1) if len(valid) > 1 else 0.0
    roughness = math.sqrt(var)
    c = n // 2
    zc, zn, zs, ze, zw = at(c, c), at(c, c + 1) if c + 1 < n else None, at(c, c - 1) if c - 1 >= 0 else None, at(c + 1, c) if c + 1 < n else None, at(c - 1, c) if c - 1 >= 0 else None
    slope = None
    if all(v is not None for v in (zc, zn, zs, ze, zw)):
        dx = 2.0 * spacing_m
        dzdx = (ze - zw) / dx
        dzdy = (zn - zs) / dx
        slope = math.degrees(math.atan(math.sqrt(dzdx * dzdx + dzdy * dzdy)))
    return {
        "elevation_m": zc,
        "relative_relief_m": relief,
        "slope_deg": slope,
        "roughness_m": roughness,
        "n_valid": len(valid),
    }


def subwindow_samples(elevations: Sequence[Optional[float]], n: int, spacing_m: float, win: int = 3) -> List[Dict[str, float]]:
    """T samples (relief, slope, roughness) on every win x win subwindow."""
    samples = []
    for y0 in range(0, n - win + 1):
        for x0 in range(0, n - win + 1):
            sub = []
            for iy in range(y0, y0 + win):
                for ix in range(x0, x0 + win):
                    sub.append(elevations[iy * n + ix])
            metrics = terrain_metrics(sub, win, spacing_m)
            if (
                metrics["relative_relief_m"] is not None
                and metrics["slope_deg"] is not None
                and metrics["roughness_m"] is not None
            ):
                samples.append(
                    {
                        "relative_relief_m": metrics["relative_relief_m"],
                        "slope_deg": metrics["slope_deg"],
                        "roughness_m": metrics["roughness_m"],
                    }
                )
    return samples
