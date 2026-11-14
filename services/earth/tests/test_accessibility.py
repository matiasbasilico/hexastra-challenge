from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
for extra in (ROOT, ROOT / "scripts", REPO / "db"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import accessibility as acc  # noqa: E402
import ingest_accessibility as ing  # noqa: E402

KM_PER_DEG_EQUATOR = 110.574  # one degree of latitude at the equator (WGS84)
MEASUREMENTS = REPO / "data" / "measurements" / "o-tierra.jsonl"
FEATURE_DEFS = REPO / "data" / "measurements" / "o-tierra.features.json"
TODAY = "2026-11-14"


def test_geodesic_matches_vincenty_reference():
    # Vincenty (1975) test line Flinders Peak - Buninyong: 54 972.271 m
    km = acc.geodesic_km(-37.95103342, 144.42486789, -37.65282114, 143.92649553)
    assert km == pytest.approx(54.972271, abs=1e-4)


def test_bbox_contains_circle_and_splits_at_antimeridian():
    (west, south, east, north), = acc.bboxes_for_radius(0.0, 10.0, 111.0)
    assert west < 9.0 and east > 11.0 and south < -1.0 and north > 1.0
    assert len(acc.bboxes_for_radius(0.0, 179.9, 100.0)) == 2
    assert acc.bboxes_for_radius(89.9, 0.0, 100.0) == [(-180.0, pytest.approx(88.96, abs=0.1), 180.0, 90.0)]


def test_distance_to_polyline_uses_segment_interior_not_only_vertices():
    x = np.array([-10.0, 10.0, 50.0, 60.0])
    y = np.array([3.0, 3.0, 50.0, 50.0])
    part = np.array([0, 0, 1, 1])
    dist, owner = acc.min_distance_to_polylines(x, y, part)
    assert dist == pytest.approx(3.0) and owner == 0
    # the vertices 10,3 -> 50,50 belong to different lines: no segment between them
    far, _ = acc.min_distance_to_polylines(np.array([10.0, -10.0]), np.array([-1.0, 1.0]), np.array([0, 1]))
    assert far == pytest.approx(np.hypot(10.0, 1.0))
    assert acc.min_distance_to_polylines(np.array([]), np.array([]), np.array([])) == (None, None)


def test_nearest_road_reads_a_vector_layer(tmp_path):
    path = tmp_path / "roads.geojson"
    line = lambda coords, sid: {"type": "Feature", "properties": {"SOURCEID": sid, "FCLASS": 1},
                                "geometry": {"type": "LineString", "coordinates": coords}}
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        line([[-1.0, 0.5], [1.0, 0.5]], "near"), line([[-1.0, 3.0], [1.0, 3.0]], "far")]}), encoding="utf-8")
    hit = acc.nearest_road(path, 0.0, 0.0, columns=("SOURCEID", "FCLASS"))
    assert hit["distance_km"] == pytest.approx(0.5 * KM_PER_DEG_EQUATOR, rel=1e-3)
    assert hit["attributes"]["SOURCEID"] == "near"
    assert acc.nearest_road(path, 0.0, 120.0, radii_km=(100.0,)) is None


def test_airports_filter_closed_and_heliports_and_scheduled(tmp_path):
    csv_path = tmp_path / "airports.csv"
    csv_path.write_text(
        "ident,type,name,latitude_deg,longitude_deg,iso_country,scheduled_service\n"
        "HELI,heliport,Helipad,0.01,0,AR,no\n"
        "OLD,closed,Closed strip,0.02,0,AR,no\n"
        "STRIP,small_airport,Strip,0.1,0,AR,no\n"
        "BIG,large_airport,Big,1.0,0,AR,yes\n"
        "BAD,small_airport,No coords,,,AR,no\n", encoding="utf-8")
    airports = acc.load_airports(csv_path)
    assert [a["ident"] for a in airports] == ["STRIP", "BIG"]
    assert acc.nearest_airport(airports, 0.0, 0.0)["ident"] == "STRIP"
    big = acc.nearest_airport(airports, 0.0, 0.0, scheduled_only=True)
    assert big["ident"] == "BIG" and big["distance_km"] == pytest.approx(KM_PER_DEG_EQUATOR, rel=1e-3)
    assert acc.nearest_airport([], 0.0, 0.0) is None


def write_raster(path: Path, data: np.ndarray, west: float, north: float, cell: float) -> None:
    import rasterio
    from rasterio.transform import from_origin

    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1,
                       dtype="float32", crs="EPSG:4326", transform=from_origin(west, north, cell, cell), nodata=-9999.0) as dst:
        dst.write(data.astype("float32"), 1)


def test_population_sums_only_cells_inside_the_radius(tmp_path):
    tif = tmp_path / "pop.tif"
    data = np.ones((200, 200))  # 0.01 deg cells over [-1, 1] x [-1, 1]
    data[:, :100] = -9999.0     # western half without data
    write_raster(tif, data, -1.0, 1.0, 0.01)
    res = acc.population_within(tif, 0.0, 0.0, radius_km=50.0)
    cell_km2 = (0.01 * 111.32) * (0.01 * KM_PER_DEG_EQUATOR)
    assert res["value"] == pytest.approx(np.pi * 50.0 ** 2 / 2 / cell_km2, rel=0.02)
    assert res["valid_cells"] == pytest.approx(res["cells"] / 2, rel=0.02)


