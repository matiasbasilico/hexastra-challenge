# Propuesta G — geología, mineralogía y materiales

Agente G, 14 nov 2026. Estado: **G v0 categórico cargado para los 74 sitios** (`data/measurements/g-mapas.jsonl`). No cambia `services/earth/tasi.py`: la fórmula de S_G (§6) y su cableado siguen necesitando el OK del usuario.

Decisiones del usuario (14 nov): correr los 74 sitios en este mismo PR; que las features `g_*` sirvan para los tres cuerpos; sumar las clases «volcánico indiviso» y «sedimentario indiviso»; avanzar con la fase 2 (eje composicional en el infrarrojo térmico).

## 1. El problema

Hoy G está vacío. `tasi.py` sólo acepta un coseno entre espectros reales (`s_spectral`) y, además, `rank()` le pasa al sitio terrestre `{"score_ready": False}` fijo, así que S_G nunca puede salir aunque se carguen datos. Hace falta:

1. una representación de G que signifique lo mismo en la Tierra, la Luna y Marte;
2. fuentes oficiales o reconocidas que la llenen para nuestros 74 sitios (60 terrestres + 7 lunares + 7 marcianos);
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
- Luna con M3: 6 de los 7 destinos lunares son polares (Shackleton, Haworth, Malapert, de Gerlache, Amundsen, Nobile). Ahí la iluminación es rasante y hay sombra permanente, justo donde el espectro VSWIR es menos confiable. Sólo Marius Hills es ecuatorial.
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

### Representación propuesta: vector G de 9 componentes

| Feature | Qué es | Tierra (palabra clave en `lith`) | Luna (unidad DOMU) | Marte (unidad SIM 3292) |
|---|---|---|---|---|
| `g_lito_basaltico` | volcánico máfico | basalt, mafic volcanic, basanite | mare Em, Im1, Im2, Imd, EIp; manto oscuro Id (piroclástico) | volcánicas Av, Ave, lAv, lAvf, AHv, eHv, lHv, lHvf, Hve, Nve, lNv → basálticas por McSween et al. 2009 (doi:10.1126/science.1165871) |
| `g_lito_silicico` | volcánico intermedio a félsico | andesite, dacite, rhyolite, trachyte, ignimbrite, tuff | — | — |
| `g_lito_clastico` | sedimentario clástico o no consolidado | sandstone, shale, siltstone, conglomerate, siliciclastic, alluvium, sand… | — | — (los médanos lApd quedan para la v1) |
| `g_lito_quimico` | carbonatos y evaporitas | limestone, dolomite, carbonate, evaporite, gypsum, halite | — | — |
| `g_lito_cristalino` | plutónico o metamórfico | granite, gneiss, schist, plutonic, metamorphic | — | — |
| `g_lito_hielo` | hielo | ice, glacier | — | casquete lApc |
| `g_lito_volc_indiviso` | volcánico sin composición en el mapa | volcanic, volcaniclastic, volcano-sedimentary (sólo si no hay una clase volcánica fina) | — | — |
| `g_lito_sed_indiviso` | sedimentario sin tipo en el mapa | sedimentary (sólo si no hay una clase sedimentaria fina) | — | — |
| `g_impacto` | origen por impacto (0/1) | 1 si figura en la tabla de Osinski et al. 2022 | 1 en cráteres, cuencas, formaciones de eyecta y terras/planicies (la DOMU las interpreta como «megaregolito; eyecta de cráteres y cuencas»); 0 en mare | 1 en AHi; **null** en el resto (un cráter de menos de ~100 km no se ve a 1:20M; que no esté en el mapa no quiere decir 0) |

Las ocho fracciones de composición suman 1. Si el texto de litología trae varias clases, se reparte en partes iguales. Un término genérico (`sedimentary` a secas, `volcanic` sin más) va a la clase **indivisa** de su familia: no se adivina si es clástico o químico, pero tampoco se pierde que es sedimentario. Las clases se agrupan en cuatro familias (volcánica, sedimentaria, cristalina, hielo) para dar crédito parcial en S_G. Si no aparece ninguna palabra clave (p. ej. «lake»), la composición queda **null** con «a completar». Tampoco se completa la composición de cráteres y terras lunares ni de las unidades morfoestratigráficas de Marte: el mapa las define por su origen y no por su roca.

