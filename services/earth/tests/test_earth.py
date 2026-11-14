from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from covariance import ledoit_wolf  # noqa: E402
from geocode import assign_country, regions_from_sites  # noqa: E402
from tasi import DEFAULT_WEIGHTS, normalize_weights, rank, viability_mask  # noqa: E402


def test_geocode_known_points_use_natural_earth_not_guesses():
    yungay = assign_country(-24.069867, -69.866033)
    assert yungay["found"] is True
    assert yungay["country_iso"] == "CL"
    assert yungay["continent"] == "South America"
    fogo = assign_country(14.95, -24.34166667)
    assert fogo["country_iso"] == "CV"
    assert fogo["continent"] == "Africa"
    uv = assign_country(-77.861565, 160.717946)
    assert uv["country_iso"] == "AQ"
    assert uv["continent"] == "Antarctica"
    arg = assign_country(-26.659722, -67.514167)
    assert arg["country_iso"] == "AR"


def test_ledoit_wolf_shrinkage_is_bounded():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(80, 3))
    sigma, shrinkage = ledoit_wolf(X)
    assert 0.0 <= shrinkage <= 1.0
    assert sigma.shape == (3, 3)
    # SPD enough to invert
    np.linalg.inv(sigma)


def test_mask_discards_ndvi_and_water_but_not_unknown():
    wet = {"features": {"ndvi": {"value": 0.02}, "has_liquid_water": {"value": 1.0}}}
    green = {"features": {"ndvi": {"value": 0.4}, "has_liquid_water": {"value": 0.0}}}
    unknown = {"features": {"ndvi": {"value": None}, "has_liquid_water": {"value": None}}}
    assert viability_mask(wet)["viable"] is False
    assert "continental_liquid_water" in viability_mask(wet)["reasons"]
    assert viability_mask(green)["viable"] is False
    assert "ndvi_gt_0.15" in viability_mask(green)["reasons"]
    m = viability_mask(unknown)
    assert m["viable"] is True
    assert "ndvi_unavailable" in m["unknown_flags"]


def test_weights_renormalize_when_g_and_o_missing():
    w = normalize_weights(DEFAULT_WEIGHTS, {"G": False, "T": True, "E": True, "V": True, "O": False})
    assert set(w["renormalized"]) == {"T", "E", "V"}
    assert pytest.approx(sum(w["renormalized"].values()), rel=1e-9) == 1.0
    assert w["renormalized"]["T"] == pytest.approx(1.0 / 3.0)


def _feat(val):
    return {"value": val, "unit": "x", "source": "unit test fixture", "quality": "measured", "is_real": True}


def test_tasi_ranks_closer_topography_higher():
    cov = {
        "labels": ["relative_relief_m", "slope_deg", "roughness_m"],
        "sigma": [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0]],
        "n_samples": 10,
        "shrinkage": 0.0,
        "method": "unit test diagonal Sigma",
    }
    target = {
        "id": "fake-target",
        "name": "Fixture target",
        "body": "moon",
        "lat": 0,
        "lon": 0,
        "components": {
            "G": {"available": False, "score_ready": False, "reason": "no spectra in fixture"},
            "T": {
                "available": True,
                "score_ready": True,
                "vector": [10.0, 5.0, 2.0],
                "vector_labels": ["relative_relief_m", "slope_deg", "roughness_m"],
                "metrics": {},
            },
            "E": {"available": False, "score_ready": False, "metrics": {}, "reason": "none"},
            "Vo": {"available": False, "score_ready": False, "metrics": {}, "reason": "none"},
            "O": {"available": False, "score_ready": False, "reason": "none"},
        },
    }
    close = {
        "id": "close",
        "name": "Close",
        "features": {
            "relative_relief": _feat(10.2),
            "slope": _feat(5.1),
            "roughness": _feat(2.1),
            "ndvi": _feat(0.01),
            "has_liquid_water": _feat(0.0),
        },
    }
    far = {
        "id": "far",
        "name": "Far",
        "features": {
            "relative_relief": _feat(80.0),
            "slope": _feat(40.0),
            "roughness": _feat(30.0),
            "ndvi": _feat(0.01),
            "has_liquid_water": _feat(0.0),
        },
    }
    out = rank(target, [far, close], cov, weights={"G": 0, "T": 1, "E": 0, "V": 0, "O": 0}, gamma=1.0, top=5)
    assert out["matches"][0]["site"]["id"] == "close"
    assert out["matches"][0]["score"] > out["matches"][1]["score"]


