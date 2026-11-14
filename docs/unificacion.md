# Unificación conceptual — HexAstra

Documento de trabajo (solo lectura sobre la Mac). No implementa cambios.
Fecha de inspección: 14 de noviembre de 2026, alrededor de las 12:10 ART (America/Buenos_Aires, UTC−3).
Fotos: 21 JPG en `imagen/Hexastra-20261114T142804Z-1-001.zip` (44 MB), tomadas con un Galaxy S24 Ultra entre las 11:04:57 y las 11:06:48 ART. Planilla de contacto: `docs/screens/fotos-contact-sheet.jpg`.

---

## 1. Narrativa unificada (el concepto que no invalida a nadie)

HexAstra es un mapa que, dado un destino concreto en la Luna o en Marte y una misión (rover, hielo, cuevas, hábitat), le dice a un ingeniero o científico qué lugares de la Tierra sirven mejor para practicar, con un puntaje que se explica solo: qué dimensiones pesaron, dónde cae la analogía (gravedad, presión, radiación, día lunar) y cuáles sitios son poco estudiados. El documento impreso de 21 páginas es el norte de producto: grilla hexagonal H3, campana de Gauss por variable, promedio geométrico ponderado según la misión, confianza, novedad y practicidad. El monorepo `nasa` (GitHub `kevirui/nasa`) es la infraestructura para datos reales: FastAPI, GDAL/Rasterio/PySTAC, PostGIS, Redis y un globo 3D con Cesium. El prototipo que ya corre en `hexastra-analogos` (modo fácil, lugares destacados, planetary-service en :8766 y earth-service en :8767, índice TASI) es la demo usable de hoy y se integra como capa de analogía, sin tirar ni el documento ni el monorepo.

Las tres piezas se complementan: el documento define *qué* medimos y *cómo se lo contamos al jurado*; el monorepo define *cómo procesamos rasters y STAC de verdad*; nuestro prototipo ya *muestra un ranking y un mapa que se pueden abrir ahora*.

---

## 2. Qué hay en las fotos

No son pizarras ni diapositivas sueltas. Son fotos de un documento impreso titulado **«HexAstra · Base del proyecto: análogos terrestres de la Luna y Marte»**, de 21 páginas. Las 21 fotos cubren 20 páginas distintas: `20261114_110615.jpg` y `20261114_110632.jpg` son la misma hoja (página 16, recapturada). **No aparece una foto cuya página se lea como “Page 20 of 21”.** Las páginas cuyo pie no se leyó con claridad se marcan con asterisco (número inferido por el orden del texto). Nada de lo que sigue está inventado; si un dato no estaba en la foto, se indica.

### Página 1 (`110457`) — Visión y funcionamiento

HexAstra es un mapa interactivo que le dice a un ingeniero o científico qué lugares de la Tierra sirven mejor para practicar una misión a la Luna o a Marte, según lo que necesita probar. Usa datos satelitales abiertos para medir el parecido de cada rincón de Argentina con un lugar concreto, y lo muestra en un mapa que se explica solo. El usuario elige un destino (por ejemplo Jezero o el polo sur lunar) y una misión (probar un rover, buscar hielo, explorar cuevas). El mapa se pinta con un puntaje de 0 a 100 por zona, explica por qué y dice con honestidad qué no se parece.

Se distingue de un mapa de «esto se parece a Marte» porque: mide el parecido por dimensión (terreno, temperatura, agua, geología, viento, subsuelo), no por aspecto visual; depende de la misión; busca sitios nuevos; cada puntaje muestra qué variables pesaron y dónde falla la analogía (gravedad, presión, radiación); usa **hexágonos** como unidad de análisis, de ahí el nombre del equipo.

Alcance recomendado para empezar: Argentina completa, 2 destinos lunares, 3 destinos marcianos, 6 dimensiones de análisis y 5 funciones diferenciadoras (sección 9). La capa de radar y el resto del mundo quedan como «próximo paso».

El usuario llega a un resultado útil en cuatro pasos y menos de 30 segundos: (1) elige el destino; (2) elige la misión (preset rover, hielo, cuevas, hábitat, o sliders propios).

### Página 2 (`110503`) — Pantalla y destinos lunares

Pasos 3 y 4: mirar el mapa (color de violeta = poco parecido a naranja = muy parecido) y tocar un hexágono para abrir una ficha (puntaje, gráfico radar, qué es análogo, qué no, qué pruebas permite, confianza y novedad).

Pantalla: centro = mapa de hexágonos H3 con capas y un modo 2D con relieve sombreado; panel izquierdo = destino, misión, sliders y filtro por provincia; panel derecho = ficha y comparador; barra inferior = ranking de los 10 mejores; el estado vive en la URL. El filtro por provincia solo sirve para navegar; el cálculo es siempre por hexágono.

Colores por dimensión (el documento los fija para app y materiales): Terreno en azul, Térmica y luz en naranja, Agua y hielo en verde, Geología en azul marino, Polvo y viento en rosa, Subsuelo en verde oscuro.

**§3 Destinos de referencia.** Catálogo propuesto: 11 destinos, 5 en el MVP. Cada destino es un perfil medido sobre un **polígono**, no un punto (de ahí salen el valor típico y la variación). Coordenadas marcadas como aproximadas:

| Destino | Cuerpo | Coordenadas (aprox.) | Qué lo define | Misión típica | MVP |
|---|---|---|---|---|---|
| Cresta de Shackleton (polo sur) | Luna | 89,9° S | Luz casi continua en las crestas, pendientes moderadas, cráteres en sombra eterna cerca | Hábitat e ISRU | Sí |
| Marius Hills | Luna | 13° N, 57° O | Domos volcánicos y pozos de colapso de tubos de lava | Cuevas | Sí |
| Borde de Faustini | Luna | 87° S, 77° E | Borde de cráter junto a una trampa fría con posible hielo | Hielo e ISRU | No |
| Macizo Malapert | Luna | 86° S, 0° E | Relieve alto, línea de vista a la Tierra, luz prolongada | Hábitat y comunicaciones | No |

### Página 3* (`110507`) — Destinos de Marte y las seis dimensiones

| Destino | Cuerpo | Coordenadas (aprox.) | Qué lo define | Misión típica | MVP |
|---|---|---|---|---|---|
| Pozo de Mare Tranquillitatis | Luna | 8,3° N, 33,2° E | Pozo de colapso en basalto, entrada a una posible cueva | Cuevas | No |
| Jezero | Marte | 18,4° N, 77,7° E | Delta antiguo, arcillas y carbonatos, bloques dispersos | Rover, geología y astrobiología | Sí |
| Planicie Utopía | Marte | 40–50° N | Hielo subterráneo poco profundo, terreno llano, frío extremo | Hielo e ISRU | Sí |
| Arsia Mons | Marte | 9° S, 121° O | Volcán con pozos tipo claraboya sobre tubos de lava | Cuevas | Sí |
| Cráter Gale | Marte | 5,4° S, 137,8° E | Capas sedimentarias con sulfatos y arcillas | Rover y geología | No |
| Oxia Planum | Marte | 18° N, 25° O | Arcillas antiguas, terreno suave, sitio del rover ExoMars | Astrobiología y aterrizaje | No |
| Meridiani Planum | Marte | 2° S, 6° O | Llanura muy plana con hematita, aterrizaje seguro | Aterrizaje | No |

Los cinco del MVP «cubren las tres necesidades más repetidas de la exploración (hielo, cuevas y geología móvil) y encajan con lo que Argentina ofrece en la Puna, en Payunia y en Somuncurá».

