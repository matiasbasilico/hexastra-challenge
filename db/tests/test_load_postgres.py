"""Round trip against the local PostGIS (skipped when hexastra-db is not running)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "db"))

URL = os.environ.get("HEXASTRA_DATABASE_URL", "postgresql://hexastra:hexastra-local@127.0.0.1:55432/hexastra")


def _db_up() -> bool:
    try:
        import psycopg

        with psycopg.connect(URL, connect_timeout=2):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="hexastra-db no está corriendo")


@pytest.mark.parametrize("service", ["planetary", "earth"])
def test_db_catalog_matches_merged_json(service, monkeypatch):
    import load
    from build import build

    monkeypatch.setenv("HEXASTRA_DATABASE_URL", URL)
    assert load.main() == 0
    sys.path.insert(0, str(ROOT / "services" / service))
    import importlib

    dbsource = importlib.import_module("dbsource")
    dbsource.clear_cache()
    from_db = dbsource.load(service, ROOT / "services" / service / "data", url=URL)
    dbsource.clear_cache()
    merged, _ = build()
    expected = merged[service]
    assert [s["id"] for s in from_db["sites"]] == [s["id"] for s in expected["sites"]]
    for got, want in zip(from_db["sites"], expected["sites"]):
        assert (got["lat"], got["lon"]) == (want["lat"], want["lon"])
        for fid, item in want["features"].items():
            assert got["features"][fid]["value"] == item.get("value"), (got["id"], fid)
            assert got["features"][fid]["quality"] == (item.get("quality") or got["features"][fid]["quality"])
    if service == "earth":
        assert from_db["covariance"]["labels"] == expected["covariance"]["labels"]
    sys.path.remove(str(ROOT / "services" / service))
