"""S_G (geology.py) y su uso en TASI: opción (ii) aprobada el 14 nov 2026."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from geology import COMPOSITION, LABELS, s_geology, values_from_component, values_from_features
from tasi import rank

ROOT = Path(__file__).resolve().parents[3]


def vals(impact=None, **comp):
    out = {k: None for k in LABELS}
    if comp:
        out.update({k: 0.0 for k in COMPOSITION})
        out.update({"g_lito_" + k: v for k, v in comp.items()})
    out["g_impacto"] = impact
    return out


def test_same_rock_and_same_origin_is_one():
    r = s_geology(vals(0.0, basaltico=1.0), vals(0.0, basaltico=1.0))
    assert r["score"] == pytest.approx(1.0) and r["coverage"] == "2/2"


def test_one_block_only_is_halved():
    # Lonar (cráter en basalto) vs Shackleton (cráter lunar sin composición): 1,0 · ½.
    r = s_geology(vals(1.0), vals(1.0, basaltico=1.0))
    assert r["score_raw"] == pytest.approx(1.0)
    assert r["score"] == pytest.approx(0.5)
    assert r["coverage"] == "1/2" and r["missing_blocks"] == ["composition"]


def test_undivided_class_gets_family_credit():
    r = s_geology(vals(0.0, basaltico=1.0), vals(0.0, volc_indiviso=1.0))
    assert r["blocks"][0]["s"] == pytest.approx(0.5)
    assert r["score"] == pytest.approx(0.75)


def test_different_rock_and_origin_is_zero():
    r = s_geology(vals(0.0, basaltico=1.0), vals(1.0, clastico=1.0))
    assert r["score"] == pytest.approx(0.0)


def test_no_shared_block_is_unavailable_not_zero():
    r = s_geology(vals(None), vals(1.0, basaltico=1.0))
    assert r["available"] is False and r["score"] is None


def test_partial_composition_is_not_used():
    target = vals(0.0, basaltico=1.0)
    target["g_lito_hielo"] = None
    r = s_geology(target, vals(0.0, basaltico=1.0))
    assert r["coverage"] == "1/2"


def test_values_from_component_reads_labels_and_vector():
    comp = {"vector_labels": list(LABELS), "vector": [1.0] + [0.0] * (len(COMPOSITION) - 1) + [None]}
    v = values_from_component(comp)
    assert v["g_lito_basaltico"] == 1.0 and v["g_impacto"] is None
    feats = {"g_impacto": {"value": 1.0}, "g_lito_basaltico": {"value": None}}
    assert values_from_features(feats)["g_impacto"] == 1.0


def test_planetary_vector_uses_the_same_labels():
    path = ROOT / "services" / "planetary" / "vector.py"
    spec = importlib.util.spec_from_file_location("planetary_vector_for_g_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert tuple(mod.G_LABELS) == LABELS


def test_equivalence_table_uses_the_same_classes():
    path = ROOT / "services" / "earth" / "scripts" / "g_equivalencias.py"
    spec = importlib.util.spec_from_file_location("g_equivalencias_for_g_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.FEATURES == LABELS
    defs = json.loads((ROOT / "data" / "measurements" / "g-mapas.features.json").read_text(encoding="utf-8"))
    assert tuple(sorted(defs)) == tuple(sorted(LABELS))


def _site(sid, impact, comp):
    feats = {k: {"value": v} for k, v in vals(impact, **comp).items()}
    feats.update({"relative_relief": {"value": 100.0}, "slope": {"value": 5.0}, "roughness": {"value": 2.0},
                  "ndvi": {"value": 0.05}, "has_liquid_water": {"value": False}})
    return {"id": sid, "name": sid, "features": feats}


def test_rank_uses_geology_from_candidate_features():
    target = {
        "id": "marius-hills", "body": "moon", "name": "Marius Hills",
        "components": {
            "G": {"available": True, "score_ready": True, "vector_labels": list(LABELS),
                  "vector": [1.0] + [0.0] * (len(COMPOSITION) - 1) + [0.0]},
            "T": {}, "E": {}, "Vo": {}, "O": {},
        },
    }
    basalt = _site("basalto", 0.0, {"basaltico": 1.0})
    crater = _site("crater-sedimentario", 1.0, {"sed_indiviso": 1.0})
    cov = {"labels": ["relative_relief_m", "slope_deg", "roughness_m"], "sigma": np.eye(3).tolist()}
    out = rank(target, [crater, basalt], cov, weights={"G": 1, "T": 0, "E": 0, "V": 0, "O": 0}, top=5)
    by_id = {m["site"]["id"]: m for m in out["matches"]}
    assert by_id["basalto"]["components"]["G"]["score_0_1"] == pytest.approx(1.0)
    assert by_id["crater-sedimentario"]["components"]["G"]["score_0_1"] == pytest.approx(0.0)
    assert by_id["basalto"]["components"]["G"]["detail"]["coverage"] == "2/2"
    assert out["matches"][0]["site"]["id"] == "basalto"


def test_rank_without_target_geology_keeps_g_null():
    target = {"id": "x", "components": {"G": {"available": False, "score_ready": False, "reason": "sin g"},
                                        "T": {}, "E": {}, "Vo": {}, "O": {}}}
    out = rank(target, [_site("a", 0.0, {"basaltico": 1.0})], None, top=5)
    assert out["matches"][0]["components"]["G"]["available"] is False