Las seis dimensiones, en palabras simples: Terreno (pendiente y rugosidad); Térmica y luz (amplitud día/noche y cuánto sol recibe); Agua y hielo (sequedad, hielo o suelo congelado); Geología (rocas y minerales); Polvo y viento (viento, erosión, polvo en el aire); Subsuelo (pozos, cuevas o tubos de lava).

*La sección 4 (dimensiones en detalle y tabla de pesos de los presets) se cita más adelante («confirmar las 6 dimensiones y los presets, sección 4») pero no aparece como capítulo propio en estas fotos. Solo hay ejemplos parciales de pesos en la página 7.*

### Página 4* (`110510`) y página 5 (`110514`) — Datos necesarios

Tabla de fuentes por dimensión. Muchas celdas dicen «Confirmado que existe» o «A verificar». Resumen:

- **Terreno** (pendiente a tres escalas, rugosidad, elevación): Tierra = NASADEM o ASTER vía Earthdata; elevación ALOS de JAXA como alternativa [A verificar]. Luna = LOLA y modelo de elevación del polo sur (PDS) [Confirmado que existen; resoluciones A verificar]. Marte = MOLA (PDS) [Confirmado]; modelos de HiRISE y CTX [A verificar].
- **Térmica y luz** (temperatura media, amplitud día/noche, inercia térmica aparente, horas de luz): Tierra = MODIS de temperatura de superficie vía Earthdata (~1.000 m) [A verificar]. Luna = Diviner, unos 500 m [Confirmado]; mapas de iluminación [A verificar]. Marte = THEMIS y TES (PDS) [Confirmado]; MCS [A verificar].
- **Agua y hielo** (índice de aridez, probabilidad de permafrost, hielo): Tierra = precipitación de JAXA G-Portal [Confirmado que ofrece precipitación]; CHIRPS o ERA5 [fuera del listado oficial, abiertos]. Luna = LEND y LCROSS [Confirmado]; mapas de trampas frías de Diviner [A verificar]. Marte = GRS de Odyssey, SHARAD y MARSIS [Confirmado que existen].
- **Geología** (tipo de roca, índices de arcilla, carbonato y hierro): Tierra = mapas litológicos (GLiM, SEGEMAR); ASTER vía Earthdata [A verificar]. Luna = datos espectrales de Chandrayaan-1 y Kaguya [Confirmado que existen en PDS; mapas listos A verificar]. Marte = CRISM, OMEGA y TES [Confirmado que existen].
- **Polvo y viento** (viento medio y máximo, polvo en el aire, formas eólicas): Tierra = ERA5, MERRA-2, MODIS de aerosoles [A verificar]. Luna = sin atmósfera: textura del regolito como sustituto (por ejemplo, abundancia de rocas de Diviner [A verificar]). Marte = opacidad de polvo de MCS, Mars Climate Database [A verificar].
- **Subsuelo** (depresiones circulares dentro de campos de basalto): Tierra = modelo de elevación más máscara basáltica, Global Volcanism Program. Luna = catálogo de pozos lunares (datos de LROC) [A verificar]. Marte = catálogo de claraboyas de tubos de lava [A verificar].
- **Radar (opcional, nuevo)** (eco del radar: rugosidad y señal de subsuelo): Tierra = RADARSAT-1 y RCM (banda C) [Confirmado que existen y son de acceso público, al menos en parte]. Luna = Mini-RF [Confirmado que existe en PDS]. Marte = SHARAD, MARSIS, RIMFAX [Confirmado que existen].
- **Practicidad (aparte):** distancia a rutas, aeropuertos, poblaciones — OpenStreetMap, GHSL. No aplica en Luna/Marte.
- **Límites:** provincias y estados — IGN Argentina, geoBoundaries, Natural Earth. No aplica en Luna/Marte.

Dónde conseguirlo: NASA Earthdata Search, PDS y Lunar Orbital Data Explorer, JAXA G-Portal, portal canadiense EODMS (radar) y ASF DAAC (RADARSAT-1). Google Earth Engine «sigue siendo útil para procesar la Tierra sin descargar todo, pero no está en el listado oficial».

Qué se hace con cada dato, en orden: (1) recortar al área de trabajo (Argentina y el polígono de cada destino); (2) llevar a una grilla común de hexágonos H3; (3) resumir cada variable por hexágono (media, desvío y percentiles); (4) normalizar (sección 6); (5) guardar con metadatos: fuente, versión, fecha, resolución y si es un dato directo o un sustituto.

### Página 6 (`110517`) y página 7 (`110529`) — Cómo se calcula el puntaje (sección 6, inferida)

**Paso 1 — parecido por variable (la campana):**

`s = exp( − (x − r)² / ( 2 · (σ² + τ²) ) )`

- `x`: valor medido en el hexágono (por ejemplo, su pendiente).
- `r`: valor típico del destino (la pendiente de Jezero).
- `σ` (sigma): cuánto varía esa variable dentro del destino.
- `τ` (tau): tolerancia que fija el equipo por variable.

Vale 1 cuando el hexágono tiene exactamente el valor del destino y baja suave a medida que se aleja. Ejemplo del documento (r = 8°, σ = 3°, τ = 2°; denominador 2 · (9 + 4) = 26):

| Pendiente del hexágono | Cuenta | Parecido |
|---|---|---|
| 8° | exp(0 / 26) | 1,00 |
| 10° | exp(−4 / 26) | 0,86 |
| 12° | exp(−16 / 26) | 0,54 |
| 14° | exp(−36 / 26) | 0,25 |
| 16° | exp(−64 / 26) | 0,09 |

**Paso 2 — parecido por dimensión:** `D` = promedio de las notas de las variables de esa dimensión. Ejemplo: Terreno con 0,54, 0,80 y 0,70 → D = 0,68.

**Paso 3 — puntaje total (promedio geométrico ponderado):**

`S = 100 · exp( suma de w · ln D )`, con los pesos `w` sumando 1.

En simple: una materia muy mala arrastra todo el puntaje hacia abajo, «como el eslabón débil de una cadena». Un mismo hexágono con cinco dimensiones en 0,9 y el subsuelo en 0,1 da puntajes distintos según la misión (números del ejemplo del documento):

| Cómo se calcula | Puntaje |
|---|---|
| Promedio común (pesos iguales) | 77 |
| Promedio geométrico, pesos iguales | 62 |
| Geométrico con el preset Rover (subsuelo pesa 5) | 81 |
| Geométrico con el preset Cuevas (subsuelo pesa 45) | 33 |

«Pesa 5» y «pesa 45» están así en el texto; no se aclara en la foto si son pesos ya normalizados o pesos relativos antes de normalizar. Hay un modo opcional «eslabón más débil» que usa el mínimo de las dimensiones con peso mayor que cero. El logaritmo de 0 no existe: la app nunca deja una dimensión por debajo de 3/255 (alrededor de 0,012).

**Paso 4 — qué dimensión resta más.** Pérdida total `L = − (suma de w · ln D)`; la parte de cada dimensión es `(− w · ln D) / L`. Ejemplo preset Cuevas: L = 1,094. El subsuelo explica 1,036 (95 %) y las otras cinco juntas 0,058 (5 %).

**Paso 5 — confianza.** Se repite el cálculo N = 200 veces, cada vez con cada peso multiplicado por un factor al azar de entre 0,8 y 1,2 (±20 %) y vuelto a normalizar para que sumen 1. Se cuenta en cuántas repeticiones el hexágono queda en el 10 % superior. `C = repeticiones en que queda arriba / 200`. Ejemplo: 180 de 200 → C = 0,9 (robusto).

### Página 8 (`110541`) — Confianza, novedad y practicidad

