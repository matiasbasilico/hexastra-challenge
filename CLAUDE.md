# HexAstra — reglas del repo para todos los agentes

Este archivo lo leen todos los agentes que trabajan en el repo (orquestador, subagentes y worktrees de Orca). Si una instrucción puntual choca con estas reglas, mandan estas reglas; ante una duda que no resuelven, preguntá al usuario en vez de suponer.

## 1. Objetivo principal (no perderlo de vista)

NASA Space Apps 2026 — *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*. Texto oficial completo y lista de recursos: [`docs/desafio.md`](docs/desafio.md).

> Usar datos abiertos de NASA y de otras agencias espaciales para **identificar y caracterizar análogos terrestres nuevos** de las posibles bases lunares permanentes y de los sitios de aterrizaje y exploración en Marte, y presentarlo como mapa, visualización u otra herramienta.

Toda tarea tiene que acercarnos a esto. Lo que el desafío pide explícitamente:

- **Ir más allá de lo visual:** justificar la analogía con datos, por dimensión.
- **Decir qué se parece, cuánto y qué no.** Un sitio puede ser buen análogo geológico y malo térmico.
- **Buscar análogos poco estudiados**, no redescubrir Atacama, Haughton, Islandia, Hawái o la Antártida (esos sirven como línea de base).
- **Combinar varios datasets** y **cuidar la escala** (un cráter o un valle, no un desierto entero).
- **Conectar con la exploración:** qué se puede probar ahí (instrumentos, operaciones, recursos, riesgos).
- **Reconocer los límites de la Tierra:** gravedad, vacío lunar, atmósfera marciana fina, radiación. Se muestran como brecha cuantificada, no entran al puntaje.

Dimensiones del desafío y cómo las cubre la matriz V = [G, T, E, Vo, O] (`contracts/feature_vector.schema.json`):

| Dimensión del desafío | Componente |
|---|---|
| Geología, mineralogía, materiales | **G** |
| Terreno, elevación, pendiente, rugosidad, cráteres | **T** |
| Temperatura, iluminación, extremos | **E** |
| Agua, hielo, permafrost, recursos; polvo y viento | **Vo** |
| Aterrizaje, movilidad, operaciones, construcción | **O** |
| Biología/habitabilidad, cuevas/subsuelo | todavía sin componente propio: proponer antes de inventar uno |

## 2. Decisiones tomadas (no reabrir sin el usuario)

- **Puntaje: solo TASI** (`services/earth/tasi.py`). No implementar la fórmula S del documento impreso (Gauss + promedio geométrico).
- **MVP: el mapa de puntos actual** (Leaflet). No grilla H3, no Cesium, no migrar a Next/MapLibre.
- **No tocar** el monorepo `~/Desarrollo/nasa/nasa` (ni su Postgres en el puerto 5432) ni las carpetas viejas.
- **Base de datos:** PostgreSQL + PostGIS propio del repo (contenedor `hexastra-db`, `127.0.0.1:55432`, `docker compose up -d db`). Se reconstruye entera desde archivos versionados con `db/load.py` (catálogos base + `data/measurements/*.jsonl`). Las APIs leen de ahí cuando `HEXASTRA_DATABASE_URL` está definida; si no, del snapshot `catalog.merged.json` (`db/export.py`) o del catálogo base. `/health` informa `catalog_origin`.
- **Componentes de similitud sin contraparte:** G y O sólo puntúan si hay un valor comparable en los dos lados (destino y sitio terrestre). Cargar datos de un solo lado está bien, pero cambiar fórmulas de `tasi.py` requiere propuesta y OK del usuario.
- **Publicación:** front en Cloudflare Pages (`scripts/deploy_pages.sh`); servicios en la Mac vía túnel `cloudflared` (`scripts/share.sh`). El sitio es público con link.

## 3. Reglas de datos (críticas)

