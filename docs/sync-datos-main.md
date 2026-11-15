# Sincronización de datasets desde main

Origen revisado: `bc924246273bc99ffe7b4225c2ebb88ec33664f5`. Se incorporaron únicamente ocho archivos nuevos de datos y sus siete archivos de soporte (productores, requisitos, pruebas y definición del índice propuesto de hielo). No se hizo un merge de la rama.

- `vo-hielo.jsonl`: 169 registros, 55 con valor; se preservan los nulos y sus causas de cobertura/calidad.
- `vo-mascara.jsonl`: 120 registros, 100 con valor, con fuentes MODIS/AppEEARS.
- Subconjuntos crudos: MODIS (NDVI/agua), ESA Permafrost_cci, LRO Diviner y Mars Odyssey GRS.
- Se conservó el `bodies.json` actual: mantiene las dosis terrestres y lunares documentadas y el día lunar con mayor precisión. La versión de main reemplaza esas dosis por pendientes.

Verificación de preservación: SHA-256 de los 44 archivos de `index.html`, `classic.html`, `css/`, `js/` y `assets/` idénticos antes y después de incorporar los datasets. Huella agregada del manifiesto: `0a782d2003de08744439b210da130d88945236b2b701042088a8a51213008b5c`.

Las pruebas de los nuevos productores y la validación de todos los registros pasan junto a los tests del proyecto. Esta sincronización no carga ni exporta la base compartida. La demo sigue consultando los datos ya integrados en PostgreSQL en modo de solo lectura.