def test_regions_lists_iso():
    payload = regions_from_sites(
        [
            {"continent": "South America", "country_iso": "AR", "country_name": "Argentina"},
            {"continent": "South America", "country_iso": "AR", "country_name": "Argentina"},
            {"continent": "Africa", "country_iso": "NA", "country_name": "Namibia"},
        ]
    )
    names = [c["name"] for c in payload["continents"]]
    assert names == ["Africa", "South America"]
    sa = payload["continents"][1]["countries"][0]
    assert sa["iso"] == "AR" and sa["count"] == 2


@pytest.mark.skipif(
    not (ROOT / "data" / "catalog.json").exists(),
    reason="earth catalog not ingested yet",
)
def test_earth_http_endpoints():
    from main import app

    client = TestClient(app)
    h = client.get("/health")
    assert h.status_code == 200 and h.json()["ok"] is True
    assert h.headers.get("access-control-allow-origin") == "*" or True  # CORS on actual request
    r = client.get("/health", headers={"Origin": "http://127.0.0.1:8765"})
    assert r.headers.get("access-control-allow-origin") == "*"
    regions = client.get("/regions").json()
    assert regions["continents"]
    isos = [c["iso"] for cont in regions["continents"] for c in cont["countries"]]
    assert "AR" in isos
    ar = client.get("/candidates", params={"continent": "South America", "country": "AR"}).json()
    assert ar["n"] >= 5
    assert all(s["country_iso"] == "AR" for s in ar["sites"])
    bad = client.get("/candidates", params={"country": "ARG"})
    assert bad.status_code == 400
    # TASI without a vector should 400
    missing = client.post("/tasi", json={"gamma": 1, "top": 3})
    assert missing.status_code == 400
    vec = {
        "id": "test-target",
        "name": "Test",
        "body": "mars",
        "lat": 18.4,
        "lon": 77.5,
        "components": {
            "G": {"available": False, "score_ready": False, "reason": "no spectra"},
            "T": {
                "available": True,
                "score_ready": True,
                "vector": [20.0, 3.0, 5.0],
                "vector_labels": ["relative_relief_m", "slope_deg", "roughness_m"],
                "metrics": {},
            },
            "E": {
                "available": True,
                "score_ready": True,
                "metrics": {
                    "temp_mean": {"value": -60.0, "unit": "degC", "source": "test", "quality": "measured", "is_real": True},
                    "temp_diurnal_range": {"value": 50.0, "unit": "degC", "source": "test", "quality": "measured", "is_real": True},
                    "illumination_pct": {"value": None, "quality": "unavailable", "is_real": False},
                },
            },
            "Vo": {
                "available": True,
                "score_ready": True,
                "metrics": {
                    "precip_mm": {"value": 0.0, "unit": "mm", "source": "convention", "quality": "convention", "is_real": True},
                    "water_ice_indicator": {"value": None, "quality": "unavailable", "is_real": False},
                },
            },
            "O": {"available": False, "score_ready": False, "reason": "unmapped"},
        },
    }
    ranked = client.post("/tasi", json={"target": vec, "gamma": 1.0, "top": 5, "country": "AR"})
    assert ranked.status_code == 200
    body = ranked.json()
    assert body["index"] == "TASI"
    assert len(body["matches"]) <= 5
    if body["matches"]:
        assert body["matches"][0]["score"] is None or 0 <= body["matches"][0]["score"] <= 100
        # G and O should be unavailable in the breakdown
        assert body["matches"][0]["components"]["G"]["available"] is False
        assert body["matches"][0]["components"]["O"]["available"] is False



@pytest.mark.skipif(
    not (ROOT / "data" / "catalog.json").exists(),
    reason="earth catalog not ingested yet",
)
def test_featured_endpoint_contains_required_baselines():
    from main import app

    client = TestClient(app)
    r = client.get("/featured")
    assert r.status_code == 200
    body = r.json()
    ids = [s["id"] for s in body["sites"]]
    required = {
        "university-valley",
        "haughton",
        "devon-island-fmars",
        "timanfaya",
        "teide",
        "kilauea",
        "mauna-kea",
        "yungay-atacama",
        "campo-piedra-pomez",
        "payun-matru",
        "laguna-diamante",
        "socompa",
    }
    missing = required - set(ids)
    assert not missing, missing
    assert all(s.get("featured") for s in body["sites"])
    # Haughton and FMARS must be two distinct points
    sites = {s["id"]: s for s in body["sites"]}
    assert (sites["haughton"]["lat"], sites["haughton"]["lon"]) != (
        sites["devon-island-fmars"]["lat"],
        sites["devon-island-fmars"]["lon"],
    )
    # ranks are sorted
    ranks = [s.get("featured_rank") for s in body["sites"] if s.get("featured_rank") is not None]
    assert ranks == sorted(ranks)