Si queda arriba en 70 de 200, C = 0,35: depende de un peso arbitrario. Aclaración honesta: esta confianza mide la **sensibilidad a los pesos**, no la calidad de los datos. Propuesta: un segundo indicador de calidad que baje cuando una dimensión se apoya en variables sustituto (sección 5).

**Paso 6 — novedad:** `N = 1 − (el mayor parecido con cualquier análogo ya conocido)`. Si se parece al destino y también mucho a Atacama, no es una novedad. Ejemplos del documento: parecido máximo 0,85 → N = 0,15 (poco nuevo); máximo 0,30 → N = 0,70 (muy nuevo). Propuesta concreta: tratar a cada análogo conocido como si fuera un destino (su polígono da el perfil `r` y `σ`) y calcular su puntaje `S` contra el hexágono con pesos iguales.

Regla de candidato a descubrimiento (propuesta inicial): `S ≥ 70` y `N ≥ 0,5`. Conjunto A de análogos: Atacama, cráter Haughton, Valle de la Muerte, Mauna Kea y Kilauea, Río Tinto, Valles Secos de McMurdo, Askja y Krafla, depresión de Danakil [lista del documento original, A verificar]. Cuidado: una novedad alta también puede significar «dato malo»; un candidato solo se destaca si además tiene confianza razonable.

**Practicidad (aparte):** `P` de 0 a 100 combina distancia a rutas, aeropuertos y poblaciones, y altitud. Se dibuja un gráfico S contra P: el cuadrante de arriba a la derecha es «se parece y se puede llegar».

Por qué es rápido en el navegador: se precocina `ln D` de cada hexágono una sola vez. Unos 77.000 hexágonos de Argentina × 6 = 462.000 operaciones por movimiento de slider. 5 destinos × 6 dimensiones × 77.000 hexágonos × 1 byte ≈ 2,3 MB.

### Página 9* (`110544`) y página 10 (`110548`) — Símbolos y cómo se programa

Tabla de símbolos: `s` parecido de una variable (0–1); `D` parecido de una dimensión (0–1); `w` peso de una dimensión (0–1, suman 1); `S` puntaje total (0–100); `I` parte de la pérdida (0–1); `C` confianza (0–1); `N` novedad (0–1); `P` practicidad (0–100). La confianza son 200 repeticiones, unos 92 millones de operaciones, en un Web Worker.

El pipeline en Python guarda un byte por hexágono y dimensión (`D` de 0 a 255). El navegador usa una tabla de 256 logaritmos ya calculados. El documento incluye código Python (`similitud` con campana de Gauss, apilado de `D`, `tofile` a `public/data/dest_jezero_r6.bin`) y TypeScript/JavaScript (`puntajes` que hace `100 * exp(sum w * LN[D])`). La confianza repite `puntajes` 200 veces con pesos perturbados y un corte de percentil 90 (selección rápida, sin ordenar todo).

Empieza **§7 Física aplicada, explicada simple**: (1) traducir mediciones distintas a la misma regla; (2) ser honestos con lo que la Tierra no puede imitar.

### Página 11 (`110551`) y página 12 (`110554`) — Física

Valores de referencia, aproximados, **[A verificar contra NASA, USGS o ESA antes de usarlos en la app]**:

| Cuerpo | Gravedad (m/s²) | Presión en superficie | Duración del día | Temperatura típica | Radiación en superficie |
|---|---|---|---|---|---|
| Tierra | 9,81 | 101.325 Pa a nivel del mar | 24 h | 15 °C de media | Unos 0,001 mSv/día de rayos cósmicos a nivel del mar |
| Luna | 1,62 (0,165 de la terrestre) | Menos de 10⁻⁹ Pa (vacío) | 29,5 días terrestres | Unos +120 °C de día y −170 °C de noche; más frío aún en sombras permanentes | Cerca de 1,4 mSv/día |
| Marte | 3,71 (0,378 de la terrestre) | Unos 600 Pa (0,6 % de la Tierra) | 24 h 39 min | Unos −63 °C de media | Cerca de 0,7 mSv/día |

**7.1 Gravedad y movilidad.** `F = m · g · (sen θ + c · cos θ)`. Masa equivalente de prueba: `m de prueba = m en destino · g del destino / g de la Tierra`. Rover de 900 kg en Marte: 900 × 0,378 = 340 kg en la Tierra; en la Luna: 149 kg. En Marte las cosas pesan casi tres veces menos (3,71 contra 9,81).

**7.2 Térmica.** Inercia térmica aparente: `ATI = (1 − A) / ΔT`. El documento aclara un **ejemplo con números inventados**: albedo 0,25, ΔT de 10 K → ATI = 0,075 (roca); ΔT de 40 K → 0,019 (polvo fino). Esto funciona entre Tierra y Marte porque sus días duran casi lo mismo. Con la Luna no, porque su día dura 29,5 días: allí se comparan las temperaturas nocturnas y, si se confirma, la abundancia de rocas que se deriva de Diviner [A verificar]. Diviner mide la temperatura de la superficie lunar a unos 500 m [Confirmado].

**7.3 Presión.** `p(h) = p0 · exp(− h / H)`, con H de unos 8,4 km. A 6.739 m (cumbre del Llullaillaco): 101,3 · exp(−6,739 / 8,400) = unos 45 kPa. Marte tiene unos 0,6 kPa, así que incluso en la cumbre la Tierra tiene unas 75 veces más presión. Conclusión honesta: ningún lugar de la Tierra imita la atmósfera marciana. Se muestra como **brecha cuantificada**, no como parte del puntaje.

**7.4 Radiación y UV.** Crecen con la altura y con la latitud geomagnética; en la Puna estarían entre las más altas del planeta [A verificar con datos]. Aun así, la dosis en Marte y en la Luna es del orden de cientos de veces la del nivel del mar. Se muestra como **límite del análogo**, con orden de magnitud, no como variable de similitud.

**7.5 Pendiente y escala.** Método de Horn (ventana 3×3) en tres escalas fijas, por ejemplo 30, 100 y 300 m, y se compara cada escala con su par.

### Página 13 (`110604`) y página 14 (`110608`) — Luz, subsuelo, aridez, viento, radar, brechas

**7.6 Luz.** En el polo lunar el Sol nunca sube más de unos 1,5° sobre el horizonte; en el polo terrestre el máximo es 23,4°: ningún sitio terrestre reproduce esa luz rasante. Lo que sí se puede comparar es la **fracción del año con Sol sobre el horizonte local** (modelo de elevación en 36 direcciones + fórmulas astronómicas). Función opcional y de las más costosas.

**7.7 Subsuelo.** Candidatos a claraboya: rellenar las depresiones del DEM y restar; conservar depresiones casi circulares dentro de campos de basalto; la densidad por km² es la variable de la dimensión Subsuelo.

**7.8 Aridez.** `AI = P / PET`. Por debajo de 0,05 el clima es hiperárido, y ese es el valor de referencia para la Luna y Marte.

**7.9 Viento.** En Marte hace falta un viento mucho más fuerte para mover arena, porque el aire tiene unas 100 veces menos presión. El viento terrestre sirve como señal de procesos eólicos (dunas, yardangs), no como medida de fuerza equivalente.

**7.10 Radar (nuevo, opcional).** SAR. Mini-RF (Luna); SHARAD, MARSIS, RIMFAX (Marte, este último en Perseverance) [Confirmado que figuran en el PDS]. RADARSAT-1 y RCM en la Tierra. Cuidado: cada radar usa una longitud de onda distinta. RADARSAT-1 y RCM trabajan en banda C [A verificar]; Mini-RF usa otras bandas [A verificar]. Cobertura abierta sobre Argentina: [A verificar]. Requiere registro y descargas pesadas.

**7.11 Qué no puede igualar la Tierra (brecha en números):**

