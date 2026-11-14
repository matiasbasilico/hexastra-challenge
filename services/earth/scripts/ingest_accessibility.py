#!/usr/bin/env python3
"""Accessibility of the Earth sites -> data/measurements/o-tierra.jsonl.

Features (straight-line geodesic distances on WGS84, not travel distances):
  dist_road_km               nearest road segment, NASA SEDAC gROADS v1.
  dist_airport_km            nearest open aerodrome with a runway, OurAirports.
  dist_airport_scheduled_km  nearest aerodrome with scheduled service, OurAirports.
  population_50km            people within 50 km, NASA SEDAC GPWv4 r11 population count 2020.
  dist_road_osm_km           nearest drivable way, OpenStreetMap (second source: gROADS is from 1980-2010).
  population_50km_ghsl       people within 50 km, GHS-POP R2023A epoch 2020 (second source: GPWv4
                             spreads census population evenly inside each administrative unit).

Inputs are downloaded once into ~/.cache/hexastra/o-tierra (override with HEXASTRA_CACHE):
  groads/groads-v1-global-gdb.zip                         (Earthdata login, ~/.netrc)
  gpw/gpw-v4-population-count-rev11_2020_30_sec_tif.zip   (Earthdata login, ~/.netrc)
  ourairports/airports.csv                                (public)
  ghsl/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.zip      (public, JRC)
  osm/<site>_<radius_km>.json                             (Overpass responses, one per query)

Usage:
  services/.venv/bin/python services/earth/scripts/ingest_accessibility.py [--download] [--validate-only]

Never invents numbers: a missing input or an uncovered site is written as null with a note.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
EARTH_ROOT = HERE.parent
REPO = EARTH_ROOT.parents[1]
if str(EARTH_ROOT) not in sys.path:
    sys.path.insert(0, str(EARTH_ROOT))

import accessibility as acc  # noqa: E402
from clients.overpass import ROAD_CLASSES, OverpassError, roads_around  # noqa: E402

LOG = logging.getLogger("ingest_accessibility")
METHOD = "services/earth/scripts/ingest_accessibility.py"
CATALOG = EARTH_ROOT / "data" / "catalog.json"
OUT = REPO / "data" / "measurements" / "o-tierra.jsonl"
CACHE = Path(os.environ.get("HEXASTRA_CACHE", str(Path.home() / ".cache" / "hexastra" / "o-tierra")))

SEDAC = "https://data.earthdata.nasa.gov/nasa-earth/human-dimensions/sedac-root/downloads/data"
GROADS_URL = SEDAC + "/groads/groads-global-roads-open-access-v1/groads-v1-global-gdb.zip"
GPW_URL = SEDAC + "/gpw-v4/gpw-v4-population-count-rev11/gpw-v4-population-count-rev11_2020_30_sec_tif.zip"
AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
GROADS_ZIP = CACHE / "groads" / "groads-v1-global-gdb.zip"
GPW_ZIP = CACHE / "gpw" / "gpw-v4-population-count-rev11_2020_30_sec_tif.zip"
AIRPORTS_CSV = CACHE / "ourairports" / "airports.csv"
GHSL_URL = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
            "GHS_POP_E2020_GLOBE_R2023A_4326_30ss/V1-0/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.zip")
GHSL_ZIP = CACHE / "ghsl" / "GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.zip"
OSM_CACHE = CACHE / "osm"
OSM_RADII_KM = (5, 25, 100, 400)

ANTARCTIC_LAT = -60.0  # Antarctic Treaty area: no roads in gROADS, no census behind GPWv4 or GHS-POP
ROAD_ATTRS = ("SOURCEID", "FCLASS")
FEATURES = ("dist_road_km", "dist_airport_km", "dist_airport_scheduled_km", "population_50km",
            "dist_road_osm_km", "population_50km_ghsl")
UNITS = {f: "persons" if f.startswith("population") else "km" for f in FEATURES}

STRAIGHT = "Distancia geodésica en línea recta (WGS84), no distancia de viaje; puede cruzar agua o relieve."
SRC_ROADS = (
    "NASA SEDAC gROADS v1 (Global Roads Open Access Data Set, 1980-2010), CIESIN/ITOS, doi:10.7927/H4VD6WCT, "
    "geodatabase global vía NASA Earthdata, consultado %s. " + GROADS_URL
)
SRC_POP = (
    "NASA SEDAC GPWv4 Population Count, Revision 11 (v4.11), año 2020, 30 arcsec, CIESIN, doi:10.7927/H4JW8BX5, "
    "vía NASA Earthdata, consultado %s. " + GPW_URL
)
SRC_AIRPORTS = (
    "OurAirports airports.csv (dominio público; fuente externa: las fuentes oficiales del desafío no publican "
    "un catálogo mundial de aeródromos), consultado %s. " + AIRPORTS_URL
)

SRC_OSM = (
    "OpenStreetMap (© colaboradores de OpenStreetMap, ODbL) vía Overpass API, vías highway=" + "/".join(ROAD_CLASSES)
    + " y sus _link (fuente externa: segunda fuente porque gROADS v1 es de 1980-2010), consultado %s. "
    "https://www.openstreetmap.org/copyright"
)
SRC_GHSL = (
    "GHS-POP R2023A, época 2020, 30 arcsec WGS84 (GHS_POP_E2020_GLOBE_R2023A_4326_30ss V1-0), Comisión Europea JRC "
    "(Copernicus GHSL), doi:10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE, consultado %s. " + GHSL_URL
)

# Validation: site, airport ident, published distance (km), tolerance (km), reference.
AIRPORT_CHECKS = (
    ("haughton", "CYRB", None, None, "Resolute Bay (Cornwallis Island) es el aeropuerto de acceso al cráter Haughton"),
    ("base-marambio", "SAWB", 0.0, 2.0, "La base Marambio tiene pista propia (SAWB)"),
)


def download(url: str, dest: Path, netrc: bool) -> None:
    """Fetch with curl so Earthdata credentials stay in ~/.netrc and are never printed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    cmd = ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "8", "--retry-all-errors",
           "--continue-at", "-", "--output", str(tmp)]
    if netrc:
        jar = str(CACHE / ".cookies")
        cmd += ["--netrc", "--cookie-jar", jar, "--cookie", jar]
    subprocess.run(cmd + [url], check=True)
    if dest.suffix == ".zip" and not zipfile.is_zipfile(tmp):
        tmp.unlink()
        raise RuntimeError("%s no devolvió un zip (¿login o perfil de Earthdata incompleto?)" % url)
    tmp.replace(dest)


