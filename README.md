# Análogos argentinos — Hexastra

Prototipo de mapa interactivo y **servicios TASI** para el [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/).

Equipo **Hexastra**, sede Buenos Aires. Interfaz en español rioplatense.

Integrantes:
- Matias Basilico
- Juan Martín Verna
- Marcela Gutiérrez

La idea: caracterizar terrenos **argentinos** (y un catálogo terrestre **mundial** de terrenos análogos) con datos citados, y compararlos con sitios de **Marte** y de la **Luna**. El desafío pide justificar la analogía, decir dónde se corta, y no quedarse en los análogos ya famosos (Atacama, Islandia, Hawái, Antártida). La ficha narrativa del primer prototipo sigue centrada en la Argentina; el buscador TASI busca en todo el mundo y se puede filtrar por continente y país.

El **buscador de análogos** pide un vector del objetivo a `planetary-service` y un ranking TASI a `earth-service`. TASI es una **propuesta del equipo**, no un índice publicado bajo esa sigla (se buscó bibliografía el 14 de noviembre de 2026). Si un componente no tiene dato real, queda nulo y se renormalizan los pesos. **No se fabrican números.**

## Cómo levantarlo

### Opción recomendada (los dos servicios + el front)

Python 3.9+ (el código evita sintaxis más nueva). En la raíz del prototipo:

```bash
cd hexastra-analogos
chmod +x run_all.sh
./run_all.sh
```

Eso instala un venv en `services/.venv` si hace falta y levanta:

| Qué | URL |
| --- | --- |
| Front (mapa + buscador) | http://127.0.0.1:8765/ |
| planetary-service (Luna/Marte, OpenAPI) | http://127.0.0.1:8766/docs |
| earth-service (candidatos mundiales + TASI, OpenAPI) | http://127.0.0.1:8767/docs |

El front llama a esos puertos desde el navegador (CORS abierto). Para apuntar a otros hosts:

```js
localStorage.setItem("HEXASTRA_PLANETARY_URL", "http://127.0.0.1:8766");
localStorage.setItem("HEXASTRA_EARTH_URL", "http://127.0.0.1:8767");
```

Los defaults también están en `js/config.js`. La capa de llamadas, pensada para el front avanzado y para el *easy mode* en paralelo, está documentada en `js/api.js`.

### Docker

```bash
docker compose up --build
```

### Solo el mapa estático (sin buscador)

```bash
cd hexastra-analogos
python3 -m http.server 8765
```

Si los servicios no están, el buscador se deshabilita y el mapa (fichas de la Argentina) sigue andando.

### Tests

Los tests de ingesta (DEM, accesibilidad) necesitan además `services/planetary/requirements-ingest.txt` y `services/earth/requirements-ingest.txt` (rasterio, pyogrio, shapely).

```bash
cd hexastra-analogos
./services/run_tests.sh
# o por separado (no juntos en un solo pytest: ambos servicios tienen catalog.py/main.py)
services/.venv/bin/python -m pytest -q services/planetary/tests
services/.venv/bin/python -m pytest -q services/earth/tests
```

### Comprobaciones con curl

```bash
curl -s http://127.0.0.1:8766/health
curl -s http://127.0.0.1:8766/sites?body=moon
curl -s http://127.0.0.1:8766/sites/shackleton-rim/vector
curl -s http://127.0.0.1:8767/health
curl -s http://127.0.0.1:8767/regions
curl -s 'http://127.0.0.1:8767/candidates?continent=South%20America&country=AR'
# ranking: primero el vector, después POST /tasi
curl -s http://127.0.0.1:8766/sites/jezero/vector -o /tmp/jezero.json
curl -s -X POST http://127.0.0.1:8767/tasi \
  -H 'Content-Type: application/json' \
  -d "{\"target\": $(cat /tmp/jezero.json), \"gamma\": 1, \"top\": 5, \"country\": \"AR\"}"
```

## Arquitectura de los servicios

No hay imports Python compartidos. El contrato es `contracts/feature_vector.schema.json`.