| Aspecto | Tierra frente a Marte | Tierra frente a Luna |
|---|---|---|
| Gravedad | 2,6 veces mayor | 6,1 veces mayor |
| Presión (mejor caso, cumbre del Llullaillaco) | Unas 75 veces mayor | Incomparable: la Luna es vacío |
| Radiación | Marte recibe cientos de veces más | La Luna recibe más de mil veces más |
| Día | Casi igual (24 h contra 24 h 39 min) | 29,5 días contra 24 h |
| Suelo | Percloratos en Marte; ningún suelo terrestre se le parece en eso | Regolito filoso y vítreo; ningún suelo terrestre se le parece |

Código Python en la página: `pendiente_horn` (Horn 3×3) y `masa_equivalente`.

### Página 15* (`110612`) y página 16* (`110615`, recaptura `110632`) — Sitios candidatos en Argentina (§8)

Siguen funciones `presion_kpa` (p0 = 101.325, H = 8400.0; comentario: 6739 m dan unos 45 kPa) e `inercia_termica_aparente`.

«Estos son 11 lugares para probar con la app, y tres de ellos (los destacados) servirían como “descubrimientos destacados” de la demo. Son hipótesis nacidas de lo que se sabe de la geografía: cada una hay que confirmarla con los datos antes de afirmarla.»

| Sitio | Provincia | Qué lo hace interesante | Análogo de | Destacado |
|---|---|---|---|---|
| Campo de Piedra Pómez | Catamarca | Pómez e ignimbrita, yardangs, muy seco, gran altura | Marte: procesos eólicos | Sí |
| Payunia | Mendoza | Campo volcánico basáltico; posibles tubos de lava a verificar | Luna y Marte: volcanismo y cuevas | Sí |
| Puna: Laguna Diamante y Socompa | Catamarca y Salta | Lagunas y microbialitos a más de 3.500 m, sal, UV, volcanes | Marte: antiguos lagos, evaporitas y vida extrema | Sí |
| Cumbres andinas con permafrost (Llullaillaco y similares) | Salta | Frío extremo, hielo en el suelo, aire fino | Marte: hielo subterráneo; operaciones en altura | No |
| Meseta de Somuncurá | Río Negro | Meseta basáltica, plana, clima frío y seco | Luna: llanuras de mares basálticos; aterrizaje | No |
| Pali Aike | Santa Cruz | Volcanismo con maares y coladas en estepa fría | Marte: volcanismo con agua | No |
| Campo del Cielo | Chaco y Santiago del Estero | Cráteres de impacto pequeños con meteoritos de hierro | Luna y Marte: cráteres de impacto | No |
| Cráteres de Río Cuarto | Córdoba | Depresiones alargadas; origen de impacto discutido | Luna y Marte: impactos oblicuos [A verificar] | No |
| Médanos de Fiambalá y Tatón | Catamarca | Dunas enormes en un desierto de altura | Marte: dunas y arena | No |
| Valle de la Luna (Ischigualasto) y Talampaya | San Juan y La Rioja | Barrancos y capas sedimentarias muy erosionadas | Marte: terreno sedimentario como el de Gale | No |
| Antártida Argentina (Marambio, Esperanza) | Tierra del Fuego, Antártida e Islas | Frío polar, hielo y logística de bases permanentes | Luna y Marte: operación de un hábitat aislado | No |

Idea para el radar [A verificar]: si hay cobertura, mirar primero Fiambalá y Payunia.

Análogos ya conocidos (para calcular la novedad): desierto de Atacama (Chile), cráter Haughton (Canadá), Valle de la Muerte (EE. UU.), Mauna Kea y Kilauea (Hawái), Río Tinto (España), Valles Secos de McMurdo (Antártida), Askja y Krafla (Islandia) y la depresión de Danakil (Etiopía). Cada uno con su propio polígono [lista del original, A verificar].

Fuera de Argentina (cierre que aparece arriba de la página 17): cuando el MVP funcione, el mismo pipeline sirve para cualquier país con solo cambiar el recorte. Dos candidatos para empezar son Bolivia (altiplano y Salar de Uyuni) y Namibia (Namib).

### Página 17 (`110638`) — §9 «El algo más: lo que lo vuelve ganador»

El salto de «mapa lindo» a «proyecto de 10» es pasar de mostrar parecidos a **ayudar a decidir y a descubrir**, con ciencia que el jurado pueda auditar. Cinco funciones centrales y tres opcionales (más dos extras baratos nuevos). Orden por impacto y esfuerzo (estimación del equipo, se puede discutir):

- Hacer primero: prueba de validez, capa de honestidad, detector de novedad, gemelo terrestre inverso, plan de campaña de pruebas.
- Extras baratos: modo historia y bilingüe; botón «Ver en Worldview» (nuevo).
- Apuestas grandes, solo si sobra tiempo: simulador de recorrido; capa de radar (nueva).
- **Recortar primero: vista 3D lado a lado.**

Stack propuesto en la tabla:

| Capa | Herramienta propuesta | Para qué |
|---|---|---|
| Procesamiento de datos | Python con rasterio, GDAL, xarray, numpy, h3-py | Recortar, calcular variables y resumir por hexágono |
| Datos de la Tierra | NASA Earthdata y JAXA G-Portal; GEE como apoyo opcional | MODIS, ASTER y elevación |
| Datos de la Luna y Marte | PDS y Orbital Data Explorer | Elevación, temperatura, hielo, radar y minerales |
| Grilla | H3 (hexágonos) | Resolución 5 (~250 km²) vista general; 6 (~36 km²) por defecto; 7 (~5 km²) al elegir una provincia |
| Interfaz | Vite, TypeScript y React o Svelte | Paneles, sliders, fichas |
| Mapa | MapLibre GL JS con deck.gl (capa H3) | Decenas de miles de hexágonos con GPU |
| Gráficos | D3 o Chart.js | Radar de dimensiones y dispersión S contra P |

### Página 18 (`110641`) — Rendimiento, pitch y demo

Sigue la tabla: cálculo en el navegador = arreglos tipados y un Web Worker; exportar = jsPDF o impresión del navegador; alojamiento = GitHub Pages, Netlify o Cloudflare Pages (sitio estático gratuito).

**§10.6 Presupuesto de rendimiento** (estimaciones; hay que medirlas): recalcular puntajes al mover un slider = 77.000 × 6 = 462.000 operaciones, unos pocos milisegundos, hilo principal; recolorear 77.000 hexágonos = un atributo por hexágono, GPU con deck.gl; confianza con 200 repeticiones = unos 92 millones de operaciones más una selección por repetición, Web Worker; novedad y practicidad ya calculadas en el pipeline.

*Las secciones 10.1–10.5, 11 y 12 no aparecen en las fotos (la numeración salta de §9 a §10.6 y luego a §13). Puede que estén en la página 20 que falta, o que no formen parte de esta versión impresa.*

**§13 Pitch y guión de demo.** Pitch en 30 segundos (borrador): «Para ir a la Luna y a Marte, la NASA practica en la Tierra, pero siempre en los mismos lugares. HexAstra usa datos abiertos de satélites para medir qué tan parecido es cada rincón del planeta a un destino concreto, según lo que la misión necesita probar. Empezamos por Argentina, donde hay lugares casi sin estudiar, y para cada resultado mostramos cuánto confiar y dónde la analogía falla.»

Guión de demo de 3 minutos (hipótesis de cómo contarlo; se ajusta a lo que salga de los datos reales): (1) 0:00 gancho Atacama o Haughton, ¿qué otros lugares nadie midió?; (2) 0:20 Jezero + preset rover, el mapa se pinta; (3) 0:50 preset de hielo, el mapa se reordena.

