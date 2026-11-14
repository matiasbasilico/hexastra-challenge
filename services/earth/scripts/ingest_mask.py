#!/usr/bin/env python3
"""Viability mask inputs for the 60 Earth sites: NDVI and continental liquid water.

Writes data/measurements/vo-mascara.jsonl. Two steps:

    services/.venv/bin/python services/earth/scripts/ingest_mask.py fetch   # AppEEARS tasks -> raw CSVs
    services/.venv/bin/python services/earth/scripts/ingest_mask.py build   # raw CSVs -> jsonl

Definitions (also in docs/propuestas/vo-hielo.md, Parte A):

* ndvi: MODIS Terra MOD13Q1 v061 (250 m, 16-day), pixel that contains the site
  coordinate, 2015-01-01..2024-12-31. Mean of the composites with
  pixel_reliability == 0 ("good data"). Needs at least MIN_GOOD composites,
  otherwise null.
* has_liquid_water: MODIS MOD44W v061 (250 m, yearly land/water mask), pixel
  that contains the site coordinate, years 2015..2023. 1 if the pixel is
  classified as inland water (seven_class 3 shallow inland, 5 deep inland) in at
  least half of the years; 0 otherwise. Ocean classes never count (the mask is
  about continental water). Ephemeral water (class 4) and water in the 3x3
  neighbourhood (~375 m) are reported in the note, not in the value.

No value is invented: a site without enough valid data stays null.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

HERE = Path(__file__).resolve().parent
EARTH_ROOT = HERE.parent
REPO = EARTH_ROOT.parent.parent
if str(EARTH_ROOT) not in sys.path:
    sys.path.insert(0, str(EARTH_ROOT))

CATALOG = EARTH_ROOT / "data" / "catalog.json"
RAW = EARTH_ROOT / "data" / "raw" / "appeears"
OUT = REPO / "data" / "measurements" / "vo-mascara.jsonl"
METHOD = "services/earth/scripts/ingest_mask.py"
RETRIEVED = "2026-11-14"

NDVI_PRODUCT = "MOD13Q1.061"
NDVI_LAYERS = ("_250m_16_days_NDVI", "_250m_16_days_pixel_reliability")
NDVI_START, NDVI_END = "01-01-2015", "12-31-2024"
MIN_GOOD = 23  # at least one year's worth of good composites

WATER_PRODUCT = "MOD44W.061"
WATER_LAYERS = ("water_mask", "seven_class")
WATER_START, WATER_END = "01-01-2015", "12-31-2023"
INLAND_WATER = {3, 5}
EPHEMERAL = {4}
PIXEL_M = 231.66  # MODIS 250 m sinusoidal pixel
EARTH_R = 6371008.8

URL_APPEEARS = "https://appeears.earthdatacloud.nasa.gov/"
URL_MOD13Q1 = "https://doi.org/10.5067/MODIS/MOD13Q1.061"
URL_MOD44W = "https://doi.org/10.5067/MODIS/MOD44W.061"


def load_sites() -> List[Dict]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))["sites"]


def neighbourhood(site: Dict) -> List[Dict[str, object]]:
    """Centre + 8 neighbours one MODIS pixel apart (ids site__dx_dy)."""
    lat, lon = float(site["lat"]), float(site["lon"])
    dlat = math.degrees(PIXEL_M / EARTH_R)
    dlon = dlat / max(math.cos(math.radians(lat)), 1e-6)
    out = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out.append({
                "id": "%s__%d_%d" % (site["id"], dx, dy),
                "latitude": round(lat + dy * dlat, 6),
                "longitude": round(lon + dx * dlon, 6),
            })
    return out


def fetch() -> None:
    from clients import appeears

    RAW.mkdir(parents=True, exist_ok=True)
    sites = load_sites()
    token = appeears.login()
    ndvi_pts = [{"id": s["id"], "latitude": s["lat"], "longitude": s["lon"]} for s in sites]
    water_pts = [p for s in sites for p in neighbourhood(s)]
    specs = {
        "ndvi": ("hexastra-vo-ndvi", NDVI_PRODUCT, NDVI_LAYERS, ndvi_pts, NDVI_START, NDVI_END),
        "water": ("hexastra-vo-water", WATER_PRODUCT, WATER_LAYERS, water_pts, WATER_START, WATER_END),
    }
    tasks = {}
    for name, spec in specs.items():
        if (RAW / ("%s.csv" % name)).exists():
            continue
        tasks[name] = appeears.find_task(token, spec[0]) or appeears.submit_point_task(token, *spec)
    for name, task_id in tasks.items():
        appeears.wait(token, task_id)
        (RAW / ("%s.csv" % name)).write_text(appeears.download_results_csv(token, task_id), encoding="utf-8")
        (RAW / ("%s.task.json" % name)).write_text(json.dumps({"task_id": task_id}), encoding="utf-8")
        print("ok", name, task_id)


def _col(row: Dict[str, str], suffix: str) -> Optional[str]:
    for k, v in row.items():
        if k.endswith(suffix):
            return v
    return None


def _float(x: Optional[str]) -> Optional[float]:
    try:
        v = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def ndvi_stats(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    """Per site: mean/median NDVI over composites with pixel_reliability == 0."""
    vals: Dict[str, List[float]] = defaultdict(list)
    total: Dict[str, int] = defaultdict(int)
    for r in rows:
        sid = r["ID"]
        total[sid] += 1
        rel = _float(_col(r, "_250m_16_days_pixel_reliability"))
        ndvi = _float(_col(r, "_250m_16_days_NDVI"))
        if rel == 0 and ndvi is not None and -1.0 <= ndvi <= 1.0:
            vals[sid].append(ndvi)
    out = {}
    for sid, n in total.items():
        v = sorted(vals.get(sid, []))
        stat = {"n_total": n, "n_good": len(v)}
        if v:
            stat["mean"] = sum(v) / len(v)
            stat["median"] = v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2
            stat["p90"] = v[min(len(v) - 1, int(0.9 * len(v)))]
        out[sid] = stat
    return out


def water_stats(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, object]]:
    """Per site: yearly seven_class of the centre pixel and of the 3x3 neighbourhood."""
    by_site: Dict[str, Dict[str, object]] = defaultdict(lambda: {"centre": {}, "neigh": defaultdict(set)})
    for r in rows:
        pid = r["ID"]
        sid, _, offset = pid.rpartition("__")
        cls = _float(_col(r, "_seven_class"))
        if cls is None or cls >= 253:
            continue
        year = r["Date"][:4]
        entry = by_site[sid]
        if offset == "0_0":
            entry["centre"][year] = int(cls)  # type: ignore[index]
        entry["neigh"][year].add(int(cls))  # type: ignore[index]
    return by_site


def water_flag(centre: Dict[str, int]) -> Optional[int]:
    if not centre:
        return None
    inland = sum(1 for c in centre.values() if c in INLAND_WATER)
    return 1 if inland * 2 >= len(centre) else 0


def _row(site_id, feature, value, unit, quality, source, note):
    return {
        "site_id": site_id, "feature": feature, "value": value, "unit": unit,
        "quality": quality, "is_real": value is not None, "source": source,
        "note": note, "method": METHOD, "retrieved_at": RETRIEVED,
    }


def ndvi_row(site_id: str, stat: Optional[Dict]) -> Dict:
    src = ("MODIS Terra MOD13Q1 v061 (250 m, 16 días) vía NASA AppEEARS (Earthdata), píxel del punto, "
           "2015-01-01..2024-12-31, media de compuestos con pixel_reliability = 0; consultado %s "
           "(America/Buenos_Aires). %s %s" % (RETRIEVED, URL_APPEEARS, URL_MOD13Q1))
    if not stat or stat.get("n_good", 0) < MIN_GOOD:
        n = (stat or {}).get("n_good", 0)
        return _row(site_id, "ndvi", None, "unitless", "unavailable", src,
                    "Solo %d compuestos de buena calidad (mínimo %d): a completar con otro criterio o producto." % (n, MIN_GOOD))
    note = "n_good=%d de %d compuestos; mediana=%.3f; p90=%.3f." % (
        stat["n_good"], stat["n_total"], stat["median"], stat["p90"])
    return _row(site_id, "ndvi", round(stat["mean"], 4), "unitless", "measured", src, note)


def water_row(site_id: str, stat: Optional[Dict]) -> Dict:
    src = ("MODIS MOD44W v061 (máscara tierra/agua anual, 250 m) vía NASA AppEEARS (Earthdata), capa seven_class, "
           "píxel del punto, años 2015..2023; 1 si es agua continental (clase 3 o 5) en al menos la mitad de los años; "
           "consultado %s (America/Buenos_Aires). %s %s" % (RETRIEVED, URL_APPEEARS, URL_MOD44W))
    centre = (stat or {}).get("centre") or {}
    flag = water_flag(centre)
    if flag is None:
        return _row(site_id, "has_liquid_water", None, "boolean_as_0_1", "unavailable", src,
                    "Sin clase válida de MOD44W en el píxel: a completar.")
    years = sorted(centre)
    classes = [centre[y] for y in years]
    neigh = stat["neigh"]
    neigh_inland = sum(1 for y in years if neigh.get(y, set()) & INLAND_WATER)
    ephemeral = sum(1 for c in classes if c in EPHEMERAL)
    note = "Clases seven_class del píxel %s-%s: %s. Años con agua continental en el entorno 3x3 (~375 m): %d de %d. Años efímeros en el píxel: %d." % (
        years[0], years[-1], ",".join(str(c) for c in classes), neigh_inland, len(years), ephemeral)
    return _row(site_id, "has_liquid_water", flag, "boolean_as_0_1", "measured", src, note)


def build() -> List[Dict]:
    from clients.appeears import parse_csv

    sites = load_sites()
    ndvi = ndvi_stats(parse_csv((RAW / "ndvi.csv").read_text(encoding="utf-8")))
    water = water_stats(parse_csv((RAW / "water.csv").read_text(encoding="utf-8")))
    rows = []
    for s in sites:
        rows.append(ndvi_row(s["id"], ndvi.get(s["id"])))
        rows.append(water_row(s["id"], water.get(s["id"])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return rows


def main(argv: List[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "build"
    if cmd == "fetch":
        fetch()
    elif cmd == "build":
        rows = build()
        print("filas:", len(rows), "->", OUT)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