**Defensa ante el jurado:** media-alta. Cada valor sale de un mapa publicado y de una regla escrita (`services/earth/scripts/g_equivalencias.py`), y cada fila cita la unidad leída. La tabla sigue la idea de *análogo funcional* de Foucher et al. 2021 (Planet. Space Sci. 197:105162, doi:10.1016/j.pss.2021.105162): se compara la propiedad que importa para un uso concreto (aquí, tipo de roca y proceso de formación) y no la composición total. El punto débil está a la vista y conviene mostrarlo: la escala de los mapas (1:5M y 1:20M) y que en Marte muchas unidades no tienen litología.

**Esfuerzo:** ya está hecho para los 74 sitios (`services/earth/scripts/ingest_g_mapas.py`, unos minutos; las descargas quedan en `~/.cache/hexastra/g`).

## 4. Recomendación

**Camino (b), categórico, como G v0 para el MVP**, y el espectral en una fase 2 acotada.

Por qué:

1. Cubre los 74 sitios con un dato trazable (la corrida en seco de abajo lo confirma) y no depende de cubos de GB ni de iluminación polar.
2. Encaja con la regla de «decir qué se parece y qué no»: el vector separa composición e impacto, y un nulo dice por qué falta.
3. El espectral, con los destinos que tenemos (6 de 7 lunares polares), entrega poco y cuesta mucho antes de la entrega.

Para la fase 2 propongo un eje composicional que llene justo lo que falta en los destinos, y que hay que evaluar antes de usarlo: un índice de sílice por la posición del rasgo de Christiansen en el infrarrojo térmico, con Diviner en la Luna (producto global en PDS), TES/THEMIS en Marte y ASTER GED en la Tierra (global, 100 m, por AppEEARS). Ojo: la posición del rasgo cambia entre el vacío y la atmósfera, y hay que documentar la corrección antes de comparar. Las referencias concretas de la fase 2 quedan **a verificar**.

## 5. Carga completa (74 sitios, `g-mapas.jsonl`)

Script: `services/earth/scripts/ingest_g_mapas.py` (más `remote_zip.py` y `g_equivalencias.py`). Dependencia extra: `pyshp` (`services/earth/requirements-g.txt`). Calidad `derived` (clase derivada de un mapa publicado con una regla documentada); los nulos van como `unavailable`. Son 666 filas: 74 sitios × 9 features. Las features se declaran con `"service": ["earth", "planetary"]` (cambio chico en `db/build.py`, con test) para usar la misma definición en los tres cuerpos.

**Cobertura**

| | Composición | Impacto |
|---|---|---|
| Tierra (60) | 58 | 60 |
| Luna (7) | 1 (Marius Hills) | 7 |
| Marte (7) | 2 (Pavonis, Arsia) | 1 (Gale) |

En la Tierra, el impacto vale 1 en los 11 sitios que están dentro de una estructura de la tabla de Osinski et al. 2022: Lonar, Meteor Crater (Barringer), Vredefort, Tswaing, Popigai, Ries, Haughton, Devon/FMARS (a 6,9 km del centro de Haughton, dentro del radio de ~11,5 km), Wolfe Creek, Acraman y Campo del Cielo (Tabla 3: cráter sin metamorfismo de choque). En los otros 49 vale 0. Río Cuarto queda en 0 porque no está en esa tabla.

**Qué quedó null y por qué**

- Composición de **lake-natron** («lake» no es una litología) y de **popigai** (el mapa dice impactita, que no es una de nuestras clases; su impacto sí es 1).
- Composición de los **6 destinos lunares polares**, de **gale** y de las unidades morfoestratigráficas de Marte (**jezero, medusae-fossae, meridiani, utopia-planitia**): el mapa define la unidad por su origen o su terreno, no por su roca. A completar en la fase 2.
- Impacto de **jezero, medusae-fossae, pavonis-mons, meridiani, utopia-planitia y arsia-mons**: a 1:20M no se mapean cráteres chicos, y que no estén en el mapa no quiere decir 0.

