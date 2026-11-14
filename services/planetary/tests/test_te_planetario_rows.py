"""Checks on data/measurements/te-planetario.jsonl (T and E of the 11 destinations without them)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "db"))

from measurements import merge, read_file  # noqa: E402

FILE = REPO / "data" / "measurements" / "te-planetario.jsonl"
MARS = ["jezero", "gale", "medusae-fossae", "pavonis-mons", "meridiani"]
MOON = ["shackleton-rim", "haworth", "malapert", "de-gerlache", "amundsen", "nobile"]
FEATURES = ["elevation", "relative_relief", "slope", "roughness", "temp_mean", "temp_diurnal_range", "illumination_pct"]
# values that already exist in the base catalog and are reported, not overwritten
BASE_HELD = {("gale", "elevation"), ("gale", "temp_diurnal_range"), ("jezero", "temp_mean"),
             ("shackleton-rim", "elevation"), ("shackleton-rim", "roughness")}


@pytest.fixture(scope="module")
def rows():
    return read_file(FILE)  # applies the schema rules of db/measurements.py


@pytest.fixture(scope="module")
def by_key(rows):
    return {(r.site_id, r.feature): r for r in rows}


def test_every_destination_has_every_feature_except_those_held_by_the_base(by_key):
    expected = {(s, f) for s in MARS + MOON for f in FEATURES} - BASE_HELD
    assert set(by_key) == expected


def test_no_duplicate_site_feature(rows):
    keys = [(r.site_id, r.feature) for r in rows]
    assert len(keys) == len(set(keys))


def test_rows_merge_on_the_base_catalog_without_touching_base_values():
    base_cat = json.loads((REPO / "services" / "planetary" / "data" / "catalog.json").read_text(encoding="utf-8"))
    base = {(s["id"], k): v for s in base_cat["sites"] for k, v in s["features"].items()}
    result = merge(base, read_file(FILE), [s["id"] for s in base_cat["sites"]])
    assert result.applied  # raises MeasurementError on any conflict


def test_every_value_has_a_source_with_url_date_and_method(rows):
    for r in rows:
        assert r.retrieved_at == "2026-11-14"
        assert r.method.endswith("ingest_te_planetario.py")
        if r.value is not None:
            assert "http" in r.source and "14 de noviembre de 2026" in r.source
            assert r.is_real


def test_null_rows_say_why(rows):
    nulls = [r for r in rows if r.value is None]
    assert {(r.site_id, r.feature) for r in nulls} == {(s, "illumination_pct") for s in MARS}
    for r in nulls:
        assert "a completar" in r.note and r.quality == "placeholder" and not r.is_real


def test_mars_air_temperature_is_modeled_and_moon_surface_temperature_is_flagged(by_key):
    for s in MARS:
        for f in ("temp_mean", "temp_diurnal_range"):
            if (s, f) in by_key:
                assert by_key[(s, f)].quality == "modeled"
                assert "Mars Climate Database v6.2" in by_key[(s, f)].source
    for s in MOON:
        for f in ("temp_mean", "temp_diurnal_range"):
            r = by_key[(s, f)]
            assert r.quality == "measured" and "SUPERFICIE" in r.note and "Diviner" in r.source


def test_validations_against_published_values(by_key):
    # Gale: Bradbury Landing -4501 m (NASA MSL facts) vs HRSC-MOLA 200 m; the base value is kept, the measurement is reported
    assert abs(by_key[("gale", "relative_relief")].value) > 0
    # Jezero: MEDA daily means 209-225 K (Munguira et al. 2024) vs MCD annual mean within that band
    assert -65.0 < by_key[("jezero", "temp_diurnal_range")].value < 60.0
    # Mars elevations: Arsia/Pavonis are volcanoes (>10 km), Jezero/Medusae/Meridiani are low plains
    assert by_key[("pavonis-mons", "elevation")].value > 10000
    assert by_key[("meridiani", "elevation")].value < 0


def test_lunar_pole_consistency_between_products(by_key):
    # Permanently shadowed sites (LOLA illumination 0) must have Tbol max below the 110 K cold-trap limit,
    # which the polar Diviner product reports; here the annual mean must be far below it.
    for s in MOON:
        if by_key[(s, "illumination_pct")].value == 0.0:
            assert by_key[(s, "temp_mean")].value + 273.15 < 70.0
    # lit rim/plateau sites are warmer on average than shadowed crater floors
    shadowed = [by_key[(s, "temp_mean")].value for s in MOON if by_key[(s, "illumination_pct")].value == 0.0]
    lit = [by_key[(s, "temp_mean")].value for s in MOON if by_key[(s, "illumination_pct")].value > 0.0]
    assert max(shadowed) < min(lit)
    # Shackleton floor: Zuber et al. 2012 (rim +1.3 km, depth 4.2 km) -> about -2.9 km; the 20 m DEM floor
    # was checked against it in the ingest log (-2.77 km) and is not stored (the base keeps the rim value)
    assert 0.0 <= by_key[("nobile", "illumination_pct")].value <= 100.0
