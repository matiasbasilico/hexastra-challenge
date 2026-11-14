"""Measurement files (data/measurements/*.jsonl): format, validation and merge.

Pure functions, no database. Used by db/load.py and by the tests.

One JSON object per line:

    {"site_id": "pali-aike", "feature": "ndvi", "value": 0.08, "unit": "unitless",
     "quality": "measured", "is_real": true,
     "source": "MODIS MOD13Q1 v061 via NASA AppEEARS, 2015-2024 mean, consultado 2026-11-14. https://...",
     "note": null, "method": "services/earth/scripts/ingest_ndvi.py", "retrieved_at": "2026-11-14"}

Rules (CLAUDE.md §3):
* value null  -> quality placeholder/unavailable and a note containing "a completar".
* value set   -> source with a URL (except quality "convention").
* A row may only change a feature that already has a value in the base catalog if it
  sets "replaces_base": true and explains why in "replaces_reason".
* Two files may never write the same (site_id, feature): the orchestrator decides.

New feature ids are declared once in data/measurements/<file>.features.json.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

QUALITIES_WITH_VALUE = {"measured", "derived", "modeled", "convention", "derived_from_published_range"}
QUALITIES_NULL = {"placeholder", "unavailable"}
REQUIRED = ("site_id", "feature", "value", "unit", "quality", "is_real", "source", "method", "retrieved_at")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class MeasurementError(ValueError):
    pass


@dataclass(frozen=True)
class Row:
    site_id: str
    feature: str
    value: Optional[float]
    unit: Optional[str]
    quality: str
    is_real: bool
    source: Optional[str]
    note: Optional[str]
    method: Optional[str]
    retrieved_at: Optional[str]
    dataset: str
    comparable: Optional[bool] = None
    replaces_base: bool = False
    replaces_reason: Optional[str] = None


def validate(obj: Dict[str, Any], where: str) -> Row:
    missing = [k for k in REQUIRED if k not in obj]
    if missing:
        raise MeasurementError("%s: faltan campos %s" % (where, missing))
    value = obj["value"]
    if value is not None and not isinstance(value, (int, float)):
        raise MeasurementError("%s: value debe ser número o null" % where)
    quality = obj["quality"]
    note = obj.get("note")
    if value is None:
        if quality not in QUALITIES_NULL:
            raise MeasurementError("%s: un null necesita quality placeholder/unavailable" % where)
        if not note or "a completar" not in note:
            raise MeasurementError("%s: un null necesita una nota con 'a completar'" % where)
        if obj["is_real"]:
            raise MeasurementError("%s: un null no puede ser is_real" % where)
    else:
        if quality not in QUALITIES_WITH_VALUE:
            raise MeasurementError("%s: quality '%s' no válida para un valor" % (where, quality))
        if quality != "convention" and "http" not in (obj.get("source") or ""):
            raise MeasurementError("%s: el valor necesita una fuente con URL" % where)
    if obj.get("retrieved_at") and not DATE.match(str(obj["retrieved_at"])):
        raise MeasurementError("%s: retrieved_at debe ser AAAA-MM-DD" % where)
    if obj.get("replaces_base") and not obj.get("replaces_reason"):
        raise MeasurementError("%s: replaces_base necesita replaces_reason" % where)
    return Row(
        site_id=obj["site_id"], feature=obj["feature"],
        value=None if value is None else float(value), unit=obj["unit"], quality=quality,
        is_real=bool(obj["is_real"]), source=obj.get("source"), note=note,
        method=obj.get("method"), retrieved_at=obj.get("retrieved_at"), dataset=where.split(":")[0],
        comparable=obj.get("comparable"), replaces_base=bool(obj.get("replaces_base")),
        replaces_reason=obj.get("replaces_reason"),
    )


def read_file(path: Path) -> List[Row]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MeasurementError("%s:%s: JSON inválido (%s)" % (path.name, n, exc)) from exc
        rows.append(validate(obj, "%s:%s" % (path.name, n)))
    return rows


def read_dir(directory: Path) -> Tuple[List[Row], Dict[str, Dict[str, Any]]]:
    """All rows and declared feature definitions in a measurements directory."""
    rows: List[Row] = []
    defs: Dict[str, Dict[str, Any]] = {}
    for path in sorted(directory.glob("*.jsonl")):
        rows.extend(read_file(path))
    for path in sorted(directory.glob("*.features.json")):
        for fid, payload in json.loads(path.read_text(encoding="utf-8")).items():
            if fid in defs and defs[fid] != payload:
                raise MeasurementError("feature '%s' declarada distinta en dos archivos" % fid)
            defs[fid] = payload
    return rows, defs


@dataclass
class MergeResult:
    features: Dict[Tuple[str, str], Dict[str, Any]]
    applied: List[Row] = field(default_factory=list)


def merge(base: Dict[Tuple[str, str], Dict[str, Any]], rows: Iterable[Row], site_ids: Iterable[str]) -> MergeResult:
    """Overlay measurement rows on the base features keyed by (site_id, feature)."""
    known = set(site_ids)
    out = dict(base)
    owner: Dict[Tuple[str, str], str] = {}
    applied = []
    for row in rows:
        key = (row.site_id, row.feature)
        if row.site_id not in known:
            raise MeasurementError("%s: sitio desconocido '%s'" % (row.dataset, row.site_id))
        if key in owner:
            raise MeasurementError(
                "(%s, %s) lo escriben %s y %s: lo decide el orquestador" % (row.site_id, row.feature, owner[key], row.dataset)
            )
        current = out.get(key)
        if current and current.get("value") is not None and not row.replaces_base:
            raise MeasurementError(
                "%s: (%s, %s) ya tiene valor en el catálogo base; usar replaces_base con motivo"
                % (row.dataset, row.site_id, row.feature)
            )
        owner[key] = row.dataset
        out[key] = {
            "value": row.value, "unit": row.unit, "quality": row.quality, "is_real": row.is_real,
            "source": row.source, "note": row.note, "comparable": True if row.comparable is None else row.comparable,
            "method": row.method, "retrieved_at": row.retrieved_at, "dataset": row.dataset,
        }
        applied.append(row)
    return MergeResult(features=out, applied=applied)
