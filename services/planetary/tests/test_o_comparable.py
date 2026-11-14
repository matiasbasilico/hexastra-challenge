"""Rows of data/measurements/o-comparable.jsonl and the pure helpers that produce them."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent
for p in (str(ROOT), str(ROOT / "scripts"), str(REPO / "db")):
    if p not in sys.path:
        sys.path.insert(0, p)

import rocks  # noqa: E402
from hazard import SLOPE_THRESHOLDS_DEG, feature_id, slope_fractions  # noqa: E402
from measurements import validate  # noqa: E402

JSONL = REPO / "data" / "measurements" / "o-comparable.jsonl"
FEATURES = REPO / "data" / "measurements" / "o-comparable.features.json"
GRIDS = ROOT / "data" / "o_comparable_grids.json"
SLOPE_IDS = [feature_id(t) for t in SLOPE_THRESHOLDS_DEG]


def rows():
    return [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]


def site_ids():
    out = {}
    for path in (ROOT / "data" / "catalog.json", REPO / "services" / "earth" / "data" / "catalog.json"):
        for s in json.loads(path.read_text(encoding="utf-8"))["sites"]:
            out[s["id"]] = s.get("body") or "earth"
    return out


# ------------------------------------------------------------------ helpers

def test_diviner_pixel_matches_the_label_geometry():
    # line 0 starts at 80 N, sample 0 at 0 E, 128 px/deg; west longitudes wrap to 0-360
    assert rocks.diviner_pixel(80.0, 0.0, 128, 80.0) == (0, 0)
    assert rocks.diviner_pixel(14.0917, -56.7701, 128, 80.0) == (int((80 - 14.0917) * 128), int(303.2299 * 128))
    assert rocks.diviner_pixel(-85.0, 11.4, 128, 80.0) is None


def test_diviner_nodata_and_scale():
    assert rocks.diviner_value(-32768) is None
    assert rocks.diviner_value(6) == pytest.approx(0.006)


def test_parse_vicar_reads_little_endian_ints():
    label = "LBLSIZE=100 FORMAT='FULL' TYPE='IMAGE' NL=2 NS=2 NB=1".ljust(100)
    blob = label.encode("latin1") + struct.pack("<4i", 19, 0, 7, 22)
    assert rocks.parse_vicar(blob) == [[19, 0], [7, 22]]


def test_wms_bbox_is_the_8ppd_cell_containing_the_point():
    w, s, e, n = rocks.wms_cell_bbox(18.44, 77.45, 8)
    assert (w, s, e, n) == (77.375, 18.375, 77.5, 18.5)
    assert w <= 77.45 < e and s <= 18.44 < n
    w, _, _, _ = rocks.wms_cell_bbox(1.48, 247.04, 8)  # east 0-360 -> -180..180
    assert w == pytest.approx(-113.0)


# ------------------------------------------------------------------ rows

def test_every_row_passes_the_loader_rules():
    for i, r in enumerate(rows(), start=1):
        validate(r, "o-comparable.jsonl:%d" % i)


def test_all_74_sites_have_every_slope_fraction_and_rock_row():
    ids = site_ids()
    got = {(r["site_id"], r["feature"]) for r in rows()}
    assert len(ids) == 74
    for sid, body in ids.items():
        for f in SLOPE_IDS + ["rock_abundance_pct"]:
            assert (sid, f) in got, (sid, f)
        assert ((sid, "rock_abundance_irtm_pct") in got) == (body == "mars")


def test_no_duplicate_keys_and_features_are_declared():
    keys = [(r["site_id"], r["feature"]) for r in rows()]
    assert len(keys) == len(set(keys))
    declared = json.loads(FEATURES.read_text(encoding="utf-8"))
    assert {r["feature"] for r in rows()} <= set(declared)


def test_slope_rows_recompute_from_the_stored_grids():
    grids = json.loads(GRIDS.read_text(encoding="utf-8"))["sites"]
    for r in rows():
        if r["feature"] not in SLOPE_IDS or r["value"] is None:
            continue
        fr = slope_fractions(grids[r["site_id"]]["z"])
        assert r["value"] == pytest.approx(fr[r["feature"]], abs=5e-4)
        assert 0.0 <= r["value"] <= 1.0


def test_fractions_are_monotonic_in_the_threshold():
    by = {}
    for r in rows():
        if r["feature"] in SLOPE_IDS and r["value"] is not None:
            by.setdefault(r["site_id"], {})[r["feature"]] = r["value"]
    for sid, v in by.items():
        assert v["slope_frac_gt_10deg"] >= v["slope_frac_gt_15deg"] >= v["slope_frac_gt_30deg"], sid


def test_each_threshold_cites_its_source():
    for r in rows():
        if r["feature"] in SLOPE_IDS and r["value"] is not None:
            assert "ntrs.nasa.gov" in r["source"] or "science.nasa.gov" in r["source"]


def test_earth_rock_abundance_is_null_not_a_proxy():
    ids = site_ids()
    for r in rows():
        if r["feature"] == "rock_abundance_pct" and ids[r["site_id"]] == "earth":
            assert r["value"] is None and r["quality"] == "unavailable" and r["comparable"] is False


def test_lunar_south_pole_has_no_rock_value():
    for r in rows():
        if r["feature"] == "rock_abundance_pct" and r["site_id"] in (
                "shackleton-rim", "haworth", "malapert", "de-gerlache", "amundsen", "nobile"):
            assert r["value"] is None and "80°" in r["note"]


def test_bockfjorden_sea_grid_is_null():
    for r in rows():
        if r["site_id"] == "bockfjorden" and r["feature"] in SLOPE_IDS:
            assert r["value"] is None and "agua" in r["note"]
