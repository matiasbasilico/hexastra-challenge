# Propuesta G — geología, mineralogía y materiales

Agente G, 14 nov 2026. Estado: **propuesta + piloto de 12 sitios** (`data/measurements/g-piloto.jsonl`). No cambia `services/earth/tasi.py`. La fórmula de S_G y el cableado que propongo al final necesitan el OK del usuario.

## 1. El problema

Hoy G está vacío. `tasi.py` sólo acepta un coseno entre espectros reales (`s_spectral`) y, además, `rank()` le pasa al sitio terrestre `{"score_ready": False}` fijo, así que S_G nunca puede salir aunque se carguen datos. Hace falta:

1. una representación de G que signifique lo mismo en la Tierra, la Luna y Marte;
2. fuentes oficiales o reconocidas que la llenen para nuestros 74 sitios (60 terrestres + 8 lunares + 6 marcianos);
3. una forma de comparar que respete los nulos (regla 6 de CLAUDE.md: no rellenar para subir puntajes).

## 2. Camino (a): espectral

| | Tierra | Luna | Marte |
|---|---|---|---|
| Instrumento | EMIT (VSWIR 0,38–2,5 µm, 60 m) · ASTER GED AG100 (5 bandas TIR 8,3–11,3 µm, 100 m) | M3 / Chandrayaan-1 (85 bandas en modo global, 140 m; 280 m en la 2.ª fase) | CRISM MSP (72 bandas, ~200 m) |
| Archivo | NASA Earthdata / LP DAAC (EMITL2BMIN, doi:10.5067/EMIT/EMITL2BMIN.001; AG100 v003) | PDS Imaging Node | PDS Geosciences (MTRDR, parámetros de resumen) |
| Cobertura | EMIT: 54° N–54° S y sólo las regiones áridas que apunta la misión. ASTER GED: global, escenas 2000–2008 | >95 % de la Luna en modo global; SNR objetivo >100 en la referencia polar (contra >400 en el ecuador) | ~80 % de Marte en MSP |

**Qué sería comparable:** no las bandas crudas (cada sensor tiene otras longitudes de onda, otra resolución y otra corrección atmosférica), sino índices con la misma definición física: profundidad de banda a 1 µm (olivino/piroxeno), a 1,9 µm (agua de hidratación), a 2,1–2,3 µm (sulfatos, filosilicatos, carbonatos). EMIT ya publica identificación de minerales con Tetracorder; CRISM publica parámetros de resumen. Para M3 y EMIT habría que calcular los índices a mano sobre reflectancia.

**Cobertura de nuestros sitios (estimación, no verificada sitio por sitio):**

- Tierra con EMIT: como máximo 49 de 60 (quedan fuera por latitud Haughton, Devon/FMARS, McGill, Bockfjorden, Popigai, Askja, Tolbachik, Valley of 10,000 Smokes, los dos valles secos antárticos y las bases Marambio y Esperanza). Dentro de esa franja falta confirmar granulo por granulo.
- Luna con M3: 7 de los 8 destinos son polares (Shackleton, Haworth, Malapert, de Gerlache, Amundsen, Nobile). Ahí la iluminación es rasante y hay sombra permanente, justo donde el espectro VSWIR es menos confiable. Sólo Marius Hills es ecuatorial.
- Marte con CRISM: probable para Jezero, Gale y Meridiani (sitios muy observados); para Pavonis, Arsia, Medusae Fossae y Utopia hay que buscar cubos.

**Costo:** cubos de cientos de MB a varios GB por escena (M3 L2, CRISM TRDR/MTRDR, EMIT L2A), correcciones fotométricas distintas por cuerpo y una cadena de procesamiento por instrumento. Calculo de 3 a 5 días-persona para llegar a un índice común validado en un puñado de sitios.

**Defensa ante el jurado:** es alta si funciona, porque compara mineralogía medida y no interpretada. El riesgo, sin embargo, es grande: alguien puede preguntar con razón por qué un índice a 1 µm de M3 en un borde polar en penumbra se compara con EMIT en un salar, y no tenemos una buena respuesta en el tiempo que queda.

## 3. Camino (b): categórico (mapas geológicos + tabla de equivalencias)

