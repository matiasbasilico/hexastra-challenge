from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from catalog import all_sites, covariance, featured_sites, filter_sites, load_catalog, site_by_id, summary
from geocode import regions_from_sites
from tasi import DEFAULT_WEIGHTS, NDVI_THRESHOLD, earth_scales, rank
from clients import earthdata

app = FastAPI(
    title="Hexastra earth-service",
    version="0.2.0",
    description=(
        "Worldwide terrestrial analog candidates, viability mask M(x), "
        "and TASI ranking against a planetary feature vector. "
        "Does not call planetary-service unless PLANETARY_URL and target_id are provided."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TasiRequest(BaseModel):
    target: Optional[Dict[str, Any]] = Field(None, description="Feature vector from planetary-service (contracts/feature_vector.schema.json).")
    target_id: Optional[str] = Field(None, description="Optional. If set and PLANETARY_URL is configured, the vector is fetched.")
    weights: Optional[Dict[str, float]] = Field(None, description="Keys G, T, E, V, O. Renormalized over available components.")
    gamma: float = 1.0
    top: int = 5
    continent: Optional[str] = None
    country: Optional[str] = Field(None, description="ISO-3166 alpha-2")
    apply_mask: bool = True


def _candidates(continent: Optional[str], country: Optional[str]):
    if country and len(country.strip()) != 2:
        raise HTTPException(status_code=400, detail="country must be an ISO-3166 alpha-2 code (two letters).")
    return filter_sites(continent=continent, country=country)


def _fetch_target(target_id: str) -> Dict[str, Any]:
    base = (os.environ.get("PLANETARY_URL") or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=400,
            detail="target vector missing and PLANETARY_URL is not set; pass the vector from planetary-service in the body.",
        )
    url = "%s/sites/%s/vector" % (base, target_id)
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach planetary-service: %s" % exc)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Unknown target_id on planetary-service: %s" % target_id)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail="planetary-service responded %s" % r.status_code)
    return r.json()


@app.get("/health")
def health() -> Dict[str, Any]:
    cat = load_catalog()
    return {
        "ok": True,
        "service": "earth",
        "n_sites": len(cat.get("sites") or []),
        "catalog_origin": (cat.get("meta") or {}).get("catalog_origin"),
        "covariance": bool(covariance()),
        "earthdata_cdse": earthdata.status(),
        "planetary_url_configured": bool(os.environ.get("PLANETARY_URL")),
    }


@app.get("/regions")
def regions() -> Dict[str, Any]:
    return regions_from_sites(filter_sites())


METHOD_PATH = Path(__file__).resolve().parent / "data" / "method.json"


@app.get("/method")
def method() -> Dict[str, Any]:
    """Everything the front needs to explain TASI, taken from the running code and catalog.

    Texts and presets live in data/method.json; weights, thresholds, scales and the
    covariance come from tasi.py and the current catalog, so the explanation cannot drift.
    """
    with METHOD_PATH.open(encoding="utf-8") as f:
        doc = json.load(f)
    cov = covariance() or {}
    return {
        **doc,
        "default_weights": dict(DEFAULT_WEIGHTS),
        "default_gamma": TasiRequest.model_fields["gamma"].default,
        "ndvi_threshold": NDVI_THRESHOLD,
        "scales": earth_scales(all_sites()),
        "covariance": {
            k: cov.get(k) for k in ("labels", "n_samples", "shrinkage", "method", "source")
        },
        "catalog": {
            "n_sites": len(all_sites()),
            "origin": (load_catalog().get("meta") or {}).get("catalog_origin"),
        },
    }


@app.get("/featured")
def featured() -> Dict[str, Any]:
    """Reference baseline / shortcut sites (includes well-known analogs kept as baselines)."""
    sites = featured_sites()
    return {
        "n": len(sites),
        "note": (
            "Featured sites are reference baselines and UI shortcuts. "
            "Some are well-known analogs (Atacama, Hawái, Dry Valleys, Canarias, Devon Island); "
            "the challenge asks to look beyond them. Lesser-known Argentine candidates stay flagged "
            "with highlight_less_studied. Coordinates are sourced; country/ISO come from Natural Earth 50m."
        ),
        "sites": [summary(s) for s in sites],
    }


@app.get("/candidates")
def candidates(
    continent: Optional[str] = None,
    country: Optional[str] = Query(None, description="ISO-3166 alpha-2"),
) -> Dict[str, Any]:
    sites = _candidates(continent, country)
    return {
        "n": len(sites),
        "continent": continent,
        "country": country.upper() if country else None,
        "sites": [summary(s) for s in sites],
    }


@app.get("/candidates/{site_id}")
def candidate_detail(site_id: str) -> Dict[str, Any]:
    site = site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Unknown Earth candidate: %s" % site_id)
    return site


@app.post("/tasi")
def tasi_post(body: TasiRequest) -> Dict[str, Any]:
    target = body.target
    if target is None and body.target_id:
        target = _fetch_target(body.target_id)
    if not target or not target.get("components"):
        raise HTTPException(status_code=400, detail="A target feature vector with 'components' is required.")
    cands = _candidates(body.continent, body.country)
    result = rank(
        target_vector=target,
        candidates=cands,
        cov=covariance(),
        weights=body.weights or DEFAULT_WEIGHTS,
        gamma=body.gamma,
        top=body.top,
        apply_mask=body.apply_mask,
    )
    result["filter"] = {"continent": body.continent, "country": body.country.upper() if body.country else None}
    return result


@app.get("/tasi")
def tasi_get(
    target_id: Optional[str] = None,
    gamma: float = 1.0,
    top: int = 5,
    continent: Optional[str] = None,
    country: Optional[str] = Query(None, description="ISO-3166 alpha-2"),
    apply_mask: bool = True,
    wG: float = 0.2,
    wT: float = 0.2,
    wE: float = 0.2,
    wV: float = 0.2,
    wO: float = 0.2,
) -> Dict[str, Any]:
    if not target_id:
        raise HTTPException(status_code=400, detail="GET /tasi requires target_id and PLANETARY_URL, or use POST /tasi with a target vector.")
    target = _fetch_target(target_id)
    cands = _candidates(continent, country)
    result = rank(
        target_vector=target,
        candidates=cands,
        cov=covariance(),
        weights={"G": wG, "T": wT, "E": wE, "V": wV, "O": wO},
        gamma=gamma,
        top=top,
        apply_mask=apply_mask,
    )
    result["filter"] = {"continent": continent, "country": country.upper() if country else None}
    return result
