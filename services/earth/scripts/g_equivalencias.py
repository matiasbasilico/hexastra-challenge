"""Tabla de equivalencias G (geología / materiales) entre la Tierra, la Luna y Marte.

Propuesta del agente G, versión 0 (piloto). Ver docs/propuestas/G.md.

Cada sitio recibe un vector con dos bloques:

* Composición dominante a escala de mapa (fracciones que suman 1):
  basáltico, silícico, clástico, químico, cristalino, hielo.
* Origen por impacto (0/1): si el punto cae en material de impacto mapeado
  (Luna/Marte) o dentro de una estructura de impacto confirmada (Tierra).

Reglas de honestidad:

* Si el mapa no dice la composición (p. ej. unidades morfoestratigráficas de
  Marte, o cráteres y terras lunares, que el mapa define por origen), la
  composición queda null «a completar»; no se rellena.
* Si el mapa no puede resolver el impacto a su escala (cráteres chicos de
  Marte en el mapa 1:20M), g_impacto queda null; ausencia en el mapa no es 0.
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

COMPOSITION = (
    "g_lito_basaltico",
    "g_lito_silicico",
    "g_lito_clastico",
    "g_lito_quimico",
    "g_lito_cristalino",
    "g_lito_hielo",
)
IMPACT = "g_impacto"
FEATURES = COMPOSITION + (IMPACT,)

FEATURE_DEFS = {
    "g_lito_basaltico": "Fracción basáltica / volcánica máfica (incluye piroclastos basálticos)",
    "g_lito_silicico": "Fracción volcánica intermedia a félsica (andesita, dacita, riolita, ignimbrita)",
    "g_lito_clastico": "Fracción sedimentaria clástica o no consolidada (arenisca, aluvio, médanos)",
    "g_lito_quimico": "Fracción sedimentaria química (carbonatos, evaporitas)",
    "g_lito_cristalino": "Fracción plutónica o metamórfica (granito, gneis, esquisto)",
    "g_lito_hielo": "Fracción de hielo (glaciares, casquete polar)",
    "g_impacto": "1 si el punto está en material de impacto mapeado o en una estructura de impacto confirmada",
}

# ---------------------------------------------------------------- Tierra
# Palabras clave sobre el campo "lith" de Macrostrat (escala small, ~1:5M).
EARTH_KEYWORDS: Tuple[Tuple[str, str], ...] = (
    ("basalt", "g_lito_basaltico"),
    ("mafic volcanic", "g_lito_basaltico"),
    ("volcanic: mafic", "g_lito_basaltico"),
    ("basanite", "g_lito_basaltico"),
    ("andesite", "g_lito_silicico"),
    ("dacite", "g_lito_silicico"),
    ("rhyolite", "g_lito_silicico"),
    ("trachyte", "g_lito_silicico"),
    ("ignimbrite", "g_lito_silicico"),
    ("tuff", "g_lito_silicico"),
    ("felsic volcanic", "g_lito_silicico"),
    ("intermediate volcanic", "g_lito_silicico"),
    ("volcanic: felsic", "g_lito_silicico"),
    ("volcanic: intermediate", "g_lito_silicico"),
    ("sandstone", "g_lito_clastico"),
    ("siltstone", "g_lito_clastico"),
    ("shale", "g_lito_clastico"),
    ("mudstone", "g_lito_clastico"),
    ("conglomerate", "g_lito_clastico"),
    ("siliciclastic", "g_lito_clastico"),
    ("alluvium", "g_lito_clastico"),
    ("unconsolidated", "g_lito_clastico"),
    ("sediment", "g_lito_clastico"),
    ("sand", "g_lito_clastico"),
    ("gravel", "g_lito_clastico"),
    ("limestone", "g_lito_quimico"),
    ("dolomite", "g_lito_quimico"),
    ("carbonate", "g_lito_quimico"),
    ("evaporite", "g_lito_quimico"),
    ("gypsum", "g_lito_quimico"),
    ("halite", "g_lito_quimico"),
    ("granite", "g_lito_cristalino"),
    ("gneiss", "g_lito_cristalino"),
    ("schist", "g_lito_cristalino"),
    ("plutonic", "g_lito_cristalino"),
    ("metamorphic", "g_lito_cristalino"),
    ("ice", "g_lito_hielo"),
    ("glacier", "g_lito_hielo"),
)


def earth_composition(liths: str) -> Optional[Dict[str, float]]:
    """Fracciones iguales entre las clases reconocidas en el texto de litologías.

    None si ninguna palabra clave coincide (no se adivina).
    """
    text = (liths or "").lower()
    found = []
    for keyword, cls in EARTH_KEYWORDS:
        if keyword in text and cls not in found:
            # "sediment" también aparece en "sedimentary"; "ice" en "pumice"/"silicic":
            # se evalúan sólo palabras completas para evitar falsos positivos.
            if _whole_word(text, keyword):
                found.append(cls)
    if not found:
        return None
    share = 1.0 / len(found)
    return {cls: (share if cls in found else 0.0) for cls in COMPOSITION}


def _whole_word(text: str, keyword: str) -> bool:
    return re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(keyword), text) is not None


# ---------------------------------------------------------------- Luna
# Unified Geologic Map of the Moon 1:5M (Fortezzo et al. 2020). Interpretaciones
# tomadas de la DOMU incluida en el paquete GIS.
MOON_BASALTIC = {"Em", "Im1", "Im2", "Imd", "EIp", "Id"}
MOON_IMPACT_PREFIXES = ("Cc", "Ccc", "Csc", "Ec", "Ecc", "Esc", "Ic", "Icc", "Isc", "Icf", "Ib", "Ibm",
                        "Iia", "Iiap", "Iic", "Iif", "Ioh", "Ios", "Iom", "Iork", "Iorm", "Nc", "Nb",
                        "Nbl", "Nbm", "Nbsc", "Nnj", "pNb", "pNbm", "pNc")
# Terras y planicies: la DOMU las interpreta como "megaregolito / eyecta de cráteres y cuencas".
MOON_EJECTA_TERRA = {"It", "INt", "Nt", "pNt", "Ntp", "Ip", "INp", "Np"}


def moon_vector(unit: str) -> Tuple[Optional[Dict[str, float]], Optional[float], str]:
    """(composición o None, impacto o None, regla aplicada)."""
    if unit in MOON_BASALTIC:
        comp = {cls: (1.0 if cls == "g_lito_basaltico" else 0.0) for cls in COMPOSITION}
        return comp, 0.0, "unidad de mare / material volcánico basáltico según la DOMU"
    if unit in MOON_EJECTA_TERRA or unit.startswith(MOON_IMPACT_PREFIXES):
        return None, 1.0, "unidad de cráter, cuenca o eyecta según la DOMU; el mapa no da composición"
    return None, None, "unidad sin regla de equivalencia (a completar)"


# ---------------------------------------------------------------- Marte
# Geologic Map of Mars 1:20M, SIM 3292 (Tanaka et al. 2014). Unidades volcánicas
# -> basálticas por la composición de la corteza (McSween et al. 2009).
MARS_VOLCANIC = {"Av", "Ave", "lAv", "lAvf", "AHv", "eHv", "lHv", "lHvf", "Hve", "Nve", "lNv"}
MARS_IMPACT = {"AHi"}
MARS_ICE = {"lApc"}


def mars_vector(unit: str) -> Tuple[Optional[Dict[str, float]], Optional[float], str]:
    if unit in MARS_VOLCANIC:
        comp = {cls: (1.0 if cls == "g_lito_basaltico" else 0.0) for cls in COMPOSITION}
        return comp, None, "unidad volcánica (SIM 3292) -> basáltica (McSween et al. 2009); impacto no resuelto a 1:20M"
    if unit in MARS_IMPACT:
        return None, 1.0, "unidad de impacto AHi (SIM 3292); el mapa no da composición"
    if unit in MARS_ICE:
        comp = {cls: (1.0 if cls == "g_lito_hielo" else 0.0) for cls in COMPOSITION}
        return comp, None, "casquete polar lApc (SIM 3292)"
    return None, None, "unidad morfoestratigráfica sin litología en SIM 3292 (a completar con CRISM/TES)"
