"""NASA Trek WMTS client.

Capabilities documents for Moon (LOLA shade / roughness) and Mars (MOLA blend)
returned HTTP 200 on 2026-11-14. Trek serves image tiles, not a public numeric
GetFeatureInfo / point-sample API. This client can confirm that Capabilities
are reachable; it does not decode PNG colors into metres.
"""
from __future__ import annotations

from typing import Any, Dict, List

import httpx

USER_AGENT = "HexastraAnalogos/0.1 (NASA Space Apps 2026 prototype)"
LAYERS = {
    "moon_lola_shade": "https://trek.nasa.gov/tiles/Moon/EQ/LRO_LOLA_Shade_Global_128ppd_v04/1.0.0/WMTSCapabilities.xml",
    "moon_lola_roughness": "https://trek.nasa.gov/tiles/Moon/EQ/LRO_LOLA_ClrRoughness_Global_16ppd/1.0.0/WMTSCapabilities.xml",
    "mars_mola_blend": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/WMTSCapabilities.xml",
}


def capabilities_status(timeout: float = 12.0) -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for name, url in LAYERS.items():
            try:
                r = client.get(url)
                out.append({"layer": name, "url": url, "status": r.status_code, "bytes": len(r.content), "ok": r.status_code == 200})
            except httpx.HTTPError as exc:
                out.append({"layer": name, "url": url, "ok": False, "error": str(exc)})
    return {
        "layers": out,
        "numeric_point_sample": False,
        "note": (
            "WMTS Capabilities were queried. Tiles are visualization rasters. "
            "This service does not sample numeric elevation/roughness from tile colors. "
            "JMARS was not found to offer a public unauthenticated point-query HTTP API for this prototype."
        ),
    }
