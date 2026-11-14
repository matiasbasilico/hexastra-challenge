"""Carga del catálogo unificado Tierra–Luna–Marte."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    with DATA.open(encoding="utf-8") as f:
        return json.load(f)


def feature_schema() -> dict:
    return load_catalog()["features"]


def all_sites() -> list[dict]:
    return load_catalog()["sites"]


def sites_by_body(body: str | None) -> list[dict]:
    sites = all_sites()
    if body:
        body = body.lower()
        sites = [s for s in sites if s["body"] == body]
    return sites


def site_by_id(site_id: str) -> dict | None:
    for s in all_sites():
        if s["id"] == site_id:
            return s
    return None


def numeric_value(site: dict, feature_id: str) -> float | None:
    feat = site.get("features", {}).get(feature_id)
    if not feat:
        return None
    v = feat.get("value")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
