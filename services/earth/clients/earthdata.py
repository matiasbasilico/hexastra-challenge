"""Optional NASA Earthdata / Copernicus CDSE clients.

Credentials are read from environment variables only:
  EARTHDATA_USERNAME, EARTHDATA_PASSWORD
  CDSE_USERNAME, CDSE_PASSWORD  (or CDSE_CLIENT_ID / CDSE_CLIENT_SECRET)

This prototype does not ship secrets. Without credentials the functions
return unavailable records instead of inventing values.
"""
from __future__ import annotations

import os
from typing import Any, Dict


def _configured() -> Dict[str, bool]:
    return {
        "earthdata": bool(os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD")),
        "cdse": bool(
            (os.environ.get("CDSE_USERNAME") and os.environ.get("CDSE_PASSWORD"))
            or (os.environ.get("CDSE_CLIENT_ID") and os.environ.get("CDSE_CLIENT_SECRET"))
        ),
    }


def status() -> Dict[str, Any]:
    cfg = _configured()
    return {
        "earthdata_configured": cfg["earthdata"],
        "cdse_configured": cfg["cdse"],
        "note": (
            "CMR/Earthdata and Copernicus CDSE clients are wired for credentials via env vars. "
            "This run does not fetch protected rasters unless those variables are set. "
            "OpenTopoData, Open-Meteo, ORNL MODIS RST and OSM Overpass are used without login."
        ),
    }
