#!/usr/bin/env python3
"""Fill temp_mean and temp_diurnal_range for Moon/Mars targets.

Mars: Mars Climate Database web interface (MCD v6.2, climatology average solar
scenario), 2 m above the surface, Ls = all, local time = all.
Moon: Diviner Global Cumulative Product (LRO-L-DLRE-5-GCP-V1.0), bolometric
surface temperature, read with an HTTP range request (96 rows of 113 bytes).

Usage (from services/planetary):
    ../.venv/bin/python scripts/ingest_climate.py marius-hills utopia-planitia arsia-mons
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from climate import (  # noqa: E402
    GCP_LT_BINS, GCP_ROW_BYTES, diurnal_stats, gcp_file_and_offset, mcd_annual_stats,
    parse_gcp_rows, parse_mcd_table,
)

CATALOG = ROOT / "data" / "catalog.json"
WHEN = "14 de noviembre de 2026 (America/Buenos_Aires)"
UA = {"User-Agent": "Mozilla/5.0 (HexastraAnalogos/0.1; NASA Space Apps 2026 prototype)"}
MCD_CGI = "https://www-mars.lmd.jussieu.fr/mcd_python/cgi-bin/mcdcgi.py"
MCD_ROOT = "https://www-mars.lmd.jussieu.fr/mcd_python/"
GCP_BASE = "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/"


def mars_stats(lat: float, lon: float) -> Dict[str, Any]:
    params = {
        "datekeyhtml": 1, "ls": "all", "localtime": "all", "latitude": lat, "longitude": lon,
        "altitude": "2.", "zkey": 3, "spacecraft": "none", "isfixedlt": "off", "dust": 1,
        "hrkey": 1, "averaging": "off", "dpi": 80, "islog": "off", "colorm": "jet",
        "proj": "cyl", "iswind": "off", "var1": "t", "var2": "none", "var3": "none", "var4": "none",
    }
    with httpx.Client(timeout=180, headers=UA, follow_redirects=True) as client:
        page = client.get(MCD_CGI + "?" + urlencode(params)).text
        match = re.search(r"href='\.\./(txt/[0-9a-f]+\.txt)'", page)
        if not match:
            raise RuntimeError("MCD did not return a data file: %s" % page[:200])
        text = client.get(MCD_ROOT + match.group(1)).text
    if "MCD_v6.2" not in text or "Altitude 2.0 m ALS" not in text:
        raise RuntimeError("unexpected MCD header")
    return mcd_annual_stats(parse_mcd_table(text))


def moon_stats(lat: float, lon: float) -> Dict[str, Any]:
    name, offset, centre = gcp_file_and_offset(lat, lon)
    end = offset + GCP_ROW_BYTES * GCP_LT_BINS - 1
    with httpx.Client(timeout=60, headers={**UA, "Range": "bytes=%d-%d" % (offset, end)}) as client:
        r = client.get(GCP_BASE + name)
        r.raise_for_status()
    rows = parse_gcp_rows(r.text)
    if len(rows) != GCP_LT_BINS or {(round(a, 2), round(b, 2)) for a, b, _, _ in rows} != {(round(centre[1], 2), round(centre[0], 2))}:
        raise RuntimeError("GCP rows do not match the expected bin %s" % (centre,))
    stats = diurnal_stats([t for _, _, _, t in rows])
    return {**stats, "file": name, "bin_centre": centre}


def feature(value, quality, source, note):
    return {"value": value, "unit": "degC", "is_real": value is not None, "quality": quality,
            "source": source, "note": note, "comparable": True}


def apply_mars(site: Dict[str, Any], s: Dict[str, Any]) -> Dict[str, Any]:
    src = (
        "Mars Climate Database v6.2 (LMD/OU/IAA/ESA/CNES), escenario climatology average solar, "
        "temperatura del aire a 2 m sobre la superficie, Ls 0–345° cada 15° y 24 horas locales, "
        "consultado el %s vía %s . Media anual de las medias diarias y media anual de (máx − mín) "
        "diario, ponderadas por el tiempo que Marte pasa en cada Ls (2ª ley de Kepler, e = 0,0934, "
        "perihelio Ls 251°). Validación: en Jezero el mismo método da medias diarias de 207–222 K "
        "contra 209–225 K medidos por MEDA (Munguira et al. 2024)." % (WHEN, MCD_ROOT)
    )
    note = ("Modelo climático (como ERA5 en la Tierra), no una medición in situ en el punto. "
            "Medias diarias a lo largo del año: %.1f–%.1f K." % (s["daily_mean_min_K"], s["daily_mean_max_K"]))
    feats = dict(site["features"])
    feats["temp_mean"] = feature(round(s["mean_K"] - 273.15, 2), "modeled", src, note)
    feats["temp_diurnal_range"] = feature(round(s["diurnal_range_K"], 2), "modeled", src, note)
    return {**site, "features": feats}


def apply_moon(site: Dict[str, Any], s: Dict[str, Any]) -> Dict[str, Any]:
    src = (
        "Diviner (LRO) Global Cumulative Product LRO-L-DLRE-5-GCP-V1.0, %s, bin de 0,5° centrado en "
        "%.2f°N %.2f°E, temperatura bolométrica de superficie (Tbol) en 96 bins de 0,25 h de hora "
        "local, observaciones 2009-07-05 a 2015-04-01; Williams et al. (2017), Icarus 283, 300–325. "
        "Leído por rango HTTP el %s: %s%s . Media y (máx − mín) del ciclo diurno; %s de %s bins con "
        "dato, huecos (máx. %s bins seguidos) completados por interpolación lineal circular."
        % (s["file"], s["bin_centre"][0], s["bin_centre"][1], WHEN, GCP_BASE, s["file"],
           s["n_valid"], s["n_bins"], s["max_gap_bins"])
    )
    note = ("Temperatura de SUPERFICIE: la Luna no tiene aire, así que no es comparable 1:1 con la "
            "temperatura del aire a 2 m de la Tierra (ERA5). La amplitud de un día lunar dura 29,5 días terrestres.")
    feats = dict(site["features"])
    feats["temp_mean"] = feature(round(s["mean_K"] - 273.15, 2), "measured", src, note)
    feats["temp_diurnal_range"] = feature(round(s["diurnal_range_K"], 2), "measured", src, note)
    return {**site, "features": feats}


def main(ids: List[str]) -> int:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    sites = []
    failures: List[str] = []
    for site in cat["sites"]:
        if site["id"] in ids:
            try:
                if site["body"] == "mars":
                    s = mars_stats(site["lat"], site["lon"])
                    site = apply_mars(site, s)
                else:
                    s = moon_stats(site["lat"], site["lon"])
                    site = apply_moon(site, s)
                print(site["id"], {k: v for k, v in s.items() if not isinstance(v, (list, tuple))}, flush=True)
            except Exception as exc:  # leave the site untouched (null + "a completar")
                failures.append(site["id"])
                print(site["id"], "FAILED, left unchanged:", exc, flush=True)
        sites.append(site)
    CATALOG.write_text(json.dumps({**cat, "sites": sites}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
