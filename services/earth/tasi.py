"""TASI — Terrestrial Analog Similarity Index (Hexastra prototype).

This is a team-defined index, not a published standard found in the literature
under this acronym (as verified on 2026-11-14). The formula is intentional and
transparent.

V = [G, T, E, Vo, O]
  G  geology / materials. Categorical map classes + impact origin (geology.py);
     the spectral cosine is kept only for real spectra on both sides.
  T  topography + roughness (Mahalanobis on relative relief, slope, roughness).
  E  thermal regime + illumination.
  Vo volatiles / ice / precipitation.
  O  operational constraints comparable across bodies. Left null unless both
     sides have a sourced, comparable metric.

Step A — boolean mask M(x):
  discard Earth candidates with NDVI > 0.15 or continental liquid water.
  If NDVI or water is unknown, the site is not discarded; a flag is raised.

Step B — S_T = exp(-gamma * D_M), D_M = sqrt((Tx-Ty)^T Sigma^{-1} (Tx-Ty))
  Sigma is a Ledoit-Wolf covariance estimated on Earth terrain cells.

Step C — S_G (geology.py, approved 2026-11-14): blocks composition and impact,
  only those with data on both sides; S_G = mean(blocks) * (blocks / 2).
  Falls back to the spectral cosine only if both sides carry real spectra.

Step D — TASI = sum w_k S_k over components that are available on both sides.
  Weights are renormalized to sum 1. Coverage is reported.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from covariance import LABELS as T_LABELS
from covariance import submatrix
from geology import s_geology, values_from_component, values_from_features

DEFAULT_WEIGHTS = {"G": 0.2, "T": 0.2, "E": 0.2, "V": 0.2, "O": 0.2}
NDVI_THRESHOLD = 0.15
COMPONENT_KEYS = ("G", "T", "E", "V", "O")  # V in the API maps to Vo in the vector


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, bool):
        return float(x)
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return float(x)
    return None


def metric_value(component: Dict[str, Any], name: str) -> Optional[float]:
    metrics = (component or {}).get("metrics") or {}
    item = metrics.get(name) or {}
    return _num(item.get("value"))


def viability_mask(site: Dict[str, Any]) -> Dict[str, Any]:
    feats = site.get("features") or {}
    ndvi_item = feats.get("ndvi") or {}
    water_item = feats.get("has_liquid_water") or {}
    ndvi = _num(ndvi_item.get("value"))
    water_raw = water_item.get("value")
    water = None
    if water_raw is True or water_raw == 1 or water_raw == 1.0:
        water = True
    elif water_raw is False or water_raw == 0 or water_raw == 0.0:
        water = False
    reasons = []
    if ndvi is not None and ndvi > NDVI_THRESHOLD:
        reasons.append("ndvi_gt_0.15")
    if water is True:
        reasons.append("continental_liquid_water")
    unknown = []
    if ndvi is None:
        unknown.append("ndvi_unavailable")
    if water is None:
        unknown.append("water_unavailable")
    return {
        "viable": len(reasons) == 0,
        "reasons": reasons,
        "unknown_flags": unknown,
        "ndvi": ndvi,
        "has_liquid_water": water,
        "threshold_ndvi": NDVI_THRESHOLD,
        "rule": "Discard if NDVI > 0.15 or continental liquid water is present at the point. Unknown values do not discard the site; they are flagged.",
    }


def site_T_vector(site: Dict[str, Any]) -> Dict[str, Optional[float]]:
    feats = site.get("features") or {}
    return {
        "relative_relief_m": _num((feats.get("relative_relief") or {}).get("value")),
        "slope_deg": _num((feats.get("slope") or {}).get("value")),
        "roughness_m": _num((feats.get("roughness") or {}).get("value")),
    }


def component_T_vector(comp: Dict[str, Any]) -> Dict[str, Optional[float]]:
    # Prefer explicit labels + vector; fall back to metric names.
    labels = comp.get("vector_labels") or []
    vec = comp.get("vector") or []
    out = {k: None for k in T_LABELS}
    if labels and vec and len(labels) == len(vec):
        for lab, val in zip(labels, vec):
            if lab in out:
                out[lab] = _num(val)
        return out
    for key, alias in (
        ("relative_relief_m", "relative_relief_m"),
        ("slope_deg", "slope_deg"),
        ("roughness_m", "roughness_m"),
    ):
        out[key] = metric_value(comp, alias)
    return out


def mahalanobis(tx: Sequence[float], ty: Sequence[float], sigma_inv: np.ndarray) -> float:
    d = np.asarray(tx, dtype=float) - np.asarray(ty, dtype=float)
    val = float(d.T @ sigma_inv @ d)
    if val < 0 and val > -1e-12:
        val = 0.0
    if val < 0:
        val = 0.0
    return math.sqrt(val)


def s_topography(
    tx: Dict[str, Optional[float]],
    ty: Dict[str, Optional[float]],
    cov: Dict[str, Any],
    gamma: float,
) -> Dict[str, Any]:
    used = [k for k in T_LABELS if tx.get(k) is not None and ty.get(k) is not None]
    if not used or not cov:
        return {
            "available": False,
            "score": None,
            "D_M": None,
            "reason": "No shared topographic dimensions (relative relief, slope, roughness) with a sourced value on both sides, or Sigma is missing.",
            "used": used,
        }
    _sub, inv, used = submatrix(cov, used)
    vx = [tx[k] for k in used]
    vy = [ty[k] for k in used]
    dm = mahalanobis(vx, vy, inv)
    g = max(0.0, float(gamma))
    score = math.exp(-g * dm)
    return {
        "available": True,
        "score": score,
        "D_M": dm,
        "gamma": g,
        "used": used,
        "reason": None,
        "formula": "S_T = exp(-gamma * D_M), D_M = sqrt((Tx-Ty)^T Sigma^{-1} (Tx-Ty))",
    }


def _scaled_similarity(pairs: List[Tuple[str, float, float, float]]) -> Dict[str, Any]:
    """pairs: (name, x, y, scale). s_i = exp(-|x-y|/scale), then average."""
    if not pairs:
        return {"available": False, "score": None, "reason": "No shared metrics.", "parts": []}
    parts = []
    acc = 0.0
    for name, x, y, scale in pairs:
        s = math.exp(-abs(x - y) / scale) if scale > 0 else None
        parts.append({"metric": name, "x": x, "y": y, "scale": scale, "s": s})
        if s is not None:
            acc += s
    n = len([p for p in parts if p["s"] is not None])
    score = (acc / n) if n else None
    return {
        "available": score is not None,
        "score": score,
        "reason": None if score is not None else "No usable pairs.",
        "parts": parts,
        "formula": "Average of exp(-|x-y|/scale) on shared metrics. Scales are the Earth-catalog standard deviations (or a documented fallback if std is 0).",
    }


def earth_scales(sites: List[Dict[str, Any]]) -> Dict[str, float]:
    buckets: Dict[str, List[float]] = {
        "temp_mean": [],
        "temp_diurnal_range": [],
        "illumination_pct": [],
        "precip_mm": [],
        "water_ice_indicator": [],
    }
    for site in sites:
        feats = site.get("features") or {}
        for key in buckets:
            val = _num((feats.get(key) or {}).get("value"))
            if val is not None:
                buckets[key].append(val)
    scales = {}
    fallback = {"temp_mean": 20.0, "temp_diurnal_range": 10.0, "illumination_pct": 20.0, "precip_mm": 200.0, "water_ice_indicator": 0.5}
    for key, vals in buckets.items():
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
            std = math.sqrt(var)
            scales[key] = std if std > 1e-6 else fallback[key]
        else:
            scales[key] = fallback[key]
        # Document fallback use
        scales[key + "_n"] = len(vals)
    return scales


def s_thermal(target_e: Dict[str, Any], cand_feats: Dict[str, Any], scales: Dict[str, float]) -> Dict[str, Any]:
    keys = ("temp_mean", "temp_diurnal_range", "illumination_pct")
    pairs = []
    for key in keys:
        x = metric_value(target_e, key)
        y = _num((cand_feats.get(key) or {}).get("value"))
        if x is not None and y is not None:
            pairs.append((key, x, y, scales.get(key) or 1.0))
    out = _scaled_similarity(pairs)
    if not pairs:
        out["reason"] = "No shared thermal/illumination metrics with sourced values on both sides."
    return out


def s_volatiles(target_v: Dict[str, Any], cand_feats: Dict[str, Any], scales: Dict[str, float]) -> Dict[str, Any]:
    keys = ("precip_mm", "water_ice_indicator")
    pairs = []
    for key in keys:
        x = metric_value(target_v, key)
        y = _num((cand_feats.get(key) or {}).get("value"))
        if x is not None and y is not None:
            pairs.append((key, x, y, scales.get(key) or 1.0))
    out = _scaled_similarity(pairs)
    if not pairs:
        out["reason"] = "No shared volatile metrics with sourced values on both sides."
    else:
        flags = []
        # Convention precip=0 on airless bodies is valid but should be flagged.
        for part in out.get("parts") or []:
            if part["metric"] == "precip_mm":
                flags.append("precip_comparison_uses_whatever_quality_flag_the_target_declares (often a 0 mm convention on Moon/Mars).")
        out["quality_flags"] = flags
    return out


def s_spectral(target_g: Dict[str, Any], candidate_g: Dict[str, Any]) -> Dict[str, Any]:
    if not (target_g or {}).get("score_ready") or not (candidate_g or {}).get("score_ready"):
        return {
            "available": False,
            "score": None,
            "reason": (target_g or {}).get("reason")
            or (candidate_g or {}).get("reason")
            or "No real spectral / mineralogy vectors were available (S_G is not invented).",
        }
    vx = [v for v in (target_g.get("vector") or []) if v is not None]
    vy = [v for v in (candidate_g.get("vector") or []) if v is not None]
    if len(vx) != len(vy) or len(vx) < 2:
        return {"available": False, "score": None, "reason": "Spectral vectors missing or of different length."}
    a = np.asarray(vx, dtype=float)
    b = np.asarray(vy, dtype=float)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return {"available": False, "score": None, "reason": "Zero spectral vector."}
    score = float(np.dot(a, b) / (na * nb))
    # cosine is [-1, 1]; clip to [0, 1] for the weighted sum, document it.
    return {
        "available": True,
        "score": max(0.0, min(1.0, score)),
        "cosine_raw": score,
        "reason": None,
        "formula": "S_G = max(0, cosine(spectrum_x, spectrum_y))",
    }


def s_operational(target_o: Dict[str, Any], cand_feats: Dict[str, Any]) -> Dict[str, Any]:
    if not (target_o or {}).get("score_ready"):
        return {
            "available": False,
            "score": None,
            "reason": (target_o or {}).get("reason")
            or "No sourced operational metric that is comparable across the target body and Earth was available. Accessibility of an Earth site alone is not treated as similarity to a Moon/Mars site.",
        }
    return {
        "available": False,
        "score": None,
        "reason": "O is declared on the target but this prototype still lacks a mapped Earth counterpart; S_O left null.",
    }


def s_geology_component(target_g: Dict[str, Any], cand_feats: Dict[str, Any]) -> Dict[str, Any]:
    """S_G for a target G component and an Earth candidate's features."""
    target_vals = values_from_component(target_g or {})
    if any(v is not None for v in target_vals.values()):
        return s_geology(target_vals, values_from_features(cand_feats or {}))
    # No categorical geology on the target: only real spectra could be compared.
    return s_spectral(target_g or {}, {"score_ready": False})


