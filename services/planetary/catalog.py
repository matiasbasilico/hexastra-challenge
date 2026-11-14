from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

CATALOG_PATH = Path(__file__).resolve().parent / "data" / "catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> Dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def all_sites() -> List[Dict[str, Any]]:
    return list(load_catalog().get("sites") or [])


def sites_by_body(body: Optional[str] = None) -> List[Dict[str, Any]]:
    sites = all_sites()
    if not body:
        return sites
    want = body.strip().lower()
    if want not in ("moon", "mars"):
        return []
    return [s for s in sites if s.get("body") == want]


def site_by_id(site_id: str) -> Optional[Dict[str, Any]]:
    for s in all_sites():
        if s["id"] == site_id:
            return s
    return None


def feature_schema() -> Dict[str, Any]:
    return load_catalog().get("features") or {}
