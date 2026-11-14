#!/usr/bin/env python3
"""Fill elevation, relative relief, slope and roughness of Moon/Mars targets
from the public USGS global DEMs, reading only a small window over HTTP.

Usage (from services/planetary):
    ../.venv/bin/python scripts/ingest_dem.py marius-hills utopia-planitia arsia-mons

Requires rasterio (GDAL /vsicurl/). Never invents values: a failed read leaves
the feature as it was (null + "a completar").
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from terrain import GRID_N, SPACING_M, grid_points, sample_grid, terrain_metrics  # noqa: E402

CATALOG = ROOT / "data" / "catalog.json"
WHEN = "14 de noviembre de 2026 (America/Buenos_Aires)"

DEMS: Dict[str, Dict[str, Any]] = {
    "moon": {
        "url": "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif",
        "s3": "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif",
        "radius_m": 1737400.0,
        "projected": True,  # SimpleCylindrical in metres on the 1737.4 km sphere
        "name": "LRO LOLA LDEM global 118 m/píxel (Mar 2014), USGS Astrogeology",
        "datum": "esfera lunar de 1.737,4 km",
        "native_m": 118.45,
    },
    "mars": {
        "url": "https://planetarymaps.usgs.gov/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif",
        "s3": "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif",
        "radius_m": 3396190.0,
        "projected": False,  # geographic degrees, Mars 2000 sphere
        "name": "Mars MGS MOLA – MEX HRSC Blended DEM global 200 m/píxel v2, USGS Astrogeology",
        "datum": "areoide MOLA (esfera Mars 2000 de 3.396,19 km para la geometría)",
        "native_m": 200.0,
    },
}


def measure(site: Dict[str, Any]) -> Dict[str, Optional[float]]:
    import math

    import rasterio
    from rasterio.windows import Window

    dem = DEMS[site["body"]]
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    with rasterio.open("/vsicurl/" + dem["s3"]) as ds:
        inv = ~ds.transform
        scale = (ds.scales or (1.0,))[0] or 1.0
        offset = (ds.offsets or (0.0,))[0] or 0.0
        nodata = ds.nodata

        def to_pixel(lat: float, lon: float):
            if dem["projected"]:
                x = dem["radius_m"] * math.radians(lon)
                y = dem["radius_m"] * math.radians(lat)
            else:
                x, y = lon, lat
            col, row = inv * (x, y)
            return col - 0.5, row - 0.5  # value of a cell sits at its centre

        def read_window(col: int, row: int, width: int, height: int) -> List[List[Optional[float]]]:
            arr = ds.read(1, window=Window(col, row, width, height))
            return [
                [None if (nodata is not None and v == nodata) else float(v) * scale + offset for v in line]
                for line in arr.tolist()
            ]

        pts = grid_points(site["lat"], site["lon"], dem["radius_m"])
        z = sample_grid(pts, to_pixel, read_window)
    return terrain_metrics(z)


def feature(value, unit, quality, source, note=None):
    return {"value": value, "unit": unit, "is_real": value is not None, "quality": quality,
            "source": source, "note": note, "comparable": True}


def apply(site: Dict[str, Any], m: Dict[str, Optional[float]]) -> Dict[str, Any]:
    dem = DEMS[site["body"]]
    base = (
        "%s, leído por HTTP (GDAL /vsicurl/) el %s: grilla %sx%s a %s m sobre la esfera del cuerpo, "
        "valores bilineales. Misma geometría y fórmulas que los candidatos terrestres "
        "(services/earth/clients/opentopo.py). %s"
        % (dem["name"], WHEN, GRID_N, GRID_N, int(SPACING_M), dem["url"])
    )
    scale_note = None
    if dem["native_m"] > SPACING_M * 1.2:
        scale_note = (
            "El DEM nativo es de %s m/píxel y la grilla es de %s m: el relieve fino queda suavizado "
            "respecto de ASTER 30 m en la Tierra." % (int(dem["native_m"]), int(SPACING_M))
        )
    def r(v):
        return None if v is None else round(v, 2)
    feats = dict(site["features"])
    feats["elevation"] = feature(
        r(m["elevation_m"]), "m", "measured" if m["elevation_m"] is not None else "placeholder",
        base + " Cota respecto del %s; no entra en S_T." % dem["datum"],
    )
    for key, mkey, unit, definition in (
        ("relative_relief", "relative_relief_m", "m", "relieve relativo = máx − mín de la grilla"),
        ("slope", "slope_deg", "deg", "pendiente del centro con los cuatro vecinos cardinales"),
        ("roughness", "roughness_m", "m", "rugosidad = desvío estándar muestral de la grilla"),
    ):
        val = r(m[mkey])
        feats[key] = feature(
            val, unit, "derived" if val is not None else "placeholder",
            base + " " + definition[0].upper() + definition[1:] + ".",
            scale_note if val is not None else "valor no cargado: lectura del DEM sin datos (a completar)",
        )
    return {**site, "features": feats}


RELATIVE_RELIEF_DEF = {
    "id": "relative_relief",
    "name_es": "Relieve relativo",
    "description": "Máximo menos mínimo de una grilla 7×7 a 120 m alrededor del punto (misma definición que en la Tierra).",
    "unit": "m",
    "numeric": True,
    "use_log": False,
    "default_weight": 1.0,
    "why_normalize": "Va de pocos metros en planicies a cientos en flancos volcánicos; TASI lo compara con Mahalanobis.",
}


def main(ids: List[str]) -> int:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    sites = []
    for site in cat["sites"]:
        if site["id"] in ids:
            m = measure(site)
            print(site["id"], {k: (None if v is None else round(v, 2)) for k, v in m.items()}, flush=True)
            site = apply(site, m)
        sites.append(site)
    features = dict(cat["features"])
    features.setdefault("relative_relief", RELATIVE_RELIEF_DEF)
    out = {**cat, "features": features, "sites": sites}
    CATALOG.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
