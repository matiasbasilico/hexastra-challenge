"""OSM Overpass client: detect continental liquid water near a point."""
from __future__ import annotations

from typing import Any, Dict, List

import httpx

ENDPOINTS: List[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "HexastraAnalogos/0.1 (NASA Space Apps 2026 prototype)"


def has_liquid_water(lat: float, lon: float, radius_m: int = 250, timeout: float = 25.0) -> Dict[str, Any]:
    query = """
    [out:json][timeout:20];
    (
      way["natural"="water"](around:{r},{lat},{lon});
      relation["natural"="water"](around:{r},{lat},{lon});
      way["landuse"="reservoir"](around:{r},{lat},{lon});
      way["waterway"="river"](around:{r},{lat},{lon});
      way["waterway"="canal"](around:{r},{lat},{lon});
    );
    out ids;
    """.format(r=radius_m, lat=lat, lon=lon)
    errors = []
    for url in ENDPOINTS:
        try:
            with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
                r = client.post(url, data={"data": query})
                r.raise_for_status()
                payload = r.json()
        except Exception as exc:
            errors.append("%s: %s" % (url, exc))
            continue
        elements = payload.get("elements") or []
        return {
            "value": bool(elements),
            "quality": "measured",
            "is_real": True,
            "source": (
                "OpenStreetMap Overpass API (%s), features with natural=water, landuse=reservoir "
                "or waterway=river/canal within %s m of the point. %s element(s)."
                % (url, radius_m, len(elements))
            ),
            "elements": len(elements),
        }
    return {
        "value": None,
        "quality": "unavailable",
        "is_real": False,
        "source": "OSM Overpass API request failed on all endpoints: %s" % " | ".join(errors),
        "elements": 0,
    }