| | Tierra | Luna | Marte |
|---|---|---|---|
| Mapa | Macrostrat API v2, `scale=small` (~1:5M: CGMW South America 2018, Geologic Map of North America, etc.); si no hay unidad, `scale=tiny` (Chorlton 2007, GSC OF 5529) | USGS Unified Geologic Map of the Moon 1:5M v2 (Fortezzo, Spudis y Harrel 2020) | USGS SIM 3292, Geologic Map of Mars 1:20M (Tanaka et al. 2014, doi:10.3133/sim3292) |
| Acceso | API pública por punto (CC-BY 4.0; Peters et al. 2018, doi:10.1029/2018GC007467) | Shapefile `GeoUnits` dentro de un ZIP de 224 MB; bajamos sólo los miembros necesarios (~84 MB comprimidos) por HTTP Range | Shapefile `SIM3292_Global_Geology` dentro de un ZIP de 809 MB; bajamos sólo ese miembro |
| Impacto en la Tierra | Osinski et al. 2022, *Impact Earth*, Earth-Sci. Rev. 232:104112, tabla de cráteres confirmados | — | — |

¿Por qué Macrostrat y no GLiM? GLiM (Hartmann y Moosdorf 2012) es la referencia clásica, pero en PANGAEA sólo hay una grilla de 0,5° (~50 km, demasiado gruesa para la regla de escala) y el vector original se distribuye como una geodatabase por fuera de PANGAEA. Macrostrat devuelve la litología del mapa fuente en el punto, cita ese mapa y trabaja a 1:5M, la misma escala que el mapa lunar. Ninguna agencia de la lista oficial del desafío publica un mapa litológico global de la Tierra, así que esto es una fuente del nivel 3 (§4 de CLAUDE.md) y queda documentado.

### Representación propuesta: vector G de 7 componentes

| Feature | Qué es | Tierra (palabra clave en `lith`) | Luna (unidad DOMU) | Marte (unidad SIM 3292) |
|---|---|---|---|---|
| `g_lito_basaltico` | volcánico máfico | basalt, mafic volcanic, basanite | mare Em, Im1, Im2, Imd, EIp; manto oscuro Id (piroclástico) | volcánicas Av, Ave, lAv, lAvf, AHv, eHv, lHv, lHvf, Hve, Nve, lNv → basálticas por McSween et al. 2009 (doi:10.1126/science.1165871) |
| `g_lito_silicico` | volcánico intermedio a félsico | andesite, dacite, rhyolite, trachyte, ignimbrite, tuff | — | — |
| `g_lito_clastico` | sedimentario clástico o no consolidado | sandstone, shale, siltstone, conglomerate, siliciclastic, alluvium, sand… | — | — (los médanos lApd quedan para la v1) |
| `g_lito_quimico` | carbonatos y evaporitas | limestone, dolomite, carbonate, evaporite, gypsum, halite | — | — |
| `g_lito_cristalino` | plutónico o metamórfico | granite, gneiss, schist, plutonic, metamorphic | — | — |
| `g_lito_hielo` | hielo | ice, glacier | — | casquete lApc |
| `g_impacto` | origen por impacto (0/1) | 1 si figura en la tabla de Osinski et al. 2022 | 1 en cráteres, cuencas, formaciones de eyecta y terras/planicies (la DOMU las interpreta como «megaregolito; eyecta de cráteres y cuencas»); 0 en mare | 1 en AHi; **null** en el resto (un cráter de menos de ~100 km no se ve a 1:20M; que no esté en el mapa no quiere decir 0) |

Las seis fracciones de composición suman 1. Si el texto de litología trae varias clases, se reparte en partes iguales. Si no aparece ninguna palabra clave (por ejemplo `sedimentary` a secas o `volcanic` sin más), la composición queda **null** con «a completar»: no se adivina si es clástico o químico. Tampoco se completa la composición de cráteres y terras lunares ni de las unidades morfoestratigráficas de Marte: el mapa las define por su origen y no por su roca.

**Defensa ante el jurado:** media-alta. Cada valor sale de un mapa publicado y de una regla escrita (`services/earth/scripts/g_equivalencias.py`), y cada fila cita la unidad leída. La tabla sigue la idea de *análogo funcional* de Foucher et al. 2021 (Planet. Space Sci. 197:105162, doi:10.1016/j.pss.2021.105162): se compara la propiedad que importa para un uso concreto (aquí, tipo de roca y proceso de formación) y no la composición total. El punto débil está a la vista y conviene mostrarlo: la escala de los mapas (1:5M y 1:20M) y que en Marte muchas unidades no tienen litología.

**Esfuerzo:** ya está hecho para los 12 sitios del piloto. Pasar a los 74 es correr el mismo script con la lista completa (unos minutos; las descargas quedan en `~/.cache/hexastra/g`).

## 4. Recomendación

**Camino (b), categórico, como G v0 para el MVP**, y el espectral en una fase 2 acotada.

