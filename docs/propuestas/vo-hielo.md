# Propuesta Vo — máscara de viabilidad e índice de hielo `water_ice_indicator`

Agente Vo (hielo + máscara), 14 de noviembre de 2026. **No cambia `services/earth/tasi.py`.** Sólo carga datos en `data/measurements/vo-mascara.jsonl` y `data/measurements/vo-hielo.jsonl` y propone cómo leerlos.

## Parte A — máscara de viabilidad (Paso A de TASI)

`tasi.viability_mask` descarta un sitio terrestre si `ndvi > 0,15` o si `has_liquid_water = 1`. Un valor desconocido no descarta, pero levanta una bandera. Hasta ahora NDVI estaba en 0/60 y agua en 1/60.

| Feature | Producto | Estadístico / criterio |
|---|---|---|
| `ndvi` | MODIS Terra **MOD13Q1 v061** (250 m, compuestos de 16 días) vía **NASA AppEEARS** (Earthdata) | Píxel que contiene la coordenada del sitio. **Media 2015-01-01 a 2024-12-31 de los compuestos con `pixel_reliability = 0`** («good data»). Se descartan los marginales, nieve/hielo y nubes. Con menos de 23 compuestos buenos (un año) queda `null`. La nota lleva n, mediana y p90. |
| `has_liquid_water` | MODIS **MOD44W v061** (máscara tierra/agua anual, 250 m) vía AppEEARS | Capa `seven_class` del píxel del sitio, años 2015–2023. **1 si el píxel es agua continental (clase 3 «shallow inland» o 5 «deep inland») en al menos la mitad de los años**, 0 si no. El océano (0, 6, 7) nunca cuenta. El agua efímera (clase 4) y el agua en el entorno 3×3 (~375 m) van a la nota, no al valor: la regla de TASI habla de agua *en el punto*. |

¿Por qué MOD44W y no Sentinel-2? Es un producto oficial de Earthdata (recurso n.º 1 del desafío), con la misma resolución que el NDVI y una clase explícita de agua continental. CDSE (Sentinel) no hizo falta.

Casos de control: Lake Natron, Laguna de Antofagasta y Salar de Uyuni. Los resultados están en el PR.

## Parte B — hielo de agua en los tres cuerpos

### Magnitudes crudas (features propias, `comparable: false`)

| Cuerpo | Feature | Producto (fuente oficial) | Unidad | Qué mide |
|---|---|---|---|---|
| Tierra | `permafrost_fraction` | **ESA Permafrost_cci** L4 v5.0, PFR (CEDA; ESA Open Science Catalog) | fracción 0–1 | % de la celda de 0,01° con suelo ≤ 0 °C durante ≥ 2 años (modelo CryoGrid forzado con LST MODIS + ERA5). Media 2019–2023. Cubre el hemisferio norte (25–85° N) y la Antártida libre de hielo. |
| Luna | `moon_ice_stable_frac` | **LRO Diviner Polar Resource Products v2** (LRO-L-DLRE-5-PRP-V2.0, PDS Geosciences) | fracción 0–1 | Fracción de triángulos de ~240 m, a ≤ 5 km del sitio, donde el hielo es estable a la sublimación (< 1 kg m⁻² por 10⁹ años) a ≤ 2,87 m. |
| Luna | `moon_ice_surface_frac` | ídem | fracción 0–1 | Idem, con hielo estable en superficie (`ice_depth = 0`). |
| Luna | `moon_ice_depth_min_m` | ídem | m | Profundidad de estabilidad más somera del círculo. |
| Marte | `mars_grs_h2o_wt_pct` | **2001 Mars Odyssey GRS** (ODY-M-GRS-5-ELEMENTS-V1.0, PDS Geosciences; Boynton et al. 2007) | % en peso | Hidrógeno equivalente a agua en el primer metro, bin suavizado de 5°×5°. |

Neutrones lunares (LEND / Lunar Prospector NS): el PDS de Geociencias no publica un mapa derivado de hidrógeno de LP (sólo los RDR de cuentas, y el producto derivado de LP GRS trae óxidos, no H). Quedan como trabajo futuro; por eso Marius Hills (14° N, fuera del PRP polar) queda `null`.

### Índice propuesto `I_hielo` (0–1)

**Definición común:** *fracción del área del sitio donde el hielo de agua es térmicamente estable en el primer ~1–3 m del suelo.* Es una pregunta de estabilidad («si hubiera hielo, ¿persistiría?»), no de presencia. Se eligió porque es la única que los tres cuerpos pueden contestar con productos oficiales y con la misma semántica.

