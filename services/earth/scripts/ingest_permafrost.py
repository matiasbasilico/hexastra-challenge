#!/usr/bin/env python3
"""Permafrost fraction for the Earth sites (Vo, raw magnitude for water_ice_indicator).

    services/.venv/bin/python services/earth/scripts/ingest_permafrost.py fetch  # CEDA NetCDF -> raw/cci_pfr_sites.csv
    services/.venv/bin/python services/earth/scripts/ingest_permafrost.py build  # csv -> data/measurements/vo-hielo.jsonl (earth rows)

Product: ESA Permafrost_cci, permafrost extent L4 v5.0 (PFR, permafrost area
fraction in percent, 0.01 deg grid, yearly; MODIS LST + ERA5 + CryoGrid),
distributed by CEDA and listed in the ESA Open Science Catalog. Two regional
files: northern hemisphere (25..85 N) and Antarctica (60..85 S, ice-free areas).

Statistic: PFR of the 0.01 deg cell that contains the site, mean of 2019..2023.
The 3x3 neighbourhood mean (~3 km) goes to the note. Sites outside both
regions, or on fill cells (ocean, ice sheet), stay null.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
EARTH_ROOT = HERE.parent
REPO = EARTH_ROOT.parent.parent
CATALOG = EARTH_ROOT / "data" / "catalog.json"
CACHE = EARTH_ROOT / "data" / "raw" / "cci_cache"   # NetCDF files, not versioned
SITES_CSV = EARTH_ROOT / "data" / "raw" / "cci_pfr_sites.csv"
OUT = REPO / "data" / "measurements" / "vo-hielo.jsonl"
METHOD = "services/earth/scripts/ingest_permafrost.py"
RETRIEVED = "2026-11-14"

BASE = "https://dap.ceda.ac.uk/neodc/esacci/permafrost/data/permafrost_extent/L4/area4/pp/v05.0"
CATALOGUE = "https://catalogue.ceda.ac.uk/uuid/d235665772ec4b558e9a89ac85595e71"
OSC = "https://opensciencedata.esa.int/"
YEARS = tuple(range(2019, 2024))
REGIONS = {
    "nh": ("northern_hemisphere", "AREA4", 25.0, 85.0),
    "ant": ("Antarctica", "AREA27", -85.0, -60.0),
}
FILL = 255


def url_for(region: str, year: int) -> str:
    folder, area, _, _ = REGIONS[region]
    return "%s/%s/%d/ESACCI-PERMAFROST-L4-PFR-MODISLST_CRYOGRID-%s_PP-%d-fv05.0.nc" % (BASE, folder, year, area, year)


def region_of(lat: float) -> Optional[str]:
    for key, (_, _, lo, hi) in REGIONS.items():
        if lo <= lat <= hi:
            return key
    return None


def sample(path: Path, lat: float, lon: float) -> Tuple[Optional[float], Optional[float]]:
    """(centre cell %, 3x3 mean %) of PFR, None on fill."""
    import rasterio

    with rasterio.open("netcdf:%s:PFR" % path) as ds:
        row, col = ds.index(lon, lat)
        r0, c0 = max(row - 1, 0), max(col - 1, 0)
        block = ds.read(1, window=((r0, min(row + 2, ds.height)), (c0, min(col + 2, ds.width))))
        centre = block[row - r0, col - c0]
    valid = [float(v) for v in block.ravel() if int(v) != FILL]
    c = None if int(centre) == FILL else float(centre)
    return c, (sum(valid) / len(valid) if valid else None)


def fetch() -> None:
    import httpx

    CACHE.mkdir(parents=True, exist_ok=True)
    sites = json.loads(CATALOG.read_text(encoding="utf-8"))["sites"]
    rows = []
    for region in REGIONS:
        for year in YEARS:
            path = CACHE / Path(url_for(region, year)).name
            if not path.exists():
                r = httpx.get(url_for(region, year), timeout=600.0, follow_redirects=True)
                r.raise_for_status()
                path.write_bytes(r.content)
            for s in sites:
                if region_of(s["lat"]) != region:
                    continue
                centre, neigh = sample(path, s["lat"], s["lon"])
                rows.append({"site_id": s["id"], "region": region, "year": year,
                             "pfr_centre_pct": "" if centre is None else centre,
                             "pfr_3x3_pct": "" if neigh is None else round(neigh, 2)})
    with SITES_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["site_id", "region", "year", "pfr_centre_pct", "pfr_3x3_pct"])
        w.writeheader()
        w.writerows(rows)


def _f(x: str) -> Optional[float]:
    return float(x) if x not in ("", None) else None


def pfr_stats(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, object]]:
    acc: Dict[str, Dict[str, list]] = {}
    for r in rows:
        a = acc.setdefault(r["site_id"], {"centre": [], "neigh": [], "years": 0})
        a["years"] += 1
        c, n = _f(r["pfr_centre_pct"]), _f(r["pfr_3x3_pct"])
        if c is not None:
            a["centre"].append(c)
        if n is not None:
            a["neigh"].append(n)
    out = {}
    for sid, a in acc.items():
        out[sid] = {
            "years": a["years"], "n_centre": len(a["centre"]),
            "centre_mean": (sum(a["centre"]) / len(a["centre"])) if a["centre"] else None,
            "neigh_mean": (sum(a["neigh"]) / len(a["neigh"])) if a["neigh"] else None,
        }
    return out


SOURCE = ("ESA Permafrost_cci, permafrost extent L4 v5.0 (PFR, %% de área con permafrost, grilla 0,01°, anual; "
          "MODIS LST + ERA5 + CryoGrid), vía CEDA (listado en el ESA Open Science Catalog). Celda del punto, "
          "media 2019–2023; consultado %s (America/Buenos_Aires). %s %s %s" % (RETRIEVED, CATALOGUE, BASE, OSC))


def permafrost_row(site: Dict, stat: Optional[Dict]) -> Dict:
    base = {"site_id": site["id"], "feature": "permafrost_fraction", "unit": "fraction_0_1",
            "source": SOURCE, "method": METHOD, "retrieved_at": RETRIEVED}
    if region_of(site["lat"]) is None:
        return {**base, "value": None, "quality": "unavailable", "is_real": False,
                "note": "Fuera de la cobertura de Permafrost_cci v5.0 (solo hemisferio norte 25–85° N y Antártida): a completar con otro producto (p. ej. permafrost de montaña andino)."}
    if not stat or stat["centre_mean"] is None:
        return {**base, "value": None, "quality": "unavailable", "is_real": False,
                "note": "Celda sin dato (relleno: océano o capa de hielo) en 2019–2023: a completar."}
    note = "Media de %d años; media del entorno 3x3 (~3 km): %s %%. Permafrost es suelo ≤ 0 °C por ≥ 2 años: indica estabilidad térmica del hielo, no su presencia." % (
        stat["n_centre"], "n/d" if stat["neigh_mean"] is None else "%.1f" % stat["neigh_mean"])
    return {**base, "value": round(stat["centre_mean"] / 100.0, 4), "quality": "measured", "is_real": True,
            "note": note, "comparable": False}


def build() -> List[Dict]:
    sites = json.loads(CATALOG.read_text(encoding="utf-8"))["sites"]
    with SITES_CSV.open(encoding="utf-8") as fh:
        stats = pfr_stats(csv.DictReader(fh))
    return [permafrost_row(s, stats.get(s["id"])) for s in sites]


def write(rows: List[Dict]) -> None:
    """Replace this script's rows in vo-hielo.jsonl, keep the other scripts' rows."""
    keep = []
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("method") != METHOD:
                keep.append(line)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(l + "\n" for l in keep) + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main(argv: List[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "fetch":
        fetch()
        print("ok", SITES_CSV)
    elif cmd == "build":
        rows = build()
        write(rows)
        print("filas:", len(rows), "->", OUT)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
