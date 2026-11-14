#!/usr/bin/env python3
"""T and E of the 11 planetary destinations that still lack them -> data/measurements/te-planetario.jsonl.

Mars (jezero, gale, medusae-fossae, pavonis-mons, meridiani):
  T  HRSC-MOLA blended DEM 200 m (USGS), 7x7 grid at 120 m  (scripts/ingest_dem.py::measure)
  E  Mars Climate Database v6.2, air at 2 m, Ls-weighted      (scripts/ingest_climate.py::mars_stats)
Moon south pole (shackleton-rim, haworth, malapert, de-gerlache, amundsen, nobile):
  T  LOLA GDR polar stereographic DEM LDEM_80S_20M (PDS Geosciences), 7x7 grid at 120 m
  E  Diviner polar cumulative product (PCP) Tbol 240 m x 96 local-time bins, summer + winter
  illumination_pct  LOLA average illumination AVGVISIB_75S_120M (Mazarico et al. 2011)

It never overwrites a value of the base catalog (those are only reported) and writes a
null row with "a completar" for anything that could not be read.

Usage (from the repo root):
    services/.venv/bin/python services/planetary/scripts/ingest_te_planetario.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parent.parent
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from polar import (  # noqa: E402
    MOON_RADIUS_M, PCP_RECORD_BYTES, local_grid_points, parse_pcp_line, pcp_bin_value, pcp_summary,
    polar_xy_south,
)
from terrain import GRID_N, SPACING_M, bilinear, sample_grid, terrain_metrics  # noqa: E402
from climate import diurnal_stats  # noqa: E402

CATALOG = ROOT / "data" / "catalog.json"
OUT = REPO / "data" / "measurements" / "te-planetario.jsonl"
METHOD = "services/planetary/scripts/ingest_te_planetario.py"
RETRIEVED = "2026-11-14"
WHEN = "14 de noviembre de 2026 (America/Buenos_Aires)"
UA = {"User-Agent": "Mozilla/5.0 (HexastraAnalogos/0.1; NASA Space Apps 2026 prototype)"}

MARS_IDS = ["jezero", "gale", "medusae-fossae", "pavonis-mons", "meridiani"]
MOON_IDS = ["shackleton-rim", "haworth", "malapert", "de-gerlache", "amundsen", "nobile"]

PDS_LOLA = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/"
POLAR_DEM = PDS_LOLA + "data/lola_gdr/polar/img/ldem_80s_20m.lbl"
ILLUM = PDS_LOLA + "extras/illumination/img/avgvisib_75s_120m_201608.lbl"
GLOBAL_DEM = "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif"
PCP = ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
       "data_derived_pcp/diurnal/ltim/pols/pcp_avg_tbol_pols_%s_ltim%02d_240.tab")
SEASONS = {"sum": "verano austral (subsolar sur)", "win": "invierno austral (subsolar norte)"}
LT_BINS = 96
MIN_VALID_BINS = 48
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.lbl,.img,.IMG"}


def row(site: str, feature: str, value: Optional[float], unit: str, quality: str, source: str,
        note: Optional[str], comparable: bool = True) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "site_id": site, "feature": feature, "value": value, "unit": unit,
        "quality": quality if value is not None else "placeholder", "is_real": value is not None,
        "source": source, "note": note, "comparable": comparable, "method": METHOD,
        "retrieved_at": RETRIEVED,
    }
    return out


def null_row(site: str, feature: str, unit: str, why: str, source: str = "sin fuente verificada") -> Dict[str, Any]:
    return row(site, feature, None, unit, "placeholder", source, "%s (a completar)" % why)


def r2(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v, 2)


# ----------------------------------------------------------------------------- terrain

def terrain_rows(site: Dict[str, Any], m: Dict[str, Optional[float]], dem_name: str, url: str,
                 datum: str, native_m: float, extra: str) -> List[Dict[str, Any]]:
    base = ("%s, leído por HTTP (GDAL /vsicurl/) el %s: grilla %sx%s a %s m, valores bilineales, "
            "mismas fórmulas que los candidatos terrestres (services/earth/clients/opentopo.py). %s %s"
            % (dem_name, WHEN, GRID_N, GRID_N, int(SPACING_M), url, extra)).strip()
    scale_note = None
    if native_m > SPACING_M * 1.2:
        scale_note = ("El DEM nativo es de %d m/píxel y la grilla de %d m: el relieve fino queda suavizado "
                      "respecto de ASTER 30 m en la Tierra." % (int(native_m), int(SPACING_M)))
    rows = [row(site["id"], "elevation", r2(m["elevation_m"]), "m", "measured",
                base + " Cota respecto de %s; no entra en S_T." % datum, None)]
    for feature, key, unit, definition in (
        ("relative_relief", "relative_relief_m", "m", "Relieve relativo = máx − mín de la grilla."),
        ("slope", "slope_deg", "deg", "Pendiente del centro con los cuatro vecinos cardinales."),
        ("roughness", "roughness_m", "m", "Rugosidad = desvío estándar muestral de la grilla."),
    ):
        v = r2(m[key])
        if v is None:
            rows.append(null_row(site["id"], feature, unit, "lectura del DEM sin datos suficientes", url))
        else:
            rows.append(row(site["id"], feature, v, unit, "derived", base + " " + definition, scale_note))
    return rows


def mars_terrain(site: Dict[str, Any]) -> Tuple[Dict[str, Optional[float]], List[Dict[str, Any]]]:
    import ingest_dem

    m = ingest_dem.measure(site)
    d = ingest_dem.DEMS["mars"]
    rows = terrain_rows(site, m, d["name"], d["url"], d["datum"], d["native_m"], "")
    return m, rows


def _open(url: str):
    import rasterio

    for k, v in GDAL_ENV.items():
        os.environ[k] = v
    return rasterio.open("/vsicurl/" + url)


def _reader(ds, scale: float):
    from rasterio.windows import Window

    nodata = ds.nodata

    def read_window(col: int, row_: int, width: int, height: int) -> List[List[Optional[float]]]:
        arr = ds.read(1, window=Window(col, row_, width, height))
        return [[None if (nodata is not None and v == nodata) else float(v) * scale for v in line]
                for line in arr.tolist()]

    return read_window


def polar_pixel(ds):
    inv = ~ds.transform

    def to_pixel(lat: float, lon: float) -> Tuple[float, float]:
        x, y = polar_xy_south(lat, lon)
        col, row_ = inv * (x, y)
        return col - 0.5, row_ - 0.5

    return to_pixel


def moon_terrain(site: Dict[str, Any]) -> Tuple[Dict[str, Optional[float]], List[Dict[str, Any]]]:
    with _open(POLAR_DEM) as ds:
        scale = (ds.scales or (1.0,))[0]  # DN * 0.5 = height above the 1737.4 km sphere (offset not added)
        z = sample_grid(local_grid_points(site["lat"], site["lon"]), polar_pixel(ds), _reader(ds, scale))
    m = terrain_metrics(z)
    extra = ("DEM polar estereográfico (esfera lunar de 1.737,4 km, verdadero en el polo) de 20 m/píxel; la grilla "
             "se arma en metros este/norte locales por círculo máximo, porque una grilla lat/lon se degenera en −90°.")
    rows = terrain_rows(
        site, m, "LRO LOLA GDR polar LDEM_80S_20M (PDS Geosciences, producto con datos LOLA preliminares según su label)",
        POLAR_DEM, "esfera lunar de 1.737,4 km", 20.0, extra)
    return m, rows


def moon_global_elevation(site: Dict[str, Any]) -> Optional[float]:
    """Independent check: elevation from the global 118 m LDEM (valid at -85 deg and below only as a sanity check)."""
    from rasterio.windows import Window

    with _open(GLOBAL_DEM) as ds:
        scale = (ds.scales or (1.0,))[0] or 1.0
        offset = (ds.offsets or (0.0,))[0] or 0.0
        x, y = MOON_RADIUS_M * math.radians(site["lon"]), MOON_RADIUS_M * math.radians(site["lat"])
        col, row_ = ~ds.transform * (x, y)
        v = ds.read(1, window=Window(int(col), int(row_), 1, 1))[0, 0]
    return float(v) * scale + offset


# ----------------------------------------------------------------------------- illumination

def moon_illumination(site: Dict[str, Any]) -> Optional[float]:
    with _open(ILLUM) as ds:
        scale = (ds.scales or (1.0,))[0]
        v = sample_grid([(site["lat"], site["lon"])], polar_pixel(ds), _reader(ds, scale))[0]
    return None if v is None else 100.0 * v


def illumination_row(site: Dict[str, Any], pct: Optional[float]) -> Dict[str, Any]:
    if pct is None:
        return null_row(site["id"], "illumination_pct", "percent", "el mapa de iluminación no devolvió dato", ILLUM)
    src = ("LRO LOLA, mapa de iluminación promedio AVGVISIB_75S_120M (2016-08, 120 m/píxel, estereográfico polar; calculado "
           "sobre LDEM_75S_120M, Mazarico et al. 2011, Icarus 211, 1066–1081). Valor = fracción de pasos de tiempo con el "
           "píxel iluminado por cualquier fracción del disco solar (DN × 4e-5) × 100, interpolación bilineal en el punto. "
           "PDS Geosciences, extras/illumination, consultado el %s. %s" % (WHEN, ILLUM))
    note = ("Iluminación promedio por modelo sobre el DEM, no una medición directa; el rango de simulación va de 2009 a 2013 y "
            "algunos mapas muestran artefactos lineales del DEM (readme del producto). El producto no es de soporte PDS.")
    return row(site["id"], "illumination_pct", round(pct, 2), "percent", "modeled", src, note)


# ----------------------------------------------------------------------------- Mars E

def mars_climate(site: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    import ingest_climate

    s = ingest_climate.mars_stats(site["lat"], site["lon"])
    applied = ingest_climate.apply_mars({"features": {}}, s)["features"]
    rows = []
    for feature in ("temp_mean", "temp_diurnal_range"):
        f = applied[feature]
        why = ("No se encontró en PDS una climatología gridded de temperatura del AIRE a 2 m comparable con ERA5; REMS y MEDA "
               "son mediciones in situ solo en Gale y Jezero. Se usó la Mars Climate Database v6.2 (modelo con datos de "
               "TES/MCS), validada en Jezero contra MEDA. ")
        rows.append(row(site["id"], feature, f["value"], "degC", "modeled", f["source"], why + f["note"]))
    return s, rows


# ----------------------------------------------------------------------------- Moon E (Diviner PCP)

class PcpFile:
    """One Diviner PCP table read with HTTP range requests."""

    def __init__(self, client: httpx.Client, url: str) -> None:
        self.client, self.url = client, url
        head = self._retry(lambda: self.client.head(url, follow_redirects=True))
        self.n_rows = int(head.headers["content-length"]) // PCP_RECORD_BYTES - 1  # minus the header record

    def _retry(self, fn):
        last: Optional[Exception] = None
        for _ in range(4):
            try:
                r = fn()
                r.raise_for_status()
                return r
            except Exception as exc:  # network hiccup: retry, then fail loudly
                last = exc
        raise RuntimeError("%s: %s" % (self.url, last))

    def read_rows(self, first: int, count: int) -> List[Tuple[float, float, float]]:
        start = (first + 1) * PCP_RECORD_BYTES
        end = start + count * PCP_RECORD_BYTES - 1
        r = self._retry(lambda: self.client.get(self.url, headers={"Range": "bytes=%d-%d" % (start, end)},
                                                follow_redirects=True))
        parsed = [parse_pcp_line(line) for line in r.text.splitlines()]
        rows = [p for p in parsed if p is not None]
        if len(rows) != count:
            raise RuntimeError("%s: expected %d rows at %d, got %d" % (self.url, count, first, len(rows)))
        return rows


def moon_climate_series(client: httpx.Client, site: Dict[str, Any], pool: ThreadPoolExecutor) -> Dict[str, List[Optional[float]]]:
    x, y = polar_xy_south(site["lat"], site["lon"])
    xn, yn = x / MOON_RADIUS_M, y / MOON_RADIUS_M

    def one(args: Tuple[str, int]) -> Optional[float]:
        season, ltim = args
        f = PcpFile(client, PCP % (season, ltim))
        return pcp_bin_value(xn, yn, f.n_rows, f.read_rows)

    out: Dict[str, List[Optional[float]]] = {}
    for season in SEASONS:
        out[season] = list(pool.map(one, [(season, k) for k in range(1, LT_BINS + 1)]))
    return out


def moon_climate_rows(site: Dict[str, Any], series: Dict[str, List[Optional[float]]]) -> Tuple[Optional[Dict[str, float]], List[Dict[str, Any]]]:
    sid = site["id"]
    valid = {k: sum(v is not None for v in vals) for k, vals in series.items()}
    if min(valid.values()) < MIN_VALID_BINS:
        why = "el bin de 240 m tiene menos de %d de %d horas locales con dato (%s)" % (MIN_VALID_BINS, LT_BINS, valid)
        return None, [null_row(sid, "temp_mean", "degC", why, PCP % ("sum", 1)),
                      null_row(sid, "temp_diurnal_range", "degC", why, PCP % ("sum", 1))]
    s = pcp_summary(series)
    gaps = {k: (v["n_valid"], v["max_gap_bins"]) for k, v in s["seasons"].items()}
    x, y = polar_xy_south(site["lat"], site["lon"])
    src = ("Diviner (LRO) Polar Cumulative Product, bundle lro_diviner_derived1, colección data_derived_pcp/diurnal/ltim/pols, "
           "archivos pcp_avg_tbol_pols_{sum,win}_ltim01…96_240.tab (Tbol bolométrica de superficie, bins de 240 m × 0,25 h de hora "
           "local, observaciones nadir 2009-07-05 a 2019-02-17; Williams et al. 2019, JGR Planets 124, 2505–2521). Bin que contiene "
           "x=%.6f y=%.6f (distancias al polo normalizadas por 1.737,4 km). Leído por rango HTTP (búsqueda binaria sobre registros "
           "de 59 bytes) el %s: https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/diurnal/ltim/pols/ . "
           "Se calcula media y (máx − mín) del ciclo de 96 horas locales por estación (huecos llenados por interpolación lineal "
           "circular) y se promedian verano e invierno australes."
           % (x / MOON_RADIUS_M, y / MOON_RADIUS_M, WHEN))
    note = ("Temperatura de SUPERFICIE (Tbol), no del aire a 2 m como ERA5: la Luna no tiene aire. Promedio simple de las dos "
            "estaciones (subsolar sur y norte, ~mitad del año cada una), sin ponderar. Bins con dato (verano/invierno): %s/%s de %d; "
            "hueco máximo (bins seguidos): %s/%s. La 'hora local' en el polo es un ciclo diurno con el Sol cerca del horizonte."
            % (s["seasons"]["sum"]["n_valid"], s["seasons"]["win"]["n_valid"], LT_BINS, gaps["sum"][1], gaps["win"][1]))
    return s, [
        row(sid, "temp_mean", round(s["mean_K"] - 273.15, 2), "degC", "measured", src, note),
        row(sid, "temp_diurnal_range", round(s["diurnal_range_K"], 2), "degC", "measured", src, note),
    ]


# ----------------------------------------------------------------------------- main

def load_base() -> Dict[str, Dict[str, Any]]:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {s["id"]: s for s in cat["sites"]}


def drop_conflicts(rows: List[Dict[str, Any]], base: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    kept, report = [], []
    for r in rows:
        current = base[r["site_id"]]["features"].get(r["feature"], {}).get("value")
        if current is not None:
            report.append("%s.%s: base=%s | medido=%s %s (no se pisa)" % (r["site_id"], r["feature"], current, r["value"], r["unit"]))
        else:
            kept.append(r)
    return kept, report


def main() -> int:
    base = load_base()
    rows: List[Dict[str, Any]] = []
    checks: List[str] = []
    failures: List[str] = []
    for sid in MARS_IDS:
        site = base[sid]
        try:
            m, rs = mars_terrain(site)
            rows += rs
            checks.append("%s T: elev=%s relief=%s slope=%s rough=%s" % (sid, r2(m["elevation_m"]), r2(m["relative_relief_m"]), r2(m["slope_deg"]), r2(m["roughness_m"])))
        except Exception as exc:
            failures.append("%s T: %s" % (sid, exc))
            rows += [null_row(sid, f, u, "falló la lectura del DEM: %s" % type(exc).__name__) for f, u in
                     (("elevation", "m"), ("relative_relief", "m"), ("slope", "deg"), ("roughness", "m"))]
        try:
            s, rs = mars_climate(site)
            rows += rs
            checks.append("%s E: mean=%.1f K range=%.1f K daily-means %.1f-%.1f K" % (sid, s["mean_K"], s["diurnal_range_K"], s["daily_mean_min_K"], s["daily_mean_max_K"]))
        except Exception as exc:
            failures.append("%s E: %s" % (sid, exc))
            rows += [null_row(sid, f, "degC", "falló la consulta al MCD: %s" % type(exc).__name__) for f in ("temp_mean", "temp_diurnal_range")]
        rows.append(null_row(sid, "illumination_pct", "percent",
                             "no hay un producto oficial de iluminación promedio comparable con el LOLA lunar para Marte"))
    with httpx.Client(timeout=60, headers=UA, limits=httpx.Limits(max_connections=32)) as client, ThreadPoolExecutor(24) as pool:
        for sid in MOON_IDS:
            site = base[sid]
            try:
                m, rs = moon_terrain(site)
                rows += rs
                glob = moon_global_elevation(site)
                checks.append("%s T: elev=%s (LDEM global 118 m: %s) relief=%s slope=%s rough=%s" % (sid, r2(m["elevation_m"]), r2(glob), r2(m["relative_relief_m"]), r2(m["slope_deg"]), r2(m["roughness_m"])))
            except Exception as exc:
                failures.append("%s T: %s" % (sid, exc))
                rows += [null_row(sid, f, u, "falló la lectura del DEM: %s" % type(exc).__name__) for f, u in
                         (("elevation", "m"), ("relative_relief", "m"), ("slope", "deg"), ("roughness", "m"))]
            try:
                pct = moon_illumination(site)
                rows.append(illumination_row(site, pct))
                checks.append("%s illum=%s%%" % (sid, r2(pct)))
            except Exception as exc:
                failures.append("%s illum: %s" % (sid, exc))
                rows.append(null_row(sid, "illumination_pct", "percent", "falló la lectura del mapa: %s" % type(exc).__name__, ILLUM))
            try:
                series = moon_climate_series(client, site, pool)
                s, rs = moon_climate_rows(site, series)
                rows += rs
                if s:
                    checks.append("%s E: mean=%.1f K range=%.1f K max=%.1f K" % (sid, s["mean_K"], s["diurnal_range_K"], s["max_K"]))
                else:
                    checks.append("%s E: null (pocos bins)" % sid)
            except Exception as exc:
                failures.append("%s E: %s" % (sid, exc))
                rows += [null_row(sid, f, "degC", "falló la lectura de Diviner: %s" % type(exc).__name__) for f in ("temp_mean", "temp_diurnal_range")]
    kept, conflicts = drop_conflicts(rows, base)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
    print("\n".join(checks))
    print("\nNO PISADOS (ya tenían valor en el catálogo base):")
    print("\n".join(conflicts) or "  ninguno")
    print("\nFALLAS:", failures or "ninguna")
    print("\n%d filas -> %s" % (len(kept), OUT))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