Por qué:

1. Cubre los 74 sitios con un dato trazable (la corrida en seco de abajo lo confirma) y no depende de cubos de GB ni de iluminación polar.
2. Encaja con la regla de «decir qué se parece y qué no»: el vector separa composición e impacto, y un nulo dice por qué falta.
3. El espectral, con los destinos que tenemos (7 de 8 lunares polares), entrega poco y cuesta mucho antes de la entrega.

Para la fase 2 propongo un eje composicional que llene justo lo que falta en los destinos, y que hay que evaluar antes de usarlo: un índice de sílice por la posición del rasgo de Christiansen en el infrarrojo térmico, con Diviner en la Luna (producto global en PDS), TES/THEMIS en Marte y ASTER GED en la Tierra (global, 100 m, por AppEEARS). Ojo: la posición del rasgo cambia entre el vacío y la atmósfera, y hay que documentar la corrección antes de comparar. Las referencias concretas de la fase 2 quedan **a verificar**.

## 5. Piloto (12 sitios, `g-piloto.jsonl`)

Script: `services/earth/scripts/ingest_g_piloto.py` (más `remote_zip.py` y `g_equivalencias.py`). Dependencias extra: `services/earth/requirements-g.txt`. Calidad `derived` (clase derivada de un mapa publicado con una regla documentada); los nulos van como `unavailable`.

| Sitio | Cuerpo | Unidad o litología leída | Mapa fuente | Composición | Impacto |
|---|---|---|---|---|---|
| pali-aike | Tierra | Neogene–Quaternary Basaltic · basalt | CGMW South America 1:5M (2018) | basáltico 1,0 | 0 |
| craters-of-the-moon | Tierra | Quaternary volcanic: mafic rocks | Geologic Map of North America (Garrity y Soller) | basáltico 1,0 | 0 |
| payun-matru | Tierra | Quaternary Basaltic · basalt | CGMW South America 1:5M | basáltico 1,0 | 0 |
| campo-piedra-pomez | Tierra | Quaternary Rhyolitic · rhyolite | CGMW South America 1:5M | silícico 1,0 | 0 |
| lonar | Tierra | Mesozoic–Cenozoic volcanic rocks · flood basalt (escala `tiny`: `small` no tiene unidad ahí) | Chorlton 2007, GSC OF 5529 | basáltico 1,0 | 1 (Osinski 2022) |
| meteor-crater | Tierra | Triassic sedimentary · «sedimentary» | Geologic Map of North America | **null** (no dice si es clástico o químico) | 1 (Osinski 2022, «Barringer») |
| marius-hills | Luna | EIp, meseta volcánica | Unified Geologic Map of the Moon | basáltico 1,0 | 0 |
| shackleton-rim | Luna | Ec, cráter eratosteniano | Unified Geologic Map of the Moon | **null** | 1 |
| pavonis-mons | Marte | Ave, edificio volcánico amazónico | SIM 3292 | basáltico 1,0 | **null** |
| arsia-mons | Marte | Ave | SIM 3292 | basáltico 1,0 | **null** |
| jezero | Marte | HNt, unidad de transición | SIM 3292 | **null** | **null** |
| gale | Marte | AHi, unidad de impacto | SIM 3292 | **null** | 1 |

### Validaciones contra lo publicado (en `services/earth/tests/test_g_piloto.py`)

- Pali Aike → basáltico. D'Orazio et al. 2000 (Tectonophysics 321:407–427) describen basaltos alcalinos y basanitas.
- Lonar y Meteor Crater → impacto 1. Los dos están en la tabla de Osinski et al. 2022 (Lonar con blanco «Crystalline», Barringer con «Sedimentary»). En esa tabla Lonar figura en «19.58, 76.31», que parece 19°58′ / 76°31′ escrito como decimal; el cruce se hace por nombre y no por coordenada.
- Pavonis y Arsia → unidad volcánica Ave (Tanaka et al. 2014).
- Gale → AHi. Con unos 150 km de diámetro, sí entra en la escala 1:20M.
- Marius Hills → unidad volcánica EIp. Coincide con el LROC Lunar Pits Atlas, que ya usa el catálogo.

### Qué quedó null y por qué

- Composición de **meteor-crater**: el mapa dice sólo «sedimentary».
- Composición de **shackleton-rim** y **gale**: son unidades de impacto; el mapa no da la roca. A completar con un producto composicional (fase 2).
- Composición de **jezero** e impacto de **jezero**, **pavonis-mons** y **arsia-mons**: SIM 3292 es morfoestratigráfico y no resuelve cráteres chicos.

