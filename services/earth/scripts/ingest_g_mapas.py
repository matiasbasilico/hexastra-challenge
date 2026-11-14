"""G (geología): vector categórico de materiales para los 74 sitios del catálogo.

Escribe data/measurements/g-mapas.jsonl y g-mapas.features.json.

Fuentes (consultadas por este script):
* Tierra: Macrostrat API v2, /geologic_units/map, escala "small" (~1:5M), que
  devuelve la litología del mapa fuente en el punto (p. ej. CGMW 1:5M).
  Estructuras de impacto confirmadas: Osinski et al. 2022, Impact Earth, tabla.
* Luna: USGS Unified Geologic Map of the Moon 1:5M v2 (Fortezzo et al. 2020).
* Marte: USGS SIM 3292 Geologic Map of Mars 1:20M (Tanaka et al. 2014).

Uso:
    services/.venv/bin/python services/earth/scripts/ingest_g_mapas.py
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
METHOD = "services/earth/scripts/ingest_g_mapas.py"
CACHE = Path.home() / ".cache" / "hexastra" / "g"
OUT = ROOT / "data" / "measurements" / "g-mapas.jsonl"
OUT_FEATURES = ROOT / "data" / "measurements" / "g-mapas.features.json"

MACROSTRAT = "https://macrostrat.org/api/v2/geologic_units/map"
MOON_ZIP = "https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip"
MOON_PREFIX = "Unified_Geologic_Map_of_the_Moon_GIS/Lunar_GIS/Shapefiles/GeoUnits"
MARS_ZIP = "https://pubs.usgs.gov/sim/3292/downloads/sim3292_database.zip"
MARS_PREFIX = "SIM3292_MarsGlobalGeologicGIS_20M/SIM3292_Shapefiles/SIM3292_Global_Geology"
LPGRS_TAB = ("https://pds-geosciences.wustl.edu/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/"
             "lpgrs_high1_elem_abundance_2deg.tab")
MOON_RADIUS_M = 1737400.0  # GeoUnits.prj: Moon2000 equidistant cylindrical, clon 0

SRC_LPGRS = ("Lunar Prospector GRS elemental abundance LP-L-GRS-5-ELEM-ABUNDANCE-V1.0 (Prettyman et al. 2006), "
             "píxeles de 2° de área igual, PDS Geosciences Node, consultado %s. %s; umbral FHT de Jolliff et al. 2000 "
             "(JGR 105:4197), resumido en http://www.psrd.hawaii.edu/Aug00/newMoon.html" % (TODAY, LPGRS_TAB))
SRC_MOON = ("USGS Unified Geologic Map of the Moon 1:5M v2 (Fortezzo, Spudis y Harrel 2020), GeoUnits + DOMU, "
            "consultado %s. %s" % (TODAY, MOON_ZIP))
SRC_MARS = ("USGS SIM 3292 Geologic Map of Mars 1:20M (Tanaka et al. 2014, doi:10.3133/sim3292), "
            "SIM3292_Global_Geology, consultado %s. %s" % (TODAY, MARS_ZIP))
SRC_MARS_BASALT = "Unidades volcánicas -> basálticas: McSween, Taylor y Wyatt 2009, Science 324:736, https://doi.org/10.1126/science.1165871"
SRC_EARTH = ("Macrostrat API v2 geologic_units/map, scale=small y, si no hay unidad, tiny (Peters et al. 2018, doi:10.1029/2018GC007467; CC-BY 4.0), "
             "consultado %s. %s" % (TODAY, MACROSTRAT))
SRC_IMPACT = ("Osinski et al. 2022, Impact Earth: A review of the terrestrial impact record, Earth-Sci. Rev. 232:104112, "
              "Tabla de cráteres confirmados, https://doi.org/10.1016/j.earscirev.2022.104112")

# Sitios terrestres dentro de una estructura de impacto confirmada en Osinski et al. 2022.
# Valor: (nombre en la tabla del paper, nota). El resto de los sitios terrestres va 0.
EARTH_IMPACT: Dict[str, Tuple[str, str]] = {
    "lonar": ("Lonar", "Tabla de cráteres confirmados (blanco «Crystalline»)."),
    "meteor-crater": ("Barringer", "Tabla de cráteres confirmados (blanco «Sedimentary»)."),
    "vredefort": ("Vredefort", "Tabla de cráteres confirmados; D ≈ 300 km, el punto del catálogo es el centroide."),
    "tswaing": ("Tswaing", "Tabla de cráteres confirmados."),
    "popigai": ("Popigai", "Tabla de cráteres confirmados; D ≈ 100 km."),
    "nordlinger-ries": ("Ries", "Tabla de cráteres confirmados; D ≈ 24 km."),
    "haughton": ("Haughton", "Tabla de cráteres confirmados; D ≈ 23 km."),
    "devon-island-fmars": ("Haughton", "FMARS está a ~7 km del centro de Haughton (coordenadas del catálogo), dentro del radio de ~11,5 km (D ≈ 23 km en Osinski et al. 2022)."),
    "wolfe-creek": ("Wolfe Creek", "Tabla de cráteres confirmados."),
    "acraman": ("Acraman", "Tabla de cráteres confirmados; D ≈ 90 km."),
    "campo-del-cielo": ("Campo del Cielo", "Tabla 3: cráteres de impacto sin metamorfismo de choque documentado (impacto de baja velocidad con meteoritos)."),
}


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


def earth_result(client: httpx.Client, site: Dict[str, Any]) -> GResult:
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
    known = EARTH_IMPACT.get(site["id"])
    impact = 1.0 if known else 0.0
    impact_note = ("Estructura '%s' en Osinski et al. 2022. %s" % known) if known else (
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


@dataclass(frozen=True)
class LpPixel:
    index: int
    lat0: float
    lat1: float
    lon0: float
    lon1: float
    feo_wt: float  # % en peso
    th_ppm: float


def load_lpgrs() -> List[LpPixel]:
    """Tabla de 2° de Lunar Prospector GRS (columnas: ver LPGRS_ELEM_ABUNDANCE.FMT)."""
    path = CACHE / "lpgrs" / "lpgrs_high1_elem_abundance_2deg.tab"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(follow_redirects=True, timeout=300) as client:
            resp = client.get(LPGRS_TAB)
            resp.raise_for_status()
            path.write_bytes(resp.content)
    pixels = []
    for line in path.read_text(encoding="ascii").splitlines():
        f = line.split()
        if len(f) < 16:
            continue
        # 0 índice, 1-4 límites, 5 AM, 6 densidad, 7 MgO, 8 Al2O3, 9 SiO2, 10 CaO, 11 TiO2, 12 FeO (g/g), 13 K, 14 Th (ppm)
        pixels.append(LpPixel(int(f[0]), float(f[1]), float(f[2]), float(f[3]), float(f[4]),
                              100.0 * float(f[12]), float(f[14])))
    if len(pixels) < 10000:
        raise RuntimeError("tabla LP GRS incompleta (%d píxeles)" % len(pixels))
    return pixels


def lp_pixel(pixels: List[LpPixel], lat: float, lon: float) -> LpPixel:
    lon = lon if lon < 180 else lon - 360
    for p in pixels:
        if (p.lat0 <= lat < p.lat1 or (lat >= 90 and p.lat1 == 90)) and p.lon0 <= lon < p.lon1:
            return p
    raise LookupError("sin píxel LP GRS para %s,%s" % (lat, lon))


def moon_result(reader: shapefile.Reader, site: Dict[str, Any], pixels: List[LpPixel]) -> GResult:
    x = MOON_RADIUS_M * math.radians(site["lon"])
    y = MOON_RADIUS_M * math.radians(site["lat"])
    unit = _polygon_unit(reader, x, y, "FIRST_Unit")
    px = lp_pixel(pixels, site["lat"], site["lon"])
    comp, impact, rule = eq.moon_vector(unit or "", px.feo_wt, px.th_ppm)
    lp_text = "Lunar Prospector GRS píxel %d [%.0f°,%.0f°]×[%.1f°,%.1f°]: FeO %.2f %%, Th %.2f ppm." % (
        px.index, px.lat0, px.lat1, px.lon0, px.lon1, px.feo_wt, px.th_ppm)
    uses_lp = bool(comp and comp.get("g_lito_feldespatico"))
    return GResult(
        site_id=site["id"], composition=comp, impact=impact,
        detail="Unidad mapeada: %s. Regla: %s. %s" % (unit, rule, lp_text),
        source=SRC_MOON + ("; " + SRC_LPGRS if uses_lp else ""),
        composition_note=None if comp else "Ni el mapa 1:5M ni FeO/Th de Lunar Prospector permiten asignar una clase; a completar.",
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
    impact_src = SRC_IMPACT if res.source == SRC_EARTH else res.source
    impact_note = "%s %s" % (res.detail, res.impact_note or "")
    rows.append(_row(res.site_id, eq.IMPACT, res.impact, impact_src, impact_note.strip()))
    return rows


def feature_defs() -> Dict[str, Dict[str, Any]]:
    return {
        fid: {
            "service": ["earth", "planetary"],
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
        for site in sites.values():
            if site.get("body", "earth") == "earth":
                results.append(earth_result(client, site))
    moon = moon_reader()
    lp = load_lpgrs()
    mars = mars_reader()
    for site in sites.values():
        if site.get("body") not in ("moon", "mars"):
            continue
        results.append(moon_result(moon, site, lp) if site["body"] == "moon" else mars_result(mars, site))
    lines = [json.dumps(r, ensure_ascii=False) for res in results for r in rows_for(res)]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_FEATURES.write_text(json.dumps(feature_defs(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for res in results:
        print(res.site_id, res.composition and {k: v for k, v in res.composition.items() if v}, res.impact, "|", res.detail[:160])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
