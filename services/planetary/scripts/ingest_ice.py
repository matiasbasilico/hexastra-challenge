#!/usr/bin/env python3
"""Water-ice magnitudes for the Moon and Mars targets (Vo).

    services/.venv/bin/python services/planetary/scripts/ingest_ice.py fetch   # PDS -> data/raw (small subsets)
    services/.venv/bin/python services/planetary/scripts/ingest_ice.py build   # data/raw -> rows (used by ingest_vo_hielo.py)

Moon — LRO Diviner Polar Resource Products v2 (LRO-L-DLRE-5-PRP-V2.0, PDS
Geosciences Node), south polar table. Each row is a ~240 m triangle with
`ice_depth`: depth (m) at which water ice would sublimate at 1 kg m^-2 per
billion years; 0 = stable at the surface; -999 = deeper than 2.8738 m (not
stable in the modelled column). Per target we take the triangles whose centre
lies within RADIUS_KM of the site coordinate and report:
  * moon_ice_stable_frac   fraction of triangles with ice stable within 2.87 m
  * moon_ice_surface_frac  fraction with ice stable at the surface (depth 0)
  * moon_ice_depth_min_m   shallowest stability depth in the circle
Sites outside the PRP coverage (latitude > -75.9) stay null.

Mars — 2001 Mars Odyssey GRS element concentrations (ODY-M-GRS-5-ELEMENTS-V1.0,
Boynton et al. 2007), smoothed 5x5 deg H2O table, weight percent. The value of
the 5 deg bin that contains the site; bins poleward of +-57.5 are not in the
product (9999.999) and stay null.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
PLANETARY = HERE.parent
CATALOG = PLANETARY / "data" / "catalog.json"
RAW = PLANETARY / "data" / "raw"
MOON_RAW = RAW / "diviner_prp_south_sites.csv"
MARS_RAW = RAW / "ody_grs_h2o_sr_5x5.tab"
CACHE = RAW / "cache"  # full PDS downloads, not versioned

PRP_URL = "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/dlre_prp_south.tab"
PRP_LABEL = "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/dlre_prp_south.xml"
GRS_URL = "https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.tab"
GRS_LABEL = "https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.lbl"

MOON_R_KM = 1737.4
RADIUS_KM = 5.0       # analysis circle (site scale: a rim or a crater floor)
SEARCH_KM = 10.0      # what fetch keeps, so RADIUS_KM can be revisited offline
PRP_MIN_LAT = -75.9   # northern edge of the south PRP table
ICE_EXCLUDE = -999.0
MIN_TRIANGLES = 20
GRS_NA = 9999.0


def load_targets(body: str) -> List[Dict]:
    return [s for s in json.loads(CATALOG.read_text(encoding="utf-8"))["sites"] if s["body"] == body]


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float, radius: float = MOON_R_KM) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return radius * math.acos(max(-1.0, min(1.0, c)))


# ---------------------------------------------------------------- Moon

def parse_prp_line(line: str) -> Optional[Tuple[float, float, float, float, float]]:
    """(clat, clon, temp_avg, temp_max, ice_depth) or None for the header."""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != 15:
        return None
    try:
        clon, clat = float(parts[9]), float(parts[10])
        return clat, clon, float(parts[12]), float(parts[13]), float(parts[14])
    except ValueError:
        return None


def filter_prp(lines: Iterable[str], targets: List[Dict], search_km: float = SEARCH_KM) -> Iterator[Dict]:
    polar = [t for t in targets if t["lat"] <= PRP_MIN_LAT + 1.0]
    deg = math.degrees(search_km / MOON_R_KM)
    for line in lines:
        rec = parse_prp_line(line)
        if rec is None:
            continue
        clat, clon, tavg, tmax, depth = rec
        for t in polar:
            if abs(clat - t["lat"]) > deg:
                continue
            d = great_circle_km(t["lat"], t["lon"], clat, clon)
            if d <= search_km:
                yield {"site_id": t["id"], "dist_km": round(d, 4), "clat": clat, "clon": clon,
                       "temp_avg_k": tavg, "temp_max_k": tmax, "ice_depth_m": depth}


def download_resumable(url: str, path: Path, attempts: int = 30) -> Path:
    """Download with HTTP Range resume; the PDS server resets long transfers."""
    import time

    import httpx

    path.parent.mkdir(parents=True, exist_ok=True)
    total = int(httpx.head(url, timeout=60.0, follow_redirects=True).headers["content-length"])
    for _ in range(attempts):
        done = path.stat().st_size if path.exists() else 0
        if done >= total:
            return path
        try:
            headers = {"Range": "bytes=%d-" % done}
            with httpx.stream("GET", url, headers=headers, timeout=httpx.Timeout(60.0, read=120.0), follow_redirects=True) as r:
                r.raise_for_status()
                with path.open("ab") as fh:
                    for chunk in r.iter_bytes(1 << 20):
                        fh.write(chunk)
        except httpx.HTTPError:
            time.sleep(5)
    raise RuntimeError("no se pudo completar la descarga de %s" % url)


def fetch_moon() -> int:
    targets = load_targets("moon")
    local = download_resumable(PRP_URL, CACHE / "dlre_prp_south.tab")
    n = 0
    with local.open(encoding="ascii", errors="replace") as src, MOON_RAW.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["site_id", "dist_km", "clat", "clon", "temp_avg_k", "temp_max_k", "ice_depth_m"])
        w.writeheader()
        for row in filter_prp(src, targets):
            w.writerow(row)
            n += 1
    return n


def moon_stats(rows: Iterable[Dict], radius_km: float = RADIUS_KM) -> Dict[str, Dict[str, float]]:
    acc: Dict[str, List[Dict]] = {}
    for r in rows:
        if float(r["dist_km"]) <= radius_km:
            acc.setdefault(r["site_id"], []).append(r)
    out = {}
    for sid, rs in acc.items():
        depths = [float(r["ice_depth_m"]) for r in rs]
        stable = [d for d in depths if d != ICE_EXCLUDE and d >= 0]
        tmax = sorted(float(r["temp_max_k"]) for r in rs)
        out[sid] = {
            "n": len(rs),
            "stable_frac": len(stable) / len(rs),
            "surface_frac": sum(1 for d in stable if d == 0.0) / len(rs),
            "depth_min": min(stable) if stable else None,
            "tmax_median": tmax[len(tmax) // 2],
            "tmax_min": tmax[0],
        }
    return out


# ---------------------------------------------------------------- Mars

def fetch_mars() -> None:
    import httpx

    RAW.mkdir(parents=True, exist_ok=True)
    r = httpx.get(GRS_URL, timeout=120.0, follow_redirects=True)
    r.raise_for_status()
    MARS_RAW.write_bytes(r.content)


def parse_grs(text: str) -> Dict[Tuple[float, float], Tuple[Optional[float], Optional[float]]]:
    grid = {}
    for line in text.splitlines():
        p = line.split()
        if len(p) < 4:
            continue
        lat, lon, conc, sigma = (float(x) for x in p[:4])
        grid[(lat, lon)] = (None if conc >= GRS_NA else conc, None if sigma >= GRS_NA else sigma)
    return grid


def grs_bin(lat: float, lon_east: float) -> Tuple[float, float]:
    """Centre of the 5x5 deg bin that contains the point (longitude 0..360 E)."""
    lon = lon_east % 360.0
    return (math.floor(lat / 5.0) * 5.0 + 2.5, math.floor(lon / 5.0) * 5.0 + 2.5)


# ---------------------------------------------------------------- rows

REPO = PLANETARY.parent.parent
OUT = REPO / "data" / "measurements" / "vo-hielo.jsonl"
METHOD = "services/planetary/scripts/ingest_ice.py"
RETRIEVED = "2026-11-14"
WHEN = "consultado %s (America/Buenos_Aires)" % RETRIEVED
PRP_SOURCE = ("LRO Diviner Polar Resource Products v2 (LRO-L-DLRE-5-PRP-V2.0, Paige et al.), tabla polar sur, "
              "PDS Geosciences Node; triángulos de ~240 m con centro a <= %.0f km del punto; %s. %s %s"
              % (RADIUS_KM, WHEN, PRP_URL, PRP_LABEL))
GRS_SOURCE = ("2001 Mars Odyssey GRS, concentraciones elementales (ODY-M-GRS-5-ELEMENTS-V1.0, Boynton et al. 2007, "
              "doi:10.1029/2007JE002887), tabla H2O suavizada 5x5 grados, bin que contiene el punto; %s. %s %s"
              % (WHEN, GRS_URL, GRS_LABEL))
INDEX_NOTE = "Índice I_hielo (docs/propuestas/vo-hielo.md): fracción del área del sitio donde el hielo de agua es térmicamente estable en el primer ~1–3 m."


def _row(site_id: str, feature: str, value, unit: str, quality: str, source: str, note: Optional[str],
         comparable: Optional[bool] = None) -> Dict:
    row = {"site_id": site_id, "feature": feature, "value": value, "unit": unit, "quality": quality,
           "is_real": value is not None, "source": source, "note": note, "method": METHOD, "retrieved_at": RETRIEVED}
    if comparable is not None:
        row["comparable"] = comparable
    return row


def moon_rows(targets: List[Dict], stats: Dict[str, Dict]) -> List[Dict]:
    out = []
    for t in targets:
        st = stats.get(t["id"])
        if t["lat"] > PRP_MIN_LAT or not st or st["n"] < MIN_TRIANGLES:
            why = ("fuera de la cobertura del PRP polar sur (lat > %.1f)" % PRP_MIN_LAT if t["lat"] > PRP_MIN_LAT
                   else "menos de %d triángulos en el círculo" % MIN_TRIANGLES)
            note = "Sin dato Diviner PRP: %s; a completar (p. ej. con LEND o neutrones de Lunar Prospector)." % why
            for fid, unit in (("moon_ice_stable_frac", "fraction_0_1"), ("moon_ice_surface_frac", "fraction_0_1"),
                              ("moon_ice_depth_min_m", "m"), ("water_ice_indicator", "index_0_1")):
                out.append(_row(t["id"], fid, None, unit, "unavailable", PRP_SOURCE, note, False if fid != "water_ice_indicator" else None))
            continue
        ctx = "n=%d triángulos; Tmax mediana %.1f K (mín %.1f K)." % (st["n"], st["tmax_median"], st["tmax_min"])
        out.append(_row(t["id"], "moon_ice_stable_frac", round(st["stable_frac"], 4), "fraction_0_1", "derived", PRP_SOURCE,
                        "Fracción de triángulos con ice_depth en [0, 2,87 m]. " + ctx, False))
        out.append(_row(t["id"], "moon_ice_surface_frac", round(st["surface_frac"], 4), "fraction_0_1", "derived", PRP_SOURCE,
                        "Fracción de triángulos con ice_depth = 0 (hielo estable en superficie). " + ctx, False))
        if st["depth_min"] is None:
            out.append(_row(t["id"], "moon_ice_depth_min_m", None, "m", "unavailable", PRP_SOURCE,
                            "Ningún triángulo con hielo estable en los 2,87 m modelados: no hay profundidad que reportar (a completar si se usa un modelo más profundo). " + ctx, False))
        else:
            out.append(_row(t["id"], "moon_ice_depth_min_m", round(st["depth_min"], 4), "m", "derived", PRP_SOURCE,
                            "Profundidad de estabilidad más somera del círculo. " + ctx, False))
        out.append(_row(t["id"], "water_ice_indicator", round(st["stable_frac"], 4), "index_0_1", "derived", PRP_SOURCE,
                        INDEX_NOTE + " Luna: = moon_ice_stable_frac.", True))
    return out


def mars_rows(targets: List[Dict], grid: Dict) -> List[Dict]:
    out = []
    for t in targets:
        key = grs_bin(t["lat"], t["lon"])
        conc, sigma = grid.get(key, (None, None))
        if conc is None:
            out.append(_row(t["id"], "mars_grs_h2o_wt_pct", None, "wt_pct", "unavailable", GRS_SOURCE,
                            "Bin %s sin dato en el producto (latitud alta o sin cobertura): a completar." % (key,), False))
        else:
            out.append(_row(t["id"], "mars_grs_h2o_wt_pct", conc, "wt_pct", "measured", GRS_SOURCE,
                            "Bin centrado en lat %.1f, lon %.1f E; sigma %.3f wt%%. Hidrógeno equivalente a agua en el primer metro (incluye minerales hidratados; a estas latitudes no implica hielo)." % (key[0], key[1], sigma or float("nan")), False))
        out.append(_row(t["id"], "water_ice_indicator", None, "index_0_1", "unavailable", GRS_SOURCE,
                        INDEX_NOTE + " Marte: el GRS mide hidrógeno, no estabilidad del hielo; falta un mapa de estabilidad o de consistencia de hielo "
                        "(p. ej. SWIM, Morgan et al. 2021) para este punto: a completar."))
    return out


def build() -> List[Dict]:
    with MOON_RAW.open(encoding="utf-8") as fh:
        mstats = moon_stats(csv.DictReader(fh))
    grid = parse_grs(MARS_RAW.read_text(encoding="ascii"))
    return moon_rows(load_targets("moon"), mstats) + mars_rows(load_targets("mars"), grid)


def write(rows: List[Dict]) -> None:
    """Replace this script's rows in vo-hielo.jsonl, keep the other scripts' rows."""
    keep = []
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("method") != METHOD:
                keep.append(line)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(l + "\n" for l in keep) + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


# ---------------------------------------------------------------- CLI

def main(argv: List[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "fetch":
        fetch_mars()
        print("mars ok", MARS_RAW)
        print("moon filas", fetch_moon(), MOON_RAW)
        return 0
    if cmd == "fetch-mars":
        fetch_mars()
        return 0
    if cmd == "build":
        rows = build()
        write(rows)
        print("filas:", len(rows), "->", OUT)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
