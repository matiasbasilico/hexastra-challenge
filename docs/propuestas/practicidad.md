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