**planetary-service** (`services/planetary/`, puerto 8766) es dueño del catálogo Luna/Marte y de los clientes de fuentes planetarias.

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/health` | Estado (sin llamar a la red) |
| GET | `/sources?live=true` | Sonda opcional de Lunar Landing Site API y Trek WMTS |
| GET | `/features` | Esquema de rasgos del catálogo |
| GET | `/sites?body=moon\|mars` | Lista de objetivos |
| GET | `/sites/{id}` | Ficha |
| GET | `/sites/{id}/vector` | Vector listo para TASI (G, T, E, Vo, O) |
| GET | `/docs` | OpenAPI |

**earth-service** (`services/earth/`, puerto 8767) es dueño del catálogo terrestre **mundial**, de la máscara M(x), de Sigma (Ledoit-Wolf) y del ranking TASI. No llama a planetary-service salvo que reciba `target_id` y esté definido `PLANETARY_URL`.

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/health` | Estado |
| GET | `/regions` | Continentes → países (ISO-3166 alpha-2) presentes en el catálogo |
| GET | `/featured` | Sitios base / atajos (`featured=true`), análogos conocidos como línea de base y candidatos argentinos |
| GET | `/candidates?continent=&country=` | Candidatos, filtro opcional (país = ISO alpha-2) |
| GET | `/candidates/{id}` | Ficha con mediciones y fuentes |
| POST | `/tasi` | Body: `{ target, weights, gamma, top, continent, country, apply_mask }` |
| GET | `/tasi?target_id=&...` | Igual, si `PLANETARY_URL` está configurada |
| GET | `/docs` | OpenAPI |

El front **no** llama un servicio desde el otro: `getTargetVector(id)` y después `rankAnalogs({ targetVector, ... })` (`js/api.js`).

El monolito `api/` (antes `GET /similar` en el puerto 8765) quedó deprecado.

## TASI (Terrestrial Analog Similarity Index)

Vector V = [G, T, E, Vo, O]:

1. **Máscara M(x).** Se descarta un candidato terrestre si NDVI > 0,15 o si hay agua líquida continental en el punto (OSM Overpass). Si el NDVI no se pudo bajar, **no se descarta**; se marca `ndvi_unavailable`.
2. **S_T.** Distancia de Mahalanobis sobre **relieve relativo, pendiente y rugosidad** (no la cota absoluta). `S_T = exp(−gamma · D_M)`, con Sigma estimada por Ledoit-Wolf (2004) a partir de celdas ASTER alrededor de los candidatos.
3. **S_G.** Coseno espectral (CRISM vs ASTER/MODIS, etc.) **solo si hay espectros reales**. En este prototipo no hay; S_G queda nulo.
4. **S_E / S_V.** Promedio de `exp(−|x−y|/escala)` en las métricas compartidas (temperatura, amplitud, iluminación; precipitación / indicador de hielo). Las escalas son desvíos del catálogo terrestre. La precipitación 0 mm en Luna/Marte es una convención documentada.
5. **S_O.** Solo con una métrica operacional comparable entre el cuerpo objetivo y la Tierra. Si no existe, queda nulo (la accesibilidad de un sitio terrestre **no** se hace pasar por similitud con la Luna o Marte).
6. **Suma.** `TASI = Σ w_k S_k` sobre componentes disponibles; los pesos se renormalizan. El puntaje se informa en 0–100. Se devuelve cobertura y desglose.

### Fuentes verificadas (14 de noviembre de 2026, America/Buenos_Aires)

