from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app  # noqa: E402
from vector import feature_vector  # noqa: E402
from catalog import site_by_id  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "planetary"
    assert body["n_sites"] >= 14


def test_cors():
    r = client.get("/health", headers={"Origin": "http://127.0.0.1:8765"})
    assert r.headers.get("access-control-allow-origin") == "*"


def test_sites_requires_moon_or_mars():
    r = client.get("/sites", params={"body": "earth"})
    assert r.status_code == 400


def test_sites_filter_moon_and_mars():
    moon = client.get("/sites", params={"body": "moon"}).json()
    mars = client.get("/sites", params={"body": "mars"}).json()
    assert moon["n"] >= 1 and mars["n"] >= 1
    assert all(s["body"] == "moon" for s in moon["sites"])
    assert all(s["body"] == "mars" for s in mars["sites"])
    ids = {s["id"] for s in moon["sites"] + mars["sites"]}
    assert "shackleton-rim" in ids
    assert "jezero" in ids


def test_unknown_site():
    r = client.get("/sites/not-a-place/vector")
    assert r.status_code == 404


def test_vector_schema_and_no_invented_g_or_o():
    r = client.get("/sites/shackleton-rim/vector")
    assert r.status_code == 200
    vec = r.json()
    assert vec["id"] == "shackleton-rim"
    assert vec["body"] == "moon"
    for key in ("G", "T", "E", "Vo", "O"):
        assert key in vec["components"]
        assert "available" in vec["components"][key]
        assert "score_ready" in vec["components"][key]
    assert vec["components"]["G"]["available"] is False
    assert vec["components"]["G"]["score_ready"] is False
    assert vec["components"]["O"]["available"] is False
    # T must not include absolute elevation in the vector labels
    labels = vec["components"]["T"].get("vector_labels") or []
    assert "elevation" not in labels and "elevation_m" not in labels


def test_vector_does_not_fill_missing_slope():
    site = site_by_id("haworth")
    assert site is not None
    slope = ((site.get("features") or {}).get("slope") or {}).get("value")
    assert slope is None
    vec = feature_vector(site)
    metrics = vec["components"]["T"]["metrics"]
    assert metrics["slope_deg"]["value"] is None
    # score_ready may still be true if roughness/relief exist; haworth is mostly empty
    # either way, missing values stay None
    if vec["components"]["T"]["available"]:
        assert any(v is None or k != "slope_deg" for k, v in zip(vec["components"]["T"]["vector_labels"], vec["components"]["T"]["vector"]))


# --- Sitios del documento HexAstra (Marius Hills, Utopia Planitia, Arsia Mons) ---

DOCUMENT_TARGETS = {
    "marius-hills": ("moon", 14.0917, -56.7701, "lroc.im-ldi.com/atlases/pits/1"),
    "utopia-planitia": ("mars", 48.27, 134.28, "giss.nasa.gov/tools/mars24"),
    "arsia-mons": ("mars", -8.26, -120.09, "planetarynames.wr.usgs.gov/Feature/394"),
}


@pytest.mark.parametrize("site_id", sorted(DOCUMENT_TARGETS))
def test_document_target_listed_with_cited_coordinates(site_id):
    body, lat, lon, url = DOCUMENT_TARGETS[site_id]
    listed = client.get("/sites", params={"body": body}).json()["sites"]
    site = next((s for s in listed if s["id"] == site_id), None)
    assert site is not None, site_id
    assert site["body"] == body
    assert site["lat"] == pytest.approx(lat)
    assert site["lon"] == pytest.approx(lon)
    assert url in site["coord_source"]


@pytest.mark.parametrize("site_id", sorted(DOCUMENT_TARGETS))
def test_document_target_lon_conventions_agree(site_id):
    site = site_by_id(site_id)
    assert site is not None
    assert -180 <= site["lon"] <= 180
    assert site["lon_east_0_360"] == pytest.approx(site["lon"] % 360)


ALLOWED_QUALITY = {"measured", "derived", "modeled", "convention"}