1. **Nunca inventar** coordenadas, elevaciones, temperaturas, espectros ni ningún valor. Tampoco "promediar" fuentes que no coinciden.
2. **Todo valor lleva fuente** en `source`: dataset, producto/versión, URL y fecha de consulta (America/Buenos_Aires). Wikipedia solo como último recurso y marcada así.
3. **Lo que no se pudo verificar va `null`** con `quality: "placeholder"` (o `"unavailable"`) y nota "a completar". Un sitio sin coordenada verificada no entra; se lista en el reporte.
4. `quality` honesta: `measured` (medición), `derived` (calculado de una medición), `modeled` (modelo/reanálisis: ERA5, MCD), `convention` (convención documentada), `derived_from_published_range`, `placeholder`/`unavailable`.
5. **Comparabilidad:** misma definición en la Tierra y en Luna/Marte (p. ej. T = grilla 7×7 a 120 m). Si la escala o la magnitud difiere (DEM de 200 m, temperatura de superficie vs. aire), se dice en `note`.
6. TASI renormaliza pesos sobre los componentes con dato y reporta cobertura: respetarlo, no rellenar para "subir" puntajes.
7. **Validar contra un valor publicado** cada pipeline nuevo antes de cargar (ej.: Bradbury Landing −4.501 m; Jezero MEDA 209–225 K).
8. Ningún secreto en el repo ni en el chat: credenciales en `~/.netrc` (Earthdata) o `~/.config/hexastra/*.env`.

## 4. Fuentes: primero las oficiales del desafío

Usar en este orden. Una fuente externa solo si la oficial no tiene el dato, y documentando por qué.

1. **Recursos oficiales del desafío** ([`docs/desafio.md`](docs/desafio.md)):
   - NASA Earthdata Search / Worldview (Tierra: MODIS, ASTER, NASADEM, EMIT, SMAP…).
   - NASA PDS y LRO (LROC, LOLA, Diviner — incluidos sus productos polares y de recursos —, LEND, Mini-RF); PDS de Marte (MOLA, CRISM, THEMIS, GRS/neutrones…).
   - CSA: RCM, RADARSAT-1 (radar, banda C).
   - ESA: Copernicus Data Space (Sentinel), ESA Open Science Catalog (p. ej. permafrost CCI).
   - JAXA: G-Portal (precipitación GSMaP, nieve, vegetación).
2. Productos de agencias o institutos derivados de esas misiones (USGS Astrogeology, IAU/USGS Gazetteer, Mars Climate Database LMD/ESA/CNES, NASA GISS Mars24).
3. Fuentes abiertas reconocidas (Smithsonian GVP, Earth Impact Database, Natural Earth, OpenStreetMap, GHSL, COMNAP, papers con DOI).
4. Wikipedia: último recurso, marcada en `coord_source`/`source`.

Respetar las condiciones de uso de cada sitio no gubernamental.

## 5. Cómo trabajan los agentes

- **Un agente, una tarea, un worktree, un PR.** Nada de commits en `main`, merges ni force-push. Commits chicos y descriptivos en español (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- **Datos nuevos:** cada agente escribe sus mediciones en `data/measurements/<agente>.jsonl` con su script de ingesta reproducible (formato y reglas: [`data/measurements/README.md`](data/measurements/README.md)). No edita los catálogos base ni el archivo de otro agente, ni corre `db/export.py`; puede correr `db/load.py` contra la base local para probar. La integración la hace el orquestador.
- **Tests:** `./services/run_tests.sh` en verde, más tests nuevos que validen esquema, fuentes y nulos de lo que agregaste.
- **Reporte final de cada agente:** qué cargó (tabla sitio × feature × valor × fuente), qué quedó `null` y por qué, validaciones hechas, dudas para el usuario.
- **No apagar** la demo que corre en 8765/8766/8767; usar otros puertos para verificar.

## 6. Arranque rápido

- Servicios + front: `./run_all.sh` (8765 front, 8766 planetary, 8767 earth).
- Base: `docker compose up -d db && services/.venv/bin/python db/load.py`; servicios contra la base con `HEXASTRA_DATABASE_URL=postgresql://hexastra:hexastra-local@127.0.0.1:55432/hexastra ./run_all.sh`.
- Tests: `./services/run_tests.sh` (planetary, earth y `db/tests`).
- Link para compartir: `./scripts/deploy_pages.sh` y `./scripts/share.sh <url-de-pages>`.
- Plan, decisiones y fuentes por sitio: `docs/unificacion.md` (§8) y `README.md`.
