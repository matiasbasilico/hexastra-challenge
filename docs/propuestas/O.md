# Propuesta: S_O, similitud operacional (componente O)

Estado: **propuesta, no implementada**. `services/earth/tasi.py` no cambia hasta que el usuario apruebe la fórmula. Los datos ya están cargados en `data/measurements/o-comparable.jsonl` (script: `services/planetary/scripts/ingest_o_comparable.py`).

## Qué es O y qué no

O compara **condiciones para aterrizar y moverse** medidas igual en los dos lados. No incluye la accesibilidad del sitio terrestre (rutas, aeropuertos, población): esa es la practicidad P de `feat/o-tierra` y no mide parecido con la Luna o Marte.

## Métricas cargadas

| Feature | Definición | Luna | Marte | Tierra |
|---|---|---|---|---|
| `slope_frac_gt_10deg` | Fracción de las 25 celdas interiores de la grilla 7×7 a 120 m (la de T, unos 600 m × 600 m) con pendiente > 10°. La pendiente de cada celda se calcula con la fórmula de la pendiente central de T: cuatro vecinos cardinales, base de 240 m. | 7/7 | 7/7 | 59/60 |
| `slope_frac_gt_15deg` | Ídem con umbral de 15° | 7/7 | 7/7 | 59/60 |
| `slope_frac_gt_30deg` | Ídem con umbral de 30° | 7/7 | 7/7 | 59/60 |
| `rock_abundance_pct` | % del área cubierta por rocas, por separación térmica | 1/7 (Diviner, solo Marius Hills) | 3/7 (TES) | **0/60** |
| `rock_abundance_irtm_pct` | Ídem con Viking IRTM, grilla de 1° | — | 7/7 | — |

**DEMs.** Son los mismos que usa T:

- Marte: HRSC-MOLA de 200 m.
- Luna, polo sur: LOLA LDEM_80S_20M.
- Marius Hills: LOLA LDEM de 118 m.
- Tierra: ASTER GDEM v3 vía OpenTopoData.

En los 74 sitios, la pendiente de la celda central coincide con la `slope` de T (diferencia < 0,02°).

**Umbrales, con su fuente primaria:**

