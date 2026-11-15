"""G v0: comparison of sourced map categories (docs/propuestas/G.md).

Use the mean of shared composition/impact blocks and report coverage separately.
Missing evidence is never a zero or a penalty. These are not measured spectra.
"""
from __future__ import annotations

import math
from typing import Any, Dict

CLASSES = ("basaltico", "silicico", "clastico", "quimico", "cristalino", "hielo", "volc_indiviso", "sed_indiviso")
KEYS = tuple("g_lito_" + k for k in CLASSES)
FAMILIES = ((0, 1, 6), (2, 3, 7), (4,), (5,))


def sourced_value(item: Dict[str, Any]):
    value = (item or {}).get("value")
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if not item.get("source") or item.get("is_real") is False or item.get("comparable") is False:
        return None
    if item.get("quality") not in ("measured", "derived", "convention", "derived_from_published_range"):
        return None
    return float(value)


def composition(metrics):
    values = [sourced_value(metrics.get(k) or {}) for k in KEYS]
    if any(v is None or not 0 <= v <= 1 for v in values):
        return None
    return values if math.isclose(sum(values), 1.0, abs_tol=1e-6) else None


def similarity(target: Dict[str, Any], candidate_features: Dict[str, Any]) -> Dict[str, Any]:
    tm = target.get("metrics") or {}
    cm = {k: candidate_features.get(k) or {} for k in (*KEYS, "g_impacto")}
    a, b = composition(tm), composition(cm)
    blocks = {}
    if a is not None and b is not None:
        fine = sum(min(x, y) for x, y in zip(a, b))
        family = sum(min(sum(a[i] for i in group), sum(b[i] for i in group)) for group in FAMILIES)
        blocks["composition"] = (fine + family) / 2.0
    ai, bi = sourced_value(tm.get("g_impacto") or {}), sourced_value(cm.get("g_impacto") or {})
    if ai in (0, 1) and bi in (0, 1):
        blocks["impact"] = 1.0 - abs(ai - bi)
    ready = bool(blocks)
    return {
        "available": ready,
        "score": sum(blocks.values()) / len(blocks) if ready else None,
        "data_available": any(sourced_value(m) is not None for m in [*tm.values(), *cm.values()]),
        "reason": None if ready else "Hay geología parcial, pero falta un bloque comparable en ambos sitios." if any(sourced_value(m) is not None for m in [*tm.values(), *cm.values()]) else "Sin datos geológicos verificables para este par.",
        "representation": "geology_categories_v0",
        "blocks": blocks,
        "coverage": {"n_available": len(blocks), "n_possible": 2},
        "target_metrics": tm,
        "candidate_metrics": cm,
        "formula": "S_comp = 0.5 * overlap(classes) + 0.5 * overlap(families); S_impact = 1 - abs(x-y); S_G = mean(shared blocks). Missing blocks excluded; coverage reported separately.",
        "quality_flags": ["categorical_map_not_spectrum", "coarse_map_scale", "partial_geology_coverage"] if len(blocks) < 2 else ["categorical_map_not_spectrum", "coarse_map_scale"],
    }
