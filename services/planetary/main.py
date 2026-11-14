from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from catalog import all_sites, feature_schema, load_catalog, site_by_id, sites_by_body
from clients import lunar_landing, trek
from vector import feature_vector

app = FastAPI(
    title="Hexastra planetary-service",
    version="0.2.0",
    description="Moon and Mars site catalog and TASI-ready feature vectors. No Earth ranking lives here.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _summary(site: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": site["id"],
        "name": site.get("name"),
        "short_name": site.get("short_name") or site.get("name"),
        "body": site.get("body"),
        "lat": site.get("lat"),
        "lon": site.get("lon"),
        "coord_source": site.get("coord_source"),
        "summary": site.get("summary"),
        "tags": site.get("tags") or [],
        "geology_class": site.get("geology_class"),
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    cat = load_catalog()
    return {
        "ok": True,
        "service": "planetary",
        "n_sites": len(cat.get("sites") or []),
        "catalog_origin": (cat.get("meta") or {}).get("catalog_origin"),
        "lunar_landing_site_api": cat.get("meta", {}).get("lunar_landing_site_api"),
        "trek": cat.get("meta", {}).get("trek"),
    }


@app.get("/sources")
def sources(live: bool = False) -> Dict[str, Any]:
    """Documented source status. Pass live=true to probe external endpoints (may be slow)."""
    payload = {"catalog": load_catalog().get("meta", {})}
    if live:
        payload["live"] = {
            "lunar_landing_site_api": lunar_landing.probe(),
            "trek": trek.capabilities_status(),
        }
    return payload


@app.get("/trek")
def trek_status() -> Dict[str, Any]:
    return trek.capabilities_status()


@app.get("/features")
def features() -> Dict[str, Any]:
    return {"features": feature_schema()}


@app.get("/sites")
def sites(body: Optional[str] = Query(None, description="moon or mars")) -> Dict[str, Any]:
    if body and body.lower() not in ("moon", "mars"):
        raise HTTPException(status_code=400, detail="body must be moon or mars")
    found = sites_by_body(body)
    return {"n": len(found), "body": body, "sites": [_summary(s) for s in found]}


@app.get("/sites/{site_id}")
def site_detail(site_id: str) -> Dict[str, Any]:
    site = site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Unknown planetary site: %s" % site_id)
    return site


@app.get("/sites/{site_id}/vector")
def site_vector(site_id: str) -> Dict[str, Any]:
    site = site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Unknown planetary site: %s" % site_id)
    return feature_vector(site)
