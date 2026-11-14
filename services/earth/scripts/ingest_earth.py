#!/usr/bin/env python3
"""Build the worldwide Earth catalog: geocode, DEM, climate, water, optional NDVI, Sigma.

Never invents numbers. Failures are stored as null + quality=unavailable.
Resumes from data/ingest_cache.json if present.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a script from services/earth or from repo root.
HERE = Path(__file__).resolve().parent
EARTH_ROOT = HERE.parent
if str(EARTH_ROOT) not in sys.path:
    sys.path.insert(0, str(EARTH_ROOT))

from geocode import assign_country_with_fallback  # noqa: E402
from covariance import fit_from_samples  # noqa: E402
from clients.opentopo import batch_elevations, grid_points, subwindow_samples, terrain_metrics  # noqa: E402
from clients.openmeteo import climatology  # noqa: E402
from clients.overpass import has_liquid_water  # noqa: E402
from clients import ornl_ndvi  # noqa: E402

DATA = EARTH_ROOT / "data"
SEED = DATA / "sites_seed.json"
CACHE = DATA / "ingest_cache.json"
CATALOG = DATA / "catalog.json"
COVPATH = DATA / "covariance.json"
GRID_N = 7
SPACING_M = 120.0
DATASET = "aster30m"
# America/Buenos_Aires is UTC-3; record both.
WHEN = "14 de noviembre de 2026 (America/Buenos_Aires)"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def measurement(value, unit, source, quality, is_real):
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "quality": quality,
        "is_real": is_real,
    }


def main() -> int:
    seed = load_json(SEED, None)
    if not seed:
        print("missing seed", SEED)
        return 1
    cache = load_json(CACHE, {"sites": {}})
    sites_out = cache.setdefault("sites", {})
    ndvi_disabled = cache.get("ndvi_disabled")
    water_disabled = cache.get("water_disabled")
    cov_samples = cache.setdefault("cov_samples", [])

    for raw in seed["sites"]:
        sid = raw["id"]
        rec = sites_out.get(sid) or {}
        print("===", sid, "===", flush=True)
        # geocode always (cheap, local)
        geo = assign_country_with_fallback(raw["lat"], raw["lon"])
        rec["id"] = sid
        rec["body"] = "earth"
        rec["name"] = raw["name"]
        rec["short_name"] = raw.get("short_name")
        rec["lat"] = raw["lat"]
        rec["lon"] = raw["lon"]
        rec["coord_source"] = raw["coord_source"]
        rec["summary"] = raw.get("summary")
        rec["analog_types"] = raw.get("analog_types") or []
        rec["known_level"] = raw.get("known_level")
        rec["highlight_less_studied"] = bool(raw.get("highlight_less_studied"))
        rec["featured"] = bool(raw.get("featured"))
        rec["featured_label"] = raw.get("featured_label")
        rec["featured_rank"] = raw.get("featured_rank")
        rec["featured_note"] = raw.get("featured_note")
        rec["continent"] = geo.get("continent")
        rec["country_iso"] = geo.get("country_iso")
        rec["country_name"] = geo.get("country_name")
        rec["country_source"] = geo.get("source")
        rec["country_found"] = bool(geo.get("found"))

        if not rec.get("dem"):
            try:
                pts, dlat, dlon = grid_points(raw["lat"], raw["lon"], n=GRID_N, spacing_m=SPACING_M)
                z = batch_elevations(pts, dataset=DATASET)
                metrics = terrain_metrics(z, GRID_N, SPACING_M)
                samples = subwindow_samples(z, GRID_N, SPACING_M, win=3)
                rec["dem"] = {
                    "dataset": DATASET,
                    "spacing_m": SPACING_M,
                    "grid_n": GRID_N,
                    "center": metrics,
                    "n_subwindow_samples": len(samples),
                    "source": (
                        "OpenTopoData %s (ASTER GDEM v3) on a %sx%s grid at %s m spacing, "
                        "consulted %s. Centre slope from cardinal neighbours; "
                        "relative relief = max-min of valid cells; roughness = sample std. dev. "
                        "https://api.opentopodata.org/v1/%s"
                        % (DATASET, GRID_N, GRID_N, SPACING_M, WHEN, DATASET)
                    ),
                }
                rec["_cov_samples"] = samples
                print("  DEM elev=", metrics.get("elevation_m"), "slope=", metrics.get("slope_deg"), "relief=", metrics.get("relative_relief_m"), flush=True)
                time.sleep(1.05)
            except Exception as exc:
                rec["dem"] = {"error": str(exc), "center": {}}
                rec["_cov_samples"] = []
                print("  DEM FAIL", exc, flush=True)
                time.sleep(1.0)

        climate_ok = rec.get("climate") and not rec.get("climate", {}).get("error") and rec.get("climate", {}).get("t2m_mean_C") is not None
        if not climate_ok:
            try:
                rec["climate"] = climatology(raw["lat"], raw["lon"])
                print("  climate T=", rec["climate"].get("t2m_mean_C"), "P=", rec["climate"].get("mean_annual_precipitation_mm"), flush=True)
                time.sleep(2.5)
            except Exception as exc:
                rec["climate"] = {"error": str(exc)}
                print("  climate FAIL", exc, flush=True)
                time.sleep(8)

        # A previous Overpass attempt (even if value is null / unavailable) is not retried
        # on every ingest; inventing water would be worse than leaving the flag.
        water_done = rec.get("water") is not None
        if not water_done:
            if water_disabled:
                rec["water"] = {
                    "value": None,
                    "quality": "unavailable",
                    "is_real": False,
                    "source": "OSM Overpass skipped after repeated failures in this ingest (not guessed).",
                    "elements": 0,
                }
            else:
                rec["water"] = has_liquid_water(raw["lat"], raw["lon"])
                if rec["water"].get("value") is None:
                    cache["water_fails"] = cache.get("water_fails", 0) + 1
                    if cache["water_fails"] >= 3:
                        cache["water_disabled"] = True
                        water_disabled = True
                        print("  Overpass looks down; disabling further water calls.", flush=True)

            print("  water", rec["water"].get("value"), rec["water"].get("elements"), flush=True)
            time.sleep(0.8)

        if rec.get("ndvi") is None:
            if ndvi_disabled:
                rec["ndvi"] = {
                    "value": None,
                    "quality": "unavailable",
                    "is_real": False,
                    "source": "ORNL MOD13Q1 skipped after a previous timeout/error in this ingest (not guessed).",
                }
            else:
                try:
                    rec["ndvi"] = ornl_ndvi.mean_ndvi(raw["lat"], raw["lon"])
                    print("  ndvi", rec["ndvi"].get("value"), rec["ndvi"].get("quality"), flush=True)
                    if rec["ndvi"].get("value") is None and "timed out" in (rec["ndvi"].get("source") or "").lower() or "failed" in (rec["ndvi"].get("source") or "").lower():
                        # After two hard failures, skip the rest to finish ingest.
                        fails = cache.get("ndvi_fails", 0) + 1
                        cache["ndvi_fails"] = fails
                        if fails >= 2:
                            cache["ndvi_disabled"] = True
                            ndvi_disabled = True
                            print("  NDVI API looks down; disabling further calls.", flush=True)
                except Exception as exc:
                    rec["ndvi"] = {"value": None, "quality": "unavailable", "is_real": False, "source": "ORNL MOD13Q1 failed: %s" % exc}
                    cache["ndvi_fails"] = cache.get("ndvi_fails", 0) + 1
                    if cache["ndvi_fails"] >= 2:
                        cache["ndvi_disabled"] = True
                        ndvi_disabled = True

        sites_out[sid] = rec
        cache["sites"] = sites_out
        save_json(CACHE, cache)

    # Rebuild covariance samples from all sites (fresh list)
    all_samples = []
    for rec in sites_out.values():
        all_samples.extend(rec.get("_cov_samples") or [])
    cov = None
    if all_samples:
        cov = fit_from_samples(all_samples)
        cov["source"] = (
            "ASTER GDEM v3 via OpenTopoData, 3x3 subwindows inside a 7x7 grid (120 m) "
            "around each Earth candidate, %s. Ledoit-Wolf shrinkage. n=%s"
            % (WHEN, cov["n_samples"])
        )
        save_json(COVPATH, cov)
        print("covariance n=", cov["n_samples"], "shrinkage=", cov["shrinkage"], flush=True)

    catalog_sites = []
    for raw in seed["sites"]:
        rec = sites_out[raw["id"]]
        demc = (rec.get("dem") or {}).get("center") or {}
        climate = rec.get("climate") or {}
        water = rec.get("water") or {}
        ndvi = rec.get("ndvi") or {}
        dem_source = (rec.get("dem") or {}).get("source") or "OpenTopoData ASTER GDEM v3"
        features = {
            "elevation": measurement(
                demc.get("elevation_m"), "m", dem_source,
                "measured" if demc.get("elevation_m") is not None else "unavailable",
                demc.get("elevation_m") is not None,
            ),
            "relative_relief": measurement(
                None if demc.get("relative_relief_m") is None else round(demc["relative_relief_m"], 2),
                "m", dem_source,
                "derived" if demc.get("relative_relief_m") is not None else "unavailable",
                demc.get("relative_relief_m") is not None,
            ),
            "slope": measurement(
                None if demc.get("slope_deg") is None else round(demc["slope_deg"], 2),
                "deg", dem_source,
                "derived" if demc.get("slope_deg") is not None else "unavailable",
                demc.get("slope_deg") is not None,
            ),
            "roughness": measurement(
                None if demc.get("roughness_m") is None else round(demc["roughness_m"], 2),
                "m", dem_source,
                "derived" if demc.get("roughness_m") is not None else "unavailable",
                demc.get("roughness_m") is not None,
            ),
            "temp_mean": measurement(
                climate.get("t2m_mean_C"), "degC", climate.get("source_temperature"),
                "measured" if climate.get("t2m_mean_C") is not None else "unavailable",
                climate.get("t2m_mean_C") is not None,
            ),
            "temp_diurnal_range": measurement(
                climate.get("mean_diurnal_range_C"), "degC", climate.get("source_temperature"),
                "measured" if climate.get("mean_diurnal_range_C") is not None else "unavailable",
                climate.get("mean_diurnal_range_C") is not None,
            ),
            "precip_mm": measurement(
                climate.get("mean_annual_precipitation_mm"), "mm", climate.get("source_precipitation"),
                "measured" if climate.get("mean_annual_precipitation_mm") is not None else "unavailable",
                climate.get("mean_annual_precipitation_mm") is not None,
            ),
            "illumination_pct": measurement(
                None, "percent",
                "No sourced illumination / insolation product was sampled for this point.",
                "unavailable", False,
            ),
            "water_ice_indicator": measurement(
                None, None,
                "No sourced water-ice fraction was sampled; liquid water is stored separately from OSM Overpass.",
                "unavailable", False,
            ),
            "ndvi": measurement(
                ndvi.get("value"), "unitless", ndvi.get("source"),
                ndvi.get("quality") or "unavailable", bool(ndvi.get("is_real") and ndvi.get("value") is not None),
            ),
            "has_liquid_water": measurement(
                1.0 if water.get("value") is True else (0.0 if water.get("value") is False else None),
                "boolean_as_0_1", water.get("source"),
                water.get("quality") or "unavailable",
                water.get("is_real") is True and water.get("value") is not None,
            ),
        }
        catalog_sites.append({
            "id": rec["id"],
            "body": "earth",
            "name": rec["name"],
            "short_name": rec.get("short_name"),
            "lat": rec["lat"],
            "lon": rec["lon"],
            "coord_source": rec["coord_source"],
            "summary": rec.get("summary"),
            "analog_types": rec.get("analog_types"),
            "known_level": rec.get("known_level"),
            "highlight_less_studied": rec.get("highlight_less_studied"),
            "featured": rec.get("featured"),
            "featured_label": rec.get("featured_label"),
            "featured_rank": rec.get("featured_rank"),
            "featured_note": rec.get("featured_note"),
            "continent": rec.get("continent"),
            "country_iso": rec.get("country_iso"),
            "country_name": rec.get("country_name"),
            "country_source": rec.get("country_source"),
            "features": features,
        })

    catalog = {
        "meta": {
            "title": "Hexastra worldwide Earth analog-type catalog",
            "team": "Hexastra",
            "created": "2026-11-14",
            "timezone": "America/Buenos_Aires",
            "disclaimer": (
                "Coordinates are sourced. Continent and ISO-3166 alpha-2 come from Natural Earth 50m "
                "admin-0 point-in-polygon (not guessed). Topography is ASTER GDEM v3 via OpenTopoData "
                "(relative relief, slope, roughness). Climate is Open-Meteo ERA5/ERA5-Land 1991-2020. "
                "Liquid water is OSM Overpass. NDVI is ORNL MOD13Q1 when the API answers, otherwise null. "
                "No placeholder numeric values were filled in."
            ),
            "dem": "OpenTopoData aster30m (ASTER GDEM v3), 7x7 at 120 m, %s" % WHEN,
            "climate": "Open-Meteo archive, single ERA5 (0.25°) request for temperature and precipitation, 1991-01-01 to 2020-12-31.",
            "geocoding": "Natural Earth 50m admin-0 countries, point-in-polygon. ISO_A2, or ISO_A2_EH when ISO_A2 is -99.",
            "n_sites": len(catalog_sites),
        },
        "sites": catalog_sites,
        "covariance": cov,
    }
    save_json(CATALOG, catalog)
    print("wrote", CATALOG, "n=", len(catalog_sites), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
