from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

DB = Path(__file__).resolve().parents[1]
if str(DB) not in sys.path:
    sys.path.insert(0, str(DB))

from measurements import MeasurementError, merge, read_dir, validate  # noqa: E402


def row(**kw):
    base = {
        "site_id": "pali-aike", "feature": "ndvi", "value": 0.08, "unit": "unitless",
        "quality": "measured", "is_real": True,
        "source": "MODIS MOD13Q1 v061 via AppEEARS. https://appeears.earthdatacloud.nasa.gov",
        "note": None, "method": "x.py", "retrieved_at": "2026-11-14",
    }
    base.update(kw)
    return base


def test_valid_row_passes():
    r = validate(row(), "a.jsonl:1")
    assert r.value == 0.08 and r.dataset == "a.jsonl"


@pytest.mark.parametrize("bad, message", [
    (dict(value=None, quality="measured", is_real=False), "placeholder"),
    (dict(value=None, quality="unavailable", is_real=False, note="sin dato"), "a completar"),
    (dict(source="sin url"), "URL"),
    (dict(quality="guessed"), "no válida"),
    (dict(retrieved_at="14/11/2026"), "AAAA-MM-DD"),
    (dict(replaces_base=True), "replaces_reason"),
])
def test_rules_reject_bad_rows(bad, message):
    with pytest.raises(MeasurementError, match=message):
        validate(row(**bad), "a.jsonl:1")


def test_null_with_note_is_allowed():
    r = validate(row(value=None, quality="unavailable", is_real=False, note="API caída, a completar"), "a.jsonl:1")
    assert r.value is None


def test_merge_fills_nulls_but_never_overwrites_silently():
    base = {("pali-aike", "ndvi"): {"value": None}, ("pali-aike", "slope"): {"value": 2.0}}
    ok = merge(base, [validate(row(), "a.jsonl:1")], ["pali-aike"])
    assert ok.features[("pali-aike", "ndvi")]["value"] == 0.08
    with pytest.raises(MeasurementError, match="replaces_base"):
        merge(base, [validate(row(feature="slope", value=3.0), "a.jsonl:1")], ["pali-aike"])
    replaced = merge(base, [validate(row(feature="slope", value=3.0, replaces_base=True,
                                         replaces_reason="DEM oficial NASADEM"), "a.jsonl:1")], ["pali-aike"])
    assert replaced.features[("pali-aike", "slope")]["value"] == 3.0


def test_two_files_cannot_write_the_same_cell():
    rows = [validate(row(), "a.jsonl:1"), validate(row(value=0.1), "b.jsonl:1")]
    with pytest.raises(MeasurementError, match="orquestador"):
        merge({}, rows, ["pali-aike"])


def test_unknown_site_is_rejected():
    with pytest.raises(MeasurementError, match="desconocido"):
        merge({}, [validate(row(site_id="nowhere"), "a.jsonl:1")], ["pali-aike"])


def test_read_dir_collects_rows_and_feature_defs(tmp_path):
    (tmp_path / "a.jsonl").write_text(json.dumps(row()) + "\n\n", encoding="utf-8")
    (tmp_path / "a.features.json").write_text(json.dumps({"ndvi_mean": {"service": "earth", "unit": "unitless"}}), encoding="utf-8")
    rows, defs = read_dir(tmp_path)
    assert len(rows) == 1 and "ndvi_mean" in defs


def test_repo_measurement_files_are_valid():
    from build import build

    merged, report = build()
    assert report["sites"] == {"planetary": len(merged["planetary"]["sites"]), "earth": len(merged["earth"]["sites"])}
