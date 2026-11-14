# Mediciones por agente (`*.jsonl`)

Cada agente agrega **su propio** archivo `<agente>.jsonl`, por ejemplo `vo-hielo.jsonl` u `o-tierra.jsonl`, más el script reproducible que lo genera. Nadie edita los catálogos base (`services/*/data/catalog.json`) ni el archivo de otro agente. La integración (base de datos y snapshots) la hace el orquestador con:

```bash
docker compose up -d db                      # PostGIS hexastra-db en 127.0.0.1:55432
services/.venv/bin/python db/load.py         # reconstruye la base: catálogos base + estos archivos
services/.venv/bin/python db/export.py       # snapshots services/*/data/catalog.merged.json
HEXASTRA_DATABASE_URL=postgresql://hexastra:hexastra-local@127.0.0.1:55432/hexastra ./run_all.sh
```

## Formato (una línea JSON por medición)

```json
{"site_id": "pali-aike", "feature": "ndvi", "value": 0.08, "unit": "unitless",
 "quality": "measured", "is_real": true,
 "source": "MODIS MOD13Q1 v061 vía NASA AppEEARS, media 2015–2024, consultado 2026-11-14. https://appeears.earthdatacloud.nasa.gov/",
 "note": null, "method": "services/earth/scripts/ingest_ndvi.py", "retrieved_at": "2026-11-14"}
```

Campos obligatorios: `site_id`, `feature`, `value`, `unit`, `quality`, `is_real`, `source`, `method`, `retrieved_at`. Opcionales: `note`, `comparable`, `replaces_base` y `replaces_reason`.

## Reglas (las valida `db/measurements.py`; si no se cumplen, `db/load.py` falla)

- `value: null` → `quality` `placeholder` o `unavailable`, `is_real: false` y una `note` con «a completar».
- Con valor → `quality` ∈ `measured`, `derived`, `modeled`, `convention`, `derived_from_published_range`, y `source` con URL (salvo `convention`).
- `site_id` tiene que existir en algún catálogo base.
- No se pisa un valor del catálogo base sin `"replaces_base": true` y `"replaces_reason"`.
- Dos archivos no pueden escribir el mismo `(site_id, feature)`: si pasa, decide el orquestador.
- Una feature nueva se declara una sola vez en `<agente>.features.json` (`{"id": {"service": "earth"|"planetary", "unit": …, "name_es": …, "description": …}}`).
- Una feature que vale para la Tierra y para la Luna/Marte (misma definición en los dos lados, p. ej. las `g_*`) se declara con `"service": ["earth", "planetary"]` y aparece en los dos catálogos.

Antes del PR, corré `./services/run_tests.sh`: incluye `db/tests`, que valida todos los archivos de esta carpeta.
