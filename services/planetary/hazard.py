"""Operational hazard metrics comparable on Earth, the Moon and Mars (component O).

Pure functions, no network. They reuse the T geometry exactly: a 7x7 elevation
grid at 120 m around the point (services/planetary/terrain.py on Moon/Mars,
services/earth/clients/opentopo.py on Earth), row-major from the south-west.

Slope of a cell = the same finite difference T uses for the centre (four
cardinal neighbours, baseline 2 x 120 m = 240 m). It is computed for the 5x5
interior cells (the border has no complete neighbourhood), so a fraction moves
in steps of 1/25 = 0.04 and describes an area of about 600 m x 600 m.

Scale caveat: landing and rover requirements are written for metre-scale
baselines (lander footprint, wheel base). A 240 m baseline smooths those slopes
out, so these fractions are a lower bound of the real hazard and are only
comparable between sites measured with the same grid, which is the point here.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

GRID_N = 7
SPACING_M = 120.0

# Thresholds in degrees. Sources are documented in docs/propuestas/O.md and in
# each measurement row; keep the ids in sync with o-comparable.features.json.
SLOPE_THRESHOLDS_DEG = (10.0, 15.0, 30.0)


def feature_id(threshold_deg: float) -> str:
    return "slope_frac_gt_%ddeg" % int(round(threshold_deg))


def cell_slopes(elevations: Sequence[Optional[float]], n: int = GRID_N,
                spacing_m: float = SPACING_M) -> List[Optional[float]]:
    """Slope (deg) of each interior cell, row-major; None where a neighbour is missing."""
    if len(elevations) != n * n:
        raise ValueError("expected %s elevations, got %s" % (n * n, len(elevations)))

    def at(ix: int, iy: int) -> Optional[float]:
        return elevations[iy * n + ix]

    out: List[Optional[float]] = []
    dx = 2.0 * spacing_m
    for iy in range(1, n - 1):
        for ix in range(1, n - 1):
            zc, zn, zs, ze, zw = at(ix, iy), at(ix, iy + 1), at(ix, iy - 1), at(ix + 1, iy), at(ix - 1, iy)
            if any(v is None for v in (zc, zn, zs, ze, zw)):
                out.append(None)
                continue
            dzdx = (ze - zw) / dx
            dzdy = (zn - zs) / dx
            out.append(math.degrees(math.atan(math.hypot(dzdx, dzdy))))
    return out


MIN_VALID_CELLS = 20  # of 25: below this the fraction is not reported


def slope_fractions(elevations: Sequence[Optional[float]], thresholds: Sequence[float] = SLOPE_THRESHOLDS_DEG,
                    n: int = GRID_N, spacing_m: float = SPACING_M) -> Dict[str, Optional[float]]:
    """{feature_id: fraction of interior cells with slope > threshold} plus n_valid / max."""
    slopes = [s for s in cell_slopes(elevations, n, spacing_m) if s is not None]
    out: Dict[str, Optional[float]] = {"n_valid": float(len(slopes)), "max_slope_deg": max(slopes) if slopes else None}
    for t in thresholds:
        if len(slopes) < MIN_VALID_CELLS:
            out[feature_id(t)] = None
        else:
            out[feature_id(t)] = sum(1 for s in slopes if s > t) / len(slopes)
    return out


def is_sea_fill(elevations: Sequence[Optional[float]]) -> bool:
    """True when every cell is exactly 0 m: ASTER GDEM fills sea with 0, so it is water, not flat ground."""
    valid = [z for z in elevations if z is not None]
    return bool(valid) and all(z == 0.0 for z in valid)
