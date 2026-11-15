# Versioned measurements (`*.jsonl`)

Each data contributor adds **their own** `<agent>.jsonl` file, such as `vo-hielo.jsonl` or `o-tierra.jsonl`, together with the reproducible script that generates it. Do not edit base catalogs (`services/*/data/catalog.json`) or another contributor's file. The coordinator performs database/snapshot integration:

```bash
docker compose up -d db                      # PostGIS: hexastra-db at 127.0.0.1:55432
services/.venv/bin/python db/load.py         # Rebuild from base catalogs and measurements
services/.venv/bin/python db/export.py       # Export services/*/data/catalog.merged.json snapshots
HEXASTRA_DATABASE_URL=postgresql://hexastra:hexastra-local@127.0.0.1:55432/hexastra ./run_all.sh
```

These integration commands rebuild/export the selected database. Do not run them against the shared demonstration database without integration authorization. A documentation change does not authorize database writes.

## Format

Use one JSON object per line. This is an illustrative schema example, not an instruction to invent a measurement:

```json
{"site_id":"pali-aike","feature":"ndvi","value":null,"unit":"unitless","quality":"unavailable","is_real":false,"source":"No verified product value available.","note":"a completar","method":"services/earth/scripts/ingest_mask.py","retrieved_at":"2026-11-14"}
```

Required fields: `site_id`, `feature`, `value`, `unit`, `quality`, `is_real`, `source`, `method`, and `retrieved_at`. Optional fields include `note`, `comparable`, `replaces_base`, and `replaces_reason`. Retain the original field names and source strings: these are data contracts and provenance, not documentation to translate.

## Validation rules

`db/measurements.py` validates these rules; `db/load.py` fails on invalid input:

- A `null` value requires `quality` of `placeholder` or `unavailable`, `is_real: false`, and a note containing the required literal `a completar` (pending verification).
- A non-null value requires `quality` in `measured`, `derived`, `modeled`, `convention`, or `derived_from_published_range`, and a source URL except for documented conventions.
- The `site_id` must exist in a base catalog.
- Replacing a base value requires `"replaces_base": true` and `"replaces_reason"`.
- Two files must not write the same `(site_id, feature)` pair. The coordinator resolves a conflict.
- Declare each new feature once in `<agent>.features.json`, using `{"id":{"service":"earth"|"planetary","unit":...,"name_es":...,"description":...}}`.
- A feature with the same definition on Earth and Moon/Mars, such as `g_*`, uses `"service": ["earth", "planetary"]` and appears in both catalogs.

Before opening a PR, run `./services/run_tests.sh`. Its `db/tests` suite validates every measurement file in this directory.
