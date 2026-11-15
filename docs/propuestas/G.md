# Geological comparison: categorical G v0

**Implemented November 15, 2026.** The active method in `services/earth/geology.py` compares sourced geological map categories and reports coverage. The ingestion pipeline covers 74 sites: 60 on Earth, seven on the Moon, and seven on Mars. This guide documents the implemented method; it does not propose a replacement scoring formula.

## Representation and sources

A rock-type category and an impact-origin indicator provide a common representation across the three bodies. They are map interpretations, not measured mineral spectra.

| Body | Source | Sampling and limitations |
|---|---|---|
| Earth | [Macrostrat API v2](https://macrostrat.org/api), including its attributed underlying geological maps | Query the site coordinate at `scale=small`, then `scale=tiny` when necessary. Source lithology and map citation remain in each record. |
| Moon | [USGS Unified Geologic Map of the Moon](https://astrogeology.usgs.gov/search/map/unified_geologic_map_of_the_moon_1_5m_2020), Fortezzo, Spudis and Harrel 2020 | Geological unit at the site coordinate; 1:5 million scale. |
| Mars | [USGS Geologic Map of Mars, SIM 3292](https://pubs.usgs.gov/sim/3292/), Tanaka et al. 2014 | Geological unit at the site coordinate; 1:20 million scale. |
| Earth impact origin | [Impact Earth, Osinski et al. 2022](https://doi.org/10.1016/j.earscirev.2022.104112) | Confirmed-structure catalog matching, with its documented exceptions and limits. |

Macrostrat is a recognized external resource used because the official challenge list does not supply the required global terrestrial lithological point map. Its API and underlying map attribution must be retained. The [Macrostrat reference](https://doi.org/10.1029/2018GC007467) describes the resource. The volcanic-unit interpretation for Mars cites [McSween, Taylor and Wyatt 2009](https://doi.org/10.1126/science.1165871).

## Nine feature fields

The original field identifiers remain unchanged to preserve data contracts and measurement provenance.

| Feature | Meaning | Mapping rule |
|---|---|---|
| `g_lito_basaltico` | Mafic volcanic | Earth basalt/mafic terms; lunar mare and mapped volcanic units; mapped Martian volcanic units interpreted as basaltic using the cited reference. |
| `g_lito_silicico` | Intermediate to felsic volcanic | Earth andesite, dacite, rhyolite, trachyte, ignimbrite, and tuff terms. |
| `g_lito_clastico` | Clastic or unconsolidated sediment | Sandstone, shale, siltstone, conglomerate, siliciclastic, alluvium, and related terms. |
| `g_lito_quimico` | Carbonates and evaporites | Limestone, dolomite, carbonate, evaporite, gypsum, and halite terms. |
| `g_lito_cristalino` | Plutonic or metamorphic rock | Granite, gneiss, schist, plutonic, and metamorphic terms. |
| `g_lito_hielo` | Ice | Mapped ice/glacier lithology or the Martian `lApc` cap unit. |
| `g_lito_volc_indiviso` | Undivided volcanic | Generic volcanic terms when the map does not resolve a finer volcanic class. |
| `g_lito_sed_indiviso` | Undivided sedimentary | Generic sedimentary terms when the map does not resolve a finer sediment class. |
| `g_impacto` | Impact origin, 0 or 1 | Earth catalog matching; mapped lunar impact/mare origin; Martian `AHi` impact unit. Other Martian units retain null rather than implying no small crater exists. |

The eight composition fractions sum to one. Multiple recognized classes share equal fractions. Generic terms use the undivided class within their family rather than an invented finer classification. Unrecognized lithology, such as a unit described only as a lake, leaves the composition block null. Lunar highland/crater units and Martian morphostratigraphic units are not assigned a rock type when the map does not identify one.

Four composition families group the classes: volcanic, sedimentary, crystalline, and ice. The exact equivalence table is versioned in `services/earth/scripts/g_equivalencias.py`.

## Active S_G formula

For normalized class vectors `a` and `b`, and their corresponding family totals `A` and `B`:

```text
S_comp = 0.5 * sum(min(a_i, b_i)) + 0.5 * sum(min(A_f, B_f))
S_imp  = 1 - abs(a_imp - b_imp)
blocks = composition if available on both sides,
         impact if available on both sides
S_G    = mean(blocks), or null when no block can be compared
coverage = number of shared blocks / 2
```

**Do not multiply S_G by coverage.** The active implementation excludes missing blocks and reports evidence coverage separately. It does not treat missing information as zero or penalize it. This replaced the earlier unimplemented coverage-penalty proposal.

A score of 1 with one shared block carries less evidence than a score of 1 with both blocks. For example, an impact-origin match alone does not establish a rock-type match. Conversely, a valid zero is a genuine disagreement in an available block, not missing evidence.

Each composition block requires sourced, comparable fractions in [0, 1] that sum to one. The implementation rejects unsupported quality states, nonfinite values, explicit `is_real: false`, and `comparable: false`.

## Dataset coverage

`data/measurements/g-mapas.jsonl` contains **666 records**: 74 sites × nine fields, of which **556 are non-null**. Derived categories use `quality: derived`; unavailable values preserve null and a reason. The feature declarations use `"service": ["earth", "planetary"]` so definitions remain identical across bodies.

| Body | Sites with composition | Sites with impact indicator |
|---|---:|---:|
| Earth, 60 sites | 58 | 60 |
| Moon, seven sites | 1: Marius Hills | 7 |
| Mars, seven sites | 2: Pavonis and Arsia | 1: Gale |

Remaining gaps have explicit causes:

- Lake Natron is mapped as a lake; Popigai's impactite is not one of the composition classes. Their composition blocks remain null.
- Six polar lunar targets, Gale, and Martian morphostratigraphic units lack a map-derived rock composition in this representation.
- Jezero, Medusae Fossae, Meridiani, and Utopia have no shared categorical G block and therefore no G score. TASI renormalizes over the remaining available components.
- A coarse Martian map's failure to show a small crater is not evidence of its absence. Most Martian impact indicators remain null.
- An Earth impact value of zero records the implemented catalog classification, not a universal proof against a disputed impact hypothesis. Río Cuarto remains scientifically disputed.

## Validation and reproduction

Producer: `services/earth/scripts/ingest_g_mapas.py`, with `remote_zip.py` and `g_equivalencias.py`. Extra dependencies are declared in `services/earth/requirements-g.txt`. Download caches remain outside version control.

Published-reference checks in `services/earth/tests/test_g_mapas.py` cover basaltic Pali Aike, known impact structures, chemical deposits at Salar de Uyuni, volcanic `Ave` at Pavonis/Arsia, impact `AHi` at Gale, and volcanic `EIp` at Marius Hills. API integration preserves existing sourced non-null measurements and does not require a write to the shared demo database.

The map scales and categorical interpretation limit the result. No CRISM, M3, or EMIT spectra are claimed by this dataset, and no unverified spectral extension is part of the active method.

## Complete map-derived classification

Values below reproduce the versioned ingestion result. Class labels are translated for documentation; technical feature IDs and site IDs are unchanged. Source-unit descriptions retain their original wording.

| Site | Body | Composition | g_impacto | Source unit or lithology |
|---|---|---|---|---|
| campo-piedra-pomez | Earth | silicic 1 | 0 | Rhyolite (small) |
| laguna-negra | Earth | silicic 1 | 0 | Andesite and related volcanic (small) |
| payun-matru | Earth | basaltic 1 | 0 | basalt (small) |
| ischigualasto | Earth | clastic 1 | 0 | Siliciclastic (small) |
| laguna-antofagasta | Earth | basaltic 1 | 0 | basalt (small) |
| salar-de-uyuni | Earth | chemical 1 | 0 | Evaporite (small) |
| yungay-atacama | Earth | crystalline 1 | 0 | Granite (small) |
| valle-de-la-luna-chile | Earth | clastic 1 | 0 | Siliciclastic (small) |
| dallol | Earth | undivided volcanic 1 | 0 | volcanic (small) |
| erta-ale | Earth | undivided volcanic 1 | 0 | volcanic (small) |
| sossusvlei | Earth | undivided sedimentary 1 | 0 | sedimentary (small) |
| richat | Earth | undivided sedimentary 1 | 0 | sedimentary (small) |
| vredefort | Earth | undivided sedimentary 1 | 1 | sedimentary (karoo) (small) |
| tswaing | Earth | crystalline 1 | 1 | plutonic (small) |
| chott-el-djerid | Earth | chemical 1 | 0 | evaporites; sedimentary (small) |
| lake-natron | Earth | **null** | 0 | lake (small) |
| pico-do-fogo | Earth | basaltic 1 | 0 | mafic volcanic rocks (tiny) |
| da-qaidam | Earth | undivided sedimentary 1 | 0 | sedimentary rocks (tiny) |
| lut-desert | Earth | undivided sedimentary 1 | 0 | sedimentary rocks (tiny) |
| lonar | Earth | basaltic 1 | 1 | flood basalt(s); mafic volcanic rocks; basalt (tiny) |
| wadi-rum | Earth | clastic 1 | 0 | sandstone; sedimentary (small) |
| tso-kar | Earth | undivided sedimentary 1 | 0 | sedimentary rocks (tiny) |
| tolbachik | Earth | basaltic 1 | 0 | mafic volcanic rocks (tiny) |
| popigai | Earth | **null** | 1 | impact breccia, impact melt rock, crater fill;  (small) |
| rio-tinto | Earth | clastic 1 | 0 | Major:{conglomerate}, Minor{sand,mud} (small) |
| nordlinger-ries | Earth | crystalline 1 | 1 | miscellaneous metamorphic rock group (small) |
| askja | Earth | basaltic 1 | 0 | volcanic: mafic rocks; basalt group; basalt, olivine basalt, (small) |
| bockfjorden | Earth | clastic 0.5 + chemical 0.5 | 0 | sandstone; limestone, dolomite, shale, sandstone, quartzite, (small) |
| badwater | Earth | undivided sedimentary 1 | 0 | sedimentary (small) |
| meteor-crater | Earth | undivided sedimentary 1 | 1 | sedimentary (small) |
| haughton | Earth | undivided sedimentary 1 | 1 | sedimentary; impact breccia, impact melt rock, crater fill (small) |
| craters-of-the-moon | Earth | basaltic 1 | 0 | volcanic: mafic rocks (small) |
| lava-beds | Earth | basaltic 1 | 0 | volcanic: mafic rocks (small) |
| pinacate | Earth | basaltic 1 | 0 | volcanic: mafic rocks (small) |
| white-sands | Earth | undivided sedimentary 1 | 0 | sedimentary (small) |
| ubehebe | Earth | undivided sedimentary 1 | 0 | sedimentary (small) |
| kilauea | Earth | basaltic 1 | 0 | shield volcano(s); mafic volcanic rocks (tiny) |
| sp-crater | Earth | basaltic 1 | 0 | volcanic: mafic rocks (small) |
| mcgill-arctic | Earth | clastic 1 | 0 | sedimentary; sandstone, siltstone, shale; marine fossils (small) |
| valley-10000-smokes | Earth | basaltic 0.5 + silicic 0.5 | 0 | volcanic, andesite, basalt, rhyolite, minor dacite; volcanic (small) |
| undara | Earth | basaltic 1 | 0 | igneous mafic volcanic (small) |
| wolfe-creek | Earth | undivided sedimentary 1 | 1 | sedimentary (small) |
| karijini | Earth | undivided sedimentary 1 | 0 | sedimentary (small) |
| acraman | Earth | silicic 1 | 1 | igneous felsic volcanic (small) |
| university-valley | Earth | basaltic 1 | 0 | mafic volcanic rocks (tiny) |
| taylor-valley | Earth | crystalline 1 | 0 | intrusive igneous rocks (tiny) |
| devon-island-fmars | Earth | clastic 0.5 + chemical 0.5 | 1 | limestone, dolostone, shale, evaporites, chalk; carbonate re (small) |
| timanfaya | Earth | basaltic 1 | 0 | volcanic; basalt (small) |
| teide | Earth | silicic 1 | 0 | trachyte; volcanic (small) |
| mauna-kea | Earth | basaltic 1 | 0 | shield volcano(s); mafic volcanic rocks (tiny) |
| laguna-diamante | Earth | clastic 1 | 0 | Siliciclastic (small) |
| socompa | Earth | undivided volcanic 1 | 0 | Volcaniclastic, volcanic (small) |
| meseta-de-somuncura | Earth | undivided volcanic 1 | 0 | Volcanic (small) |
| pali-aike | Earth | basaltic 1 | 0 | basalt (small) |
| campo-del-cielo | Earth | clastic 1 | 1 | Siliciclastic (small) |
| crateres-rio-cuarto | Earth | clastic 1 | 0 | Siliciclastic (small) |
| dunas-de-taton | Earth | crystalline 1 | 0 | Medium to high grade metamorphic (small) |
| llullaillaco | Earth | basaltic 1 | 0 | basalt (small) |
| base-marambio | Earth | undivided sedimentary 1 | 0 | sedimentary rocks (tiny) |
| base-esperanza | Earth | undivided sedimentary 1 | 0 | sedimentary rocks (tiny) |
| jezero | Mars | **null** | **null** | HNt |
| gale | Mars | **null** | 1 | AHi |
| medusae-fossae | Mars | **null** | **null** | AHtu |
| pavonis-mons | Mars | basaltic 1 | **null** | Ave |
| meridiani | Mars | **null** | **null** | HNhu |
| shackleton-rim | Moon | **null** | 1 | Ec |
| haworth | Moon | **null** | 1 | pNc |
| malapert | Moon | **null** | 1 | Ip |
| de-gerlache | Moon | **null** | 1 | Ec |
| amundsen | Moon | **null** | 1 | Nc |
| nobile | Moon | **null** | 1 | pNc |
| marius-hills | Moon | basaltic 1 | 0 | EIp |
| utopia-planitia | Mars | **null** | **null** | lHl |
| arsia-mons | Mars | basaltic 1 | **null** | Ave |
