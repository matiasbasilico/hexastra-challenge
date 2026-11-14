# Propuesta: índice de practicidad P (0–100), aparte del puntaje

**Estado:** propuesta del agente O-Tierra. Nada de esto está conectado al puntaje ni al front. Lo decide el usuario.

## Qué se propone

Un índice **P** de 0 a 100 que dice qué tan fácil es llegar y trabajar en un sitio terrestre, mostrado **al lado** del TASI y nunca dentro. El documento impreso (pág. 8, resumido en `docs/unificacion.md` §126–134) ya lo plantea así: «P combina distancia a rutas, aeropuertos y poblaciones, y altitud», con un gráfico de dispersión S contra P cuyo cuadrante superior derecho es «se parece y se puede llegar».

`tasi.py` no cambia. El componente O de TASI sigue nulo: la accesibilidad de un sitio terrestre no es similitud con un sitio de la Luna o de Marte (`README.md`, punto 5 de TASI). Las cuatro features nuevas se cargan con `comparable: false` para que quede explícito.

## Por qué va aparte

- **No hay contraparte.** En Jezero o en Shackleton no hay rutas ni aeródromos. Un valor que sólo existe de un lado no puede puntuar parecido.
- **Tira para el otro lado.** Los sitios más parecidos suelen ser los más aislados (Haughton, valles secos antárticos). Si P entrara al puntaje, premiaría a los sitios cómodos y castigaría justo a los análogos poco estudiados que el desafío pide buscar.
- **Responde otra pregunta.** TASI dice «¿se parece?». P dice «¿puedo ir a probar algo ahí?». El desafío pide las dos cosas («conditions relevant to landing, mobility, navigation, robotic operations, human exploration, or construction»; «connect your analog to exploration»), y se leen mejor separadas.

## Entradas

Todas salen de `services/earth/scripts/ingest_accessibility.py` y quedan en `data/measurements/o-tierra.jsonl`. Las distancias son geodésicas en línea recta sobre WGS84, no de viaje.

| Feature | Unidad | Definición | Fuente |
|---|---|---|---|
| `dist_road_km` | km | Tramo de ruta más cercano | NASA SEDAC gROADS v1 (Earthdata) |
| `dist_airport_km` | km | Aeródromo abierto con pista más cercano (sin helipuertos ni cerrados) | OurAirports (externa) |
| `dist_airport_scheduled_km` | km | Igual, sólo con vuelos regulares | OurAirports (externa) |
| `population_50km` | personas | Suma de celdas de 30″ con centro a ≤ 50 km | NASA SEDAC GPWv4 r11, 2020 (Earthdata) |
| `elevation` | m | Ya está en el catálogo base | ASTER GDEM v3 |

OurAirports es una fuente externa porque ninguno de los recursos oficiales del desafío publica un catálogo mundial de aeródromos. Es de dominio público y se descarga entera, sin consultas por sitio.

## Fórmula propuesta

Cada entrada se lleva a un puntaje parcial entre 0 y 1 y P es el promedio ponderado:

```
P = 100 · Σ w_k · p_k / Σ w_k        (sobre los términos con dato)
```

| Término | Peso | p = 1 | p = 0 | Entre medio |
|---|---|---|---|---|
| Ruta (`dist_road_km`) | 0,35 | ≤ 1 km | ≥ 300 km | lineal en log(distancia) |
| Aeródromo (`dist_airport_km`) | 0,25 | ≤ 25 km | ≥ 1000 km | lineal en log(distancia) |
| Población (`population_50km`) | 0,20 | ≥ 100.000 | ≤ 100 | lineal en log(población) |
| Altitud (`elevation`) | 0,20 | ≤ 2500 m | ≥ 5500 m | lineal |

Decisiones y sus motivos:

- **Escala logarítmica en distancias y población.** Pasar de 1 a 10 km de la ruta cambia el trabajo de campo mucho más que pasar de 201 a 210 km.
- **Población como apoyo, no como molestia.** Más gente cerca significa combustible, alojamiento, atención médica y mano de obra. No se penaliza la población alta: la interferencia (luz, radio, tránsito) es un tema distinto y no tenemos dato para medirla.
- **Altitud.** Por debajo de 2500 m no suele hacer falta aclimatación; por encima de 5500 m ya no hay residencia humana permanente. Son umbrales de uso común en medicina de altura, puestos acá como convención y abiertos a revisión.
- **Pesos renormalizados sobre los términos con dato y cobertura informada**, igual que TASI. Un sitio antártico sin ruta ni población en las fuentes recibe un P parcial con su cobertura a la vista, no un cero inventado.
- **Los umbrales y pesos son una convención del equipo**, no un estándar publicado. Están como constantes con nombre en `services/earth/accessibility.py` (`P_WEIGHTS`, `P_ROAD_KM`, …) y la función `practicality_index` ya está implementada y testeada, sin que nadie la llame todavía.

