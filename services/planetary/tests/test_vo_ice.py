"""Tests for services/planetary/scripts/ingest_ice.py (Diviner PRP and Odyssey GRS)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PLANETARY = Path(__file__).resolve().parents[1]
REPO = PLANETARY.parents[1]

spec = importlib.util.spec_from_file_location("ingest_ice", PLANETARY / "scripts" / "ingest_ice.py")
ice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ice)
sys.path.insert(0, str(REPO / "db"))
from measurements import read_file  # noqa: E402

PRP_LINE = ("   299.52036,   -299.52036,  -1685.56519,    299.02863,   -299.52850,  -1685.65479,    299.03738,"
            "   -299.03738,  -1685.74780,   -45.015949249,   -75.905227661,     0.579086423,  162.934,  272.164,  -999.00000")


def test_parse_prp_line():
    assert ice.parse_prp_line(PRP_LINE) == pytest.approx((-75.905227661, -45.015949249, 162.934, 272.164, -999.0))
    assert ice.parse_prp_line("tri1_x, tri1_y, header") is None


def test_filter_prp_keeps_only_nearby_triangles():
    target = {"id": "t", "lat": -75.9, "lon": -45.0}
    kept = list(ice.filter_prp([PRP_LINE], [target], search_km=5.0))
    assert len(kept) == 1 and kept[0]["dist_km"] < 1.0
    far = {"id": "f", "lat": -80.0, "lon": -45.0}
    assert list(ice.filter_prp([PRP_LINE], [far], search_km=5.0)) == []


def test_moon_stats_fractions():
    rows = [{"site_id": "s", "dist_km": 1, "ice_depth_m": d, "temp_max_k": t}
            for d, t in ((0.0, 80), (0.5, 100), (-999.0, 250), (-1.0, 60))]
    rows.append({"site_id": "s", "dist_km": 9, "ice_depth_m": 0.0, "temp_max_k": 50})  # outside 5 km
    st = ice.moon_stats(rows)["s"]
    assert st["n"] == 4
    assert st["stable_frac"] == 0.5 and st["surface_frac"] == 0.25 and st["depth_min"] == 0.0
    assert st["code_m1_frac"] == 0.25 and st["code_m1_tmax_max"] == 60  # undocumented code kept apart


def test_moon_index_null_until_code_is_confirmed():
    st = {"n": 100, "stable_frac": 0.5, "surface_frac": 0.1, "depth_min": 0.0, "tmax_median": 90.0,
          "tmax_min": 40.0, "code_m1_frac": 0.3, "code_m1_tmax_max": 99.0}
    rows = {r["feature"]: r for r in ice.moon_rows([{"id": "h", "lat": -86.9, "lon": -4.0}], {"h": st})}
    assert rows["moon_ice_stable_frac"]["value"] == 0.5
    assert rows["moon_prp_code_m1_frac"]["value"] == 0.3
    idx = rows["water_ice_indicator"]
    assert idx["value"] is None and "a completar" in idx["note"] and "0.800" in idx["note"]


def test_grs_bin_and_parse():
    assert ice.grs_bin(18.44, 77.45) == (17.5, 77.5)
    assert ice.grs_bin(-1.95, -5.53) == (-2.5, 352.5)
    grid = ice.parse_grs("  2.5    7.5    3.000    0.300    0.400\r\n-87.5    2.5 9999.999 9999.999 9999.999\r\n")
    assert grid[(2.5, 7.5)] == (3.0, 0.3)
    assert grid[(-87.5, 2.5)] == (None, None)


def test_grs_raw_matches_published_range():
    """Boynton et al. 2007: water-equivalent H 1.5-7.5 wt%, max near Apollinaris Patera."""
    grid = ice.parse_grs(ice.MARS_RAW.read_text(encoding="ascii"))
    vals = {k: v[0] for k, v in grid.items() if v[0] is not None}
    assert 1.5 <= min(vals.values()) and max(vals.values()) <= 7.5
    top = max(vals, key=vals.get)
    assert abs(top[0] - (-8.4)) <= 5 and abs(top[1] - 174.4) <= 5


def test_mars_index_is_never_invented():
    rows = ice.mars_rows([{"id": "m", "lat": 18.44, "lon": 77.45}], {(17.5, 77.5): (3.5, 0.3)})
    by = {r["feature"]: r for r in rows}
    assert by["mars_grs_h2o_wt_pct"]["value"] == 3.5
    assert by["water_ice_indicator"]["value"] is None and "a completar" in by["water_ice_indicator"]["note"]


def test_moon_rows_null_outside_prp():
    rows = ice.moon_rows([{"id": "marius", "lat": 14.09, "lon": -56.77}], {})
    assert all(r["value"] is None and "a completar" in r["note"] for r in rows)


def test_hielo_file_planetary_rows():
    path = REPO / "data" / "measurements" / "vo-hielo.jsonl"
    if not path.exists():
        pytest.skip("todavía no generado")
    targets = json.loads(ice.CATALOG.read_text(encoding="utf-8"))["sites"]
    rows = [r for r in read_file(path) if r.method == ice.METHOD]
    assert {r.site_id for r in rows} == {t["id"] for t in targets}
    for r in rows:
        if r.value is not None:
            assert "pds-geosciences.wustl.edu" in r.source
            if r.feature in ("water_ice_indicator", "moon_ice_stable_frac", "moon_ice_surface_frac"):
                assert 0.0 <= r.value <= 1.0
