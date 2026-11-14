"""Normalización por rasgo sobre el conjunto Tierra+Luna+Marte."""
from __future__ import annotations

import math
from statistics import mean, pstdev

from catalog import all_sites, feature_schema, numeric_value


def collect_values(feature_id: str) -> list[float]:
    vals = []
    for site in all_sites():
        v = numeric_value(site, feature_id)
        if v is not None:
            vals.append(v)
    return vals


def maybe_log(feature_id: str, values: list[float], apply_log: bool) -> list[float]:
    schema = feature_schema().get(feature_id, {})
    if apply_log and schema.get("use_log"):
        return [math.log1p(max(v, 0.0)) for v in values]
    return values


def stats_for(feature_id: str, norm: str, apply_log: bool) -> dict | None:
    raw = collect_values(feature_id)
    if len(raw) < 2:
        return None
    vals = maybe_log(feature_id, raw, apply_log)
    if norm == "minmax":
        lo, hi = min(vals), max(vals)
        return {"mode": "minmax", "min": lo, "max": hi, "n": len(vals), "log": bool(apply_log and feature_schema().get(feature_id, {}).get("use_log"))}
    # zscore
    mu = mean(vals)
    sd = pstdev(vals)
    return {"mode": "zscore", "mean": mu, "sd": sd, "n": len(vals), "log": bool(apply_log and feature_schema().get(feature_id, {}).get("use_log"))}


def transform(value: float, feature_id: str, spec: dict) -> float | None:
    if value is None or spec is None:
        return None
    x = value
    if spec.get("log"):
        x = math.log1p(max(x, 0.0))
    if spec["mode"] == "minmax":
        lo, hi = spec["min"], spec["max"]
        if hi == lo:
            return 0.0
        return (x - lo) / (hi - lo)
    sd = spec["sd"]
    if sd == 0:
        return 0.0
    return (x - spec["mean"]) / sd