def test_population_is_none_without_data(tmp_path):
    tif = tmp_path / "empty.tif"
    write_raster(tif, np.full((50, 50), -9999.0), -1.0, 1.0, 0.04)
    assert acc.population_within(tif, 0.0, 0.0)["value"] is None
    assert acc.population_within(tif, 60.0, 100.0)["value"] is None  # outside the raster


def test_practicality_index_bounds_and_renormalisation():
    best = acc.practicality_index(0.5, 10.0, 500000.0, 300.0)
    worst = acc.practicality_index(800.0, 2000.0, 0.0, 6000.0)
    assert best["P"] == pytest.approx(100.0) and worst["P"] == pytest.approx(0.0)
    mid = acc.practicality_index(17.32, 158.1, 3162.0, 4000.0)  # geometric midpoints, altitude midpoint
    assert mid["P"] == pytest.approx(50.0, abs=0.1)
    partial = acc.practicality_index(None, 10.0, None, 300.0)
    assert partial["P"] == pytest.approx(100.0) and partial["coverage"] == pytest.approx(0.45)
    assert partial["scores"]["road"] is None
    assert acc.practicality_index(None, None, None, None) == {
        "P": None, "scores": {"road": None, "airport": None, "population": None, "altitude": None}, "coverage": 0.0}


def test_rows_without_inputs_are_null_with_note():
    from measurements import validate

    site = {"id": "pali-aike", "lat": -51.995, "lon": -70.155}
    rows = [ing.road_row(site, None, TODAY), ing.population_row(site, None, TODAY)] + ing.airport_rows(site, None, TODAY)
    assert [r["feature"] for r in rows] == ["dist_road_km", "population_50km", "dist_airport_km", "dist_airport_scheduled_km"]
    for n, r in enumerate(rows):
        assert r["value"] is None and r["quality"] == "unavailable" and not r["is_real"]
        validate(r, "o-tierra.jsonl:%s" % n)


def test_antarctic_sites_get_no_road_distance(tmp_path):
    row = ing.road_row({"id": "base-marambio", "lat": -64.24, "lon": -56.62}, tmp_path / "unused.gdb", TODAY)
    assert row["value"] is None and "Antártida" in row["note"] and "a completar" in row["note"].lower()


def test_validation_flags_a_wrong_airport_catalog():
    sites = {"haughton": {"lat": 75.38333333, "lon": -89.66666667}, "base-marambio": {"lat": -64.241769, "lon": -56.623225}}
    good = [{"ident": "CYRB", "name": "Resolute Bay", "type": "medium_airport", "lat": 74.7169, "lon": -94.9694, "scheduled": True, "country": "CA"},
            {"ident": "SAWB", "name": "Marambio", "type": "small_airport", "lat": -64.2383, "lon": -56.6308, "scheduled": False, "country": "AQ"}]
    assert ing.validate(sites, good) == []
    assert len(ing.validate(sites, good[:1])) == 1


# ---- the committed measurement file ----

@pytest.fixture(scope="module")
def rows():
    if not MEASUREMENTS.exists():
        pytest.skip("o-tierra.jsonl todavía no generado")
    return [json.loads(line) for line in MEASUREMENTS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_file_has_every_site_and_feature_once(rows):
    sites = [s["id"] for s in json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))["sites"]]
    keys = [(r["site_id"], r["feature"]) for r in rows]
    assert sorted(keys) == sorted((s, f) for s in sites for f in ing.FEATURES)
    assert set(json.loads(FEATURE_DEFS.read_text(encoding="utf-8"))) == set(ing.FEATURES)


def test_file_rows_are_sourced_non_negative_and_never_comparable(rows):
    from measurements import validate

    for n, r in enumerate(rows, start=1):
        validate(r, "o-tierra.jsonl:%s" % n)
        assert r["comparable"] is False and r["method"] == ing.METHOD
        if r["value"] is None:
            continue
        assert r["value"] >= 0 and "consultado" in r["source"]
        assert ("ourairports" if "airport" in r["feature"] else "earthdata.nasa.gov") in r["source"]


def test_file_known_values(rows):
    by = {(r["site_id"], r["feature"]): r for r in rows}
    assert by[("haughton", "dist_airport_km")]["value"] == pytest.approx(169.8, abs=0.5)
    assert "CYRB" in by[("haughton", "dist_airport_km")]["note"]
    assert by[("base-marambio", "dist_airport_km")]["value"] < 2.0
    for sid in ("base-marambio", "base-esperanza", "university-valley", "taylor-valley"):
        assert by[(sid, "dist_road_km")]["value"] is None
    for r in rows:
        if r["feature"] == "dist_airport_scheduled_km" and r["value"] is not None:
            assert r["value"] >= by[(r["site_id"], "dist_airport_km")]["value"]
