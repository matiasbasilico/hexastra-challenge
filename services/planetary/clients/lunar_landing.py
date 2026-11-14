"""Client for the historical Lunar Landing Site API, with a documented fallback.

Verified 2026-11-14 (America/Buenos_Aires): https://lunarlandingsiteapi.up.railway.app/
returns HTTP 404 on / and /health. Public notes describe a retired Iris Data Labs
backend. This client still probes the URL so a revival would be picked up, and
otherwise tells the service to use the static catalog (NASA / IAU / LOLA values
already stored, never invented).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

BASES = [
    "https://lunarlandingsiteapi.up.railway.app",
]
USER_AGENT = "HexastraAnalogos/0.1 (NASA Space Apps 2026 prototype)"


def probe(timeout: float = 8.0) -> Dict[str, Any]:
    attempts = []
    for base in BASES:
        for path in ("/health", "/", "/api/v1/sites"):
            url = base.rstrip("/") + path
            try:
                with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
                    r = client.get(url)
                attempts.append({"url": url, "status": r.status_code})
                if r.status_code < 400:
                    return {"available": True, "url": url, "status": r.status_code, "attempts": attempts}
            except httpx.HTTPError as exc:
                attempts.append({"url": url, "error": str(exc)})
    return {
        "available": False,
        "fallback": "static_catalog",
        "attempts": attempts,
        "note": (
            "Lunar Landing Site API was offline (HTTP 404) when probed. "
            "Moon sites come from the static catalog (IAU gazetteer anchors and published LOLA/NASA values). "
            "No elevations or slopes were invented to replace the missing API."
        ),
    }


def fetch_site(site_id: str) -> Optional[Dict[str, Any]]:
    status = probe()
    if not status.get("available"):
        return None
    return None
