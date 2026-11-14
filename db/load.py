#!/usr/bin/env python3
"""Rebuild the HexAstra Postgres/PostGIS database from versioned files.

    services/.venv/bin/python db/load.py            # uses HEXASTRA_DATABASE_URL or the local default

Drops and recreates every table (db/schema.sql), so it is idempotent: the
database is a materialized view of the base catalogs + data/measurements.
Fails without writing if any measurement file breaks the rules.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from build import build  # noqa: E402

DEFAULT_URL = "postgresql://hexastra:hexastra-local@127.0.0.1:55432/hexastra"
BASE_KEYS = {"id", "body", "name", "short_name", "lat", "lon", "features"}


def database_url() -> str:
    return os.environ.get("HEXASTRA_DATABASE_URL", DEFAULT_URL)


def main() -> int:
    import psycopg
    from psycopg.types.json import Jsonb

    merged, report = build()  # validate everything before touching the DB
    schema = (HERE / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
            for svc, cat in merged.items():
                extra = {"covariance": cat["covariance"]} if cat.get("covariance") else {}
                cur.execute(
                    "INSERT INTO catalog_meta (service, meta, extra) VALUES (%s, %s, %s)",
                    (svc, Jsonb(cat.get("meta") or {}), Jsonb(extra)),
                )
                defs = cat.get("features") if svc == "planetary" else cat.get("feature_defs")
                for fid, payload in (defs or {}).items():
                    cur.execute(
                        "INSERT INTO feature_defs (service, id, payload) VALUES (%s, %s, %s)",
                        (svc, fid, Jsonb(payload)),
                    )
                for pos, site in enumerate(cat["sites"]):
                    body = site.get("body") or "earth"
                    attrs = {k: v for k, v in site.items() if k not in BASE_KEYS}
                    cur.execute(
                        "INSERT INTO sites (id, body, name, short_name, lat, lon, geom, attrs, position) "
                        "VALUES (%s, %s, %s, %s, %s, %s, "
                        "CASE WHEN %s = 'earth' THEN ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography END, %s, %s)",
                        (site["id"], body, site["name"], site.get("short_name"), site["lat"], site["lon"],
                         body, site["lon"], site["lat"], Jsonb(attrs), pos),
                    )
                    for fid, m in (site.get("features") or {}).items():
                        cur.execute(
                            "INSERT INTO measurements (site_id, feature, value, unit, quality, is_real, source, note, "
                            "comparable, method, retrieved_at, dataset) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (site["id"], fid, m.get("value"), m.get("unit"),
                             m.get("quality") or ("measured" if m.get("value") is not None else "unavailable"),
                             bool(m.get("is_real")), m.get("source"), m.get("note"), m.get("comparable"),
                             m.get("method"), m.get("retrieved_at"), m.get("dataset") or "base:%s" % svc),
                        )
        conn.commit()
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
