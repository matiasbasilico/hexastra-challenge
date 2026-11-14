"""Thermal statistics for Moon/Mars targets from published climate products.

Pure functions (no network) so they can be unit-tested:

* Mars: Mars Climate Database (MCD v6.2, LMD/OU/IAA/ESA/CNES) web output with
  Ls = all (every 15°) and local time = all (every martian hour) at 2 m above
  the surface, the same height as ERA5 t2m used for the Earth candidates.
  The annual mean weights each Ls by the time Mars spends there (Kepler's
  second law), because equal Ls steps are not equal durations.
* Moon: Diviner Global Cumulative Product (Williams et al. 2017, Icarus 283,
  300-325), bolometric surface temperature in 0.5° bins and 0.25 h of local
  time. Empty local-time bins are filled by circular linear interpolation.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

MARS_ECCENTRICITY = 0.0934
MARS_LS_PERIHELION = 251.0  # degrees
GCP_ROW_BYTES = 113
GCP_LAT_BINS_PER_FILE = 20
GCP_LT_BINS = 96
GCP_NODATA = -9999.0


def parse_mcd_table(text: str) -> List[Tuple[float, List[float]]]:
    """Rows of (Ls, temperatures by local time) from an MCD 'Ls x local time' ASCII file."""
    rows = []
    for line in text.splitlines():
        if "||" not in line or line.startswith("----"):
            continue
        head, vals = line.split("||", 1)
        rows.append((float(head), [float(v) for v in vals.split()]))
    return rows


def ls_time_weight(ls_deg: float) -> float:
    """Relative time spent per degree of Ls (inverse of dLs/dt for a Keplerian orbit)."""
    return 1.0 / (1.0 + MARS_ECCENTRICITY * math.cos(math.radians(ls_deg - MARS_LS_PERIHELION))) ** 2


def mcd_annual_stats(rows: Sequence[Tuple[float, Sequence[float]]]) -> Dict[str, float]:
    """Time-weighted annual mean of daily means and of daily (max - min), in K."""
    seasons = [(ls, list(vals)[:24]) for ls, vals in rows if ls < 360.0]
    if not seasons or any(len(v) < 24 for _, v in seasons):
        raise ValueError("MCD table needs 24 local times for every Ls")
    weights = [ls_time_weight(ls) for ls, _ in seasons]
    total = sum(weights)
    daily_mean = [sum(v) / len(v) for _, v in seasons]
    daily_range = [max(v) - min(v) for _, v in seasons]
    return {
        "mean_K": sum(w * x for w, x in zip(weights, daily_mean)) / total,
        "diurnal_range_K": sum(w * x for w, x in zip(weights, daily_range)) / total,
        "daily_mean_min_K": min(daily_mean),
        "daily_mean_max_K": max(daily_mean),
        "n_ls": len(seasons),
    }


def gcp_file_and_offset(lat: float, lon: float) -> Tuple[str, int, Tuple[float, float]]:
    """GCP file name, byte offset of the 96 local-time rows, and bin centre for a point."""
    if not 0.0 <= lat < 90.0:
        # Only the northern file names (e.g. ..._10n20n_002.tab) were checked against the archive.
        raise ValueError("GCP file naming verified only for northern latitude bands")
    band = int(math.floor(lat / 10.0)) * 10
    lo, hi = band, band + 10

    def tag(v: int) -> str:
        return "%02d%s" % (abs(v), "s" if v < 0 else "n")

    name = "global_cumul_avg_cyl_%s%s_002.tab" % (tag(lo), tag(hi))
    lon180 = ((lon + 180.0) % 360.0) - 180.0
    ilon = int(math.floor((lon180 + 180.0) / 0.5))
    ilat = int(math.floor((lat - lo) / 0.5))
    row = 1 + (ilon * GCP_LAT_BINS_PER_FILE + ilat) * GCP_LT_BINS  # +1 header record
    centre = (lo + (ilat + 0.5) * 0.5, -180.0 + (ilon + 0.5) * 0.5)
    return name, row * GCP_ROW_BYTES, centre


def parse_gcp_rows(text: str) -> List[Tuple[float, float, float, Optional[float]]]:
    """(clon, clat, local_time, tbol_K or None) for each GCP record."""
    out = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 11:
            continue
        try:
            clon, clat, ltim, tbol = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[10])
        except ValueError:
            continue
        out.append((clon, clat, ltim, None if tbol == GCP_NODATA else tbol))
    return out


def diurnal_stats(values: Sequence[Optional[float]]) -> Dict[str, float]:
    """Mean and max-min over a circular diurnal cycle, filling gaps linearly."""
    n = len(values)
    idx = [i for i, v in enumerate(values) if v is not None]
    if len(idx) < 2:
        raise ValueError("not enough valid local-time bins")
    filled: List[float] = [0.0] * n
    max_gap = 0
    for k, i in enumerate(idx):
        j = idx[(k + 1) % len(idx)]
        span = (j - i) % n or n
        max_gap = max(max_gap, span - 1)
        for s in range(span):
            filled[(i + s) % n] = values[i] + (values[j] - values[i]) * s / span
    return {
        "mean_K": sum(filled) / n,
        "diurnal_range_K": max(filled) - min(filled),
        "n_valid": len(idx),
        "n_bins": n,
        "max_gap_bins": max_gap,
    }
