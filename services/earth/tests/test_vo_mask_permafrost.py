"""Tests for the Vo ingest scripts on Earth: viability mask (NDVI, water) and permafrost."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

EARTH = Path(__file__).resolve().parents[1]
REPO = EARTH.parents[1]
MEAS = REPO / "data" / "measurements"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, EARTH / "scripts" / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mask = _load("ingest_mask")
perma = _load("ingest_permafrost")
sys.path.insert(0, str(REPO / "db"))
from measurements import read_file  # noqa: E402

SITE_IDS = {s["id"] for s in json.loads((EARTH / "data" / "catalog.json").read_text(encoding="utf-8"))["sites"]}


# ------------------------------------------------------------------ NDVI

def _ndvi(sid, ndvi, rel):
    return {"ID": sid, "MOD13Q1_061__250m_16_days_NDVI": str(ndvi), "MOD13Q1_061__250m_16_days_pixel_reliability": str(rel)}


def test_ndvi_uses_only_good_pixels():
    rows = [_ndvi("a", 0.1, 0)] * 3 + [_ndvi("a", 0.9, 3), _ndvi("a", 0.8, 1)]
    st = mask.ndvi_stats(rows)["a"]
    assert st["n_total"] == 5 and st["n_good"] == 3
    assert st["mean"] == pytest.approx(0.1)


def test_ndvi_row_null_when_too_few_good_composites():
    row = mask.ndvi_row("a", {"n_total": 230, "n_good": 5, "mean": 0.1, "median": 0.1, "p90": 0.1})
    assert row["value"] is None and row["quality"] == "unavailable" and "a completar" in row["note"]


def test_ndvi_row_measured_with_source_url():
    row = mask.ndvi_row("a", {"n_total": 230, "n_good": 200, "mean": 0.0812, "median": 0.08, "p90": 0.1})
    assert row["value"] == 0.0812 and row["quality"] == "measured" and "https://" in row["source"]


# ------------------------------------------------------------------ water

def _water(pid, year, cls):
    return {"ID": pid, "Date": "%s-01-01" % year, "MOD44W_061_seven_class": str(cls)}


def test_water_flag_majority_of_years_inland():
    assert mask.water_flag({"2015": 3, "2016": 5, "2017": 1}) == 1
    assert mask.water_flag({"2015": 1, "2016": 4, "2017": 1}) == 0  # ephemeral does not count
    assert mask.water_flag({"2015": 0, "2016": 6, "2017": 7}) == 0  # ocean never counts
    assert mask.water_flag({}) is None


def test_water_stats_separates_centre_and_neighbourhood():
    rows = [_water("s__0_0", 2015, 1), _water("s__1_0", 2015, 5), _water("s__0_0", 2016, 255)]
    st = mask.water_stats(rows)["s"]
    assert st["centre"] == {"2015": 1}
    assert 5 in st["neigh"]["2015"]
    row = mask.water_row("s", st)
    assert row["value"] == 0 and "entorno 3x3" in row["note"]


def test_ocean_pixel_is_null_not_zero():
    st = {"centre": {"2015": 0, "2016": 0, "2017": 1}, "neigh": {}}
    row = mask.water_row("s", st)
    assert row["value"] is None and row["quality"] == "unavailable" and "a completar" in row["note"]


def test_neighbourhood_is_3x3_around_site():
    pts = mask.neighbourhood({"id": "s", "lat": -20.0, "lon": -67.0})
    assert len(pts) == 9 and pts[4]["id"] == "s__0_0"
    assert pts[4]["latitude"] == -20.0 and pts[4]["longitude"] == -67.0


# ------------------------------------------------------------------ permafrost

def test_region_coverage():
    assert perma.region_of(75.0) == "nh"
    assert perma.region_of(-77.8) == "ant"
    assert perma.region_of(-24.0) is None


def test_pfr_stats_and_rows():
    rows = [{"site_id": "x", "pfr_centre_pct": "100", "pfr_3x3_pct": "90"},
            {"site_id": "x", "pfr_centre_pct": "80", "pfr_3x3_pct": "70"}]
    st = perma.pfr_stats(rows)["x"]
    assert st["centre_mean"] == 90.0
    pf = perma.permafrost_row({"id": "x", "lat": 75.0}, st)
    assert pf["value"] == 0.9 and pf["comparable"] is False
    idx = perma.index_row(pf)
    assert idx["feature"] == "water_ice_indicator" and idx["value"] == 0.9 and idx["quality"] == "derived"


def test_permafrost_null_outside_coverage():
    pf = perma.permafrost_row({"id": "x", "lat": -24.0}, None)
    assert pf["value"] is None and "a completar" in pf["note"]
    idx = perma.index_row(pf)
    assert idx["value"] is None and "a completar" in idx["note"]


# ------------------------------------------------------------------ versioned files

@pytest.mark.parametrize("fname, features", [
    ("vo-mascara.jsonl", {"ndvi", "has_liquid_water"}),
])
def test_mask_file_covers_all_sites(fname, features):
    path = MEAS / fname
    if not path.exists():
        pytest.skip("todavía no generado")
    rows = read_file(path)
    assert {r.site_id for r in rows} == SITE_IDS
    assert {r.feature for r in rows} == features
    assert len(rows) == len(SITE_IDS) * len(features)
    for r in rows:
        assert r.method == "services/earth/scripts/ingest_mask.py"
        if r.value is not None:
            assert "appeears" in (r.source or "").lower()
        if r.feature == "has_liquid_water" and r.value is not None:
            assert r.value in (0.0, 1.0)
        if r.feature == "ndvi" and r.value is not None:
            assert -1.0 <= r.value <= 1.0


def test_hielo_file_earth_rows():
    path = MEAS / "vo-hielo.jsonl"
    if not path.exists():
        pytest.skip("todavía no generado")
    rows = [r for r in read_file(path) if r.method == perma.METHOD]
    assert {r.site_id for r in rows} == SITE_IDS
    by = {(r.site_id, r.feature): r for r in rows}
    for sid in SITE_IDS:
        pf, idx = by[(sid, "permafrost_fraction")], by[(sid, "water_ice_indicator")]
        assert pf.value == idx.value
        if pf.value is not None:
            assert 0.0 <= pf.value <= 1.0 and pf.comparable is False
