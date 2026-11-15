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


ROAD_ENDPOINTS: List[str] = ENDPOINTS[:1]  # the mirrors timed out on 2026-11-14; add them back here if they recover
ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "service", "track", "road")
ROAD_ATTEMPTS = 6
ROAD_BACKOFF_S = 5.0


class OverpassError(RuntimeError):
    pass


def roads_around(lat: float, lon: float, radius_m: int, timeout: float = 180.0) -> List[Dict[str, Any]]:
    """OSM ways tagged as drivable roads (ROAD_CLASSES and their _link variants) within radius_m.

    Each element carries `tags` and `geometry` (list of {lat, lon}). Retries with
    exponential backoff across endpoints; raises OverpassError if all attempts fail.
    """
    import time

    query = '[out:json][timeout:%d];way[highway~"^(%s)(_link)?$"](around:%d,%.7f,%.7f);out tags geom;' % (
        int(timeout), "|".join(ROAD_CLASSES), radius_m, lat, lon)
    errors: List[str] = []
    for attempt in range(ROAD_ATTEMPTS):
        url = ROAD_ENDPOINTS[attempt % len(ROAD_ENDPOINTS)]
        try:
            payload = _post_with_curl(url, query, timeout + 30.0)
        except OverpassError as exc:
            errors.append("%s: %s" % (url, str(exc)[:120]))
            time.sleep(ROAD_BACKOFF_S * 2 ** attempt)
            continue
        if payload.get("remark"):  # Overpass reports runtime errors (timeout, memory) here
            errors.append("%s: %s" % (url, payload["remark"][:120]))
            time.sleep(ROAD_BACKOFF_S * 2 ** attempt)
            continue
        return payload.get("elements") or []
    raise OverpassError(" | ".join(errors))


def _post_with_curl(url: str, query: str, max_time_s: float) -> Dict[str, Any]:
    """POST the query with the system curl.

    The venv Python links LibreSSL 2.8.3, which overpass-api.de rejects at the TLS
    handshake (SSLV3_ALERT_HANDSHAKE_FAILURE, seen 2026-11-14); curl negotiates fine.
    """
    import json
    import subprocess

    cmd = ["curl", "--silent", "--show-error", "--fail", "--max-time", str(int(max_time_s)),
           "--connect-timeout", "15", "--user-agent", USER_AGENT, "--data-urlencode", "data=" + query, url]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise OverpassError("curl: %s" % exc)
    if proc.returncode != 0:
        raise OverpassError("curl %s: %s" % (proc.returncode, proc.stderr.strip()))
    try:
        payload = json.loads(proc.stdout)
    except ValueError as exc:
        raise OverpassError("respuesta no JSON: %s" % exc)
    if not isinstance(payload, dict):
        raise OverpassError("respuesta inesperada")
    return payload
