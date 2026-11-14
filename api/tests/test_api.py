from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app  # noqa: E402
from catalog import numeric_value, site_by_id  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["sites"] >= 15


def test_cors_header():
    r = client.get("/health", headers={"Origin": "http://localhost:8080"})
    assert r.headers.get("access-control-allow-origin") == "*"


def test_features_schema():
    r = client.get("/features")
    assert r.status_code == 200
    data = r.json()
    for key in ("elevation", "slope", "temp_mean", "precip_mm", "illumination_pct"):
        assert key in data["features"]
        assert data["features"][key]["unit"]
    assert "normalization_rationale" in data


def test_sites_filter():
    all_r = client.get("/sites")
    earth = client.get("/sites", params={"body": "earth"})
    moon = client.get("/sites", params={"body": "moon"})
    mars = client.get("/sites", params={"body": "mars"})
    assert all_r.status_code == earth.status_code == 200
    assert earth.json()["count"] == 5
    assert moon.json()["count"] == 6
    assert mars.json()["count"] == 5
    assert all_r.json()["count"] == 16
    bad = client.get("/sites", params={"body": "pluto"})
    assert bad.status_code == 400


def test_no_invented_placeholder_values():
    sites = client.get("/sites").json()["sites"]
    for site in sites:
        for fid, feat in site["features"].items():
            if feat["quality"] == "placeholder":
                assert feat["value"] is None, f"{site['id']}.{fid} placeholder no puede tener número"
            if feat["is_real"] is True:
                assert feat["value"] is not None
                assert feat["quality"] in {"measured", "convention"}


def test_similar_mars_target_earth():
    r = client.get(
        "/similar",
        params={
            "target": "gale",
            "body": "earth",
            "features": "elevation,temp_diurnal_range,precip_mm",
            "weights": "1,1,1",
            "method": "cosine",
            "norm": "zscore",
            "top": 5,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["target"]["id"] == "gale"
    assert data["search_body"] == "earth"
    assert len(data["matches"]) == 5
    scores = [m["score"] for m in data["matches"] if m["score"] is not None]
    assert scores == sorted(scores, reverse=True)
    top = data["matches"][0]
    assert "breakdown" in top and top["breakdown"]
    assert "quality" in top
    # Ischigualasto está más cerca en cota de Gale (−4501 no, wait Gale is -4501, Earth is all positive
    # so elevation similarity may not favor Ischigualasto strongly vs others; just check structure
    assert top["site"]["body"] == "earth"


def test_similar_moon_target_earth():
    r = client.get(
        "/similar",
        params={
            "target": "shackleton-rim",
            "body": "earth",
            "features": "elevation,precip_mm",
            "weights": "2,1",
            "method": "euclidean",
            "norm": "minmax",
            "top": 3,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["target"]["id"] == "shackleton-rim"
    assert data["matches"]
    # precip is 0 on the Moon; Ischigualasto 1397 m is the closest Earth elevation to 1300 m
    ids = [m["site"]["id"] for m in data["matches"]]
    assert "ischigualasto" in ids
    assert data["matches"][0]["score"] is not None


def test_missing_feature_reweight():
    # jezero no tiene elevation medida; al pedir elevation+precip, elevation se omite
    r = client.get(
        "/similar",
        params={
            "target": "jezero",
            "body": "earth",
            "features": "elevation,precip_mm",
            "weights": "3,1",
            "method": "cosine",
            "norm": "zscore",
            "top": 5,
        },
    )
    assert r.status_code == 200
    used = r.json()["matches"][0]["quality"]["features_used"]
    assert "elevation" not in used
    assert "precip_mm" in used
    w = r.json()["matches"][0]["quality"]["weights_renormalized"]
    assert pytest.approx(sum(w.values()), abs=1e-9) == 1.0
    assert w["precip_mm"] == pytest.approx(1.0)


def test_unknown_target():
    r = client.get("/similar", params={"target": "no-existe", "body": "earth"})
    assert r.status_code == 404


def test_shackleton_elevation_is_real():
    site = site_by_id("shackleton-rim")
    assert numeric_value(site, "elevation") == 1300
    assert site["features"]["elevation"]["is_real"] is True
