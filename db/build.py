"""Build the merged catalogs (base catalogs + data/measurements/*.jsonl).

Shared by db/load.py (writes Postgres) and db/export.py (writes JSON snapshots).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from measurements import merge, read_dir

ROOT = Path(__file__).resolve().parent.parent
BASES = {
    "planetary": ROOT / "services" / "planetary" / "data" / "catalog.json",
    "earth": ROOT / "services" / "earth" / "data" / "catalog.json",
}
MEASUREMENTS = ROOT / "data" / "measurements"
MERGED_NAME = "catalog.merged.json"


def load_bases() -> Dict[str, Dict[str, Any]]:
    return {svc: json.loads(path.read_text(encoding="utf-8")) for svc, path in BASES.items()}


def serves(payload: Dict[str, Any], svc: str) -> bool:
    """A feature def belongs to a service. "service" may be a string or a list
    (e.g. ["earth", "planetary"] for features shared by the three bodies).
    Missing "service" keeps the historical default: planetary."""
    declared = payload.get("service", "planetary")
    return svc in declared if isinstance(declared, list) else declared == svc


def build(measurements_dir: Path = MEASUREMENTS) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Return merged catalogs per service and a small report."""
    bases = load_bases()
    service_of: Dict[str, str] = {}
    base_feats: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for svc, cat in bases.items():
        for site in cat["sites"]:
            if site["id"] in service_of:
                raise ValueError("id de sitio repetido entre servicios: %s" % site["id"])
            service_of[site["id"]] = svc
            for fid, item in (site.get("features") or {}).items():
                base_feats[(site["id"], fid)] = dict(item, dataset="base:%s" % svc)
    rows, defs = read_dir(measurements_dir) if measurements_dir.exists() else ([], {})
    result = merge(base_feats, rows, service_of.keys())

    merged: Dict[str, Dict[str, Any]] = {}
    for svc, cat in bases.items():
        out = copy.deepcopy(cat)
        if svc == "planetary":
            out["features"] = {**out.get("features", {}), **{k: v for k, v in defs.items() if serves(v, "planetary")}}
        else:
            out["feature_defs"] = {**out.get("feature_defs", {}), **{k: v for k, v in defs.items() if serves(v, "earth")}}
        sites: List[Dict[str, Any]] = []
        for site in out["sites"]:
            feats = {fid: item for (sid, fid), item in result.features.items() if sid == site["id"]}
            sites.append({**site, "features": feats})
        out["sites"] = sites
        out.setdefault("meta", {})["merged_from"] = sorted(
            {r.dataset for r in result.applied if service_of[r.site_id] == svc}
        )
        merged[svc] = out
    report = {
        "rows_applied": len(result.applied),
        "datasets": sorted({r.dataset for r in result.applied}),
        "sites": {svc: len(c["sites"]) for svc, c in merged.items()},
    }
    return merged, report
