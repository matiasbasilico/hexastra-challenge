"""Textos why/breaks/missing de /tasi (services/earth/explain.py)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from explain import add_explanations, explain_match, format_number  # noqa: E402

# Forma real de un match de tasi.rank (Marius Hills frente a Campo de Piedra Pómez).
MATCH = {
    "site": {"id": "campo-piedra-pomez", "name": "Campo de Piedra Pómez"},
    "score": 47.4,
    "components": {
        "G": {"score": None, "available": False, "reason": "No sourced spectral vector.", "detail": {}},
        "T": {"score": 74.83, "available": True, "reason": None,
              "detail": {"D_M": 0.2899, "used": ["relative_relief_m", "slope_deg", "roughness_m"]}},
        "E": {"score": 0.09, "available": True, "reason": None,
              "detail": {"parts": [
                  {"metric": "temp_mean", "x": -54.53, "y": 9.49, "scale": 10.08, "s": 0.0017},
                  {"metric": "temp_diurnal_range", "x": 295.38, "y": 12.97, "scale": 1.74, "s": 4e-71},
              ]}},
        "V": {"score": 61.67, "available": True, "reason": None,
              "detail": {"parts": [{"metric": "precip_mm", "x": 0.0, "y": 127.9, "scale": 264.6, "s": 0.6167}]}},
        "O": {"score": None, "available": False, "reason": "No comparable metric.", "detail": {}},
    },
}


def test_why_names_the_best_component_with_its_metrics():
    ex = explain_match(MATCH)
    assert ex["why"] == (
        "Lo más parecido es terreno (T), 74,8 de 100: relieve relativo, pendiente y rugosidad "
        "parecidos (distancia de Mahalanobis 0,29)."
    )


def test_breaks_names_the_worst_metric_with_both_values_and_units():
    ex = explain_match(MATCH)
    assert ex["breaks"] == (
        "Lo menos parecido es clima e iluminación (E), 0,1 de 100: amplitud térmica diaria "
        "13 °C en la Tierra frente a 295,4 °C en el destino."
    )


def test_missing_lists_components_without_data_not_zero():
    ex = explain_match(MATCH)
    assert ex["missing"] == ["Geología (G)", "Operación (O)"]
    assert "Geología" not in ex["why"] and "Geología" not in ex["breaks"]


def test_precip_zero_on_target_is_flagged_as_convention():
    only_v = {"components": {"V": MATCH["components"]["V"], "E": MATCH["components"]["E"]}}
    ex = explain_match(only_v)
    assert "precipitación anual 127,9 mm en la Tierra frente a 0 mm en el destino (convención para un cuerpo sin lluvia)" in ex["why"]


def test_single_component_does_not_invent_a_break():
    ex = explain_match({"components": {"T": MATCH["components"]["T"], "G": MATCH["components"]["G"]}})
    assert ex["why"].startswith("Lo más parecido es terreno (T)")
    assert "un solo componente" in ex["breaks"]
    assert ex["missing"] == ["Geología (G)"]


def test_no_component_with_data_leaves_why_null():
    ex = explain_match({"components": {"G": MATCH["components"]["G"], "O": MATCH["components"]["O"]}})
    assert ex["why"] is None
    assert ex["missing"] == ["Geología (G)", "Operación (O)"]


def test_add_explanations_does_not_change_scores_or_weights():
    result = {"index": "TASI", "matches": [copy.deepcopy(MATCH)]}
    before = copy.deepcopy(result)
    out = add_explanations(result)
    assert result == before, "no muta el resultado original"
    m = out["matches"][0]
    assert m["score"] == MATCH["score"]
    assert m["components"] == MATCH["components"]
    assert set(("why", "breaks", "missing", "explain_source")) <= set(m)


def test_format_number_uses_comma_decimal_and_real_minus():
    assert format_number(53.68) == "53,7"
    assert format_number(1234.5) == "1.234,5"
    assert format_number(-54.53) == "−54,5"
    assert format_number(12.0) == "12"
    assert format_number(None) == "sin dato"


@pytest.mark.skipif(not (ROOT / "data" / "catalog.json").exists(), reason="earth catalog not ingested yet")
def test_tasi_endpoint_returns_why_breaks_missing():
    from main import app

    client = TestClient(app)
    vec = {
        "id": "test-target", "name": "Test", "body": "mars", "lat": 0.0, "lon": 0.0,
        "components": {
            "G": {"available": False, "score_ready": False},
            "T": {"available": True, "score_ready": True, "metrics": {
                "relative_relief_m": {"value": 120.0, "is_real": True},
                "slope_deg": {"value": 4.0, "is_real": True},
                "roughness_m": {"value": 6.0, "is_real": True}}},
            "E": {"available": False, "score_ready": False},
            "Vo": {"available": True, "score_ready": True, "metrics": {
                "precip_mm": {"value": 0.0, "quality": "convention", "is_real": True}}},
            "O": {"available": False, "score_ready": False},
        },
    }
    res = client.post("/tasi", json={"target": vec, "top": 3})
    assert res.status_code == 200
    for m in res.json()["matches"]:
        assert "why" in m and "breaks" in m and isinstance(m["missing"], list)
        assert "Geología (G)" in m["missing"]