def ensure_inputs(do_download: bool) -> Dict[str, Optional[Path]]:
    wanted = ((GROADS_ZIP, GROADS_URL, True), (GPW_ZIP, GPW_URL, True), (AIRPORTS_CSV, AIRPORTS_URL, False),
              (GHSL_ZIP, GHSL_URL, False))
    for path, url, netrc in wanted:
        if path.exists() or not do_download:
            continue
        try:
            LOG.info("descargando %s", url)
            download(url, path, netrc)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            LOG.error("no se pudo descargar %s: %s", url, exc)
    return {
        "roads": unpacked(GROADS_ZIP, ".gdb") if GROADS_ZIP.exists() else None,
        "population": unpacked(GPW_ZIP, ".tif") if GPW_ZIP.exists() else None,
        "airports": AIRPORTS_CSV if AIRPORTS_CSV.exists() else None,
        "ghsl": unpacked(GHSL_ZIP, ".tif") if GHSL_ZIP.exists() else None,
    }


def unpacked(archive: Path, suffix: str) -> Path:
    """Extract the archive next to itself and return the first member with `suffix`."""
    target = archive.parent / (archive.stem + "_x")
    if not target.exists():
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(target)
    hits = sorted(p for p in target.rglob("*" + suffix))
    if not hits:
        raise RuntimeError("%s no contiene ningún %s" % (archive, suffix))
    return hits[0]