### Corrida en seco sobre los 74 sitios (no cargada; para dimensionar)

- Tierra: composición en **36/60**. Los 24 nulos son sobre todo «sedimentary» o «volcanic» genéricos (Dallol, Erta Ale, Badwater, White Sands, Karijini, Wolfe Creek, Vredefort, las bases antárticas…). Macrostrat marca por su cuenta «Impact structure» en Popigai y Haughton.
- Luna: composición en **1/8** (Marius Hills); impacto en **8/8**.
- Marte: composición en **2/6** (Pavonis, Arsia); impacto en **1/6** (Gale).
- Conclusión: en los destinos, los mapas hablan sobre todo de **proceso** (impacto o volcanismo) y poco de **roca**. Lo que más vale ahora es el eje de impacto; la composición de los polos lunares y de Marte pide la fase 2.

## 6. S_G propuesto (requiere OK del usuario; no está en `tasi.py`)

El coseno actual no sirve para este vector, por tres motivos:

1. Con vectores one-hot da 0 o 1 sin términos medios.
2. Descarta los `None` posición por posición, así que deja de ser la misma definición en los dos lados.
3. Un vector con una sola dimensión compartida siempre da coseno 1.

Propuesta: comparar por bloques y sólo con los que tengan dato en los dos lados.

```
S_comp = Σ_i min(a_i, b_i)        (Ruzicka sobre fracciones que suman 1; 1 = misma mezcla)
S_imp  = 1 − |a_imp − b_imp|
S_G    = promedio de los bloques disponibles en ambos lados; null si no hay ninguno
cobertura_G = bloques usados / 2   (se reporta como la cobertura de TASI)
```

Cableado necesario (también requiere OK): que `rank()` arme el G del candidato desde `features` (`g_*`) en lugar de `{"score_ready": False}`, y que `vector.py` exponga las `g_*` de los destinos como `metrics` de G.

Matriz ilustrativa con los datos del piloto (S_G y bloques usados):

| Tierra \ destino | marius-hills | shackleton-rim | pavonis-mons | arsia-mons | jezero | gale |
|---|---|---|---|---|---|---|
| pali-aike | 1,00 (2/2) | 0,00 (1/2) | 1,00 (1/2) | 1,00 (1/2) | — | 0,00 (1/2) |
| craters-of-the-moon | 1,00 (2/2) | 0,00 (1/2) | 1,00 (1/2) | 1,00 (1/2) | — | 0,00 (1/2) |
| payun-matru | 1,00 (2/2) | 0,00 (1/2) | 1,00 (1/2) | 1,00 (1/2) | — | 0,00 (1/2) |
| campo-piedra-pomez | 0,50 (2/2) | 0,00 (1/2) | 0,00 (1/2) | 0,00 (1/2) | — | 0,00 (1/2) |
| lonar | 0,50 (2/2) | 1,00 (1/2) | 1,00 (1/2) | 1,00 (1/2) | — | 1,00 (1/2) |
| meteor-crater | 0,00 (1/2) | 1,00 (1/2) | — | — | — | 1,00 (1/2) |

Se lee así: Lonar frente a Marius Hills da 0,5 porque coincide la roca (basalto) y no el proceso (impacto frente a volcanismo). Lonar frente a Shackleton da 1,0, pero con un solo bloque: sabemos que los dos son cráteres y no sabemos si la roca se parece. La cobertura tiene que verse en la interfaz.

Riesgo a vigilar: con cobertura 1/2, S_G puede valer 1,0 con poca evidencia. Opciones (decide el usuario): (i) dejarlo y mostrar la cobertura; (ii) multiplicar S_G por la cobertura; (iii) exigir los 2 bloques para puntuar.

## 7. Dudas para el usuario

1. ¿Aprobás el camino categórico como G v0 y la fórmula de S_G de §6 (con cuál de las tres opciones de cobertura)?
2. ¿Corro el script sobre los 74 sitios en otro PR (sigue siendo `derived`, mismas reglas)?
3. Las features `g_*` valen para Tierra, Luna y Marte, pero `features.json` admite un solo `service` por id; las declaré con `"service": "earth"`. ¿Lo dejamos así o el orquestador prefiere otra convención?
4. ¿Sumamos clases «sedimentario indiviso» y «volcánico indiviso» para no perder los 24 sitios terrestres con litología genérica (comparan peor, pero comparan)?
5. Fase 2: ¿invertimos en el eje TIR (Diviner / TES / ASTER GED) para darle composición a los polos lunares?