### Página 19* (`110645`) — Cierre del guión, jurado y decisiones abiertas

Sigue el guión: (4) 1:20 ficha de un hexágono destacado, radar, qué se parece, qué no, masa equivalente de un rover, opcional Worldview; (5) 1:50 candidatos a descubrimiento; (6) 2:20 prueba de validez (Atacama y Haughton arriba en el ranking); (7) 2:40 exportar ficha en PDF; (8) 2:55 «Argentina es el primer laboratorio; el mismo método sirve para cualquier país.»

Qué suele mirar un jurado (a confirmar con las reglas oficiales): uso creativo de datos abiertos, validez científica, claridad, calidad de ejecución y utilidad real. Preguntas previstas: ¿por qué promedio geométrico?; ¿de dónde salen los pesos?; ¿cómo saben que funciona?; ¿qué no se puede igualar?; ¿de dónde son los datos?

**§14 Decisiones abiertas y glosario.** Hay nueve decisiones antes de construir. En esta página se leen las primeras seis: (1) fecha límite y reglas oficiales; (2) cuántas personas somos y quién toma cada rol; (3) confirmar los 5 destinos del MVP (sección 3); (4) confirmar las 6 dimensiones y los presets (sección 4); (5) elegir el framework de la interfaz (React o Svelte), según lo que ya maneje el equipo; (6) elegir la función opcional que se suma al final (sección 9).

### Página 21 (`110648`) — Resto de decisiones y glosario

Continúa, con el borde superior un poco recortado por la foto: definir nombre final y paleta (propuesta: fondo azul noche, escala violeta a naranja para el puntaje); revisar los recursos oficiales cuando lleguen y ajustar la sección 5; **nueva:** decidir si se intenta la capa de radar, después de comprobar si hay cobertura abierta sobre Argentina.

Glosario (tal como está en la página): Análogo; Hexágono H3; Modelo de elevación (DEM); Regolito; Permafrost; ISRU; Tubo de lava; Zona en sombra permanente; Inercia térmica; Yardang; Promedio geométrico; SAR; PDS y PDS4; EDR, RDR, GDR.

---

## 3. Qué es cada repositorio

Inspección de solo lectura en `/Users/mattib/Desarrollo/nasa`. No se leyó ni se copia el contenido de ningún `.env`.

### 3.1 `nasa/` — monorepo de infraestructura (GitHub `kevirui/nasa`)

- Un único commit: `912305a` «initial commit», 13 de noviembre de 2026, 21:11:38 −03, autor kevirui. Rama `main` alineada con `origin/main`. Remoto: `https://github.com/kevirui/nasa`.
- Nombre del paquete raíz: `nasa-geospatial-monorepo`. Política documentada en `.agent/`: **Fail-Fast / cero datos de prueba**. Si falta un token o cae un servicio, debe fallar con el error real.
- Stack:
  - Frontend `apps/frontend`: Next.js 15 (App Router), React 18, TypeScript, Tailwind, CesiumJS 1.122, Jest y Playwright. Puerto **3000**. Requiere `NEXT_PUBLIC_CESIUM_ION_TOKEN`. Hoy la página es un globo Cesium a pantalla completa más un panel de diagnóstico (health + botón «Probar STAC»). No hay todavía mapa de análogos, sliders de misión ni ranking.
  - Backend `apps/backend`: Python 3.11, FastAPI, Pydantic v2, GDAL, Rasterio, NumPy, SciPy, scikit-learn, PySTAC, SQLAlchemy async + GeoAlchemy2, Redis, boto3. Puerto **8000**. Prefijo `/api/v1`.
  - Endpoints reales (no hay TASI, ni H3, ni puntaje de analogía):
    - `GET /api/v1/health` — PostGIS, Redis, S3, GDAL/Rasterio
    - `GET /api/v1/geospatial/capabilities`
    - `POST /api/v1/geospatial/stac/inspect` — catálogo STAC por defecto `https://earth-search.aws.element84.com/v1`, con caché Redis
    - `POST /api/v1/geospatial/raster/analyze` — ventana de un COG/GeoTIFF, estadísticas y K-Means
    - `GET /api/v1/storage/status` — HEAD al bucket S3/R2
  - Infra: PostgreSQL 16 + PostGIS 3.4 (puerto **5432**, tabla `spatial_aois`), Redis 7 (**6379**), AWS S3 (TODO documentado para migrar a Cloudflare R2).
- En el momento de la inspección, en la Mac ya escuchaban (no se tocó nada): OrbStack en 3000, 5432 y 6379; un proceso Python en `127.0.0.1:8000`; y nuestros servicios en `127.0.0.1:8765/8766/8767`.
- `hexastra-analogos/` **dentro** de este repo está **sin trackear** (`git status` lo muestra como `??`). Es una copia del prototipo estático temprano (Leaflet + 5 sitios argentinos + 5 de Marte + `climate-era5-1991-2020.json`). El `data/sites.json` tiene el mismo MD5 que el de nuestro proyecto actual (`bd066f6cb3e1fa4715c80d7b5a4c3572`). **No** incluye modo fácil, destacados, microservicios ni TASI. No hay que commitearlo como si fuera la versión vigente.

### 3.2 `nasa-analogos/` — primer prototipo estático

HTML/CSS/JS vanilla + Leaflet, 16 sitios clásicos del mundo (Atacama, Islandia, Valles Secos, Hawái, Sahara, Namib, Utah, Haughton, Kamchatka, Mojave, Pilbara, Yellowstone, Valle de la Muerte, Puna, cráteres del Sahara, Timanfaya). Comparación lado a lado, sin backend, sin TASI, sin hexágonos. Es el arranque más antiguo; conviene archivarlo, no desarrollarlo más.

### 3.3 `hexastra-analogos` (el nuestro, que sigue corriendo)

En la Mac: `/Users/mattib/hexastra-analogos`, repo git local en `main` (sin remoto), commits `d3c6963` y `18a9cf7`. Copia de trabajo también en `/workspace/hexastra-analogos`. Servicios que no se detuvieron: front :8765, planetary-service :8766, earth-service :8767.

- Front estático Leaflet + Chart.js, modo fácil, lugares destacados, filtros por continente/país.
- Contratos en `contracts/feature_vector.schema.json`.
- Índice **TASI** (propuesta del equipo, no un estándar publicado): máscara M(x) por NDVI > 0,15 o agua líquida; `S_T = exp(−γ · D_M)` con Mahalanobis y covarianza Ledoit-Wolf; `S_G` coseno espectral solo con espectros reales; TASI = suma ponderada de los componentes disponibles (G, T, E, Vo, O), pesos renormalizados. Hoy NDVI/agua/espectro/operacional siguen en gran parte vacíos.
- Catálogo terrestre semilla: **52 sitios** en el mundo (no una grilla H3). Destacados en el seed: Piedra Pómez, Payún Matrú, Yungay/Atacama, Haughton, Kīlauea, University Valley, Devon/FMARS, Timanfaya, Teide, Mauna Kea, Laguna Diamante, Socompa.
- Catálogo planetario: Jezero, Gale, Medusae Fossae, Pavonis Mons, Meridiani; en Luna, borde de Shackleton (medias LOLA) más Haworth, Malapert, de Gerlache, Amundsen y Nobile (anclas IAU / Artemis III). Al momento de la inspección no estaban Marius Hills, Utopía, Arsia Mons, Faustini, el pozo de Mare Tranquillitatis ni Oxia Planum. **Actualización 14 nov 2026:** Marius Hills, Utopía y Arsia Mons ya están en el catálogo (ver §8).
- Python 3.9 en la Mac (con `eval_type_backport`).

