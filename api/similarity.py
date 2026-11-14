"""Similitud ponderada (coseno y euclidiana) con omisión de faltantes y renormalización de pesos."""
from __future__ import annotations

import math

from catalog import feature_schema, numeric_value, sites_by_body
from normalize import stats_for, transform


def _parse_list(raw: str | None) -> list[str] | None:
    if raw is None or raw.strip() == "":
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def resolve_features(features_param: str | None) -> list[str]:
    schema = feature_schema()
    requested = _parse_list(features_param)
    if not requested:
        # por defecto, rasgos numéricos comparables con peso default > 0
        requested = [
            fid for fid, meta in schema.items()
            if meta.get("numeric") and meta.get("default_weight", 1) > 0 and meta.get("comparable_default", True)
        ]
    unknown = [f for f in requested if f not in schema]
    if unknown:
        raise ValueError(f"Rasgos desconocidos: {', '.join(unknown)}")
    # geology_class no es numérico
    requested = [f for f in requested if schema[f].get("numeric")]
    if not requested:
        raise ValueError("No quedó ningún rasgo numérico para comparar.")
    return requested


def resolve_weights(features: list[str], weights_param: str | None) -> dict[str, float]:
    if weights_param:
        parts = [p.strip() for p in weights_param.split(",") if p.strip()]
        if len(parts) != len(features):
            raise ValueError("La lista de pesos tiene que tener la misma longitud que la de rasgos.")
        vals = [float(p) for p in parts]
        if any(v < 0 for v in vals):
            raise ValueError("Los pesos no pueden ser negativos.")
        if sum(vals) == 0:
            raise ValueError("La suma de pesos no puede ser 0.")
        return {f: v for f, v in zip(features, vals)}
    schema = feature_schema()
    return {f: float(schema[f].get("default_weight", 1.0)) for f in features}


def _reweight(weights: dict[str, float], used: list[str]) -> dict[str, float]:
    sub = {k: weights[k] for k in used if weights[k] > 0}
    total = sum(sub.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in sub.items()}


def _vector(site: dict, features: list[str], specs: dict) -> dict[str, float | None]:
    out = {}
    for f in features:
        raw = numeric_value(site, f)
        out[f] = None if raw is None or specs.get(f) is None else transform(raw, f, specs[f])
    return out


def _cosine(a: dict[str, float], b: dict[str, float], w: dict[str, float]) -> tuple[float, dict]:
    keys = list(w.keys())
    num = sum(w[k] * a[k] * b[k] for k in keys)
    na = math.sqrt(sum(w[k] * a[k] * a[k] for k in keys))
    nb = math.sqrt(sum(w[k] * b[k] * b[k] for k in keys))
    if na == 0 or nb == 0:
        cos = 0.0
    else:
        cos = num / (na * nb)
        cos = max(-1.0, min(1.0, cos))
    score = 50.0 * (1.0 + cos)
    breakdown = []
    denom = na * nb if na and nb else 1.0
    for k in keys:
        term = w[k] * a[k] * b[k]
        breakdown.append({
            "feature": k,
            "weight_used": w[k],
            "target_normalized": a[k],
            "candidate_normalized": b[k],
            "delta_normalized": a[k] - b[k],
            "contribution": term / denom if denom else 0.0,
            "contribution_meaning": "término del producto interno ponderado dividido por |a||b| (suma = coseno)",
        })
    return score, {"cosine": cos, "features": breakdown}


def _euclidean(a: dict[str, float], b: dict[str, float], w: dict[str, float]) -> tuple[float, dict]:
    keys = list(w.keys())
    d2_terms = {k: w[k] * (a[k] - b[k]) ** 2 for k in keys}
    d = math.sqrt(sum(d2_terms.values()))
    score = 100.0 * math.exp(-d)
    total = sum(d2_terms.values()) or 1.0
    breakdown = []
    for k in keys:
        breakdown.append({
            "feature": k,
            "weight_used": w[k],
            "target_normalized": a[k],
            "candidate_normalized": b[k],
            "delta_normalized": a[k] - b[k],
            "contribution": d2_terms[k] / total,
            "contribution_meaning": "fracción de la distancia euclidiana al cuadrado ponderada",
        })
    return score, {"euclidean_distance": d, "features": breakdown}