## Cómo se mostraría

- **Gráfico TASI contra P** por destino elegido: un punto por sitio terrestre. Arriba a la derecha, «se parece y se puede llegar»; arriba a la izquierda, «se parece pero es una expedición» (ahí caen los análogos poco estudiados y los polares).
- **En la ficha del sitio:** P con sus cuatro barras parciales y los datos crudos (a qué aeródromo, a cuántos km), para que se pueda discutir el número.
- El orden del ranking sigue siendo por TASI. P no reordena.

## Límites que hay que decir

- Línea recta no es camino: puede cruzar agua (Devon Island a Resolute) o una cordillera.
- gROADS v1 es de 1980–2010 y su cobertura depende del país; no tiene rutas en la Antártida.
- OurAirports es colaborativo: puede faltar una pista o figurar una en desuso.
- GPWv4 reparte población censal de manera uniforme dentro de cada unidad administrativa; en unidades grandes y vacías (Puna, Sahara) el valor a 50 km es una estimación gruesa.
- P no mide permisos, áreas protegidas, estacionalidad del acceso ni costo. Un parque nacional con ruta asfaltada puede ser menos practicable que un campo privado sin ella.

## Qué hay que decidir

1. ¿Se acepta P como índice aparte, con estos cuatro términos?
2. ¿Pesos y umbrales así, o se ajustan?
3. ¿El término de aeródromo usa cualquier pista (`dist_airport_km`) o sólo las de vuelos regulares (`dist_airport_scheduled_km`)? La propuesta usa cualquier pista, porque las campañas a sitios remotos vuelan chárter.
4. ¿Se suma el gráfico TASI contra P al front del MVP o queda para después?

## Resultado con los datos cargados (14 de noviembre de 2026)

P calculado con la fórmula de arriba sobre los 60 sitios, ordenado de mayor a menor. Es una vista previa para discutir la propuesta: no está guardado como feature ni se usa en ningún lado.

