from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA = Path(__file__).resolve().parent / "data"
CATALOG_PATH = DATA / "catalog.json"
COV_PATH = DATA / "covariance.json"


@lru_cache(maxsize=1)
def load_catalog() -> Dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def all_sites() -> List[Dict[str, Any]]:
    return list(load_catalog().get("sites") or [])


def covariance() -> Optional[Dict[str, Any]]:
    cat = load_catalog()
    if cat.get("covariance"):
        return cat["covariance"]
    if COV_PATH.exists():
        with COV_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return None


def filter_sites(continent: Optional[str] = None, country: Optional[str] = None) -> List[Dict[str, Any]]:
    sites = all_sites()
    if continent:
        want = continent.strip().lower()
        sites = [s for s in sites if (s.get("continent") or "").lower() == want]
    if country:
        iso = country.strip().upper()
        sites = [s for s in sites if (s.get("country_iso") or "").upper() == iso]
    return sites


def site_by_id(site_id: str) -> Optional[Dict[str, Any]]:
    for s in all_sites():
        if s["id"] == site_id:
            return s
    return None


def summary(site: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": site["id"],
        "name": site.get("name"),
        "short_name": site.get("short_name"),
        "body": "earth",
        "lat": site.get("lat"),
        "lon": site.get("lon"),
        "continent": site.get("continent"),
        "country_iso": site.get("country_iso"),
        "country_name": site.get("country_name"),
        "analog_types": site.get("analog_types") or [],
        "known_level": site.get("known_level"),
        "highlight_less_studied": site.get("highlight_less_studied"),
        "featured": bool(site.get("featured")),
        "featured_label": site.get("featured_label"),
        "featured_rank": site.get("featured_rank"),
        "featured_note": site.get("featured_note"),
        "summary": site.get("summary"),
        "coord_source": site.get("coord_source"),
    }


def featured_sites() -> List[Dict[str, Any]]:
    sites = [s for s in all_sites() if s.get("featured")]
    def key(s):
        rank = s.get("featured_rank")
        return (999 if rank is None else int(rank), s.get("name") or "")
    return sorted(sites, key=key)
