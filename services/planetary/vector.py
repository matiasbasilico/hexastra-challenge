"""Build a contracts/feature_vector.schema.json vector from a catalog site.

Never fills missing numbers. G and O stay unavailable unless a real comparable
dataset is present on the site record.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _feat(site: Dict[str, Any], key: str) -> Dict[str, Any]:
    item = (site.get("features") or {}).get(key) or {}
    if not isinstance(item, dict):
        return {"value": None, "unit": None, "source": None, "quality": "unavailable", "is_real": False}
    return {
        "value": item.get("value"),
        "unit": item.get("unit"),
        "source": item.get("source"),
        "quality": item.get("quality") or ("measured" if item.get("is_real") and item.get("value") is not None else "unavailable"),
        "is_real": bool(item.get("is_real")) if "is_real" in item else (item.get("value") is not None and item.get("quality") in ("measured", "derived", "convention")),
    }


def _component(metrics: Dict[str, Dict[str, Any]], labels: Optional[list] = None, reason_if_empty: str = "", quality_flags=None) -> Dict[str, Any]:
    labels = labels or list(metrics.keys())
    vector = [metrics[k]["value"] if k in metrics else None for k in labels]
    present = [v for v in vector if v is not None]
    available = len(present) > 0
    return {
        "available": available,
        "score_ready": available,
        "reason": None if available else reason_if_empty,
        "vector": vector if available else [],
        "vector_labels": labels if available else [],
        "metrics": metrics,
        "source": "; ".join(sorted({(metrics[k].get("source") or "") for k in labels if metrics.get(k) and metrics[k].get("source")})) or None,
        "quality_flags": quality_flags or [],
    }


def feature_vector(site: Dict[str, Any]) -> Dict[str, Any]:
    flags = []
    # G — no CRISM/M3 spectra in this catalog
    G = {
        "available": False,
        "score_ready": False,
        "reason": "No sourced spectral / mineralogy vector (CRISM, M3, etc.) is stored for this site. S_G is not computed.",
        "vector": [],
        "vector_labels": [],
        "metrics": {},
        "source": None,
        "quality_flags": ["spectra_unavailable"],
    }
    # T — relative relief / slope / roughness only (no absolute elevation)
    t_metrics = {
        "relative_relief_m": _feat(site, "relative_relief"),
        "slope_deg": _feat(site, "slope"),
        "roughness_m": _feat(site, "roughness"),
    }
    T = _component(
        t_metrics,
        ["relative_relief_m", "slope_deg", "roughness_m"],
        reason_if_empty="No sourced relative relief, slope or roughness for this site. Absolute elevation is intentionally excluded from T.",
        quality_flags=["absolute_elevation_excluded_from_T"],
    )
    if T["available"] and t_metrics["roughness_m"]["value"] is not None:
        flags.append("roughness_scale_may_differ_across_bodies")

    e_metrics = {
        "temp_mean": _feat(site, "temp_mean"),
        "temp_diurnal_range": _feat(site, "temp_diurnal_range"),
        "illumination_pct": _feat(site, "illumination_pct"),
    }
    E = _component(
        e_metrics,
        ["temp_mean", "temp_diurnal_range", "illumination_pct"],
        reason_if_empty="No sourced thermal or illumination values for this site.",
    )

    v_metrics = {
        "precip_mm": _feat(site, "precip_mm"),
        "water_ice_indicator": _feat(site, "water_ice_indicator"),
    }
    Vo = _component(
        v_metrics,
        ["precip_mm", "water_ice_indicator"],
        reason_if_empty="No sourced precipitation or water-ice indicator for this site.",
    )
    if (v_metrics["precip_mm"].get("quality") == "convention") or (
        v_metrics["precip_mm"].get("value") == 0 and site.get("body") in ("moon", "mars")
    ):
        Vo["quality_flags"] = list(Vo.get("quality_flags") or []) + ["precip_zero_is_a_documented_convention_for_this_body"]
        flags.append("precip_convention")

    O = {
        "available": False,
        "score_ready": False,
        "reason": "No sourced operational constraint that is directly comparable to an Earth site (landing-accessibility mapping, etc.) is stored. S_O is left null.",
        "vector": [],
        "vector_labels": [],
        "metrics": {},
        "source": None,
        "quality_flags": ["operational_unmapped"],
    }

    return {
        "schema": "contracts/feature_vector.schema.json",
        "id": site["id"],
        "body": site.get("body"),
        "name": site.get("name"),
        "lat": site.get("lat"),
        "lon": site.get("lon"),
        "coord_source": site.get("coord_source"),
        "components": {"G": G, "T": T, "E": E, "Vo": Vo, "O": O},
        "quality_flags": flags,
        "geology_class": site.get("geology_class"),
        "summary": site.get("summary"),
        "tags": site.get("tags") or [],
    }