- **Lunar Landing Site API** (`https://lunarlandingsiteapi.up.railway.app/`): HTTP 404. Backend retirado. El catálogo lunar usa anclas IAU y valores LOLA/NASA ya publicados, sin inventar cotas.
- **NASA Trek WMTS**: los Capabilities de LOLA shade/roughness y MOLA blend respondieron HTTP 200. Son teselas de imagen; **no** se muestrea un número de elevación desde un PNG. JMARS no ofreció un API HTTP público de consulta puntual en esta corrida.
- **ORNL DAAC MOD13Q1** (NDVI): el endpoint público existía, pero en esta corrida el `dates` hizo timeout (0 bytes). El cliente está en `services/earth/clients/ornl_ndvi.py`; el catálogo deja NDVI en `null` + `unavailable` (la máscara no descarta por vegetación hasta que haya dato).
- **OpenTopoData ASTER GDEM v3** (`aster30m`): cubre también polos (SRTM no). Grilla 7×7 a 120 m.
- **Open-Meteo**: un solo pedido ERA5 (0,25°) por sitio para temperatura y precipitación 1991–2020. Se evitó ERA5-Land en el catálogo TASI porque en esta corrida devolvía nulos de lluvia y un segundo modelo disparaba HTTP 429. Las fichas estáticas de la Argentina en `data/sites.json` siguen documentando ERA5-Land (T) + ERA5 (lluvia) del primer prototipo.
- **Natural Earth 50m admin-0**: continente e ISO-3166 alpha-2 por point-in-polygon. Si `ISO_A2` es `-99` (p. ej. el polígono de Noruega/Svalbard), se usa `ISO_A2_EH`. Rusia queda en el continente Europa porque así lo publica Natural Earth, incluidos Tolbachik y Popigai.
- **NASA Earthdata / Copernicus CDSE**: clientes preparados para `EARTHDATA_USERNAME`/`PASSWORD` y `CDSE_*`. Sin credenciales no se inventa un ráster.

## Sitios del catálogo

**Tierra (fichas narrativas del mapa estático):** Campo de Piedra Pómez, Laguna Negra, Payún Matrú, Ischigualasto, Laguna de Antofagasta (menos estudiada).

**Tierra (catálogo TASI, mundial):** 60 candidatos con coordenadas citadas en desiertos, salares, campos volcánicos, cráteres de impacto, terrenos polares/periglaciales y tubos de lava, en todos los continentes (incluye sitios conocidos como Yungay/Atacama, Dry Valleys, Haughton, y otros menos usados como Laguna de Antofagasta, Da Qaidam, Tswaing, Bockfjorden, Undara, Pinacate). Identidades en `services/earth/data/sites_seed.json`; mediciones y país/ISO en `services/earth/data/catalog.json`.

**Sitios featured** (atajos / líneas de base, `GET /featured` y `getFeatured()`): University Valley (Valles secos de McMurdo), cráter Haughton e isla Devon–FMARS (dos puntos distintos), Timanfaya (Lanzarote) y Teide (Tenerife), Kīlauea y Mauna Kea, Yungay (Atacama), Campo de Piedra Pómez, Payún Matrú, Laguna Diamante (caldera de Galán, Catamarca; no la de Mendoza) y Socompa (punto GVP en Argentina según Natural Earth). Varios son análogos ya famosos: quedan como referencia, no como «menos estudiados».

**Marte:** Jezero (Perseverance), Gale (Curiosity), Medusae Fossae, Pavonis Mons, Meridiani (Opportunity), Utopia Planitia (sitio Viking 2) y Arsia Mons.

**Luna:** Marius Hills (pozo de colapso, LROC), borde de Shackleton (valores medios LOLA de Zuber et al. 2012) y anclas IAU de regiones Artemis III (Haworth, Malapert, de Gerlache, Amundsen, Nobile). El comunicado de NASA del 19 de agosto de 2022 [nombra las 13 regiones](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/) (Faustini Rim A, Peak Near Shackleton, Connecting Ridge, etc.) pero **no publica las coordenadas de los recuadros de 15×15 km**. Por eso las anclas IAU son el centro del cráter u homónimo, no el centro oficial del recuadro. En Shackleton, lat/lon son el *centro del círculo del borde* (Tabla 1 de Zuber), y la cota es la *altura media del borde* (1,3 km).

### Sitios del documento HexAstra (agregados el 14 de noviembre de 2026)

Destinos y candidatos argentinos del documento impreso (§3 y §8) que faltaban. Las coordenadas llevan fuente en `coord_source`; las mediciones sin fuente quedan en `null` con la nota «a completar». Detalle y decisiones en `docs/unificacion.md` §8.

