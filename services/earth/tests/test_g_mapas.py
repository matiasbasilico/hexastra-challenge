"""Tests de G: tabla de equivalencias, filas de g-mapas.jsonl y validaciones."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "services" / "earth" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "db"))

import g_equivalencias as eq  # noqa: E402
from measurements import validate  # noqa: E402

JSONL = ROOT / "data" / "measurements" / "g-mapas.jsonl"
FEATURES = ROOT / "data" / "measurements" / "g-mapas.features.json"


def _rows():
    return [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]


def _by_site():
    out = {}
    for r in _rows():
        out.setdefault(r["site_id"], {})[r["feature"]] = r
    return out


# ---------------------------------------------------------------- equivalencias
@pytest.mark.parametrize("liths, expected", [
    ("basalt", {"g_lito_basaltico": 1.0}),
    ("volcanic: mafic rocks", {"g_lito_basaltico": 1.0}),
    ("Rhyolite", {"g_lito_silicico": 1.0}),
    ("trachyte; volcanic", {"g_lito_silicico": 1.0}),
    ("sandstone; limestone", {"g_lito_clastico": 0.5, "g_lito_quimico": 0.5}),
])
def test_earth_keywords_map_to_classes(liths, expected):
    comp = eq.earth_composition(liths)
    assert {k: v for k, v in comp.items() if v} == expected
    assert abs(sum(comp.values()) - 1.0) < 1e-9


@pytest.mark.parametrize("liths", ["pumice", "lake", "", None])
def test_earth_unknown_lithology_is_not_guessed(liths):
    # "pumice" no debe disparar "ice"; "lake" no es una litología.
    assert eq.earth_composition(liths) is None


@pytest.mark.parametrize("liths, expected", [
    ("sedimentary", {"g_lito_sed_indiviso": 1.0}),
    ("Volcaniclastic, volcanic", {"g_lito_volc_indiviso": 1.0}),
    # La clase indivisa no se suma si el mapa ya dio una clase fina de esa familia.
    ("sandstone; sedimentary", {"g_lito_clastico": 1.0}),
    ("volcanic: mafic rocks", {"g_lito_basaltico": 1.0}),
    ("evaporites; sedimentary", {"g_lito_quimico": 1.0}),
])
def test_generic_terms_go_to_the_undivided_class_of_their_family(liths, expected):
    comp = eq.earth_composition(liths)
    assert {k: v for k, v in comp.items() if v} == expected


def test_every_composition_class_has_a_family():
    assert set(eq.FAMILY) == set(eq.COMPOSITION)


def test_moon_rules():
    comp, impact, _ = eq.moon_vector("Im2")
    assert comp["g_lito_basaltico"] == 1.0 and impact == 0.0
    comp, impact, _ = eq.moon_vector("pNc")
    assert comp is None and impact == 1.0
    comp, impact, _ = eq.moon_vector("Nt")
    assert comp is None and impact == 1.0
    assert eq.moon_vector("XYZ")[:2] == (None, None)


def test_mars_rules_never_turn_missing_impact_into_zero():
    comp, impact, _ = eq.mars_vector("Ave")
    assert comp["g_lito_basaltico"] == 1.0 and impact is None
    assert eq.mars_vector("AHi")[:2] == (None, 1.0)
    assert eq.mars_vector("HNt")[:2] == (None, None)


# ---------------------------------------------------------------- filas
def test_every_row_passes_the_repo_validator():
    rows = _rows()
    assert len(rows) == 74 * len(eq.FEATURES)
    for n, r in enumerate(rows, start=1):
        validate(r, "g-mapas.jsonl:%d" % n)


def test_features_are_declared_once_and_match_rows():
    defs = json.loads(FEATURES.read_text(encoding="utf-8"))
    assert set(defs) == set(eq.FEATURES)
    assert all(d["service"] == ["earth", "planetary"] for d in defs.values())
    assert {r["feature"] for r in _rows()} == set(eq.FEATURES)


def test_values_have_sources_and_nulls_say_why():
    for r in _rows():
        assert "http" in r["source"]
        if r["value"] is None:
            assert r["quality"] == "unavailable" and r["is_real"] is False
            assert "a completar" in r["note"]
        else:
            assert r["quality"] == "derived" and 0.0 <= r["value"] <= 1.0


def test_composition_sums_to_one_when_present():
    for site, feats in _by_site().items():
        vals = [feats[f]["value"] for f in eq.COMPOSITION]
        if any(v is None for v in vals):
            assert all(v is None for v in vals), site
        else:
            assert abs(sum(vals) - 1.0) < 1e-3, site


def test_all_catalog_sites_are_covered():
    ids = set()
    for svc in ("earth", "planetary"):
        data = json.loads((ROOT / "services" / svc / "data" / "catalog.json").read_text(encoding="utf-8"))
        ids |= {s["id"] for s in data["sites"]}
    assert set(_by_site()) == ids


def test_every_earth_site_has_an_impact_value():
    data = json.loads((ROOT / "services" / "earth" / "data" / "catalog.json").read_text(encoding="utf-8"))
    by_site = _by_site()
    for site in data["sites"]:
        assert by_site[site["id"]]["g_impacto"]["value"] in (0.0, 1.0)


# ---------------------------------------------------------------- validación contra lo publicado
@pytest.mark.parametrize("site, feature, value", [
    # Pali Aike: basaltos alcalinos y basanitas (D'Orazio et al. 2000, Tectonophysics 321:407).
    ("pali-aike", "g_lito_basaltico", 1.0),
    # Lonar y Meteor Crater (Barringer): cráteres confirmados en Osinski et al. 2022, Tabla.
    ("lonar", "g_impacto", 1.0),
    ("meteor-crater", "g_impacto", 1.0),
    ("vredefort", "g_impacto", 1.0),
    ("nordlinger-ries", "g_impacto", 1.0),
    ("haughton", "g_impacto", 1.0),
    # Río Cuarto no está entre las estructuras confirmadas de Osinski et al. 2022.
    ("crateres-rio-cuarto", "g_impacto", 0.0),
    # Salar de Uyuni: evaporitas (CGMW South America 1:5M, Quaternary Evaporitic).
    ("salar-de-uyuni", "g_lito_quimico", 1.0),
    # Pavonis Mons y Arsia Mons: edificios volcánicos (unidad Ave) en Tanaka et al. 2014.
    ("pavonis-mons", "g_lito_basaltico", 1.0),
    ("arsia-mons", "g_lito_basaltico", 1.0),
    # Gale: cráter de ~150 km mapeado como unidad de impacto AHi en SIM 3292.
    ("gale", "g_impacto", 1.0),
    # Marius Hills: meseta volcánica EIp de la DOMU lunar.
    ("marius-hills", "g_lito_basaltico", 1.0),
])
def test_pipeline_matches_published_geology(site, feature, value):
    assert _by_site()[site][feature]["value"] == value


def test_rows_for_builds_nulls_with_notes():
    pytest.importorskip("shapefile")
    pytest.importorskip("shapely")
    import ingest_g_mapas as ing

    res = ing.GResult(site_id="jezero", composition=None, impact=None, detail="Unidad mapeada: HNt.",
                      source="x https://example.org", composition_note="sin litología; a completar.",
                      impact_note="no resuelto; a completar.")
    rows = ing.rows_for(res)
    assert len(rows) == len(eq.FEATURES)
    for n, r in enumerate(rows):
        validate(r, "t:%d" % n)
        assert r["value"] is None


# ---------------------------------------------------------------- fase 2: Luna con Lunar Prospector
@pytest.mark.parametrize("feo, th, expected", [
    (4.2, 0.8, True),    # FHT anortosítico (Jolliff et al. 2000): media publicada
    (5.5, 1.5, True),    # FHT externo: media publicada, en el límite
    (10.1, 1.9, False),  # SPAT interno: no es feldespático
    (23.0, 3.3, False),  # basalto de mare
    (None, 0.8, False),  # sin dato no se adivina
])
def test_feldspathic_rule_uses_published_fht_means(feo, th, expected):
    assert eq.is_feldspathic(feo, th) is expected


def test_moon_impact_units_get_composition_only_from_orbital_chemistry():
    comp, impact, _ = eq.moon_vector("pNc", 4.8, 0.89)
    assert comp["g_lito_feldespatico"] == 1.0 and impact == 1.0
    comp, impact, _ = eq.moon_vector("pNc", 10.1, 1.9)
    assert comp is None and impact == 1.0
    comp, _, _ = eq.moon_vector("Im2", 4.0, 0.5)  # mare manda el mapa
    assert comp["g_lito_basaltico"] == 1.0


@pytest.mark.parametrize("site", ["shackleton-rim", "haworth", "malapert", "de-gerlache", "amundsen", "nobile"])
def test_lunar_polar_sites_are_feldspathic_with_lp_values_in_the_note(site):
    row = _by_site()[site]["g_lito_feldespatico"]
    assert row["value"] == 1.0
    assert "Lunar Prospector GRS píxel" in row["note"] and "pds-geosciences" in row["source"]


def test_marius_hills_lp_feo_agrees_with_the_mare_map_unit():
    import re
    note = _by_site()["marius-hills"]["g_lito_basaltico"]["note"]
    feo = float(re.search(r"FeO ([0-9.]+) %", note).group(1))
    assert feo > 15.0  # basaltos de mare: FeO alto; el mapa también dice EIp volcánico
