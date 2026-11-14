"""Country and continent assignment from Natural Earth 50m admin-0.

Point-in-polygon on the public-domain Natural Earth vector. ISO-3166 alpha-2
comes from ISO_A2, or ISO_A2_EH when ISO_A2 is the Natural Earth sentinel -99
(e.g. Norway/Svalbard polygons). Continent is the Natural Earth CONTINENT
field (Russia is classified as Europe, including Siberian sites).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data"
NE_PATH = DATA_DIR / "ne_50m_admin_0_countries.geojson"

_FEATURES: Optional[List[Dict[str, Any]]] = None
INVALID_ISO = {"-99", "-1", "", None}


def _point_in_ring(x: float, y: float, ring: List[List[float]]) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) if yj != yi else 1e-20) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def geometry_contains(geom: Dict[str, Any], lon: float, lat: float) -> bool:
    typ = geom.get("type")
    if typ == "Polygon":
        rings = geom.get("coordinates") or []
        if not rings or not _point_in_ring(lon, lat, rings[0]):
            return False
        for hole in rings[1:]:
            if _point_in_ring(lon, lat, hole):
                return False
        return True
    if typ == "MultiPolygon":
        for poly in geom.get("coordinates") or []:
            if geometry_contains({"type": "Polygon", "coordinates": poly}, lon, lat):
                return True
        return False
    return False


def load_ne() -> List[Dict[str, Any]]:
    global _FEATURES
    if _FEATURES is None:
        with NE_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        _FEATURES = data["features"]
    return _FEATURES


def iso_from_props(props: Dict[str, Any]) -> Optional[str]:
    iso = props.get("ISO_A2")
    if iso in INVALID_ISO:
        iso = props.get("ISO_A2_EH")
    if iso in INVALID_ISO:
        return None
    return str(iso).upper()


def assign_country(lat: float, lon: float) -> Dict[str, Any]:
    """Return continent, ISO alpha-2 and country name, or a not-found record."""
    for feat in load_ne():
        if geometry_contains(feat["geometry"], lon, lat):
            props = feat["properties"]
            return {
                "continent": props.get("CONTINENT"),
                "country_iso": iso_from_props(props),
                "country_name": props.get("NAME_EN") or props.get("ADMIN"),
                "source": (
                    "Natural Earth 50m admin-0 countries, point-in-polygon. "
                    "https://www.naturalearthdata.com/ and "
                    "nvkelso/natural-earth-vector ne_50m_admin_0_countries.geojson. "
                    "ISO from ISO_A2, or ISO_A2_EH when ISO_A2 is -99."
                ),
                "found": True,
            }
    return {
        "continent": None,
        "country_iso": None,
        "country_name": None,
        "source": "Natural Earth 50m admin-0: point not inside any polygon; left unassigned (not guessed).",
        "found": False,
    }


def regions_from_sites(sites: List[Dict[str, Any]]) -> Dict[str, Any]:
    continents: Dict[str, Dict[str, Any]] = {}
    for site in sites:
        cont = site.get("continent")
        iso = site.get("country_iso")
        name = site.get("country_name")
        if not cont or not iso:
            continue
        bucket = continents.setdefault(cont, {"name": cont, "countries": {}})
        countries = bucket["countries"]
        if iso not in countries:
            countries[iso] = {"iso": iso, "name": name, "count": 0}
        countries[iso]["count"] += 1
    ordered = []
    for cont in sorted(continents.keys()):
        countries = sorted(continents[cont]["countries"].values(), key=lambda c: c["name"] or c["iso"])
        ordered.append({"name": cont, "countries": countries})
    return {"source": "Derived from candidates assigned with Natural Earth 50m admin-0.", "continents": ordered}
