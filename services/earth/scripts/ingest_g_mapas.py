"""Piloto G (geología): vector categórico de materiales para 12 sitios.

Escribe data/measurements/g-piloto.jsonl y g-piloto.features.json.

Fuentes (consultadas por este script):
* Tierra: Macrostrat API v2, /geologic_units/map, escala "small" (~1:5M), que
  devuelve la litología del mapa fuente en el punto (p. ej. CGMW 1:5M).
  Estructuras de impacto confirmadas: Osinski et al. 2022, Impact Earth, tabla.
* Luna: USGS Unified Geologic Map of the Moon 1:5M v2 (Fortezzo et al. 2020).
* Marte: USGS SIM 3292 Geologic Map of Mars 1:20M (Tanaka et al. 2014).

Uso:
    services/.venv/bin/python services/earth/scripts/ingest_g_piloto.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import shapefile
from shapely.geometry import Point, shape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import g_equivalencias as eq  # noqa: E402
from remote_zip import extract_members  # noqa: E402

TODAY = "2026-11-14"
METHOD = "services/earth/scripts/ingest_g_piloto.py"
CACHE = Path.home() / ".cache" / "hexastra" / "g"
OUT = ROOT / "data" / "measurements" / "g-piloto.jsonl"
OUT_FEATURES = ROOT / "data" / "measurements" / "g-piloto.features.json"

MACROSTRAT = "https://macrostrat.org/api/v2/geologic_units/map"
MOON_ZIP = "https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip"
MOON_PREFIX = "Unified_Geologic_Map_of_the_Moon_GIS/Lunar_GIS/Shapefiles/GeoUnits"
MARS_ZIP = "https://pubs.usgs.gov/sim/3292/downloads/sim3292_database.zip"
MARS_PREFIX = "SIM3292_MarsGlobalGeologicGIS_20M/SIM3292_Shapefiles/SIM3292_Global_Geology"
MOON_RADIUS_M = 1737400.0  # GeoUnits.prj: Moon2000 equidistant cylindrical, clon 0

SRC_MOON = ("USGS Unified Geologic Map of the Moon 1:5M v2 (Fortezzo, Spudis y Harrel 2020), GeoUnits + DOMU, "
            "consultado %s. %s" % (TODAY, MOON_ZIP))
SRC_MARS = ("USGS SIM 3292 Geologic Map of Mars 1:20M (Tanaka et al. 2014, doi:10.3133/sim3292), "
            "SIM3292_Global_Geology, consultado %s. %s" % (TODAY, MARS_ZIP))
SRC_MARS_BASALT = "Unidades volcánicas -> basálticas: McSween, Taylor y Wyatt 2009, Science 324:736, https://doi.org/10.1126/science.1165871"
SRC_EARTH = ("Macrostrat API v2 geologic_units/map, scale=small y, si no hay unidad, tiny (Peters et al. 2018, doi:10.1029/2018GC007467; CC-BY 4.0), "
             "consultado %s. %s" % (TODAY, MACROSTRAT))
SRC_IMPACT = ("Osinski et al. 2022, Impact Earth: A review of the terrestrial impact record, Earth-Sci. Rev. 232:104112, "
              "Tabla de cráteres confirmados, https://doi.org/10.1016/j.earscirev.2022.104112")

# Sitios del piloto. Para la Tierra, el nombre con que figura en Osinski et al. 2022
# (None = no es una estructura de impacto confirmada en esa tabla).
EARTH_SITES: Dict[str, Optional[str]] = {
    "pali-aike": None,
    "craters-of-the-moon": None,
    "payun-matru": None,
    "campo-piedra-pomez": None,
    "lonar": "Lonar",
    "meteor-crater": "Barringer",
}
PLANETARY_SITES = ("marius-hills", "shackleton-rim", "pavonis-mons", "arsia-mons", "jezero", "gale")


@dataclass(frozen=True)
class GResult:
    site_id: str
    composition: Optional[Dict[str, float]]
    impact: Optional[float]
    detail: str  # unidad o litología leída + regla aplicada
    source: str
    composition_note: Optional[str] = None
    impact_note: Optional[str] = None


def load_sites() -> Dict[str, Dict[str, Any]]:
    out = {}
    for svc in ("earth", "planetary"):
        data = json.loads((ROOT / "services" / svc / "data" / "catalog.json").read_text(encoding="utf-8"))
        for site in data["sites"]:
            out[site["id"]] = site
    return out


# ---------------------------------------------------------------- Tierra
MACROSTRAT_SCALES = ("small", "tiny")  # ~1:5M primero; si no hay unidad, mapa mundial ~1:35M


def macrostrat_point(client: httpx.Client, lat: float, lon: float, scale: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    last = None
    for attempt in range(6):
        try:
            resp = client.get(MACROSTRAT, params={"lat": lat, "lng": lon, "scale": scale}, timeout=60)
            resp.raise_for_status()
            body = resp.json()["success"]
            return body["data"], body.get("refs") or {}
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError("Macrostrat no respondió para %s,%s: %s" % (lat, lon, last))


def earth_result(client: httpx.Client, site: Dict[str, Any], impact_name: Optional[str]) -> GResult:
    units, refs, scale = [], {}, MACROSTRAT_SCALES[0]
    for scale in MACROSTRAT_SCALES:
        units, refs = macrostrat_point(client, site["lat"], site["lon"], scale)
        if units:
            break
    liths = "; ".join(u.get("lith") or "" for u in units)
    names = "; ".join(u.get("name") or "" for u in units)
    map_refs = " | ".join(r.strip().rstrip(".") for r in refs.values())
    comp = eq.earth_composition(liths)
    detail = "Macrostrat scale=%s. Unidad: %s. Litología: %s. Mapa fuente: %s." % (
        scale, names or "sin unidad", liths or "sin dato", map_refs or "sin dato")
    impact = 1.0 if impact_name else 0.0
    impact_note = ("Estructura confirmada '%s' en Osinski et al. 2022." % impact_name) if impact_name else (
        "No figura como estructura de impacto confirmada en Osinski et al. 2022.")
    return GResult(
        site_id=site["id"], composition=comp, impact=impact, detail=detail,
        source=SRC_EARTH,
        composition_note=None if comp else "Macrostrat no devolvió una litología reconocible en el punto; a completar.",
        impact_note=impact_note,
    )


# ---------------------------------------------------------------- Luna y Marte
def _polygon_unit(reader: shapefile.Reader, x: float, y: float, field: str) -> Optional[str]:
    pt = Point(x, y)
    for i, shp in enumerate(reader.iterShapes()):
        x0, y0, x1, y1 = shp.bbox
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        if shape(shp.__geo_interface__).covers(pt):
            return reader.record(i)[field]
    return None


def moon_reader() -> shapefile.Reader:
    members = [MOON_PREFIX + ext for ext in (".shp", ".shx", ".dbf", ".prj")]
    paths = extract_members(MOON_ZIP, members, CACHE / "moon")
    return shapefile.Reader(str(paths[members[0]])[:-4])


def mars_reader() -> shapefile.Reader:
    members = [MARS_PREFIX + ext for ext in (".shp", ".shx", ".dbf", ".prj")]
    paths = extract_members(MARS_ZIP, members, CACHE / "mars")
    return shapefile.Reader(str(paths[members[0]])[:-4])


def moon_result(reader: shapefile.Reader, site: Dict[str, Any]) -> GResult:
    x = MOON_RADIUS_M * math.radians(site["lon"])
    y = MOON_RADIUS_M * math.radians(site["lat"])
    unit = _polygon_unit(reader, x, y, "FIRST_Unit")
    comp, impact, rule = eq.moon_vector(unit or "")
    return GResult(
        site_id=site["id"], composition=comp, impact=impact,
        detail="Unidad mapeada: %s. Regla: %s." % (unit, rule), source=SRC_MOON,
        composition_note=None if comp else "El mapa 1:5M define esta unidad por su origen, no por su composición; a completar con un producto composicional (p. ej. Diviner Christiansen Feature o FeO de Lunar Prospector).",
        impact_note=None if impact is not None else "Sin regla de impacto para la unidad; a completar.",
    )


def mars_result(reader: shapefile.Reader, site: Dict[str, Any]) -> GResult:
    lon = site["lon"] if site["lon"] <= 180 else site["lon"] - 360
    unit = _polygon_unit(reader, lon, site["lat"], "Unit")
    comp, impact, rule = eq.mars_vector(unit or "")
    source = SRC_MARS + ("; " + SRC_MARS_BASALT if comp and comp.get("g_lito_basaltico") else "")
    return GResult(
        site_id=site["id"], composition=comp, impact=impact,
        detail="Unidad mapeada: %s. Regla: %s." % (unit, rule), source=source,
        composition_note=None if comp else "SIM 3292 (1:20M) es morfoestratigráfico y no asigna litología a esta unidad; a completar con CRISM/TES.",
        impact_note=None if impact is not None else "Cráteres menores que la escala 1:20M no se mapean como AHi; ausencia en el mapa no es 0; a completar.",
    )


# ---------------------------------------------------------------- filas
def _row(site_id: str, feature: str, value: Optional[float], source: str, note: str) -> Dict[str, Any]:
    if value is None:
        return {"site_id": site_id, "feature": feature, "value": None, "unit": "fraction" if feature != eq.IMPACT else "boolean",
                "quality": "unavailable", "is_real": False, "source": source, "note": note,
                "method": METHOD, "retrieved_at": TODAY}
    return {"site_id": site_id, "feature": feature, "value": round(float(value), 4),
            "unit": "fraction" if feature != eq.IMPACT else "boolean",
            "quality": "derived", "is_real": True, "source": source, "note": note,
            "method": METHOD, "retrieved_at": TODAY}


def rows_for(res: GResult) -> List[Dict[str, Any]]:
    rows = []
    for feat in eq.COMPOSITION:
        if res.composition is None:
            rows.append(_row(res.site_id, feat, None, res.source, "%s %s" % (res.detail, res.composition_note)))
        else:
            rows.append(_row(res.site_id, feat, res.composition[feat], res.source,
                             "%s Clase derivada con la tabla g_equivalencias v0 (docs/propuestas/G.md)." % res.detail))
    impact_src = SRC_IMPACT if res.site_id in EARTH_SITES else res.source
    impact_note = "%s %s" % (res.detail, res.impact_note or "")
    rows.append(_row(res.site_id, eq.IMPACT, res.impact, impact_src, impact_note.strip()))
    return rows


def feature_defs() -> Dict[str, Dict[str, Any]]:
    return {
        fid: {
            "service": "earth",
            "unit": "boolean" if fid == eq.IMPACT else "fraction",
            "name_es": fid,
            "description": desc + ". Componente G (propuesta, docs/propuestas/G.md). Mismo id para Tierra, Luna y Marte.",
        }
        for fid, desc in eq.FEATURE_DEFS.items()
    }


def main() -> int:
    sites = load_sites()
    results: List[GResult] = []
    with httpx.Client(follow_redirects=True, headers={"User-Agent": "hexastra-g-pilot/0.1"}) as client:
        for sid, impact_name in EARTH_SITES.items():
            results.append(earth_result(client, sites[sid], impact_name))
    moon = moon_reader()
    mars = mars_reader()
    for sid in PLANETARY_SITES:
        site = sites[sid]
        results.append(moon_result(moon, site) if site["body"] == "moon" else mars_result(mars, site))
    lines = [json.dumps(r, ensure_ascii=False) for res in results for r in rows_for(res)]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_FEATURES.write_text(json.dumps(feature_defs(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for res in results:
        print(res.site_id, res.composition and {k: v for k, v in res.composition.items() if v}, res.impact, "|", res.detail[:160])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
