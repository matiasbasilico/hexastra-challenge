#!/usr/bin/env python3
"""Component O (operations) comparable on both sides -> data/measurements/o-comparable.jsonl.

Step 1 (network, resumable):  --fetch
    Reads the 7x7 elevation grid at 120 m of the 14 Moon/Mars destinations and the
    60 Earth sites (scripts/o_grids.py) and stores them, with their source, in
    services/planetary/data/o_comparable_grids.json. Nothing is guessed: a failed
    read is stored as an error and becomes a null row.

Step 2 (offline): default
    Computes the hazardous-slope fractions (hazard.py) and the rock abundance rows
    (rocks.py) and writes the jsonl.

Usage (from the repo root):
    services/.venv/bin/python services/planetary/scripts/ingest_o_comparable.py --fetch
    services/.venv/bin/python services/planetary/scripts/ingest_o_comparable.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
PLANETARY = HERE.parent
REPO = PLANETARY.parent.parent
for p in (str(PLANETARY), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import hazard  # noqa: E402
import o_grids  # noqa: E402

PLANETARY_CATALOG = PLANETARY / "data" / "catalog.json"
EARTH_CATALOG = REPO / "services" / "earth" / "data" / "catalog.json"
GRIDS = PLANETARY / "data" / "o_comparable_grids.json"
OUT = REPO / "data" / "measurements" / "o-comparable.jsonl"
METHOD = "services/planetary/scripts/ingest_o_comparable.py"
RETRIEVED = "2026-11-14"
WHEN = "14 de noviembre de 2026 (America/Buenos_Aires)"


def all_sites() -> List[Dict[str, Any]]:
    out = []
    for path in (PLANETARY_CATALOG, EARTH_CATALOG):
        for s in json.loads(path.read_text(encoding="utf-8"))["sites"]:
            out.append({"id": s["id"], "body": s.get("body") or "earth", "lat": s["lat"], "lon": s["lon"]})
    return out


def load_grids() -> Dict[str, Any]:
    if GRIDS.exists():
        return json.loads(GRIDS.read_text(encoding="utf-8"))
    return {"retrieved_at": RETRIEVED, "grid": "7x7 a 120 m, fila por fila desde el suroeste", "sites": {}}


def fetch() -> int:
    data = load_grids()
    for site in all_sites():
        prev = data["sites"].get(site["id"])
        if prev and prev.get("z") and not prev.get("error"):
            continue
        key = o_grids.dem_key(site)
        try:
            z = o_grids.planetary_grid(site) if site["body"] in ("moon", "mars") else o_grids.earth_grid(site)
            rec = {"dem": key, "z": [None if v is None else round(v, 3) for v in z], "error": None}
        except Exception as exc:  # stored, never replaced by an invented value
            rec = {"dem": key, "z": None, "error": "%s: %s" % (type(exc).__name__, exc)}
        data["sites"][site["id"]] = rec
        fr = hazard.slope_fractions(rec["z"]) if rec["z"] else {}
        print(site["id"], key, rec["error"] or {k: (None if v is None else round(v, 2)) for k, v in fr.items()}, flush=True)
        GRIDS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


# ------------------------------------------------------------------ rows

def row(site: str, feature: str, value: Optional[float], unit: str, quality: str, source: str,
        note: Optional[str], comparable: bool = True) -> Dict[str, Any]:
    return {
        "site_id": site, "feature": feature, "value": value, "unit": unit,
        "quality": quality if (value is not None or quality in ("placeholder", "unavailable")) else "placeholder", "is_real": value is not None,
        "source": source, "note": note, "comparable": comparable, "method": METHOD, "retrieved_at": RETRIEVED,
    }


THRESHOLD_SOURCES = {
    10.0: ("Umbral 10°: requisito de pendiente de aterrizaje de Artemis III / HLS, «Surface slope for landing "
           "(100m): <10 deg» (Dwyer Cianciolo, NASA LaRC, 2024, https://ntrs.nasa.gov/api/citations/20240009596/"
           "downloads/ArtemisHLSUpdate_2024.pdf)"),
    15.0: ("Umbral 15°: pendiente que el rover lunar VIPER maneja en forma habitual, «VIPER can generally drive on a "
           "slope of up to 15 degrees» (https://science.nasa.gov/mission/viper/lunar-operations/); también el límite "
           "de aterrizaje de InSight en Marte (<15° a 84 m y 2 m, Golombek et al. 2017, doi:10.1007/s11214-016-0321-9)"),
    30.0: ("Umbral 30°: los operadores de Perseverance evitan terrenos que inclinen el rover más de 30°, «rover "
           "drivers avoid terrains that would tilt the rover more than 30 degrees» "
           "(https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/)"),
}


def slope_source(dem: str) -> str:
    d = o_grids.DEMS[dem]
    return ("%s, leído el %s: grilla 7×7 a 120 m (la misma de T). Pendiente de cada una de las 25 celdas "
            "interiores con los cuatro vecinos cardinales (base 240 m, misma fórmula que la pendiente central de T); "
            "valor = fracción de esas celdas con pendiente mayor al umbral. %s" % (d["name"], WHEN, d["url"]))


SCALE_NOTE = ("Escala: la pendiente se mide con base de 240 m, mucho mayor que la de los requisitos (metros), así que "
              "subestima el peligro real; es comparable entre sitios porque todos usan la misma grilla.")


def slope_rows(site_id: str, rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    dem = rec["dem"]
    z = rec.get("z")
    sea = bool(z) and dem == "earth" and hazard.is_sea_fill(z)
    fr = hazard.slope_fractions(z) if z and not sea else {}
    native = float(o_grids.DEMS[dem]["native_m"])
    extra = (" El DEM nativo es de %d m/píxel (> 120 m): la pendiente queda más suavizada que en ASTER 30 m." % native
             if native > 144 else "")
    for t in hazard.SLOPE_THRESHOLDS_DEG:
        fid = hazard.feature_id(t)
        v = fr.get(fid)
        if v is None:
            why = rec.get("error") or ("las 49 celdas valen 0 m en ASTER: el punto cae sobre agua (relleno de mar), "
                                       "no sobre terreno" if sea else None) or "menos de %d celdas con pendiente válida" % hazard.MIN_VALID_CELLS
            rows.append(row(site_id, fid, None, "fraction", "placeholder", slope_source(dem),
                            "sin dato: %s (a completar)" % why))
            continue
        rows.append(row(site_id, fid, round(v, 3), "fraction", "derived",
                        slope_source(dem) + " " + THRESHOLD_SOURCES[t] + ".", SCALE_NOTE + extra))
    return rows


def grid_latlon(site: Dict[str, Any]):
    """The 49 (lat, lon) points of the T grid, used to average Diviner pixels."""
    import terrain

    if site["body"] == "moon" and float(site["lat"]) < -80.0:
        return o_grids.local_grid_points(float(site["lat"]), float(site["lon"]))
    if site["body"] == "moon":
        return terrain.grid_points(float(site["lat"]), float(site["lon"]), o_grids.MOON_RADIUS_M)
    return [(float(site["lat"]), float(site["lon"]))]


def validate() -> int:
    """Pipelines against published values (CLAUDE.md §3.7)."""
    import rocks

    mean, cov = rocks.diviner_global_mean_60()
    print("Diviner RA media ±60°: %.4f (cobertura %.1f%%); Bandfield et al. 2011 ¶23: 0.004" % (mean, cov * 100))
    pf = rocks.mars_cell(19.09, -33.25, "irtm")
    print("IRTM en Mars Pathfinder (19,09 N, 33,25 W): %s %%; Golombek et al. 2003, doi:10.1029/2002JE002035: "
          "«total measured rock abundance (19%%)»" % pf)
    ok = abs(mean - 0.004) < 0.001 and pf is not None and abs(pf - 19.0) < 3.0
    print("OK" if ok else "FALLA")
    return 0 if ok else 1


def main(argv: List[str]) -> int:
    if "--fetch" in argv:
        return fetch()
    if "--validate" in argv:
        return validate()
    import rocks

    data = load_grids()
    out: List[Dict[str, Any]] = []
    for site in all_sites():
        rec = data["sites"].get(site["id"]) or {"dem": o_grids.dem_key(site), "z": None, "error": "grilla no leída"}
        out.extend(slope_rows(site["id"], rec))
        out.extend(rocks.rock_rows(site, row, grid_latlon(site)))
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print("wrote", len(out), "rows to", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