| Cuerpo | Mapeo | Calidad | `comparable` | Justificación |
|---|---|---|---|---|
| Tierra | `I = permafrost_fraction` | `derived` | `true` | El permafrost es, por definición, el suelo donde el hielo persiste (≤ 0 °C ≥ 2 años). Es una fracción de área a escala de 1 km. |
| Luna | `I = moon_ice_stable_frac` | `derived` | `true` | Diviner calcula directamente dónde el hielo es estable a ≤ 2,87 m; se toma la fracción de área en un círculo de 5 km (escala de un borde o del piso de un cráter). |
| Marte | **no se carga (`null`)** | `unavailable` | — | El GRS mide **hidrógeno**, no estabilidad. A latitudes bajas (todos los sitios salvo Utopia) el 2–7 % en peso se explica por minerales hidratados y agua adsorbida (Boynton et al. 2007). Convertirlo en una «fracción con hielo» sería inventar. Falta un mapa de estabilidad o de consistencia de hielo (p. ej. **SWIM**, Morgan et al. 2021, Nature Astronomy; o el modelo de Mellon et al. 2004) para el punto. |

**Límites de la analogía:**

1. El mecanismo físico difiere. En la Tierra lo que manda es la temperatura del suelo bajo una atmósfera densa; en la Luna, la sublimación al vacío. Las dos fracciones responden a la misma pregunta («¿persiste el hielo?»), pero los umbrales no son idénticos. Lo marcamos como analogía de estabilidad, no como igualdad física.
2. Las escalas difieren: celda de ~1 km en la Tierra frente a un círculo de 5 km de triángulos de 240 m en la Luna. Las dos son «escala de sitio», no de región.
3. Estabilidad ≠ presencia. Un valle seco antártico puede tener permafrost seco; un PSR lunar puede ser estable sin hielo detectado. La presencia (neutrones, radar, LCROSS) sería otra feature.
4. Cobertura de Permafrost_cci: no cubre los Andes, África ni Australia fuera de la Antártida. Allí el índice queda `null` y TASI renormaliza: no se rellena con 0.

**Efecto en TASI (sin tocar fórmulas):** `s_volatiles` compara `precip_mm` y `water_ice_indicator` con `exp(-|x-y|/escala)`, donde la escala es el desvío estándar terrestre. Con este cambio:

- Contra destinos lunares polares, la Vo pasa a premiar sitios con permafrost (Ártico canadiense, Svalbard, valles secos) frente a desiertos cálidos (índice 0).
- Contra Marte, nada cambia (índice `null` en Marte).
- Un sitio terrestre fuera de cobertura sólo usa `precip_mm`, igual que hoy.

**Para decidir el usuario:** ¿aceptamos `comparable: true` para el índice Tierra↔Luna con los límites de arriba? Si no, basta con borrar las filas `water_ice_indicator` de `vo-hielo.jsonl`: las magnitudes crudas quedan igual.

## Validaciones contra valores publicados

- **Marte (GRS):** el rango del producto (1,6–7,4 % en peso en ±57,5°) cae dentro de lo publicado por Boynton et al. 2007 (1,5–7,5 %), y el máximo (7,40 % en −7,5°, 177,5° E) está junto a Apollinaris Patera, una de las dos zonas más ricas según ese trabajo. Hay un test (`test_grs_raw_matches_published_range`).
- **Luna (Diviner PRP):** ver el PR. Se espera hielo estable en superficie en el piso de Haworth (cold trap de Paige et al. 2010, Science 330, 479) y no en los bordes iluminados.
- **Tierra (Permafrost_cci):** ver el PR. Se espera fracción ~1 en Svalbard y Devon/Haughton (permafrost continuo) y 0 en los sitios templados.

## Reproducir

```bash
services/.venv/bin/python services/earth/scripts/ingest_mask.py fetch && services/.venv/bin/python services/earth/scripts/ingest_mask.py build
services/.venv/bin/python services/earth/scripts/ingest_permafrost.py fetch && services/.venv/bin/python services/earth/scripts/ingest_permafrost.py build
services/.venv/bin/python services/planetary/scripts/ingest_ice.py fetch && services/.venv/bin/python services/planetary/scripts/ingest_ice.py build
```

Los subconjuntos chicos quedan versionados en `services/*/data/raw/`. Las descargas completas (PRP de 605 MB y los NetCDF de CCI) van a carpetas `cache/` ignoradas por git.