---

## 4. Compatibilidad, solapes y conflictos

**Veredicto: es compatible, y no se invalidan.** El documento, el monorepo y nuestro prototipo apuntan al mismo producto. Lo que hay que unificar es la fórmula oficial de puntaje, la unidad espacial (punto vs hexágono), el alcance del MVP (Argentina primero vs mundo ya filtrable) y el hogar del código.

### Compatible (se refuerzan)

- La idea central: no un mapa de «se parece a Marte», sino un parecido medido por dimensiones, dependiente de la misión, honesto sobre los límites y atento a sitios poco estudiados.
- Fuentes: Earthdata, PDS, LOLA, MOLA, MODIS/Diviner/THEMIS, JAXA G-Portal, RADARSAT, CRISM. Nuestro contrato de vector de features encaja como el sobre donde viajan esas variables.
- Sitios destacados de Argentina del documento (Piedra Pómez, Payunia, Diamante y Socompa) ya están en nuestro catálogo y en el modo fácil. Los análogos clásicos del documento (Atacama, Haughton, McMurdo, Mauna Kea, Kīlauea, Río Tinto, Askja, Danakil, Valle de la Muerte, Timanfaya) también están, casi todos.
- FastAPI + NumPy/SciPy/scikit-learn aparecen en el monorepo y en earth-service (Ledoit-Wolf, Mahalanobis). El backend del monorepo ya sabe leer COGs y STAC: es el lugar natural del pipeline que el documento describe (recortar, H3, resumir).
- Cesium en el monorepo cubre el «recortar primero: vista 3D lado a lado» del documento, que nuestro Leaflet todavía no tiene.
- Paleta propuesta en el documento (fondo azul noche, escala violeta → naranja) es coherente con lo que ya venimos usando en el modo fácil.
- No hay choque de puertos hoy: 3000/8000/5432/6379 vs 8765/8766/8767.

### Solapes (hay dos implementaciones de lo mismo)

- Tres frentes: `nasa-analogos`, el `hexastra-analogos` anidado (prototipo de 5 sitios) y el `hexastra-analogos` actual. El anidado es una copia vieja, no una rama más nueva.
- Dos maneras de puntuar: TASI (suma ponderada de componentes, Mahalanobis en terreno) vs S del documento (campana univariada + promedio geométrico por misión).
- Dos unidades: puntos con ficha vs hexágonos H3 de toda Argentina (~77.000 celdas en resolución 6).
- Dos alcances de MVP: el documento pide Argentina primero y el mundo después; nosotros ya tenemos un catálogo mundial de 52 puntos y filtros por continente/país.
- Tres stacks de front imaginados: Leaflet actual, Next+Cesium del monorepo, Vite+MapLibre+deck.gl del documento.

### Conflictos a resolver (no son bloqueos)

1. **Fórmula oficial.** TASI y S no son la misma cuenta. TASI es una suma (un componente flojo se nota menos). S es un promedio geométrico (un componente flojo arrastra el total, que es justo el argumento del pitch). Conviene no mezclarlos en un solo número sin decirlo.
2. **Punto vs hexágono.** El prototipo actual no puede pintar 77.000 hexágonos ni mover sliders en milisegundos como describe el documento; Leaflet + puntos sí sirve para la demo de esta semana.
3. **Catálogos de destinos.** El MVP del documento (Shackleton, Marius Hills, Jezero, Utopía, Arsia Mons) no coincide del todo con el nuestro (Shackleton/Artemis III + Jezero/Gale/Medusae/Pavonis/Meridiani). Las coordenadas de Jezero y Gale del documento son aproximadas (18,4° N, 77,7° E y 5,4° S, 137,8° E); las nuestras están citadas de NASA GISS Mars24 (18,44° N, 77,45° E y 4,59° S, 137,44° E). No hay que “promediarlas”: hay que citar la fuente y quedarse con la citada.
4. **Sitios argentinos del documento que no estaban en nuestro seed** (resuelto el 14 nov 2026, ver §8): Llullaillaco / permafrost andino, Somuncurá, Pali Aike, Campo del Cielo, Río Cuarto, Fiambalá-Tatón, Antártida Argentina (Marambio, Esperanza). Ischigualasto sí está, pero no como destacado. Teide está destacado en nuestro seed y no figura en la lista de 11 del documento.
5. **Política de datos.** El monorepo prohíbe mocks y fallbacks silenciosos. Nuestro prototipo, por acuerdo del equipo, marca faltantes como null / «a completar» y sigue mostrando un ranking parcial (cobertura). Hay que explicitar las dos capas: infra fail-fast para I/O; puntaje parcial y honestidad cuando falta una variable.
6. **Versión de Python:** 3.11 en el monorepo vs 3.9 en la Mac para nuestros servicios.
7. **Front.** Elegir una línea (el documento deja abierta React o Svelte; el monorepo ya eligió Next+Cesium; nosotros ya tenemos Leaflet). Forzar un rewrite a MapLibre+deck.gl ahora tiraría la demo que ya corre.
8. **El `hexastra-analogos` anidado**, si se commitea como está, va a parecer la versión oficial y no lo es.

### Lo que las fotos agregan y nosotros todavía no tenemos

- El modelo de producto completo: presets de misión, sliders de pesos, puntaje que se recalcula al vuelo, ficha con “qué dimensión resta”, confianza por perturbación de pesos, novedad contra análogos clásicos, practicidad S vs P, capa de honestidad con números (masa equivalente, brecha de presión, radiación).
- La unidad H3 y el pipeline de precocinado a bytes.
- Física aplicada (Horn a tres escalas, ATI, barométrica, fracción del año con sol, detección de claraboyas).
- El pitch de 30 segundos y el guión de demo de 3 minutos, más las preguntas del jurado ya contestadas.
- Destinos MVP que nos faltan (Marius Hills, Utopía, Arsia Mons) y siete candidatos argentinos que no están en el seed.
- Prueba de validez explícita: Atacama y Haughton tienen que salir arriba si el método funciona.

---

## 5. Plan de unificación (sin implementar todavía)

### Hogar del código

Usar **`/Users/mattib/Desarrollo/nasa/nasa`** (`kevirui/nasa`) como repo oficial del equipo: ya tiene remoto, Docker, documentación `.agent/` y a Kevin como owner. Nuestro `/Users/mattib/hexastra-analogos` sigue siendo la demo que está corriendo; no se apaga ni se mueve hasta que el merge esté acordado y verificado. `nasa-analogos/` y el `hexastra-analogos/` anidado se archivan como `archive/prototipo-estatico-v0` y `archive/prototipo-analogos-ar-v1`, sin borrar historia, y no se commitea el anidado como si fuera el producto actual.

### Cómo entra lo nuestro al monorepo

- `services/planetary` → `apps/planetary` (puerto 8766, dueño del catálogo Luna/Marte y de los vectores del destino).
- `services/earth` → `apps/earth` (puerto 8767, catálogo terrestre, máscara, TASI, y más adelante la grilla H3 y el puntaje S).
- `contracts/feature_vector.schema.json` → `contracts/` en la raíz del monorepo, contrato único entre servicios.
- El front Leaflet (modo fácil + destacados) → `apps/analog-demo` (estático, puerto 8765) como **demo oficial del hackathon mientras tanto**.
- El frontend Next+Cesium se queda en `apps/frontend` (puerto 3000) y suma, como siguiente recorte, la vista 3D lado a lado que pide el documento.
- `apps/backend` (puerto 8000) no se tira: se convierte en el **pipeline de datos** del documento (STAC/COG, recortes, Horn, resumen por H3, escritura de los `.bin` de `D`). earth-service consume esos artefactos; no hace falta que el front hable con GDAL.
- `docker-compose.yml` agrega `planetary` y `earth` sin pelearse con 3000/8000/5432/6379. PostGIS/Redis del monorepo pueden cachear STAC y, más adelante, footprints H3.