| Sitio | Cuerpo | lat, lon | Fuente de la coordenada |
| --- | --- | --- | --- |
| Marius Hills (pozo de colapso) | Luna | 14.0917°N, −56.7701° (303.2299°E) | [LROC Lunar Pits Atlas #1](https://lroc.im-ldi.com/atlases/pits/1); descubrimiento Haruyama et al. 2009, GRL, doi:10.1029/2009GL040635 |
| Utopia Planitia (sitio Viking 2) | Marte | 48.27°N, 134.28°E | [NASA GISS Mars24](https://www.giss.nasa.gov/tools/mars24/help/landers.html); centro IAU 46.74°N 117.52°E en [USGS 6260](https://planetarynames.wr.usgs.gov/Feature/6260) |
| Arsia Mons | Marte | 8.26°S, −120.09° (239.91°E) | [USGS Gazetteer 394](https://planetarynames.wr.usgs.gov/Feature/394), red MDIM 2.1 |
| Meseta de Somuncurá | Tierra (AR) | 41.5833°S, 67.15°O | [Wikipedia ES](https://es.wikipedia.org/wiki/Meseta_de_Somuncur%C3%A1), **último recurso** (no está en GVP; el plan de manejo no trae coordenadas) |
| Pali Aike (sector argentino) | Tierra (AR) | 51.995°S, 70.155°O | Ross et al. 2011, J. Volcanol. Geotherm. Res. 201:253–271 |
| Campo del Cielo | Tierra (AR) | 27°38′S, 61°42′O | Earth Impact Database (PASSC, copia Wayback 2023) |
| Cráteres de Río Cuarto | Tierra (AR) | 32°45′S, 64°15′O | Grant y Schultz 1993, LPSC XXIV, [NTRS 19940011723](https://ntrs.nasa.gov/citations/19940011723). Origen discutido; a confirmar en el PDF |
| Dunas de Tatón (Fiambalá) | Tierra (AR) | 27.3436°S, 67.5386°O | Isla et al. 2021, Quaternary and Environmental Geosciences 12(2) (punto de muestreo) |
| Volcán Llullaillaco | Tierra (AR) | 24.72°S, 68.53°O | [Smithsonian GVP 355110](https://volcano.si.edu/volcano.cfm?vn=355110) (cumbre 6.739 m) |
| Base Marambio | Tierra (sin país en NE 50m) | 64.2418°S, 56.6232°O | [COMNAP Antarctic Facilities](https://github.com/PolarGeospatialCenter/comnap-antarctic-facilities) |
| Base Esperanza | Tierra (sin país en NE 50m) | 63.3970°S, 56.9981°O | COMNAP Antarctic Facilities |

- Jezero y Gale **mantienen** el punto de aterrizaje de Mars24. El documento usa el centro IAU del cráter (Jezero 18.41°N 77.69°E, USGS 14300; Gale 5.37°S 137.81°E, USGS 2071), que queda a ≈14 km y ≈51 km respectivamente; ahora se cita en `coord_source`.
- T y E de los tres destinos nuevos se midieron con productos públicos y el mismo método que la Tierra (scripts en `services/planetary/scripts/`, dependencias en `requirements-ingest.txt`):

| Destino | Relieve / pendiente / rugosidad | Temp. media / amplitud diurna | Fuente T | Fuente E |
| --- | --- | --- | --- | --- |
| Marius Hills | 47,09 m / 1,10° / 11,43 m | −54,53 °C / 295,38 K | LOLA LDEM 118 m (USGS) | Diviner GCP, Tbol de **superficie** (Williams et al. 2017) |
| Utopia Planitia | 1,39 m / 0,00° / 0,32 m | −80,27 °C / 36,77 K | HRSC-MOLA 200 m (USGS) | Mars Climate Database v6.2, aire a 2 m (modelo) |
| Arsia Mons | 46,31 m / 3,59° / 13,51 m | −72,71 °C / 65,73 K | HRSC-MOLA 200 m (USGS) | Mars Climate Database v6.2, aire a 2 m (modelo) |

  Grilla 7×7 a 120 m con valores bilineales, como en la Tierra. Validaciones: Bradbury Landing da −4.504,7 m (publicado: −4.501 m), y la MCD en Jezero da medias diarias de 207–222 K (MEDA midió 209–225 K). Iluminación e hielo siguen en `null`.
- Las bases antárticas no caen dentro de ningún polígono de Natural Earth 50m y Nominatim no devuelve ISO: quedan sin país/continente (no se adivina) y aparecen solo en la búsqueda «Mundo entero».
- La ingesta midió DEM ASTER y clima ERA5 para los 8 sitios terrestres nuevos; la covarianza Ledoit-Wolf pasó de n=1300 a n=1500, así que los puntajes T de todos los sitios se mueven levemente.

## Qué es dato real y qué es placeholder

Valores verificados el **14 de noviembre de 2026** (America/Buenos_Aires), con `quality=measured` o `convention`:

| Dato | Valor | Fuente |
| --- | --- | --- |
| Coords y clima terrestres 1991–2020, cotas SRTM | ver `data/sites.json` y `data/climate-era5-1991-2020.json` | Wikipedia/Wikidata, GVP, sitio de Ischigualasto, EPSC 2022-1152; Open-Meteo ERA5-Land (T) y ERA5 (lluvia); OpenTopoData SRTM30m |
| Pendiente y rugosidad terrestres | p. ej. Piedra Pómez 3,41° / 6,47 m; Payún 14,78° / 29,33 m | SRTM 30 m, 9 puntos a 120 m de línea de base, misma fecha |
| Jezero / Gale / Opportunity coords | 18.44°N 77.45°E; 4.59°S 137.44°E; 1.95°S 354.47°E | [NASA GISS Mars24](https://www.giss.nasa.gov/tools/mars24/help/landers.html) |
| Elevación Gale | −4501 m | [NASA Facts MSL/Curiosity](https://mars.nasa.gov/internal_resources/824/) |
| Medusae Fossae, Pavonis Mons | −2.17°, 195.80°E; 1.48°N, 247.04°E | USGS Gazetteer 3795 y 4620 |
| Shackleton centro del borde y cota media | −89.655°, 129.174°E; **1300 m**; RMS del borde ≈ 1 m (spot de 5 m) | Zuber et al. 2012, Tabla 1 LOLA, [NTRS 20120013758](https://ntrs.nasa.gov/api/citations/20120013758/downloads/20120013758.pdf) |
| Haworth, Malapert, de Gerlache, Amundsen, Nobile | centros IAU (primera red de cada ficha) | USGS Features 14502, 3603, 1439, 247, 4321 |
| Precipitación Luna/Marte | 0 mm/año | Convención documentada (no hay lluvia líquida estable), no un pluviómetro |
| Temperatura media de Marte (ficha global, no de sitio) | −59 °C | [NASA NSSDC Mars Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html) — **no** se asigna a Jezero ni a Pavonis |

**Derivados de un rango publicado** (`quality=derived_from_published_range`, `is_real=false`):

- Jezero, temperatura media **−56,15 °C**: punto medio del rango 209–225 K de medias diarias a 1,45 m en el año marciano 36 (Munguira et al. 2024, doi:10.1029/2024JE008385). No es un promedio temporal ponderado.
- Gale, amplitud diurna **60 °C**: punto medio del rango ~45–75 K de aire REMS (Martínez et al.).

**Placeholder (valor `null`)** entre otros: cotas MOLA de Jezero, Medusae, Pavonis y Meridiani; pendientes y rugosidad de Marte; temperaturas medias y amplitudes de la Luna (Williams et al. 2023 describen umbrales Diviner — PSR < 110 K, crestas en verano por lo general > ~120 K — pero no una media única de sitio que hayamos cargado); % de iluminación; indicador numérico de hielo; rugosidad LOLA no se usa por defecto en la similitud porque la escala (5 m) no es la de SRTM (120 m).

Los puntajes cualitativos de geología/relieve/sales/vulcanismo del mapa original siguen siendo juicios preliminares del primer prototipo y **no entran** al TASI.


## Compartir un link (Cloudflare Pages + túnel a esta Mac)

El front estático se publica en Cloudflare Pages (gratis, una URL por rama y una por deploy). Los servicios Python siguen corriendo en la Mac y se exponen con túneles rápidos de `cloudflared`.

```bash
npx wrangler@3 login                 # una sola vez
./scripts/deploy_pages.sh            # publica la rama actual → https://<rama>.hexastra-analogos.pages.dev
./scripts/share.sh https://<rama>.hexastra-analogos.pages.dev
# imprime: https://<rama>.hexastra-analogos.pages.dev/?planetary=https://….trycloudflare.com&earth=https://….trycloudflare.com
```

- El link funciona **solo mientras `share.sh` corre y la Mac está prendida**. Las URLs de los túneles cambian en cada corrida: compartí el link nuevo.
- `js/config.js` acepta `?planetary=` y `?earth=` solo para `https://*.trycloudflare.com` o la máquina local, y los recuerda en el navegador.
- Sin túnel, la página publicada no llega a los servicios y cae al cliente local (`js/api-stub.js`).
- El sitio en `*.pages.dev` es público para quien tenga el link.

## Capa `js/api.js` (contrato para el front)

Funciones: `getTargets(body)`, `getTargetVector(id)`, `getRegions()`, `getFeatured()`, `rankAnalogs({ targetVector, weights, gamma, top, continent, country })`. También `health()` y `getCandidates({ continent, country })`. El contrato completo está comentado al inicio de `js/api.js`. El CSS / `index.html` no se rediseñó; el buscador avanzado existente quedó cableado a esta capa para que siga andando.

## Archivos

| Ruta | Contenido |
| --- | --- |
| `index.html`, `css/`, `js/app.js` | Mapa Leaflet y buscador avanzado (sin rediseño de estilos) |
| `js/api.js`, `js/config.js` | Capa de llamadas a los dos servicios |
| `contracts/feature_vector.schema.json` | Contrato del vector G/T/E/Vo/O |
| `services/planetary/` | Microservicio Luna/Marte, puerto 8766 |
| `services/earth/` | Microservicio terrestre mundial + TASI, puerto 8767 |
| `services/earth/data/ne_50m_admin_0_countries.geojson` | Natural Earth 50m (país/continente) |
| `run_all.sh`, `docker-compose.yml` | Arranque de los tres procesos |
| `data/sites.json` | Fichas narrativas del primer prototipo (Argentina) |
| Teselas | OSM, Esri, NASA GIBS, OpenPlanetary (Marte v0.2 y Luna v0.1), WhereOnMars MOLA |

El mapa lunar en Web Mercator **comprime el polo sur**; las coordenadas están en la ficha. Las teselas de Luna v0.1 respondieron HTTP 200 en esta corrida.

## Próximos pasos

1. Reintentar NDVI (ORNL o Earthdata/AppEEARS con credenciales) y cachear valores reales para la máscara M(x).
2. Muestrear DEM LOLA y MOLA numéricos (no teselas de color) para pendiente, relieve relativo y rugosidad **en la misma línea de base** que ASTER.
3. Cargar medias de REMS (Gale) y MEDA (Jezero) y productos Diviner por región Artemis.
4. Si aparece un archivo espectral real (CRISM / ASTER), habilitar S_G; si no, dejarlo nulo.
5. Seguir sumando análogos poco estudiados, sobre todo en la Puna, y cargar resumen/demo en la ficha de Space Apps.

## Licencias y créditos

Datos de clima: Copernicus/ECMWF vía Open-Meteo. DEM: ASTER GDEM v3 vía OpenTopoData (y SRTM en las fichas estáticas originales). Límites políticos: Natural Earth (dominio público). Teselas: © OSM, Esri, NASA GIBS, OpenPlanetaryMap, WhereOnMars/Carto. LOLA: Zuber et al. 2012. Coordenadas de landers: NASA GISS. Gazetteer: USGS/IAU. Textos: equipo Hexastra, 2026. No fabricamos mediciones: si no hubo fuente, el número no se presenta como dato.
