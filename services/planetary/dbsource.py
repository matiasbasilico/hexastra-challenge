"""Catalog source shared by both services (keep services/earth/dbsource.py identical).

Order: Postgres/PostGIS when HEXASTRA_DATABASE_URL is set; otherwise the merged
JSON snapshot (data/catalog.merged.json, written by db/export.py); otherwise the
base catalog (data/catalog.json). The returned dict has the same shape as the
JSON catalogs, so endpoints do not change.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

TTL_S = 30.0
SUPPLEMENTS = ("g-mapas", "o-tierra")
_cache: Dict[str, Any] = {"at": 0.0, "data": None, "origin": None}


def _supplement(data: Dict[str, Any], service: str) -> Dict[str, Any]:
    """Fill catalog gaps from reviewed versioned G/access data, without DB writes.

    Existing non-null catalog measurements always win. Keep nulls, provenance and
    comparable:false intact; a missing file never triggers a network ingestion.
    """
    root = Path(__file__).resolve().parents[2] / "data" / "measurements"
    sites = {s["id"]: s for s in data.get("sites", [])}
    applied = []
    for name in SUPPLEMENTS:
        path = root / (name + ".jsonl")
        if not path.exists():
            continue
        used = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            site = sites.get(row["site_id"])
            if site is None:
                continue
            feats = site.setdefault("features", {})
            key = row["feature"]
            if (feats.get(key) or {}).get("value") is not None:
                continue
            feats[key] = {k: v for k, v in row.items() if k not in ("site_id", "feature")}
            feats[key]["dataset"] = name
            used = True
        if used:
            applied.append(name)
            definitions = json.loads((root / (name + ".features.json")).read_text(encoding="utf-8"))
            dest = data.setdefault("features" if service == "planetary" else "feature_defs", {})
            for key, definition in definitions.items():
                declared = definition.get("service", "planetary")
                if service in (declared if isinstance(declared, list) else [declared]):
                    dest.setdefault(key, definition)
    data.setdefault("meta", {})["supplemental_datasets"] = applied
    return data


def _from_json(data_dir: Path) -> Dict[str, Any]:
    merged = data_dir / "catalog.merged.json"
    path = merged if merged.exists() else data_dir / "catalog.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("meta", {})["catalog_origin"] = "json:%s" % path.name
    return data


def _from_db(url: str, service: str) -> Dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    bodies = ("earth",) if service == "earth" else ("moon", "mars")
    with psycopg.connect(url, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute("SELECT meta, extra FROM catalog_meta WHERE service = %s", (service,))
        meta_row = cur.fetchone()
        if meta_row is None:
            raise RuntimeError("catalog_meta sin fila para %s: correr db/load.py" % service)
        cur.execute("SELECT id, payload FROM feature_defs WHERE service = %s", (service,))
        defs = {r["id"]: r["payload"] for r in cur.fetchall()}
        cur.execute(
            "SELECT id, body, name, short_name, lat, lon, attrs FROM sites "
            "WHERE body = ANY(%s) ORDER BY position",
            (list(bodies),),
        )
        sites = cur.fetchall()
        cur.execute(
            "SELECT m.* FROM measurements m JOIN sites s ON s.id = m.site_id WHERE s.body = ANY(%s)",
            (list(bodies),),
        )
        feats: Dict[str, Dict[str, Any]] = {}
        for m in cur.fetchall():
            item = {k: m[k] for k in ("value", "unit", "quality", "is_real", "source", "note", "comparable")}
            if m.get("retrieved_at") is not None:
                item["retrieved_at"] = m["retrieved_at"].isoformat()
            item["dataset"] = m["dataset"]
            feats.setdefault(m["site_id"], {})[m["feature"]] = item
    out_sites = []
    for s in sites:
        out_sites.append({
            **(s["attrs"] or {}),
            "id": s["id"], "body": s["body"], "name": s["name"], "short_name": s["short_name"],
            "lat": s["lat"], "lon": s["lon"], "features": feats.get(s["id"], {}),
        })
    meta = dict(meta_row["meta"] or {}, catalog_origin="postgres")
    data: Dict[str, Any] = {"meta": meta, "sites": out_sites}
    if service == "planetary":
        data["features"] = defs
    else:
        data["feature_defs"] = defs
        if (meta_row["extra"] or {}).get("covariance"):
            data["covariance"] = meta_row["extra"]["covariance"]
    return data


def load(service: str, data_dir: Path, url: Optional[str] = None) -> Dict[str, Any]:
    url = url if url is not None else os.environ.get("HEXASTRA_DATABASE_URL")
    origin = "db" if url else "json"
    now = time.monotonic()
    if _cache["data"] is not None and _cache["origin"] == origin and now - _cache["at"] < TTL_S:
        return _cache["data"]
    data = _supplement(_from_db(url, service) if url else _from_json(data_dir), service)
    _cache.update(at=now, data=data, origin=origin)
    return data


def clear_cache() -> None:
    _cache.update(at=0.0, data=None, origin=None)
