"""7x7 elevation grids at 120 m for component O, with the same DEMs and geometry as T.

* Mars: HRSC-MOLA blended DEM 200 m (USGS), lat/lon grid of terrain.grid_points
  (scripts/ingest_dem.py::DEMS["mars"]).
* Moon, low latitude (Marius Hills): LOLA LDEM 118 m global (USGS), same as T.
* Moon, south pole (lat < -80): LOLA GDR LDEM_80S_20M (PDS Geosciences), polar
  stereographic, grid in local east/north metres along great circles (same geometry
  as feat/te-planetario services/planetary/polar.py; copied here because that branch
  is not merged yet).
* Earth: OpenTopoData aster30m with services/earth/clients/opentopo.py::grid_points,
  exactly as services/earth/scripts/ingest_earth.py.

Network functions only; the metrics live in services/planetary/hazard.py.
"""
from __future__ import annotations

import importlib.util
import math
import os
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
PLANETARY = HERE.parent
REPO = PLANETARY.parent.parent

MOON_RADIUS_M = 1737400.0
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.lbl,.img,.IMG"}
PDS_LOLA = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/"

DEMS: Dict[str, Dict[str, object]] = {
    "mars": {
        "read": "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif",
        "url": "https://planetarymaps.usgs.gov/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif",
        "name": "Mars MGS MOLA – MEX HRSC Blended DEM global 200 m/píxel v2 (USGS Astrogeology)",
        "native_m": 200.0,
    },
    "moon_global": {
        "read": "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif",
        "url": "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif",
        "name": "LRO LOLA LDEM global 118 m/píxel (Mar 2014, USGS Astrogeology)",
        "native_m": 118.45,
    },
    "moon_south": {
        "read": PDS_LOLA + "data/lola_gdr/polar/img/ldem_80s_20m.lbl",
        "url": PDS_LOLA + "data/lola_gdr/polar/img/ldem_80s_20m.lbl",
        "name": "LRO LOLA GDR polar LDEM_80S_20M, estereográfico polar sur 20 m/píxel (PDS Geosciences)",
        "native_m": 20.0,
    },
    "earth": {
        "read": "https://api.opentopodata.org/v1/aster30m",
        "url": "https://api.opentopodata.org/v1/aster30m",
        "name": "ASTER GDEM v3 30 m vía OpenTopoData aster30m",
        "native_m": 30.0,
    },
}


def dem_key(site: Dict[str, object]) -> str:
    body = site.get("body")
    if body == "mars":
        return "mars"
    if body == "moon":
        return "moon_south" if float(site["lat"]) < -80.0 else "moon_global"
    return "earth"


# ------------------------------------------------------------------ geometry

def polar_xy_south(lat: float, lon: float, radius_m: float = MOON_RADIUS_M) -> Tuple[float, float]:
    rho = 2.0 * radius_m * math.tan(math.radians(90.0 + lat) / 2.0)
    lam = math.radians(lon)
    return rho * math.sin(lam), rho * math.cos(lam)


def destination(lat: float, lon: float, east_m: float, north_m: float,
                radius_m: float = MOON_RADIUS_M) -> Tuple[float, float]:
    dist = math.hypot(east_m, north_m)
    if dist == 0.0:
        return lat, lon
    bearing = math.atan2(east_m, north_m)
    ang = dist / radius_m
    phi1, lam1 = math.radians(lat), math.radians(lon)
    sin_phi2 = math.sin(phi1) * math.cos(ang) + math.cos(phi1) * math.sin(ang) * math.cos(bearing)
    phi2 = math.asin(max(-1.0, min(1.0, sin_phi2)))
    lam2 = lam1 + math.atan2(math.sin(bearing) * math.sin(ang) * math.cos(phi1),
                             math.cos(ang) - math.sin(phi1) * sin_phi2)
    return math.degrees(phi2), ((math.degrees(lam2) + 180.0) % 360.0) - 180.0


def local_grid_points(lat: float, lon: float, n: int = 7, spacing_m: float = 120.0,
                      radius_m: float = MOON_RADIUS_M) -> List[Tuple[float, float]]:
    half = n // 2
    return [destination(lat, lon, ix * spacing_m, iy * spacing_m, radius_m)
            for iy in range(-half, half + 1) for ix in range(-half, half + 1)]


def _load_earth_opentopo():
    path = REPO / "services" / "earth" / "clients" / "opentopo.py"
    spec = importlib.util.spec_from_file_location("earth_opentopo", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ readers

def _open(url: str):
    import rasterio

    for k, v in GDAL_ENV.items():
        os.environ[k] = v
    return rasterio.open("/vsicurl/" + url)


def _sample(ds, points: Sequence[Tuple[float, float]], to_xy: Callable[[float, float], Tuple[float, float]],
            use_offset: bool) -> List[Optional[float]]:
    from rasterio.windows import Window

    import terrain

    inv = ~ds.transform
    scale = (ds.scales or (1.0,))[0] or 1.0
    offset = ((ds.offsets or (0.0,))[0] or 0.0) if use_offset else 0.0
    nodata = ds.nodata

    def to_pixel(lat: float, lon: float) -> Tuple[float, float]:
        col, row = inv * to_xy(lat, lon)
        return col - 0.5, row - 0.5

    def read_window(col: int, row: int, width: int, height: int) -> List[List[Optional[float]]]:
        arr = ds.read(1, window=Window(col, row, width, height))
        return [[None if (nodata is not None and v == nodata) else float(v) * scale + offset for v in line]
                for line in arr.tolist()]

    return terrain.sample_grid(points, to_pixel, read_window)


def planetary_grid(site: Dict[str, object]) -> List[Optional[float]]:
    import terrain

    key = dem_key(site)
    lat, lon = float(site["lat"]), float(site["lon"])
    with _open(str(DEMS[key]["read"])) as ds:
        if key == "mars":
            pts = terrain.grid_points(lat, lon, 3396190.0)
            return _sample(ds, pts, lambda la, lo: (lo, la), True)
        if key == "moon_global":
            pts = terrain.grid_points(lat, lon, MOON_RADIUS_M)
            return _sample(ds, pts, lambda la, lo: (MOON_RADIUS_M * math.radians(lo), MOON_RADIUS_M * math.radians(la)), True)
        # polar: DN * 0.5 = height above the 1737.4 km sphere; the offset (radius) is not added.
        return _sample(ds, local_grid_points(lat, lon), polar_xy_south, False)


def earth_grid(site: Dict[str, object], pause_s: float = 1.1) -> List[Optional[float]]:
    opentopo = _load_earth_opentopo()
    pts, _dlat, _dlon = opentopo.grid_points(float(site["lat"]), float(site["lon"]), n=7, spacing_m=120.0)
    z = opentopo.batch_elevations(pts, dataset="aster30m")
    time.sleep(pause_s)
    return z