### Cómo conviven S y TASI (ninguno se tira)

- **S (campana + promedio geométrico ponderado)** pasa a ser el **puntaje de misión** que pinta el mapa y que usa el pitch: depende de los presets, arrastra el eslabón débil y se explica en la ficha (pérdida por dimensión, confianza C, novedad N, practicidad P).
- **TASI** se queda como **índice complementario del equipo**, visible en la ficha cuando hay datos para sus componentes: la máscara de vegetación/agua, Mahalanobis en terreno (mejor que comparar pendientes una por una cuando hay covarianza real) y el coseno espectral cuando existan espectros. No se presenta como estándar publicado.
- Los pesos de misión del documento alimentan S. Los pesos de TASI (G, T, E, Vo, O) no se mezclan en la misma suma. Si una dimensión de S se puede apoyar en un componente TASI (por ejemplo Terreno ← S_T), se documenta; si no hay datos, esa dimensión queda null y el peso se renormaliza, como ya hacemos.
- La capa de honestidad del documento (gravedad, presión, radiación, día lunar, percloratos/regolito) **no entra en S ni en TASI**. Se muestra en la ficha con los valores del documento solo después de verificarlos contra NASA, USGS o ESA (el propio texto lo pide).

### Producto, en etapas que no invalidan lo que ya corre

1. **Seguir demoable ya:** modo fácil, destacados, 8765/8766/8767. Sumar al catálogo, con coordenadas citadas y sin inventar, los destinos MVP que faltan (Marius Hills, Utopía, Arsia Mons) y los sitios argentinos del documento que aún no están. Los 52 sitios mundiales quedan como capa exploratoria / filtro, no como contradicción del «Argentina primero».
2. **Contar el concepto unificado** en la página de Space Apps y en un modo «misión» del front: presets (aunque al principio solo cambien pesos de TASI o de un S simplificado sobre los puntos actuales).
3. **Pipeline H3** en `apps/backend`, empezando por un recorte chico (una provincia o un destacado) para no bloquear la demo. Recién cuando haya `D` precocinado se pinta una capa hexagonal (deck.gl o primitivas Cesium; no hace falta reescribir todo a Vite).
4. **Prueba de validez** del documento: Atacama y Haughton tienen que aparecer arriba. Si no, se informa el resultado real, no se ajusta el puntaje en silencio.
5. **Vista 3D lado a lado** en el front Cesium, cuando haya token de Cesium Ion. El Leaflet no se apaga.

### Lo que no hay que hacer

- Apagar los servicios que ya corren en 8765/8766/8767.
- Reemplazar el prototipo usable por un rewrite a MapLibre antes de tener la grilla.
- Promediar coordenadas distintas o rellenar hexágonos, espectros o pendientes con números inventados.
- Commitear `.env` ni el `hexastra-analogos` anidado como versión vigente.
- Presentar TASI como un índice publicado, ni descartarlo como si fuera un error.

---

## 6. Preguntas que solo puede cerrar el equipo

1. ¿Confirmamos `kevirui/nasa` como hogar oficial y, con el OK de Kevin, hacemos el merge ahí? ¿O preferís un repo nuevo del equipo y dejar el monorepo como infra aparte?
2. ¿Aceptamos S como puntaje que pinta el mapa y TASI como índice complementario en la ficha, o querés una sola fórmula para el jurado?
3. Para el hackathon de esta semana, ¿el MVP es el mapa de puntos que ya corre (con presets y destacados) o hay que llegar sí o sí a la grilla H3 de Argentina?
4. ¿Hay un PDF o un doc digital de estas 21 páginas? Falta al menos la página 20, y no vimos la sección 4 (tabla de pesos de los presets) ni las secciones 10.1–10.5, 11 y 12.
5. Los valores de gravedad, presión, temperatura y radiación de la página 11 están marcados «A verificar»: ¿los verificamos contra las fact sheets de NASA antes de mostrarlos, o los dejamos como «aprox., a completar»?
6. En la Mac ya hay algo escuchando en 3000, 5432, 6379 (OrbStack) y 8000 (Python), además de nuestros 8765–8767. ¿El monorepo ya lo levantaste vos, y lo dejamos así?

---

## 7. Inventario de archivos de esta inspección

- Fotos originales (en la Mac): `/Users/mattib/Desarrollo/nasa/imagen/Hexastra-20261114T142804Z-1-001.zip`
- Copia en la box: `/workspace/uploads/Hexastra-20261114T142804Z-1-001.zip`
- JPG redimensionados (lado largo 1600 px, orientación corregida): `/workspace/uploads/hexastra-fotos/resized/`
- Planilla de contacto: `docs/screens/fotos-contact-sheet.jpg`
- Este plan: `docs/unificacion.md`

Nada de esto se copió de vuelta a la Mac ni se commiteó.

---

## 8. Estado de implementación: sitios del documento (14 nov 2026)

Rama `feat/sitios-documento`. Puntaje: **solo TASI** (no se implementó S). MVP: mapa de puntos actual (sin H3, sin Cesium). Regla: ninguna coordenada sin fuente; lo que no se pudo verificar quedó en `null` con la nota «a completar».

### 8.1 Destinos de Luna y Marte agregados (`services/planetary/data/catalog.json`)