def row(site_id: str, feature: str, value: Optional[float], quality: str, source: str, note: Optional[str], today: str) -> Dict[str, Any]:
    return {
        "site_id": site_id, "feature": feature, "value": value, "unit": UNITS[feature], "quality": quality,
        "is_real": value is not None, "source": source, "note": note, "method": METHOD, "retrieved_at": today,
        "comparable": False,
    }


def missing(site_id: str, feature: str, why: str, source: str, today: str) -> Dict[str, Any]:
    return row(site_id, feature, None, "unavailable", source, why + " Dato a completar.", today)


def road_row(site: Dict[str, Any], roads: Optional[Path], today: str) -> Dict[str, Any]:
    sid, src = site["id"], SRC_ROADS % today
    if site["lat"] < ANTARCTIC_LAT:
        return missing(sid, "dist_road_km", "gROADS v1 no tiene rutas en la Antártida (sur de 60° S).", src, today)
    if roads is None:
        return missing(sid, "dist_road_km", "No se pudo descargar gROADS v1 desde Earthdata.", src, today)
    hit = acc.nearest_road(roads, site["lat"], site["lon"], columns=ROAD_ATTRS)
    if hit is None:
        return missing(sid, "dist_road_km", "Sin rutas de gROADS v1 a menos de 5000 km.", src, today)
    note = "%s Tramo más cercano: SOURCEID %s, FCLASS %s. gROADS es de 1980-2010 y su cobertura varía por país." % (
        STRAIGHT, hit["attributes"].get("SOURCEID"), hit["attributes"].get("FCLASS"))
    return row(sid, "dist_road_km", round(hit["distance_km"], 2), "derived", src, note, today)


def airport_rows(site: Dict[str, Any], airports: Optional[List[Dict[str, Any]]], today: str) -> List[Dict[str, Any]]:
    sid, src, out = site["id"], SRC_AIRPORTS % today, []
    for feature, scheduled in (("dist_airport_km", False), ("dist_airport_scheduled_km", True)):
        hit = acc.nearest_airport(airports, site["lat"], site["lon"], scheduled) if airports else None
        if hit is None:
            out.append(missing(sid, feature, "No se pudo leer el catálogo de OurAirports.", src, today))
            continue
        note = "%s Aeródromo: %s (%s, %s, %s)." % (STRAIGHT, hit["name"], hit["ident"], hit["type"], hit["country"])
        out.append(row(sid, feature, round(hit["distance_km"], 2), "derived", src, note, today))
    return out


def population_row(site: Dict[str, Any], tif: Optional[Path], today: str) -> Dict[str, Any]:
    sid, src = site["id"], SRC_POP % today
    if tif is None:
        return missing(sid, "population_50km", "No se pudo descargar GPWv4 desde Earthdata.", src, today)
    res = acc.population_within(tif, site["lat"], site["lon"])
    if res["value"] is None:
        return missing(sid, "population_50km", "GPWv4 no tiene celdas con dato a 50 km (sin unidades censales).", src, today)
    note = ("Suma de las celdas de 30 arcsec con centro a <= 50 km (%s de %s celdas con dato; el resto es agua o sin dato). "
            "GPWv4 reparte la población censal de forma uniforme dentro de cada unidad administrativa: en unidades grandes "
            "y poco pobladas puede sobrestimar la población cercana.") % (
        res["valid_cells"], res["cells"])
    return row(sid, "population_50km", round(res["value"]), "modeled", src, note, today)


def osm_elements(site: Dict[str, Any], radius_km: int, online: bool) -> Optional[List[Dict[str, Any]]]:
    """Overpass response for one site and radius, from the cache or (if online) the network."""
    path = OSM_CACHE / ("%s_%s.json" % (site["id"], radius_km))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if not online:
        return None
    try:
        elements = roads_around(site["lat"], site["lon"], radius_km * 1000)
    except OverpassError as exc:
        LOG.error("Overpass %s a %s km: %s", site["id"], radius_km, exc)
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(elements), encoding="utf-8")
    return elements