**Validaciones contra lo publicado** (`services/earth/tests/test_g_mapas.py`)

- Pali Aike → basáltico (D'Orazio et al. 2000, Tectonophysics 321:407: basaltos alcalinos y basanitas).
- Lonar, Meteor Crater, Vredefort, Ries y Haughton → impacto 1; Río Cuarto → 0 (Osinski et al. 2022). En esa tabla las coordenadas parecen grados-minutos escritos como decimal (Lonar «19.58, 76.31»), así que el cruce se hace por nombre.
- Salar de Uyuni → químico (CGMW, «Quaternary Evaporitic»).
- Pavonis y Arsia → unidad volcánica Ave; Gale → AHi (Tanaka et al. 2014).
- Marius Hills → meseta volcánica EIp (DOMU lunar).

**Tabla completa**

| Sitio | Cuerpo | Composición | g_impacto | Unidad o litología leída |
|---|---|---|---|---|
| campo-piedra-pomez | Tierra | silicico 1 | 0 | Rhyolite (small) |
| laguna-negra | Tierra | silicico 1 | 0 | Andesite and related volcanic (small) |
| payun-matru | Tierra | basaltico 1 | 0 | basalt (small) |
| ischigualasto | Tierra | clastico 1 | 0 | Siliciclastic (small) |
| laguna-antofagasta | Tierra | basaltico 1 | 0 | basalt (small) |
| salar-de-uyuni | Tierra | quimico 1 | 0 | Evaporite (small) |
| yungay-atacama | Tierra | cristalino 1 | 0 | Granite (small) |
| valle-de-la-luna-chile | Tierra | clastico 1 | 0 | Siliciclastic (small) |
| dallol | Tierra | volc_indiviso 1 | 0 | volcanic (small) |
| erta-ale | Tierra | volc_indiviso 1 | 0 | volcanic (small) |
| sossusvlei | Tierra | sed_indiviso 1 | 0 | sedimentary (small) |
| richat | Tierra | sed_indiviso 1 | 0 | sedimentary (small) |
| vredefort | Tierra | sed_indiviso 1 | 1 | sedimentary (karoo) (small) |
| tswaing | Tierra | cristalino 1 | 1 | plutonic (small) |
| chott-el-djerid | Tierra | quimico 1 | 0 | evaporites; sedimentary (small) |
| lake-natron | Tierra | **null** | 0 | lake (small) |
| pico-do-fogo | Tierra | basaltico 1 | 0 | mafic volcanic rocks (tiny) |
| da-qaidam | Tierra | sed_indiviso 1 | 0 | sedimentary rocks (tiny) |
| lut-desert | Tierra | sed_indiviso 1 | 0 | sedimentary rocks (tiny) |
| lonar | Tierra | basaltico 1 | 1 | flood basalt(s); mafic volcanic rocks; basalt (tiny) |
| wadi-rum | Tierra | clastico 1 | 0 | sandstone; sedimentary (small) |
| tso-kar | Tierra | sed_indiviso 1 | 0 | sedimentary rocks (tiny) |
| tolbachik | Tierra | basaltico 1 | 0 | mafic volcanic rocks (tiny) |
| popigai | Tierra | **null** | 1 | impact breccia, impact melt rock, crater fill;  (small) |
| rio-tinto | Tierra | clastico 1 | 0 | Major:{conglomerate}, Minor{sand,mud} (small) |
| nordlinger-ries | Tierra | cristalino 1 | 1 | miscellaneous metamorphic rock group (small) |
| askja | Tierra | basaltico 1 | 0 | volcanic: mafic rocks; basalt group; basalt, olivine basalt, (small) |
| bockfjorden | Tierra | clastico 0,5 + quimico 0,5 | 0 | sandstone; limestone, dolomite, shale, sandstone, quartzite, (small) |
| badwater | Tierra | sed_indiviso 1 | 0 | sedimentary (small) |
| meteor-crater | Tierra | sed_indiviso 1 | 1 | sedimentary (small) |
| haughton | Tierra | sed_indiviso 1 | 1 | sedimentary; impact breccia, impact melt rock, crater fill (small) |
| craters-of-the-moon | Tierra | basaltico 1 | 0 | volcanic: mafic rocks (small) |
| lava-beds | Tierra | basaltico 1 | 0 | volcanic: mafic rocks (small) |
| pinacate | Tierra | basaltico 1 | 0 | volcanic: mafic rocks (small) |
| white-sands | Tierra | sed_indiviso 1 | 0 | sedimentary (small) |
| ubehebe | Tierra | sed_indiviso 1 | 0 | sedimentary (small) |
| kilauea | Tierra | basaltico 1 | 0 | shield volcano(s); mafic volcanic rocks (tiny) |
| sp-crater | Tierra | basaltico 1 | 0 | volcanic: mafic rocks (small) |
| mcgill-arctic | Tierra | clastico 1 | 0 | sedimentary; sandstone, siltstone, shale; marine fossils (small) |
| valley-10000-smokes | Tierra | basaltico 0,5 + silicico 0,5 | 0 | volcanic, andesite, basalt, rhyolite, minor dacite; volcanic (small) |
| undara | Tierra | basaltico 1 | 0 | igneous mafic volcanic (small) |
| wolfe-creek | Tierra | sed_indiviso 1 | 1 | sedimentary (small) |
| karijini | Tierra | sed_indiviso 1 | 0 | sedimentary (small) |
| acraman | Tierra | silicico 1 | 1 | igneous felsic volcanic (small) |
| university-valley | Tierra | basaltico 1 | 0 | mafic volcanic rocks (tiny) |
| taylor-valley | Tierra | cristalino 1 | 0 | intrusive igneous rocks (tiny) |
| devon-island-fmars | Tierra | clastico 0,5 + quimico 0,5 | 1 | limestone, dolostone, shale, evaporites, chalk; carbonate re (small) |
| timanfaya | Tierra | basaltico 1 | 0 | volcanic; basalt (small) |
| teide | Tierra | silicico 1 | 0 | trachyte; volcanic (small) |
| mauna-kea | Tierra | basaltico 1 | 0 | shield volcano(s); mafic volcanic rocks (tiny) |
| laguna-diamante | Tierra | clastico 1 | 0 | Siliciclastic (small) |
| socompa | Tierra | volc_indiviso 1 | 0 | Volcaniclastic, volcanic (small) |
| meseta-de-somuncura | Tierra | volc_indiviso 1 | 0 | Volcanic (small) |
| pali-aike | Tierra | basaltico 1 | 0 | basalt (small) |
| campo-del-cielo | Tierra | clastico 1 | 1 | Siliciclastic (small) |
| crateres-rio-cuarto | Tierra | clastico 1 | 0 | Siliciclastic (small) |
| dunas-de-taton | Tierra | cristalino 1 | 0 | Medium to high grade metamorphic (small) |
| llullaillaco | Tierra | basaltico 1 | 0 | basalt (small) |
| base-marambio | Tierra | sed_indiviso 1 | 0 | sedimentary rocks (tiny) |
| base-esperanza | Tierra | sed_indiviso 1 | 0 | sedimentary rocks (tiny) |
| jezero | Marte | **null** | **null** | HNt |
| gale | Marte | **null** | 1 | AHi |
| medusae-fossae | Marte | **null** | **null** | AHtu |
| pavonis-mons | Marte | basaltico 1 | **null** | Ave |
| meridiani | Marte | **null** | **null** | HNhu |
| shackleton-rim | Luna | **null** | 1 | Ec |
| haworth | Luna | **null** | 1 | pNc |
| malapert | Luna | **null** | 1 | Ip |
| de-gerlache | Luna | **null** | 1 | Ec |
| amundsen | Luna | **null** | 1 | Nc |
| nobile | Luna | **null** | 1 | pNc |
| marius-hills | Luna | basaltico 1 | 0 | EIp |
| utopia-planitia | Marte | **null** | **null** | lHl |
| arsia-mons | Marte | basaltico 1 | **null** | Ave |

## 6. S_G propuesto (requiere OK del usuario; no está en `tasi.py`)

### En simple

S_G responde «¿qué tan parecida es la geología del sitio terrestre a la del destino?» con un número de 0 a 1. Miramos dos cosas por separado:

1. **¿Es la misma roca?** (bloque de composición). Basalto contra basalto da 1; basalto contra arenisca da 0; basalto contra «volcánico sin detalle» da 0,5, porque sabemos que los dos son volcánicos pero no si el segundo es basalto.
2. **¿Se formó igual?** (bloque de impacto). Cráter contra cráter da 1; cráter contra colada de lava da 0.

S_G es el promedio de los bloques que se pueden comparar. **Si falta el dato de un lado, ese bloque no entra**: no se inventa.

El problema aparece cuando sólo se puede comparar un bloque. Ejemplo real: Lonar (cráter en basalto) contra Shackleton (cráter lunar). Del lado lunar no sabemos la roca, así que sólo comparamos «¿los dos son cráteres?». La respuesta es sí y S_G da 1,0. Pero ese 1,0 vale menos que el 1,0 de Payún Matrú contra Marius Hills, donde coinciden la roca **y** el origen. Por eso hay que decidir qué hacer con la «cobertura» (cuántos de los 2 bloques se usaron):

| Opción | Lonar vs Shackleton (1 bloque) | Payún vs Marius Hills (2 bloques) | Efecto |
|---|---|---|---|
| (i) Mostrar la cobertura y no tocar el número | 1,0 «1/2» | 1,0 «2/2» | Simple; la interfaz tiene que mostrar «1/2» al lado del número |
| (ii) Multiplicar por la cobertura | 0,5 | 1,0 | Castiga la falta de dato; en el ranking pesa más lo bien documentado |
| (iii) Exigir los dos bloques | sin S_G | 1,0 | Lo más estricto; hoy sólo Marius Hills tendría S_G |

**Mi recomendación es (ii):** es honesta (menos evidencia, menos puntaje), no deja a 13 de los 14 destinos sin G y se explica en una línea. Cuando la fase 2 complete la composición de los destinos, la cobertura sube sola.

### Fórmula

```
familia(x) = suma de las fracciones de x por familia (volcánica, sedimentaria, cristalina, hielo)
S_comp = ½ · Σ_clases min(a_i, b_i) + ½ · Σ_familias min(A_f, B_f)
S_imp  = 1 − |a_imp − b_imp|
bloques = {S_comp si los dos lados tienen composición, S_imp si los dos tienen impacto}
S_G    = promedio(bloques) · (|bloques| / 2)        ← opción (ii); null si no hay bloques
```

Cableado necesario (también requiere OK): que `rank()` arme el G del candidato desde `features` (`g_*`) en lugar de `{"score_ready": False}`, y que `vector.py` exponga las `g_*` de los destinos como `metrics` de G.

### Ejemplo con los datos cargados (S_G sin multiplicar por la cobertura · bloques usados)

| Tierra \ destino | marius-hills | shackleton-rim | pavonis-mons | gale |
|---|---|---|---|---|
| pali-aike (basalto) | 1,00 · 2/2 | 0,00 · 1/2 | 1,00 · 1/2 | 0,00 · 1/2 |
| lonar (cráter en basalto) | 0,50 · 2/2 | 1,00 · 1/2 | 1,00 · 1/2 | 1,00 · 1/2 |
| dallol (volcánico indiviso) | 0,75 · 2/2 | 0,00 · 1/2 | 0,50 · 1/2 | 0,00 · 1/2 |
| meteor-crater (cráter en sedimentario) | 0,00 · 2/2 | 1,00 · 1/2 | 0,00 · 1/2 | 1,00 · 1/2 |
| salar-de-uyuni (evaporitas) | 0,50 · 2/2 | 0,00 · 1/2 | 0,00 · 1/2 | 0,00 · 1/2 |

Hoy sólo Marius Hills tiene los dos bloques contra casi todos los sitios terrestres (58 de 60). Jezero, Medusae Fossae, Meridiani y Utopia no tienen ningún bloque comparable: G queda sin puntaje y TASI renormaliza sobre T, E y Vo, como corresponde.

## 7. Pendiente de decisión

1. Opción de cobertura para S_G: (i), (ii) o (iii). Recomiendo (ii).
2. Con eso aprobado, implementar el cableado en `tasi.py` / `vector.py` (otro PR).