| id | Destino | lat | lon (−180..180) | lon 0–360 E | Fuente |
|---|---|---|---|---|---|
| `marius-hills` | Marius Hills, pozo de colapso | 14.0917 | −56.7701 | 303.2299 | LROC Lunar Pits Atlas, pozo #1 (https://lroc.im-ldi.com/atlases/pits/1). Descubrimiento: Haruyama et al. 2009, GRL 36, L21206, doi:10.1029/2009GL040635 |
| `utopia-planitia` | Utopia Planitia, sitio Viking 2 | 48.27 | 134.28 | 134.28 | NASA GISS Mars24 (https://www.giss.nasa.gov/tools/mars24/help/landers.html) |
| `arsia-mons` | Arsia Mons | −8.26 | −120.09 | 239.91 | USGS Gazetteer 394, red MDIM 2.1, planetocéntrica +E (https://planetarynames.wr.usgs.gov/Feature/394) |

Decisiones:

- **Marius Hills no es un nombre IAU.** El Gazetteer no tiene «Marius Hills/Colles/Montes»; el rasgo homónimo es el cráter Marius (USGS 3715, 11.90°N, −50.84°E), que no representa la cueva. Para el destino «Cuevas» se usa el pozo del LROC Pits Atlas. Las dimensiones del pozo no coinciden entre LROC (49–55 m, 40 m de profundidad) y Haruyama (65 m, 80–88 m) y no se cargan.
- **Utopía:** el documento da una franja (40–50°N). Se usa un punto real dentro de esa franja con la misma fuente que Jezero y Gale (Mars24, Viking 2). El centro IAU de la planicie (USGS 6260: 46.74°N 117.52°E en MDIM 2.1; 49.67°N 118.0°E en MDIM 2.0) queda citado. Que haya hielo somero justo en el punto Viking 2 no se verificó con fuente primaria (a completar).
- **Arsia Mons:** cota de cumbre en `null`; las cifras NASA/ASU no coinciden («>9 km», «~20 km», «más de 20 km sobre las llanuras») y ninguna está referida al datum MOLA.
- **Redes del Gazetteer en Marte:** la ficha muestra MDIM 2.0 y MDIM 2.1; se usa MDIM 2.1 (la seleccionada por defecto), que no siempre es la primera del desplegable.
- **T y E completados (14 nov 2026, segunda pasada):**
  - **T:** relieve relativo, pendiente y rugosidad en una grilla 7×7 a 120 m con valores bilineales, con las mismas fórmulas que los candidatos terrestres (`services/planetary/terrain.py`). Se lee una ventana de los DEM globales de USGS Astrogeology por HTTP: LOLA LDEM 118 m (Luna) y HRSC-MOLA Blend 200 m (Marte). Validación: Bradbury Landing da −4.504,7 m contra −4.501 m publicados por NASA. En Marte el DEM nativo (200 m) es más grueso que la grilla. En Utopia la planicie sale casi plana (pendiente 0,00°, relieve 1,39 m), lo que es consistente con un DEM suave pero no resuelve el relieve fino.
  - **E en Marius Hills:** Diviner Global Cumulative Product (LRO-L-DLRE-5-GCP-V1.0; Williams et al. 2017), bin de 0,5° y 96 horas locales, 48 con dato y huecos de hasta 1,25 h interpolados. Es temperatura de **superficie** (la Luna no tiene aire): media −54,53 °C y amplitud 295,38 K.
  - **E en Utopia y Arsia:** Mars Climate Database v6.2 (modelo, como ERA5 en la Tierra), aire a 2 m, Ls cada 15° y 24 horas locales, media anual ponderada por el tiempo en cada Ls. Utopia: −80,27 °C / 36,77 K. Arsia: −72,71 °C / 65,73 K. Validación: en Jezero el método da medias diarias de 207–222 K contra 209–225 K medidos por MEDA.
  - **Siguen en `null`:** iluminación e indicador de hielo.
  - **Efecto en TASI:** los tres destinos ya no comparten ranking. Marius usa T, E y V; Utopia y Arsia, T, E y V.

### 8.2 Verificación de Jezero y Gale

| Cráter | Centro IAU (USGS, MDIM 2.1) | Documento | Repo (Mars24, aterrizaje) | Diferencia repo vs. centro |
|---|---|---|---|---|
| Jezero (USGS 14300) | 18.41°N, 77.69°E | 18,4°N, 77,7°E | 18.44°N, 77.45°E (Perseverance) | Δlat +0.03°, Δlon −0.24° (≈14 km) |
| Gale (USGS 2071) | 5.37°S, 137.81°E | 5,4°S, 137,8°E | 4.59°S, 137.44°E (Curiosity) | Δlat +0.78°, Δlon −0.37° (≈51 km) |

Conclusión: el documento usa el centro IAU del cráter; nuestras coordenadas son los puntos de aterrizaje y Mars24 no cambió (página actualizada el 2023-12-09). Las dos son correctas para lo que representan. No se promedian: se mantiene el punto de aterrizaje (donde hay datos in situ de los rovers) y ahora se cita también el centro IAU en `coord_source`.

### 8.3 Candidatos argentinos agregados (`services/earth/data/sites_seed.json` → `catalog.json`)

| id | Sitio | lat, lon | Fuente | Menos estudiado |
|---|---|---|---|---|
| `meseta-de-somuncura` | Meseta de Somuncurá (Río Negro) | −41.5833, −67.15 | Wikipedia ES, **último recurso** | sí |
| `pali-aike` | Pali Aike, sector argentino (Santa Cruz) | −51.995, −70.155 | Ross et al. 2011, JVGR 201:253–271 | sí |
| `campo-del-cielo` | Campo del Cielo (Chaco / Santiago del Estero) | −27.6333, −61.70 | Earth Impact Database (PASSC, Wayback 2023) | no (impacto confirmado y muy citado) |
| `crateres-rio-cuarto` | Cráteres de Río Cuarto (Córdoba) | −32.75, −64.25 | Grant y Schultz 1993, LPSC XXIV, NTRS 19940011723 | sí |
| `dunas-de-taton` | Dunas de Tatón, Bolsón de Fiambalá (Catamarca) | −27.3436, −67.5386 | Isla et al. 2021, QEG 12(2):19–29 | sí |
| `llullaillaco` | Volcán Llullaillaco (Salta) | −24.72, −68.53 | Smithsonian GVP 355110 | sí |
| `base-marambio` | Base Antártica Marambio | −64.2418, −56.6232 | COMNAP Antarctic Facilities | sí |
| `base-esperanza` | Base Antártica Esperanza | −63.3970, −56.9981 | COMNAP Antarctic Facilities | sí |

Mediciones: `scripts/ingest_earth.py` midió DEM ASTER GDEM v3 (OpenTopoData, 7×7 a 120 m) y clima ERA5 1991–2020 (Open-Meteo) para los 8. NDVI y agua líquida siguen en `null`, porque la ingesta ya tenía desactivados ORNL y Overpass después de fallas previas (no se adivinan). La covarianza Ledoit-Wolf se recalculó con las ventanas nuevas (n = 1300 → 1500).

Notas por sitio:

- **Llullaillaco:** el ID GVP correcto es 355110 (355030 es Isluga, Chile). ASTER da 6.418 m en el punto contra 6.739 m de cumbre en GVP: el DEM de 30 m subestima las cumbres. El feature guarda el valor medido y la cota GVP queda en `coord_source`.
- **Pali Aike:** el «Parque Nacional Pali Aike» es chileno (CONAF), no de APN. El punto GVP 358080 (52.082°S, 69.698°W) cae sobre el límite; se eligió el de Ross et al., que el paper ubica del lado argentino.
- **Río Cuarto:** origen discutido (impacto oblicuo, Schultz y Lianza 1992; erosión eólica, Cione et al. 2002). La coordenada sale del OCR del abstract en NTRS («32°45'S, 64°15'W») y hay que confirmarla en el PDF. Wikipedia lo ubica ≈14 km más al sur.
- **Tatón:** es un punto de muestreo del paper, no el centro del campo de dunas.
- **Somuncurá:** única coordenada de Wikipedia (último recurso, marcada en `coord_source`). Wikipedia EN da otro punto (41.35°S, 66.9°W); los dos caen sobre la meseta. Queda a completar con una fuente oficial o un paper.
- **Antártida:** con el mismo método de siempre (Natural Earth 50m point-in-polygon y fallback Nominatim), las dos bases **quedan sin país ni continente**. No se las fuerza a `AR` ni a `AQ`: aparecen en la búsqueda «Mundo entero», pero no en `/candidates?country=AR` ni en el filtro «Antarctica». Decisión abierta: usar un polígono antártico de mayor resolución o una regla documentada.

### 8.4 Descartados

| Sitio | Motivo |
|---|---|
| «Parque Nacional Pali Aike» (APN) | No existe como parque nacional argentino; es chileno (CONAF). Se usa el sector argentino del campo volcánico. |
| Reserva Geológica Provincial Laguna Azul (maar, Santa Cruz) | Solo hay coordenadas en sitios turísticos o de geocaching, sin fuente oficial ni paper. A completar. |
| Médano de Saujil / dunas de Fiambalá como punto aparte | Ya cubierto por Tatón (coordenada de paper). |
| Faustini, pozo de Mare Tranquillitatis, Oxia Planum | Fuera del alcance de este cambio: el documento no los marca como MVP. |

### 8.5 Arreglos del front encontrados al verificar

- `js/api.js`: el modo fácil enviaba `continent=south-america` (slug) y earth-service filtra por el nombre de Natural Earth (`South America`), así que el ranking filtrado por continente/país quedaba vacío para **todos** los destinos. Ahora se traduce el slug.
- `services/earth/tasi.py`: `/tasi` no devolvía `highlight_less_studied` en cada match y el chip «Menos estudiado» nunca se veía en los rankings.

