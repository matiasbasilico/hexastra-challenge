# Auditoría del front: qué está escrito a mano y qué tiene que venir de la API

Revisión del 14 de noviembre de 2026 sobre `main` (`index.html`, `js/*.js`, `data/*`). La regla es que **todo contenido de datos sale de la API** (planetary-service y earth-service, que leen de PostGIS). El front solo puede tener textos de interfaz, nunca cifras, sitios ni fórmulas propias.

## Hallazgos

| # | Dónde | Qué hay hoy | Problema | Reemplazo |
|---|---|---|---|---|
| 1 | `js/app.js` (modo avanzado, la vista comparativa) | Carga `data/sites.json`: 5 sitios argentinos y 5 de Marte del primer prototipo | No usa la API: no ve los 60 sitios ni los 14 destinos, ni la Luna con datos, ni TASI | Lista: `GET {earth}/candidates`. Destinos: `GET {planetary}/sites?body=`. Ranking: `POST {earth}/tasi` |
| 2 | `js/app.js` + modal «Cómo se calcula» de `index.html` | "Índice ambiental" propio: temperatura contra −59 °C, amplitud contra 58 °C (Viking 1), aridez /500 mm, altitud /4000 m, pesos 0,20/0,20/0,35/0,25 | Es otra fórmula, no TASI; constantes escritas a mano | Borrar. Puntaje y desglose: `POST /tasi`. Explicación: `GET {earth}/method` |
| 3 | `js/app.js` (`qualitative_scores`) y `data/sites.json` | Puntajes de geología, relieve, sales y vulcanismo puestos por el equipo | Juicio, no medición; contradice "nada inventado" | Borrar. G llega por la API cuando haya datos (PR #6, piloto) |
| 4 | `js/app.js` (`paired_mars_ids`) | Par Tierra–Marte fijo en una tabla | Los pares vienen de la literatura (con fuentes), pero vivían en el front | `GET {earth}/examples`: los 5 pares del prototipo con texto y fuentes, como ejemplos de arranque; el puntaje siempre de `POST /tasi` |
| 5 | Ficha del modo avanzado | "Por qué se parece / En qué no" y descripciones de `data/sites.json` | Texto narrativo del prototipo, sin trazabilidad | `why`/`breaks` de `/tasi` (en curso en el PR #3) + `summary` y `coord_source` del sitio |
| 6 | `js/app.js` | Destino por defecto `shackleton-rim` | Menor: depende de un id | Primer destino que devuelva `/sites` o ninguno |
| 7 | `js/easy.js` | Presets de misión con pesos (Equilibrado, Terreno, Clima, Robots) y `gamma: 0.75` | Parámetros del cálculo en el front | `GET {earth}/method` → `presets`, `default_gamma` |
| 8 | `js/api-stub.js` | Respaldo sin servicios: 12 "destacados" con coordenadas y textos copiados, lee `data/catalog.json` y `data/sites.json` viejos | Duplica datos de la API y puede mostrar cifras viejas como si fueran actuales | Sin servicios: aviso claro de "servicio no disponible". Opcional: catálogo de solo lectura desde el snapshot `catalog.merged.json` exportado de la base, sin ranking |
| 9 | Tabla de límites de la Tierra (PR #3) | Gravedad, presión, radiación del documento impreso (por ejemplo Marte 3,71 m/s²) | Valores sin verificar (NASA da 3,73) | `GET {planetary}/bodies`: valores NSSDC con fuente y radiación RAD; lo no verificado queda null |
| 10 | `data/climate-era5-1991-2020.json`, `data/earth-sites.geojson`, `data/mars-sites.geojson` | Archivos estáticos | Nadie los usa | Borrar |
| 11 | `data/catalog.json`, `data/sites.json` | Catálogos del primer prototipo | Desactualizados frente a la base | Borrar cuando 1, 3, 4, 5 y 8 estén resueltos |

## Lo que sí puede quedar en el front

- Textos de interfaz: títulos, botones, ayudas y la explicación del desafío.
- Estilo y marca (`docs/marca.md`).
- Configuración de conexión (`js/config.js`).

## Endpoints nuevos para esto

- `GET {earth}/method`: pasos de TASI, presets, pesos por defecto, γ, umbral de NDVI, escalas y covarianza actuales, y origen del catálogo. Sale del código y la base en ejecución, así que la explicación no puede desfasarse.
- `GET {earth}/examples`: análogos documentados en la literatura (los ejemplos del prototipo: Piedra Pómez–Medusae Fossae, Laguna Negra–Jezero, Payún Matrú–Pavonis Mons, Ischigualasto–Gale, Laguna de Antofagasta–Jezero), con texto y fuentes y sin puntaje.
- `GET {planetary}/bodies`: gravedad, presión, duración del día, temperatura y dosis de radiación de la Tierra, la Luna y Marte, con fuente (NASA NSSDC, RAD/MSL); la dosis lunar y la terrestre quedan null hasta tener fuente primaria.
