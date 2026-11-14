"""Open-Meteo Historical Weather climatology client.

Uses a single ERA5 request for temperature and precipitation (1991-2020) to
stay within the public rate limit. ERA5-Land often returns null precipitation
and a second model doubles the request volume (HTTP 429 observed in this run).
"""
from __future__ import annotations

import time
from typing import Any, Dict

import httpx

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
USER_AGENT = "HexastraAnalogos/0.1 (NASA Space Apps 2026 prototype)"
DAILY = "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum"


def _mean(vals):
    xs = [v for v in vals if v is not None]
    if not xs:
        return None
    return sum(xs) / len(xs)


def _annual_precip(dates, pr):
    by_year = {}
    for d, p in zip(dates, pr):
        if not d:
            continue
        year = d[:4]
        if p is None:
            by_year.setdefault(year, []).append(None)
        else:
            by_year.setdefault(year, []).append(p)
    annuals = []
    for year, vals in by_year.items():
        if any(v is None for v in vals):
            continue
        annuals.append(sum(vals))
    if not annuals:
        return None, 0
    return sum(annuals) / len(annuals), len(annuals)


def fetch_daily(lat: float, lon: float, start: str, end: str, model: str, timeout: float = 90.0, retries: int = 6) -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": DAILY,
        "timezone": "UTC",
        "models": model,
    }
    last_exc = None
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        for attempt in range(retries):
            try:
                r = client.get(ARCHIVE, params=params)
                if r.status_code == 429:
                    wait = 20 + attempt * 15
                    time.sleep(wait)
                    last_exc = httpx.HTTPStatusError("429", request=r.request, response=r)
                    continue
                r.raise_for_status()
                return r.json()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                time.sleep(10 + attempt * 5)
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response is not None and exc.response.status_code in (429, 500, 502, 503, 504):
                    time.sleep(20 + attempt * 15)
                    continue
                raise
    raise last_exc  # type: ignore[misc]


def climatology(lat: float, lon: float, start: str = "1991-01-01", end: str = "2020-12-31") -> Dict[str, Any]:
    """One ERA5 request covers temperature and precipitation at 0.25°."""
    payload = fetch_daily(lat, lon, start, end, "era5")
    daily = payload.get("daily") or {}
    tmean = daily.get("temperature_2m_mean") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    dates = daily.get("time") or []
    pr = daily.get("precipitation_sum") or []
    precip, n_years = _annual_precip(dates, pr)
    ranges = []
    for a, b in zip(tmax, tmin):
        if a is not None and b is not None:
            ranges.append(a - b)
    t2m = _mean(tmean)
    return {
        "t2m_mean_C": None if t2m is None else round(t2m, 2),
        "mean_diurnal_range_C": None if not ranges else round(sum(ranges) / len(ranges), 2),
        "t2m_abs_max_C": None if not [x for x in tmax if x is not None] else max(x for x in tmax if x is not None),
        "t2m_abs_min_C": None if not [x for x in tmin if x is not None] else min(x for x in tmin if x is not None),
        "mean_annual_precipitation_mm": None if precip is None else round(precip, 1),
        "precip_complete_years": n_years,
        "period": "%s to %s" % (start, end),
        "temp_model": "era5",
        "precip_model": "era5",
        "temp_cell": {"lat": payload.get("latitude"), "lon": payload.get("longitude")},
        "precip_cell": {"lat": payload.get("latitude"), "lon": payload.get("longitude")},
        "source_temperature": (
            "Open-Meteo Historical Weather API (era5, 0.25°), daily %s to %s. "
            "A single ERA5 request is used for temperature and precipitation to respect the public rate limit "
            "(ERA5-Land often returns null precipitation). https://archive-api.open-meteo.com/v1/archive"
            % (start, end)
        ),
        "source_precipitation": (
            "Open-Meteo Historical Weather API (era5, 0.25°), daily %s to %s, "
            "%s complete calendar years used for the annual mean."
            % (start, end, n_years)
        ),
        "error": None,
    }