def normalize_weights(weights: Optional[Dict[str, float]], available: Dict[str, bool]) -> Dict[str, Any]:
    src = dict(DEFAULT_WEIGHTS)
    if weights:
        for k, v in weights.items():
            key = "V" if k in ("V", "Vo", "VO") else k
            if key in src and v is not None:
                src[key] = max(0.0, float(v))
    used = {k: src[k] for k in COMPONENT_KEYS if available.get(k) and src[k] > 0}
    total = sum(used.values())
    if total <= 0:
        return {"requested": src, "used": {}, "renormalized": {}, "note": "No available components with positive weight."}
    renorm = {k: used[k] / total for k in used}
    skipped = [k for k in COMPONENT_KEYS if k not in renorm]
    return {
        "requested": src,
        "used": used,
        "renormalized": renorm,
        "skipped": skipped,
        "note": "Weights renormalized over components that returned a score." if skipped else "All requested components available.",
    }


def target_from_vector(vector: Dict[str, Any]) -> Dict[str, Any]:
    return vector


def rank(
    target_vector: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    cov: Optional[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    gamma: float = 1.0,
    top: int = 5,
    apply_mask: bool = True,
    scales: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    comps = (target_vector or {}).get("components") or {}
    target_T = component_T_vector(comps.get("T") or {})
    if scales is None:
        scales = earth_scales(candidates)
    discarded = []
    scored = []
    for cand in candidates:
        mask = viability_mask(cand)
        if apply_mask and not mask["viable"]:
            discarded.append({
                "id": cand["id"],
                "name": cand.get("name"),
                "continent": cand.get("continent"),
                "country_iso": cand.get("country_iso"),
                "mask": mask,
            })
            continue
        st = s_topography(site_T_vector(cand), target_T, cov or {}, gamma)
        se = s_thermal(comps.get("E") or {}, cand.get("features") or {}, scales)
        sv = s_volatiles(comps.get("Vo") or comps.get("V") or {}, cand.get("features") or {}, scales)
        sg = s_geology_component(comps.get("G") or {}, cand.get("features") or {})
        so = s_operational(comps.get("O") or {}, cand.get("features") or {})
        parts = {"G": sg, "T": st, "E": se, "V": sv, "O": so}
        available = {k: bool(parts[k].get("available") and parts[k].get("score") is not None) for k in COMPONENT_KEYS}
        w = normalize_weights(weights, available)
        if not w["renormalized"]:
            tasi = None
        else:
            tasi = sum(w["renormalized"][k] * parts[k]["score"] for k in w["renormalized"])
        scored.append({
            "site": {
                "id": cand["id"],
                "name": cand.get("name"),
                "short_name": cand.get("short_name"),
                "lat": cand.get("lat"),
                "lon": cand.get("lon"),
                "continent": cand.get("continent"),
                "country_iso": cand.get("country_iso"),
                "country_name": cand.get("country_name"),
                "analog_types": cand.get("analog_types") or [],
                "known_level": cand.get("known_level"),
                "highlight_less_studied": bool(cand.get("highlight_less_studied")),
                "summary": cand.get("summary"),
            },
            "score": None if tasi is None else round(tasi * 100.0, 2),
            "score_0_1": tasi,
            "components": {
                k: {
                    "score": None if parts[k].get("score") is None else round(parts[k]["score"] * 100.0, 2),
                    "score_0_1": parts[k].get("score"),
                    "available": parts[k].get("available"),
                    "reason": parts[k].get("reason"),
                    "detail": {dk: dv for dk, dv in parts[k].items() if dk not in ("reason",)},
                }
                for k in COMPONENT_KEYS
            },
            "weights": w,
            "coverage": {
                "available_components": [k for k, ok in available.items() if ok],
                "n_available": sum(1 for ok in available.values() if ok),
                "n_possible": 5,
            },
            "mask": mask,
        })
    scored.sort(key=lambda m: (-1 if m["score"] is None else -m["score"], m["site"]["name"] or ""))
    top_n = max(1, int(top or 5))
    return {
        "index": "TASI",
        "formula": "TASI = sum w_k S_k over available components; reported as 0-100 (= 100 * TASI). S_T = exp(-gamma * Mahalanobis). S_G = mean(geology blocks) * (blocks / 2) from map classes and impact origin. S_G and S_O are null unless comparable data exist on both sides.",
        "gamma": gamma,
        "apply_mask": apply_mask,
        "target": {
            "id": target_vector.get("id"),
            "name": target_vector.get("name"),
            "body": target_vector.get("body"),
            "lat": target_vector.get("lat"),
            "lon": target_vector.get("lon"),
        },
        "n_candidates": len(candidates),
        "n_discarded_by_mask": len(discarded),
        "n_scored": len(scored),
        "matches": scored[:top_n],
        "discarded": discarded,
        "scales": {k: v for k, v in (scales or {}).items() if not str(k).endswith("_n")},
    }
