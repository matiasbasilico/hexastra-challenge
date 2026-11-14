"""S_G — similitud geológica categórica (componente G de TASI).

Aprobada por el usuario el 14 nov 2026 (docs/propuestas/G.md §6, opción ii).

Cada sitio trae, desde data/measurements/g-mapas.jsonl, dos bloques:

* composición a escala de mapa: fracciones g_lito_* que suman 1;
* origen por impacto: g_impacto (0/1).

    S_comp = ½·Σ_clases min(a_i, b_i) + ½·Σ_familias min(A_f, B_f)
    S_imp  = 1 − |a_imp − b_imp|
    S_G    = promedio(bloques comparables) · (bloques comparables / 2)

Un bloque sólo entra si tiene dato en los dos lados. El factor de cobertura baja
el puntaje cuando sólo se pudo comparar un bloque (menos evidencia, menos puntaje).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional

COMPOSITION = (
    "g_lito_basaltico",
    "g_lito_silicico",
    "g_lito_clastico",
    "g_lito_quimico",
    "g_lito_cristalino",
    "g_lito_hielo",
    "g_lito_volc_indiviso",
    "g_lito_sed_indiviso",
)
IMPACT = "g_impacto"
LABELS = COMPOSITION + (IMPACT,)

# Familias: dan crédito parcial entre una clase indivisa y sus clases finas.
FAMILY = {
    "g_lito_basaltico": "volcanica",
    "g_lito_silicico": "volcanica",
    "g_lito_volc_indiviso": "volcanica",
    "g_lito_clastico": "sedimentaria",
    "g_lito_quimico": "sedimentaria",
    "g_lito_sed_indiviso": "sedimentaria",
    "g_lito_cristalino": "cristalina",
    "g_lito_hielo": "hielo",
}
N_BLOCKS = 2
FORMULA = ("S_G = mean(available blocks) * (n_blocks / 2); "
           "S_comp = 0.5*sum_class min(a,b) + 0.5*sum_family min(A,B); S_imp = 1 - |a-b|")


def _num(x: Any) -> Optional[float]:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return float(x)
    return None


def values_from_features(feats: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    """g_* values from a site's features dict ({id: {"value": ...}})."""
    return {k: _num(((feats or {}).get(k) or {}).get("value")) for k in LABELS}


def values_from_component(comp: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    """g_* values from a G component of a feature vector (metrics or labels+vector)."""
    labels = (comp or {}).get("vector_labels") or []
    vec = (comp or {}).get("vector") or []
    if labels and len(labels) == len(vec):
        pairs = dict(zip(labels, vec))
        return {k: _num(pairs.get(k)) for k in LABELS}
    metrics = (comp or {}).get("metrics") or {}
    return {k: _num((metrics.get(k) or {}).get("value")) for k in LABELS}


def _composition(v: Mapping[str, Optional[float]]) -> Optional[Dict[str, float]]:
    vals = [v.get(k) for k in COMPOSITION]
    if any(x is None for x in vals):
        return None
    return {k: float(v[k]) for k in COMPOSITION}


def _families(comp: Mapping[str, float]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for cls, frac in comp.items():
        out[FAMILY[cls]] = out.get(FAMILY[cls], 0.0) + frac
    return out


def s_composition(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    by_class = sum(min(a[k], b[k]) for k in COMPOSITION)
    fa, fb = _families(a), _families(b)
    by_family = sum(min(fa.get(f, 0.0), fb.get(f, 0.0)) for f in set(fa) | set(fb))
    return 0.5 * by_class + 0.5 * by_family


def s_geology(target: Mapping[str, Optional[float]], candidate: Mapping[str, Optional[float]]) -> Dict[str, Any]:
    """S_G between a target (Moon/Mars) and an Earth candidate. Never fills nulls."""
    blocks: List[Dict[str, Any]] = []
    missing: List[str] = []
    ca, cb = _composition(target), _composition(candidate)
    if ca is not None and cb is not None:
        blocks.append({"block": "composition", "s": s_composition(ca, cb)})
    else:
        missing.append("composition")
    ia, ib = target.get(IMPACT), candidate.get(IMPACT)
    if ia is not None and ib is not None:
        blocks.append({"block": "impact", "s": 1.0 - abs(ia - ib)})
    else:
        missing.append("impact")
    if not blocks:
        return {
            "available": False,
            "score": None,
            "reason": "No geology block (map composition or impact origin) has a sourced value on both sides; S_G is not invented.",
            "blocks": [],
            "missing_blocks": missing,
            "coverage": "0/%d" % N_BLOCKS,
        }
    raw = sum(b["s"] for b in blocks) / len(blocks)
    factor = len(blocks) / N_BLOCKS
    return {
        "available": True,
        "score": raw * factor,
        "score_raw": raw,
        "coverage_factor": factor,
        "coverage": "%d/%d" % (len(blocks), N_BLOCKS),
        "blocks": blocks,
        "missing_blocks": missing,
        "reason": None,
        "formula": FORMULA,
    }