- **10°:** «Surface slope for landing (100m): <10 deg». Requisito de Artemis III/HLS (Dwyer Cianciolo, NASA LaRC, 2024, [NTRS 20240009596](https://ntrs.nasa.gov/api/citations/20240009596/downloads/ArtemisHLSUpdate_2024.pdf)). El 8° que se suele citar aparece en ese documento solo como curva de nivel de un mapa, no como requisito.
- **15°:** «VIPER can generally drive on a slope of up to 15 degrees» ([NASA VIPER](https://science.nasa.gov/mission/viper/lunar-operations/)). Es también el límite de aterrizaje de InSight: <15° a 84 m y a 2 m (Golombek et al. 2017, doi:10.1007/s11214-016-0321-9; esta cita la vi solo en extractos).
- **30°:** «rover drivers avoid terrains that would tilt the rover more than 30 degrees», sobre Perseverance ([NASA](https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/)).

**Escala.** Los requisitos están definidos para bases de metros a 100 m; la grilla mide pendientes con base de 240 m. Las fracciones **subestiman** el peligro real, pero se pueden comparar entre sí porque todos los sitios usan la misma grilla. Va dicho en la `note` de cada fila.

**Rocas en la Tierra.** Quedan null a propósito: ningún producto de NASA ni de ESA mide la fracción de área con rocas por separación térmica, como hacen Diviner o TES. La inercia térmica aparente de ASTER o MODIS es otra magnitud: depende de la humedad y la vegetación. Además, Diviner (rocas de 1 m o más), TES (inercia ≥ 1250) e IRTM (rocas de más de 0,1–0,15 m) definen "roca" distinto, así que ni siquiera entre la Luna y Marte es la misma magnitud.

## Fórmula propuesta

Sobre las métricas que tienen valor **en los dos lados** (destino y sitio terrestre):

```
s_pend = 1 − ( |Δf10| + |Δf15| + |Δf30| ) / 3          # fracciones en [0,1]: no hace falta escala
s_roca = exp( −|ΔRA| / σ_RA )                          # solo si RA existe en los dos lados
S_O    = promedio de los s disponibles                  # null si no hay ninguna métrica compartida
```

- **Fracciones sin normalizar por desvío.** Las tres fracciones ya están en la misma escala física, de 0 a 1 del área. Dividir por el desvío del catálogo terrestre, como hacen E y Vo, haría que S_O dependiera de qué sitios hay en el catálogo. Además, ese desvío está dominado por ceros, porque la mitad de los sitios son planos. Con `1 − |Δ|`, la lectura es directa: «difieren en un X % del área peligrosa».
- **Rocas.** Hoy nunca entran, porque la Tierra no tiene dato. La fórmula queda escrita por si aparece un producto comparable.
- **Si falta un lado.**
  - Sin las tres fracciones en los dos lados, S_O = null y TASI renormaliza como ya hace con G.
  - Bockfjorden es el único sitio sin fracciones: su grilla cae sobre el agua del fiordo, con 49 celdas a 0 m en ASTER.
- **Cobertura esperada.** Con O, los 14 destinos tienen la componente disponible contra 59 de los 60 sitios terrestres.

## Ejemplos con datos reales

Fracciones (>10°, >15°, >30°):

| Par | Destino | Sitio terrestre | s_pend = S_O | Lectura |
|---|---|---|---|---|
| Haworth (Luna) – McGill Arctic | 0,72 / 0,16 / 0 | 0,80 / 0,12 / 0 | **0,960** | Las dos son laderas moderadas, la mayor parte del área por encima del límite de HLS y casi nada por encima de 15°. Sirven para practicar aterrizaje de precisión y tránsito en pendiente. |
| Pavonis Mons (Marte) – Teide | 1,00 / 0,08 / 0 | 1,00 / 0,72 / 0 | **0,787** | Todo el área supera 10° en los dos, pero el Teide es mucho más empinado por encima de 15°: sirve como análogo de movilidad exigente, no de aterrizaje. |
| Jezero (Marte) – Tolbachik | 0 / 0 / 0 | 0,96 / 0,92 / 0,80 | **0,107** | Jezero es una planicie segura en esta escala; Tolbachik es un flanco de cono. Operacionalmente no se parecen. |
| *Jezero – Lonar* (caso límite) | 0 / 0 / 0 | 0 / 0 / 0 | **1,000** | Los dos son planos en esta escala: S_O no los distingue. Ver limitación 1. |

**Efecto sobre TASI.** Con pesos iguales y k componentes disponibles, sumar O queda así:

```
TASI' = (k · TASI + S_O) / (k + 1)
```

Con k = 2 (T y E, el caso típico hoy):

- Haworth–McGill: un sitio con TASI 60 pasaría a 72.
- Jezero–Tolbachik: pasaría a 43,6.

## Limitaciones y decisiones para el usuario

1. **No discrimina entre sitios planos.** 9 de 14 destinos y 31 de 59 sitios terrestres tienen las tres fracciones en 0. Para un destino plano, S_O = 1 contra todos los sitios planos: O solo castiga a los sitios terrestres abruptos.
   - Opción: sumar un umbral de 6°, el límite de pendiente media del módulo lunar Apollo («a mean surface slope of 6° or less», Rogers 1972, [NASA TN D-6850](https://ntrs.nasa.gov/api/citations/19720018253/downloads/19720018253.pdf)). Así se separarían las planicies suaves de las onduladas.
   - No está cargado: lo decide el usuario.
2. **Se superpone con T.** T ya usa la pendiente central, el relieve y la rugosidad de la misma grilla, así que las fracciones están correlacionadas con T y O puede contar dos veces la topografía. Opciones:
   - (a) peso de O menor, por ejemplo 0,1;
   - (b) usar las fracciones solo como bandera operativa («% del área sobre el límite de HLS») y no en el puntaje;
   - (c) aceptarlo, porque O mide la *distribución* contra umbrales de ingeniería y T mide la forma.
3. **Escala.** La base de 240 m no ve rocas ni cráteres métricos, que son los que de verdad limitan un aterrizaje. Bajar a la escala de los requisitos pide DEMs de 1–5 m (LOLA a 5 m en el polo, HiRISE en Marte, ArcticDEM o REMA en la Tierra), que no hay de forma uniforme para los 74 sitios.
4. **Otras métricas O posibles, no cargadas.** Las sugirió la investigación; todas son solo Marte–Tierra:
   - Profundidad óptica de polvo: Mars Climate Database `dod` en Marte; NASA POWER `AOD_55` (MERRA-2) en la Tierra.
   - Viento de superficie: MCD `wind` a 10 m en Marte; ERA5 o POWER `WS10M` en la Tierra.

   En la Luna tendrían que quedar «no disponible», no 0: un 0 por convención metería el vacío lunar en el puntaje, y según CLAUDE.md §1 eso va como brecha cuantificada aparte. Antes de cargarlas hay que acordarlo.