| Sitio | Ruta (km) | Aeródromo (km) | Población 50 km | Altitud (m) | P | Cobertura |
|---|---|---|---|---|---|---|
| yungay-atacama | 0.02 | 6.24 | 121997 | 1039 | 100 | 100 % |
| rio-tinto | 0.80 | 17.19 | 510673 | 0 | 100 | 100 % |
| base-marambio | null | 0.53 | null | 195 | 100 | 45 % |
| base-esperanza | null | 0.81 | null | 1 | 100 | 45 % |
| tswaing | 1.01 | 22.17 | 3979416 | 1076 | 100 | 100 % |
| wadi-rum | 0.23 | 27.10 | 179766 | 938 | 99 | 100 % |
| white-sands | 0.06 | 10.16 | 51066 | 1220 | 98 | 100 % |
| nordlinger-ries | 1.50 | 4.74 | 974488 | 421 | 98 | 100 % |
| kilauea | 0.60 | 41.78 | 120645 | 1236 | 97 | 100 % |
| valle-de-la-luna-chile | 0.99 | 16.93 | 27650 | 2417 | 96 | 100 % |
| vredefort | 2.03 | 12.27 | 439709 | 1439 | 96 | 100 % |
| dallol | 0.40 | 71.55 | 211533 | -99 | 93 | 100 % |
| craters-of-the-moon | 0.04 | 15.50 | 4519 | 1791 | 91 | 100 % |
| lonar | 0.20 | 98.56 | 2186204 | 477 | 91 | 100 % |
| timanfaya | 4.97 | 19.11 | 195174 | 137 | 90 | 100 % |
| dunas-de-taton | 1.37 | 34.16 | 9887 | 1834 | 89 | 100 % |
| crateres-rio-cuarto | 3.73 | 37.18 | 112220 | 486 | 89 | 100 % |
| campo-del-cielo | 4.27 | 15.57 | 35091 | 80 | 88 | 100 % |
| pico-do-fogo | 3.85 | 10.51 | 43478 | 2725 | 88 | 100 % |
| karijini | 0.72 | 7.35 | 573 | 772 | 85 | 100 % |
| teide | 3.55 | 26.17 | 948573 | 3553 | 85 | 100 % |
| sp-crater | 9.21 | 36.03 | 96695 | 2102 | 84 | 100 % |
| lake-natron | 15.96 | 13.45 | 104167 | 593 | 83 | 100 % |
| meteor-crater | 8.75 | 3.48 | 19471 | 1556 | 82 | 100 % |
| undara | 0.66 | 2.02 | 176 | 740 | 82 | 100 % |
| taylor-valley | null | 96.71 | null | 210 | 80 | 45 % |
| badwater | 5.27 | 24.21 | 2354 | -92 | 79 | 100 % |
| pinacate | 19.82 | 33.17 | 69841 | 978 | 79 | 100 % |
| mauna-kea | 5.74 | 11.02 | 106535 | 4163 | 78 | 100 % |
| pali-aike | 9.04 | 46.80 | 18421 | 146 | 77 | 100 % |
| chott-el-djerid | 24.63 | 39.77 | 120974 | 24 | 77 | 100 % |
| erta-ale | 6.78 | 123.05 | 75556 | 565 | 77 | 100 % |
| lava-beds | 17.67 | 20.45 | 9319 | 1450 | 76 | 100 % |
| da-qaidam | 0.24 | 154.71 | 6447 | 3189 | 75 | 100 % |
| university-valley | null | 141.83 | null | 1679 | 74 | 45 % |
| wolfe-creek | 3.45 | 39.81 | 285 | 320 | 72 | 100 % |
| ischigualasto | 10.86 | 89.28 | 8630 | 1384 | 70 | 100 % |
| laguna-antofagasta | 1.79 | 134.28 | 1331 | 3320 | 67 | 100 % |
| campo-piedra-pomez | 4.63 | 102.93 | 4475 | 3453 | 66 | 100 % |
| tso-kar | 5.12 | 71.06 | 28120 | 4546 | 66 | 100 % |
| acraman | 8.38 | 31.24 | 26 | 145 | 65 | 100 % |
| askja | 36.58 | 32.36 | 1443 | 1025 | 64 | 100 % |
| laguna-diamante | 2.15 | 111.41 | 6437 | 4577 | 63 | 100 % |
| lut-desert | 62.39 | 178.84 | 117025 | 580 | 61 | 100 % |
| llullaillaco | 5.99 | 77.06 | 77955 | 6418 | 61 | 100 % |
| ubehebe | 15.67 | 37.13 | 50 | 647 | 60 | 100 % |
| payun-matru | 25.61 | 47.04 | 6604 | 3648 | 60 | 100 % |
| laguna-negra | 9.68 | 90.85 | 7180 | 4080 | 59 | 100 % |
| meseta-de-somuncura | 35.58 | 88.26 | 1737 | 1204 | 58 | 100 % |
| socompa | 7.47 | 82.97 | 50133 | 6011 | 58 | 100 % |
| tolbachik | 22.05 | 61.09 | 2513 | 3685 | 56 | 100 % |
| richat | 9.51 | 177.20 | 276 | 420 | 56 | 100 % |
| popigai | 18.09 | 105.72 | 287 | 26 | 56 | 100 % |
| salar-de-uyuni | 28.18 | 72.03 | 3440 | 3664 | 55 | 100 % |
| sossusvlei | 53.52 | 51.55 | 299 | 571 | 54 | 100 % |
| mcgill-arctic | 534.71 | 1.94 | 0 | 451 | 45 | 100 % |
| valley-10000-smokes | 150.36 | 67.29 | 1 | 145 | 43 | 100 % |
| bockfjorden | 985.71 | 67.69 | 339 | 0 | 42 | 100 % |
| haughton | 292.66 | 169.83 | 0 | 121 | 32 | 100 % |
| devon-island-fmars | 299.50 | 168.05 | 0 | 235 | 32 | 100 % |

Qué muestra la tabla:

- **Los análogos árticos quedan abajo, como se esperaba.** Haughton y FMARS (Devon Island) tienen P ≈ 32: 170 km hasta Resolute, casi 300 km hasta la ruta más cercana de gROADS y nadie a 50 km.
- **Los cuatro sitios antárticos tienen cobertura de 45 %.** Sin ruta ni población en las fuentes, su P sale sólo de aeródromo y altitud, y por eso Marambio y Esperanza (con pista propia) dan 100. Ese número no se puede leer sin la cobertura al lado; una opción es no mostrar P cuando la cobertura es menor que un umbral.
- **La población de GPWv4 infla sitios de la Puna y de Afar.** Llullaillaco (77.955), Socompa (50.133) y Dallol (211.533) figuran con decenas de miles de personas a 50 km porque sus unidades censales son enormes y GPWv4 reparte la población de manera uniforme. Es el dato oficial, pero conviene tenerlo presente al fijar el peso de este término.
- **gROADS no tiene las rutas de Svalbard:** Bockfjorden figura a 986 km de una ruta (Noruega continental).
