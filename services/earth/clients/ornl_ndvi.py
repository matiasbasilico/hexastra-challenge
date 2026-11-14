"""ORNL DAAC MODIS/VIIRS REST client for NDVI (MOD13Q1).

The public subset API does not need Earthdata login. If it times out or
errors, the caller must leave NDVI null (no invented values).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

BASE = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
USER_AGENT = "HexastraAnalogos/0.1 (NASA Space Apps 2026 prototype)"


def dates(lat: float, lon: float, timeout: float = 40.0) -> List[Dict[str, Any]]:
    url = "%s/dates" % BASE
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        r = client.get(url, params={"latitude": lat, "longitude": lon})
        r.raise_for_status()
        payload = r.json()
    return payload.get("dates") or payload if isinstance(payload, list) else payload.get("dates") or []


def subset_ndvi(lat: float, lon: float, start: str, end: str, timeout: float = 60.0) -> Dict[str, Any]:
    url = "%s/subset" % BASE
    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": start,
        "endDate": end,
        "kmAboveBelow": 0,
        "kmLeftRight": 0,
    }
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        return r.json()


def mean_ndvi(lat: float, lon: float) -> Dict[str, Any]:
    """Mean NDVI (scale 0.0001 → unitless -1..1) over the most recent available year, if the API answers."""
    try:
        ds = dates(lat, lon)
    except Exception as exc:
        return {"value": None, "quality": "unavailable", "is_real": False, "source": "ORNL MOD13Q1 dates failed: %s" % exc}
    if not ds:
        return {"value": None, "quality": "unavailable", "is_real": False, "source": "ORNL MOD13Q1 returned no dates for this point."}
    # dates look like {"modis_date": "A2020001", "calendar_date": "2020-01-01"} or strings
    cal = []
    for item in ds:
        if isinstance(item, dict):
            cal.append(item.get("calendar_date") or item.get("modis_date"))
        else:
            cal.append(str(item))
    cal = [c for c in cal if c]
    if not cal:
        return {"value": None, "quality": "unavailable", "is_real": False, "source": "ORNL MOD13Q1 date list had no calendar dates."}
    end = cal[-1]
    # Use the last ~12 composite periods if we have them.
    start = cal[-23] if len(cal) >= 23 else cal[0]
    # The subset API often wants MODIS date strings (A YYYYDDD). Prefer those.
    modis_dates = []
    for item in ds:
        if isinstance(item, dict) and item.get("modis_date"):
            modis_dates.append(item["modis_date"])
    if modis_dates:
        start_m = modis_dates[-23] if len(modis_dates) >= 23 else modis_dates[0]
        end_m = modis_dates[-1]
        start, end = start_m, end_m
    try:
        payload = subset_ndvi(lat, lon, start, end)
    except Exception as exc:
        return {"value": None, "quality": "unavailable", "is_real": False, "source": "ORNL MOD13Q1 subset failed: %s" % exc}
    # Unpack subset bands named 250m_16_days_NDVI
    values: List[float] = []
    subsets = payload.get("subset") or []
    scale = 0.0001
    for band in subsets:
        name = (band.get("band") or band.get("id") or "")
        if "NDVI" not in str(name).upper() or "EVI" in str(name).upper() or "QA" in str(name).upper():
            continue
        raw = band.get("data") or band.get("values") or []
        for v in raw:
            if v is None:
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            # MOD13Q1 fill is typically -3000 / -2000 range; valid -2000..10000
            if fv < -2000 or fv > 10000:
                continue
            values.append(fv * scale if abs(fv) > 1 else fv)
    if not values:
        return {
            "value": None,
            "quality": "unavailable",
            "is_real": False,
            "source": "ORNL MOD13Q1 subset had no usable NDVI samples. Keys=%s" % list(payload.keys()),
        }
    mean = sum(values) / len(values)
    return {
        "value": round(mean, 4),
        "quality": "measured",
        "is_real": True,
        "n": len(values),
        "period": "%s to %s" % (start, end),
        "source": (
            "ORNL DAAC MODIS/VIIRS Subsetting Tools, product MOD13Q1, mean of valid NDVI samples "
            "(%s values, scale 0.0001) for %s–%s at the point. "
            "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
            % (len(values), start, end)
        ),
    }