def osm_road_row(site: Dict[str, Any], online: bool, today: str) -> Dict[str, Any]:
    sid, src = site["id"], SRC_OSM % today
    for radius in OSM_RADII_KM:
        elements = osm_elements(site, radius, online)
        if elements is None:
            return missing(sid, "dist_road_osm_km", "No se pudo consultar Overpass (radio %s km)." % radius, src, today)
        hit = acc.nearest_osm_way(elements, site["lat"], site["lon"])
        if hit is None:
            continue
        note = "%s Vía más cercana: way %s, highway=%s (%s vías a <= %s km). OSM es colaborativo: incluye huellas (track) y su cobertura varía. La vía puede estar aislada: no implica conexión con una red vial." % (
            STRAIGHT, hit["way_id"], hit["highway"], len(elements), radius)
        return row(sid, "dist_road_osm_km", round(hit["distance_km"], 2), "derived", src, note, today)
    return missing(sid, "dist_road_osm_km", "Sin vías de OSM a menos de %s km." % OSM_RADII_KM[-1], src, today)


def ghsl_row(site: Dict[str, Any], tif: Optional[Path], today: str) -> Dict[str, Any]:
    sid, src = site["id"], SRC_GHSL % today
    if site["lat"] < ANTARCTIC_LAT:
        return missing(sid, "population_50km_ghsl", "GHS-POP no tiene censo de base en la Antártida (sur de 60° S): su 0 no es una medición.", src, today)
    if tif is None:
        return missing(sid, "population_50km_ghsl", "No se pudo descargar GHS-POP.", src, today)
    res = acc.population_within(tif, site["lat"], site["lon"])
    if res["value"] is None:
        return missing(sid, "population_50km_ghsl", "GHS-POP no tiene celdas con dato a 50 km.", src, today)
    note = ("Suma de las celdas de 30 arcsec con centro a <= 50 km (%s de %s celdas con dato). GHS-POP reparte la población "
            "censal según la superficie construida detectada por satélite, no de forma uniforme.") % (res["valid_cells"], res["cells"])
    return row(sid, "population_50km_ghsl", round(res["value"]), "modeled", src, note, today)


def validate(sites: Dict[str, Dict[str, Any]], airports: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Checks against known values. Returns the failures (empty when everything holds)."""
    failures = []
    vincenty = acc.geodesic_km(-37.95103342, 144.42486789, -37.65282114, 143.92649553)
    if abs(vincenty - 54.972271) > 0.001:  # Vincenty (1975) Flinders Peak - Buninyong
        failures.append("geodésica Flinders-Buninyong %.6f km != 54.972271" % vincenty)
    for sid, ident, expected, tol, why in AIRPORT_CHECKS if airports else ():
        hit = acc.nearest_airport(airports, sites[sid]["lat"], sites[sid]["lon"])
        if hit["ident"] != ident or (expected is not None and abs(hit["distance_km"] - expected) > tol):
            failures.append("%s: %s a %.1f km, se esperaba %s (%s)" % (sid, hit["ident"], hit["distance_km"], ident, why))
    return failures


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--download", action="store_true", help="descargar las entradas que falten")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    today = date.today().isoformat()
    sites = json.loads(CATALOG.read_text(encoding="utf-8"))["sites"]
    inputs = ensure_inputs(args.download)
    airports = acc.load_airports(inputs["airports"]) if inputs["airports"] else None
    failures = validate({s["id"]: s for s in sites}, airports)
    for failure in failures:
        LOG.error("VALIDACIÓN: %s", failure)
    if failures:
        return 1
    if args.validate_only:
        return 0

    rows: List[Dict[str, Any]] = []
    for site in sites:
        LOG.info("%s", site["id"])
        rows.append(road_row(site, inputs["roads"], today))
        rows.extend(airport_rows(site, airports, today))
        rows.append(population_row(site, inputs["population"], today))
        rows.append(osm_road_row(site, args.download, today))
        rows.append(ghsl_row(site, inputs["ghsl"], today))
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    nulls = sum(1 for r in rows if r["value"] is None)
    LOG.info("%s filas (%s null) -> %s", len(rows), nulls, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
