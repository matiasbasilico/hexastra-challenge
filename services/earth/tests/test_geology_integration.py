import copy
import json
from pathlib import Path

import pytest

from geology import KEYS, similarity
from tasi import rank, s_operational
from explain import add_explanations
import dbsource

ROOT = Path(__file__).resolve().parents[3]


def item(value, **extra):
    return dict(value=value, quality="derived", source="https://source.example/map", is_real=value is not None, **extra)


def rock(key="g_lito_basaltico", impact=0):
    return {**{k: item(int(k == key)) for k in KEYS}, "g_impacto": item(impact)}


def test_same_rock_and_origin_are_full_match_with_two_blocks():
    out = similarity({"metrics": rock()}, rock())
    assert out["score"] == 1
    assert out["coverage"] == {"n_available": 2, "n_possible": 2}


def test_family_overlap_and_true_zero_are_not_missing():
    out = similarity({"metrics": rock()}, rock("g_lito_volc_indiviso", 1))
    assert out["blocks"] == {"composition": 0.5, "impact": 0}
    assert out["score"] == 0.25
    out = similarity({"metrics": {"g_impacto": item(1)}}, {"g_impacto": item(0)})
    assert out["available"] is True and out["score"] == 0


def test_missing_block_excluded_and_coverage_reported_without_penalty():
    out = similarity({"metrics": {"g_impacto": item(1)}}, rock(impact=1))
    assert out["score"] == 1 and out["coverage"]["n_available"] == 1
    assert out["blocks"] == {"impact": 1}


@pytest.mark.parametrize("bad", [None, float("nan"), -1, 2])
def test_invalid_or_incomplete_composition_does_not_become_a_vector(bad):
    metrics = rock()
    metrics[KEYS[0]] = item(bad)
    metrics["g_impacto"] = item(None)
    out = similarity({"metrics": metrics}, rock())
    assert out["score"] is None and out["available"] is False


def test_unverified_values_and_noncomparable_data_are_excluded():
    for extra in ({"source": None}, {"is_real": False}, {"quality": "placeholder"}, {"comparable": False}):
        out = similarity({"metrics": {"g_impacto": {**item(1), **extra}}}, rock())
        assert out["score"] is None


def test_operational_access_has_context_but_never_increases_tasi():
    access = {"dist_road_km": item(0, comparable=False), "population_50km": item(0, comparable=False)}
    out = s_operational({}, access)
    assert out["data_available"] is True and out["score"] is None and out["available"] is False
    assert out["used"] == ["dist_road_km", "population_50km"]
    target = {"id": "test", "components": {"G": {"metrics": rock()}}}
    candidate = {"id": "earth", "name": "Earth", "features": {**rock(), **access}}
    result = add_explanations(rank(target, [candidate], {}, apply_mask=False))
    match = result["matches"][0]
    assert match["score"] == 100 and match["weights"]["renormalized"] == {"G": 1}
    assert "Geología (G)" not in match["missing"] and "Operación (O)" not in match["missing"]
    assert match["coverage"]["available_components"] == ["G"]
    assert "2 de 2 bloques" in match["why"]
    candidate["features"].update({"dist_road_km": item(999), "population_50km": item(900000)})
    assert rank(target, [candidate], {}, apply_mask=False)["matches"][0]["score"] == 100


def test_supplement_is_read_only_preserves_existing_measurements_and_sources():
    base = {"sites": [{"id": "payun-matru", "features": {"g_impacto": item(1)}}]}
    original = copy.deepcopy(base)
    out = dbsource._supplement(copy.deepcopy(base), "earth")
    assert base == original
    feats = out["sites"][0]["features"]
    assert feats["g_impacto"] == original["sites"][0]["features"]["g_impacto"]
    assert feats["g_lito_basaltico"]["value"] == 1 and feats["g_lito_basaltico"]["source"]
    assert feats["dist_road_km"]["value"] == 25.61
    assert feats["dist_road_km"]["comparable"] is False
    assert "g_lito_basaltico" in out["feature_defs"]


def test_published_dataset_examples_and_real_gaps():
    rows = [json.loads(s) for s in (ROOT / "data/measurements/g-mapas.jsonl").read_text().splitlines()]
    sites = {}
    for row in rows:
        sites.setdefault(row["site_id"], {})[row["feature"]] = row
    for target_id, n in [("marius-hills", 2), ("arsia-mons", 1), ("pavonis-mons", 1)]:
        out = similarity({"metrics": sites[target_id]}, sites["payun-matru"])
        assert out["score"] == 1 and out["coverage"]["n_available"] == n
    assert similarity({"metrics": sites["jezero"]}, sites["payun-matru"])["score"] is None