@pytest.mark.parametrize("site_id", sorted(DOCUMENT_TARGETS))
def test_document_target_values_are_sourced_or_marked_null(site_id):
    feats = site_by_id(site_id)["features"]
    for key, item in feats.items():
        if item["value"] is None:
            assert item["quality"] == "placeholder", key
            assert "a completar" in item["note"], key
            continue
        assert item["quality"] in ALLOWED_QUALITY, key
        if item["quality"] != "convention":
            assert "http" in item["source"], key


@pytest.mark.parametrize("site_id", sorted(DOCUMENT_TARGETS))
def test_document_target_topography_comes_from_usgs_dem(site_id):
    feats = site_by_id(site_id)["features"]
    for key in ("relative_relief", "slope", "roughness"):
        assert feats[key]["value"] is not None, key
        assert feats[key]["quality"] == "derived"
        assert "planetarymaps.usgs.gov" in feats[key]["source"]
    assert feats["precip_mm"]["quality"] == "convention" and feats["precip_mm"]["value"] == 0.0


def test_marius_hills_thermal_is_diviner_surface_temperature():
    feats = site_by_id("marius-hills")["features"]
    for key in ("temp_mean", "temp_diurnal_range"):
        assert feats[key]["quality"] == "measured"
        assert "LRO-L-DLRE-5-GCP-V1.0" in feats[key]["source"]
        assert "SUPERFICIE" in feats[key]["note"]


@pytest.mark.parametrize("site_id", sorted(DOCUMENT_TARGETS))
def test_document_target_vector_responds(site_id):
    r = client.get(f"/sites/{site_id}/vector")
    assert r.status_code == 200
    vec = r.json()
    assert vec["id"] == site_id
    assert set(vec["components"]) == {"G", "T", "E", "Vo", "O"}
    t = vec["components"]["T"]
    assert t["score_ready"] is True
    assert t["vector_labels"] == ["relative_relief_m", "slope_deg", "roughness_m"]
    assert all(v is not None for v in t["vector"])
    assert vec["components"]["G"]["available"] is False
    assert vec["components"]["O"]["available"] is False


def test_jezero_and_gale_keep_mars24_points_and_cite_iau_centres():
    jezero = site_by_id("jezero")
    gale = site_by_id("gale")
    assert (jezero["lat"], jezero["lon"]) == (18.44, 77.45)
    assert (gale["lat"], gale["lon"]) == (-4.59, 137.44)
    assert "Feature/14300" in jezero["coord_source"]
    assert "Feature/2071" in gale["coord_source"]


def test_dbsource_is_identical_in_both_services():
    here = (ROOT / "dbsource.py").read_text(encoding="utf-8")
    other = (ROOT.parent / "earth" / "dbsource.py").read_text(encoding="utf-8")
    assert here == other


def test_bodies_values_are_sourced_or_marked_null():
    r = client.get("/bodies")
    assert r.status_code == 200
    bodies = r.json()["bodies"]
    assert set(bodies) == {"earth", "moon", "mars"}
    assert bodies["mars"]["gravity_m_s2"]["value"] == 3.73
    for body in bodies.values():
        for key, item in body.items():
            if not isinstance(item, dict):
                continue
            if item["value"] is None:
                assert "a completar" in item["note"], key
            else:
                assert "http" in item["source"], key


def test_bodies_radiation_keeps_published_units_and_scope():
    bodies = client.get("/bodies").json()["bodies"]
    earth = bodies["earth"]["surface_dose_msv_day"]
    moon = bodies["moon"]["surface_dose_msv_day"]
    assert earth["value"] == pytest.approx(0.33 / 365)
    assert earth["quality"] == "modeled"
    assert "UNSCEAR_2024_Report_Vol.II.pdf" in earth["source"]
    assert "promedio mundial" in earth["note"]
    assert "magnitudes distintas" in earth["note"]
    assert moon["value"] == pytest.approx(1369 / 1000)
    assert moon["quality"] == "measured"
    assert "PMC7518862" in moon["source"]
    assert "partículas cargadas" in moon["note"]
    for item in (earth, moon):
        assert "2026-11-14" in item["source"]
        assert "America/Argentina/Buenos_Aires" in item["source"]


def test_moon_day_is_solar_not_sidereal():
    day = client.get("/bodies").json()["bodies"]["moon"]["day_length_h"]
    assert day["value"] == pytest.approx(29.53 * 24)
    assert day["quality"] == "derived"
    assert "Día solar" in day["note"]
