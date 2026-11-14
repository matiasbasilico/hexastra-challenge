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
    assert body["n_sites"] >= 11


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
