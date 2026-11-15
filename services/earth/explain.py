"""Textos «por qué se parece / en qué no / dato a completar» para cada resultado de /tasi.

Se arman SOLO con el desglose que `tasi.rank` ya devuelve (puntaje por componente, métricas
comparadas con su valor en el destino y en la Tierra, distancia de Mahalanobis de T). No cambia
ninguna fórmula ni ningún peso: es una lectura en castellano del mismo resultado.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

COMPONENT_KEYS = ("G", "T", "E", "V", "O")

COMPONENT_LABELS = {
    "G": "Geología (G)",
    "T": "Terreno (T)",
    "E": "Clima e iluminación (E)",
    "V": "Volátiles o hielo (V)",
    "O": "Operación (O)",
}

# Etiqueta y unidad de cada métrica que comparan E y V (claves de tasi.s_thermal y tasi.s_volatiles).
METRIC_LABELS: Dict[str, Tuple[str, str]] = {
    "temp_mean": ("temperatura media", "°C"),
    "temp_diurnal_range": ("amplitud térmica diaria", "°C"),
    "illumination_pct": ("iluminación", "%"),
    "precip_mm": ("precipitación anual", "mm"),
    "water_ice_indicator": ("indicador de hielo", ""),
}

# Dimensiones de T (tasi.T_LABELS).
T_LABELS = {
    "relative_relief_m": "relieve relativo",
    "slope_deg": "pendiente",
    "roughness_m": "rugosidad",
}


def format_number(value: Optional[float], digits: int = 1) -> str:
    """Número con coma decimal y punto de miles (es-AR), sin ceros sobrantes."""
    if value is None:
        return "sin dato"
    rounded = round(float(value), digits)
    if rounded == int(rounded):
        text = "{:,.0f}".format(rounded)
    else:
        text = "{:,.{d}f}".format(rounded, d=digits).rstrip("0").rstrip(".")
    text = text.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    return text.replace("-", "−") if rounded < 0 else text


def _join(words: List[str]) -> str:
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-1]) + " y " + words[-1]


def _metric_text(part: Dict[str, Any]) -> Optional[str]:
    label, unit = METRIC_LABELS.get(part.get("metric"), (part.get("metric"), ""))
    x, y = part.get("x"), part.get("y")
    if x is None or y is None:
        return None
    suffix = (" " + unit) if unit and unit != "%" else unit
    earth = format_number(y) + suffix
    target = format_number(x) + suffix
    text = "%s %s en la Tierra frente a %s en el destino" % (label, earth, target)
    if part.get("metric") == "precip_mm" and float(x) == 0.0:
        text += " (convención para un cuerpo sin lluvia)"
    return text


def _component_line(key: str, comp: Dict[str, Any], best: bool) -> str:
    head = "%s, %s de 100" % (COMPONENT_LABELS[key], format_number(comp.get("score")))
    detail = comp.get("detail") or {}
    if key == "G":
        labels = {"composition": "tipo de roca", "impact": "origen por impacto"}
        blocks = detail.get("blocks") or {}
        body = _join([labels[k] for k in blocks])
        return "%s: se comparan %s (%s de 2 bloques geológicos)." % (head, body, len(blocks))
    if key == "T":
        used = [T_LABELS.get(u, u) for u in detail.get("used") or []]
        dm = detail.get("D_M")
        how = "parecidos" if best else "se alejan"
        body = "%s %s" % (_join(used) or "relieve", how)
        if dm is not None:
            body += " (distancia de Mahalanobis %s)" % format_number(dm, 2)
        return "%s: %s." % (head, body)
    parts = [p for p in detail.get("parts") or [] if p.get("s") is not None]
    if not parts:
        return head + "."
    # Para «por qué se parece», la métrica más parecida; para «en qué no», la más lejana.
    part = max(parts, key=lambda p: p["s"]) if best else min(parts, key=lambda p: p["s"])
    text = _metric_text(part)
    return "%s: %s." % (head, text) if text else head + "."


def explain_match(match: Dict[str, Any]) -> Dict[str, Any]:
    """Devuelve why, breaks y missing para un resultado de tasi.rank, sin modificarlo."""
    comps = match.get("components") or {}
    scored = [
        (k, comps[k]) for k in COMPONENT_KEYS
        if k in comps and comps[k].get("available") and comps[k].get("score") is not None
    ]
    missing = [COMPONENT_LABELS[k] for k in COMPONENT_KEYS if k in comps and (k, comps[k]) not in scored and not comps[k].get("data_available")]
    if not scored:
        return {
            "why": None,
            "breaks": "Ningún componente tiene dato en los dos lados: no se puede decir en qué se parece.",
            "missing": missing,
            "explain_source": "earth-service, a partir de components",
        }
    ordered = sorted(scored, key=lambda kv: -kv[1]["score"])
    best_key, best = ordered[0]
    why = "Lo más parecido es " + _lower_first(_component_line(best_key, best, best=True))
    if len(ordered) == 1:
        breaks = "Hay un solo componente con dato: no alcanza para decir en qué se separa."
    else:
        worst_key, worst = ordered[-1]
        breaks = "Lo menos parecido es " + _lower_first(_component_line(worst_key, worst, best=False))
    return {
        "why": why,
        "breaks": breaks,
        "missing": missing,
        "explain_source": "earth-service, a partir de components",
    }


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def add_explanations(result: Dict[str, Any]) -> Dict[str, Any]:
    """Copia el resultado de tasi.rank y agrega why/breaks/missing a cada match."""
    matches = [dict(m, **explain_match(m)) for m in result.get("matches") or []]
    return dict(result, matches=matches)