def similar(
    target: dict,
    body: str,
    features: list[str],
    weights: dict[str, float],
    method: str,
    norm: str,
    top: int,
    apply_log: bool = True,
) -> dict:
    method = method.lower()
    norm = norm.lower()
    if method not in {"cosine", "euclidean"}:
        raise ValueError("method debe ser cosine o euclidean")
    if norm not in {"zscore", "minmax"}:
        raise ValueError("norm debe ser zscore o minmax")
    if top < 1:
        raise ValueError("top tiene que ser >= 1")

    specs = {f: stats_for(f, norm, apply_log) for f in features}
    target_vec_all = _vector(target, features, specs)

    candidates = [s for s in sites_by_body(body) if s["id"] != target["id"]]
    results = []
    for cand in candidates:
        cand_vec_all = _vector(cand, features, specs)
        used = [
            f for f in features
            if target_vec_all[f] is not None and cand_vec_all[f] is not None and weights.get(f, 0) > 0
        ]
        skipped = [f for f in features if f not in used]
        w_used = _reweight(weights, used)
        quality = {
            "features_requested": features,
            "features_used": used,
            "features_skipped": skipped,
            "weights_original": weights,
            "weights_renormalized": w_used,
            "skip_reason": (
                "Se omitieron rasgos sin valor en el objetivo, en el candidato, o sin estadísticos de normalización (hace falta ≥2 valores en el catálogo)."
                if skipped else None
            ),
        }
        flags = []
        for f in used:
            tf = target["features"][f]
            cf = cand["features"][f]
            if tf.get("quality") != "measured" or cf.get("quality") != "measured":
                flags.append({
                    "feature": f,
                    "target_quality": tf.get("quality"),
                    "candidate_quality": cf.get("quality"),
                })
            if not tf.get("comparable", True) or not cf.get("comparable", True):
                flags.append({"feature": f, "warning": "escalas o definiciones poco comparables"})
        quality["data_quality_flags"] = flags

        if len(used) < 1 or not w_used:
            results.append({
                "site": _site_card(cand),
                "score": None,
                "method": method,
                "norm": norm,
                "quality": quality,
                "breakdown": None,
                "raw_values": _raw_pair(target, cand, features),
            })
            continue

        a = {f: target_vec_all[f] for f in used}
        b = {f: cand_vec_all[f] for f in used}
        if method == "cosine":
            score, br = _cosine(a, b, w_used)
        else:
            score, br = _euclidean(a, b, w_used)
        results.append({
            "site": _site_card(cand),
            "score": round(score, 2),
            "method": method,
            "norm": norm,
            "quality": quality,
            "breakdown": br,
            "raw_values": _raw_pair(target, cand, features),
        })

    scored = [r for r in results if r["score"] is not None]
    unscored = [r for r in results if r["score"] is None]
    scored.sort(key=lambda r: r["score"], reverse=True)
    ranked = scored + unscored
    return {
        "target": _site_card(target),
        "search_body": body,
        "method": method,
        "norm": norm,
        "log_applied_to": [f for f, s in specs.items() if s and s.get("log")],
        "normalization_stats": {f: specs[f] for f in features},
        "formula": _formula(method),
        "matches": ranked[:top],
        "candidates_considered": len(results),
        "candidates_scored": len(scored),
    }


def _site_card(site: dict) -> dict:
    return {
        "id": site["id"],
        "name": site["name"],
        "short_name": site.get("short_name"),
        "body": site["body"],
        "lat": site["lat"],
        "lon": site["lon"],
        "lon_east_0_360": site.get("lon_east_0_360"),
        "geology_class": site.get("geology_class"),
        "summary": site.get("summary"),
        "tags": site.get("tags", []),
        "artemis_note": site.get("artemis_note"),
        "coord_source": site.get("coord_source"),
    }


def _raw_pair(target: dict, cand: dict, features: list[str]) -> dict:
    out = {}
    for f in features:
        tf = target["features"].get(f, {})
        cf = cand["features"].get(f, {})
        out[f] = {
            "target": {"value": tf.get("value"), "unit": tf.get("unit"), "quality": tf.get("quality"), "source": tf.get("source")},
            "candidate": {"value": cf.get("value"), "unit": cf.get("unit"), "quality": cf.get("quality"), "source": cf.get("source")},
        }
    return out


def _formula(method: str) -> dict:
    if method == "cosine":
        return {
            "score": "50 * (1 + cosine_ponderado)",
            "cosine": "sum(w_i a_i b_i) / (sqrt(sum w_i a_i^2) sqrt(sum w_i b_i^2)), con pesos renormalizados (suman 1) sobre los rasgos presentes en ambos sitios",
        }
    return {
        "score": "100 * exp(-d)",
        "d": "sqrt(sum w_i (a_i - b_i)^2), a y b ya normalizados; pesos renormalizados sobre los rasgos presentes",
    }
