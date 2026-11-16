# HexAstra — Earth analogs for the Moon and Mars

HexAstra connects **60 Earth sites** with **14 lunar and Martian destinations**, using open data and a transparent, multidimensional similarity index. Built by Team HexAstra in Buenos Aires for the [2026 NASA Space Apps Challenge](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/).

- **Explore:** https://hexastra.pages.dev/
- **Advanced mode:** https://hexastra.pages.dev/classic.html?mode=advanced
- **Team:** https://www.spaceappschallenge.org/2026/find-a-team/hexastra/
- **Challenge:** https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/

The application supports English and Rioplatense Spanish. The browser language selects the initial interface; the language selector saves a manual preference. Use `?lang=en` or `?lang=es` for a reproducible language-specific link. Repository documentation is in English. Site names, dataset identifiers, API field names, source quotations, and existing file paths retain their original spelling.

## Team

Team members, preserving the current list on `main`:

- Matias Basilico
- Juan Martín Verna
- Marcela Gutiérrez
- Nicole Arias
- Nicolás Castillo
- Kevin Agustin Ruiz

## What it does

Before testing technology on the Moon or Mars, mission teams need to choose where to test it on Earth. HexAstra helps narrow that search and explain the tradeoffs. It goes beyond visual resemblance: each comparison shows what matches, what differs, which measurements support it, and what evidence is missing.

The catalog includes deserts, salt flats, volcanic fields, impact structures, polar environments, and lava tubes worldwide. Argentine sites receive particular attention. Well-known analogs such as Atacama, Haughton, Hawaii, and the McMurdo Dry Valleys provide baselines; their inclusion is not presented as a new discovery.

**TASI (Terrestrial Analog Similarity Index) is the team's proposed index, not an official NASA index or a mission-suitability certification.** Missing evidence remains missing. Scores use only comparable information and report coverage.

## Explore the application

### Immersive mode

The home page opens with a full 3D Earth and a first-visit introduction. No mission is applied until the user completes the three steps:

1. Choose a celestial body: Mars or the Moon, using textured planet cards.
2. Choose a destination and read its terrain, coordinates, and dated exploration context.
3. Choose a comparison focus: balanced, terrain, extreme climate, or robot testing. Region and masking controls are available within this step.

Launching a mission centers the globe on the highest-ranked valid match and opens its comparison. Up to five sites with the highest positive TASI scores pulse; this is a relative ranking, not a threshold proving a strong analogy. A temporary hint explains how to select another point.

Selecting a point shows Earth and its destination together, with both positions marked, a score, coverage, similarities, differences, measurements, and sources. Controls and comparison panels float over the globe. Desktop and mobile layouts fit the viewport; long comparison details scroll within their panel.

The globe rotates at Earth's sidereal rate, approximately **23.9345 hours per revolution**. Rotation pauses during interaction and mission/comparison workflows, and respects reduced-motion preferences. It is an illustrative animation, not a representation of Earth's current astronomical orientation or lighting. Without WebGL, the Earth view falls back to Leaflet.

The project panel provides access to the 2D Earth view and the classic interface. The globe textures are illustrations and never contribute to TASI; see [visual credits](assets/globe/CREDITS.md).

### Advanced mode

Open the [advanced interface](https://hexastra.pages.dev/classic.html?mode=advanced) directly to compare Earth and the destination in two 2D maps. Choose a target, adjust dimension weights, filter by region, change map layers, and inspect the score and sources. The classic interface also retains its guided mode and published literature examples.

Earth map layers provide different visual contexts:

| Layer | What it helps inspect | Interpretation |
|---|---|---|
| Esri satellite imagery | Surface appearance, landforms, surrounding landscape | Visual context; not a numeric terrain measurement |
| OpenStreetMap | Roads, settlements, access | Map context; separate from planetary similarity |
| NASA GIBS MODIS imagery | Regional vegetation, snow, and landscape patterns | Satellite imagery; dates and resolution matter |
| NASA GIBS land-surface temperature | Regional surface thermal patterns | Surface temperature; not equivalent to air temperature |

Planetary basemaps include OpenPlanetaryMap and WhereOnMars relief imagery. Changing a displayed layer does not recalculate TASI: numeric features come from the APIs and their documented products.

## Run locally

Python 3.9 or later is required. From the repository root:

```bash
chmod +x run_all.sh
./run_all.sh
```

The launcher creates `services/.venv` when needed and starts:

| Component | URL |
|---|---|
| Frontend | http://127.0.0.1:8765/ |
| Planetary API documentation | http://127.0.0.1:8766/docs |
| Earth API documentation | http://127.0.0.1:8767/docs |

Local service addresses can be overridden in the browser:

```js
localStorage.setItem("HEXASTRA_PLANETARY_URL", "http://127.0.0.1:8766");
localStorage.setItem("HEXASTRA_EARTH_URL", "http://127.0.0.1:8767");
```

Published pages use the same-origin proxies `/api/planetary` and `/api/earth` by default. Explicit share-link overrides accept only approved local or Cloudflare quick-tunnel hosts; a published page cannot be redirected to a local service through these parameters. See `js/config.js` and `js/api.js` for the connection contract.

To run the Docker setup:

```bash
docker compose up --build
```

To serve only the frontend:

```bash
python3 -m http.server 8765
```

Without the APIs, the illustrative Earth can remain visible, but the application reports unavailable catalogs and does not invent points or scores.

### Database and measurement files

PostgreSQL with PostGIS runs in the repository's `hexastra-db` container on `127.0.0.1:55432`. Authorized integration can rebuild a database from versioned base catalogs and `data/measurements/*.jsonl`:

```bash
docker compose up -d db
services/.venv/bin/python db/load.py
services/.venv/bin/python db/export.py
```

`db/load.py` rebuilds the selected database; these are integration commands, not steps to run against the shared demonstration database during a documentation review. Set `HEXASTRA_DATABASE_URL` to use PostgreSQL. Otherwise, the services read an exported `catalog.merged.json` snapshot when available, then the base catalog. `/health` reports `catalog_origin`.

The public demonstration runs entirely on Cloudflare using a versioned export of the verified reference APIs. It does not connect to a Mac, tunnel, or PostgreSQL instance. The Python reference services remain available for development and data updates. Geological and Earth-access supplements preserve existing non-null values and provenance. See [measurement format and integration rules](data/measurements/README.md).

### Rebuild the 3D renderer

The ready-to-serve bundle is versioned, so local startup and static deployment do not require Node.js. To modify the renderer:

```bash
npm ci
npm run build:globe
```

Sources: `js/globe.mjs` and `js/globe-data.mjs`. Output: `js/vendor/globe.bundle.js`, with the Three.js license alongside it.

### Validation

```bash
./services/run_tests.sh
```

To test each service separately:

```bash
services/.venv/bin/python -m pytest -q services/planetary/tests
services/.venv/bin/python -m pytest -q services/earth/tests
```

Do not collect both service suites in a single pytest invocation: the services deliberately use separate modules with names such as `main.py` and `catalog.py`.

Example requests:

```bash
curl -s http://127.0.0.1:8766/health
curl -s 'http://127.0.0.1:8766/sites?body=moon'
curl -s http://127.0.0.1:8766/sites/shackleton-rim/vector
curl -s http://127.0.0.1:8767/health
curl -s http://127.0.0.1:8767/regions
curl -s 'http://127.0.0.1:8767/candidates?continent=South%20America&country=AR'
```

For a ranking, first obtain a target vector from the planetary API, then submit it to `POST /tasi` on the Earth API. Its request accepts `target`, `weights`, `gamma`, `top`, `continent`, `country`, and `apply_mask`.

## Architecture and API

The frontend is static HTML, CSS, and JavaScript, with Three.js for the Earth globe and Leaflet for 2D maps. The development/reference backend has two independent FastAPI services with no shared Python imports. The public deployment uses the standalone Cloudflare runtime described below. The feature-vector contract is [`contracts/feature_vector.schema.json`](contracts/feature_vector.schema.json).

| Service | Method and route | Purpose |
|---|---|---|
| Planetary | `GET /health` | Local service health and catalog origin |
| Planetary | `GET /sources?live=true` | Optional live source checks |
| Planetary | `GET /features` | Feature definitions |
| Planetary | `GET /sites?body=moon` or `body=mars` | Target catalog |
| Planetary | `GET /sites/{id}` | Target details |
| Planetary | `GET /sites/{id}/vector` | TASI-ready target vector |
| Planetary | `GET /bodies` | Sourced physical reference values and analogy limits |
| Earth | `GET /health` | Local service health and catalog origin |
| Earth | `GET /regions` | Continents and ISO-3166 alpha-2 countries in the catalog |
| Earth | `GET /featured` | Catalog shortcuts and baseline analogs |
| Earth | `GET /examples` | Published literature pairs, narratives, and references |
| Earth | `GET /method` | Implemented method, presets, scales, covariance, and provenance |
| Earth | `GET /candidates?continent=&country=` | Candidates with optional region filters |
| Earth | `GET /candidates/{id}` | Measurements and sources for one Earth site |
| Earth | `POST /tasi` | Similarity ranking and per-component explanation |
| Earth | `GET /tasi?target_id=&...` | Ranking when `PLANETARY_URL` is configured |
| Both | `GET /docs` | Interactive OpenAPI documentation |

The frontend calls `getTargetVector(id)` followed by `rankAnalogs({ targetVector, ... })`. It also uses `getTargets`, `getRegions`, `getFeatured`, `getCandidates`, and `health` from `js/api.js`. The historical monolith under `api/` is deprecated and is not the active catalog or ranking service.

## TASI: the implemented method

The vector is **V = [G, T, E, Vo, O]**:

| Dimension | Meaning | Current implementation |
|---|---|---|
| G | Geology, mineralogy, and materials | Sourced geological map categories: composition and impact origin; not measured spectral mineralogy |
| T | Terrain and topography | Relative relief, slope, and roughness on a common sampling grid |
| E | Thermal environment and illumination | Shared temperature, diurnal range, and illumination metrics where available |
| Vo | Volatiles, water, and ice | Shared precipitation and a documented ice indicator where comparable |
| O | Operational constraints | Scores only with an equivalent metric on both bodies; Earth access information is available as context |

### Filtering, comparison, and aggregation

1. **Mask M(x).** With masking enabled, exclude an Earth candidate when `ndvi > 0.15` or `has_liquid_water = 1`. Unknown values do not exclude it; they generate availability flags. MODIS/AppEEARS mask measurements supplement the original catalog. See the [mask and ice methodology](docs/propuestas/vo-hielo.md).
2. **Terrain S_T.** Compute Mahalanobis distance over relative relief, slope, and roughness, then `S_T = exp(-gamma * D_M)`. Covariance uses the Ledoit–Wolf method. Absolute elevation is not substituted for local terrain similarity.
3. **Geology S_G.** Compare composition overlap at class and family levels, plus impact origin where both sides have it. Use the **mean of shared blocks**, and report block coverage separately. Missing blocks are neither zeros nor penalties. See the [implemented geological method](docs/propuestas/G.md). A spectral cosine is meaningful only when real comparable spectra exist; categorical map data are not presented as spectra.
4. **Environment S_E and volatiles S_V.** Average `exp(-abs(x-y)/scale)` over shared metrics. Scales come from the Earth catalog. Zero liquid precipitation on the Moon or Mars is an explicitly documented convention, not a rain-gauge measurement.
5. **Operations S_O.** Require an equivalent operational quantity on Earth and the target body. Terrestrial roads, airfields, and population do not provide a planetary counterpart. Their sourced values are shown as [campaign-planning context](docs/propuestas/practicidad.md).
6. **Aggregate.** `TASI = 100 * sum(w_k * S_k) / sum(w_k)` over available components. Report the score from 0 to 100, component details, and coverage. A valid score of zero is distinct from an unavailable score.

The vegetation/water mask is a configurable screening rule, not a universal definition of a useful analog. Users can remove it. Sites without a comparable score are hidden by the default visual filter; disabling that filter reveals them as smaller, subdued markers without a pulse.

### Evidence quality and limitations

- Values retain source, product/version, retrieval date, units, quality, and relevant comparability notes. Unverified values remain `null`.
- The shared terrain grid is 7 × 7 samples at 120 m. Lunar LOLA and Martian HRSC–MOLA products have different native resolutions; interpolating a 200 m DEM onto this grid does not create finer detail.
- Lunar surface temperature and Martian/Earth near-surface air temperature are different quantities. Their measurement context is retained in the source notes.
- Published-range midpoints are labeled `derived_from_published_range`, not presented as time-weighted measurements. For example, the Jezero reference derives from the published MEDA 209–225 K range.
- An ice-stability fraction is not proof of detected ice. Lunar PRP interpretation and planetary coverage limitations remain explicit. Unknown regions are not assigned zero ice.
- Geological maps are coarse: approximately 1:5 million for the Moon and 1:20 million for Mars. Many Martian units do not identify a rock type. Jezero, Medusae Fossae, Meridiani, and Utopia retain unavailable categorical G when no shared block exists.
- Earth cannot reproduce reduced gravity, the lunar vacuum, the thin Martian atmosphere, or their radiation environments. The app displays sourced physical reference values separately from similarity. Radiation quantities can differ in definition and context and are not site-specific risk measurements.
- Basemap colors, visual resemblance, and published analog narratives do not become numeric scores. Scores always come from the API's implemented method.

### Versioned measurement coverage

These are file-level counts as of **November 15, 2026**, not a claim that every quantity is comparable or displayed in every pair. Live catalog origin is reported by the APIs.

| File | Records | Non-null values | Content |
|---|---:|---:|---|
| `g-mapas.jsonl` | 666 | 556 | Geological map classes for 74 sites |
| `o-tierra.jsonl` | 240 | 232 | Earth roads, airfields, and population |
| `te-planetario.jsonl` | 72 | 67 | Planetary terrain and thermal features |
| `vo-hielo.jsonl` | 169 | 55 | Raw ice/permafrost products and indicator availability |
| `vo-mascara.jsonl` | 120 | 100 | MODIS vegetation and water screening |

## Catalog and coordinate conventions

The Earth catalog has 60 candidates. Featured baselines include University Valley, Haughton, Devon/FMARS, Timanfaya, Teide, Kīlauea, Mauna Kea, Yungay/Atacama, Campo de Piedra Pómez, Payún Matrú, Laguna Diamante, and Socompa. Literature examples connect Campo de Piedra Pómez–Medusae Fossae, Laguna Negra–Jezero, Payún Matrú–Pavonis Mons, Ischigualasto–Gale, and Laguna de Antofagasta–Jezero. These are documented examples, not independently validated new discoveries.

**Mars:** Jezero, Gale, Medusae Fossae, Pavonis Mons, Meridiani, Utopia Planitia/Viking 2, and Arsia Mons.

**Moon:** Marius Hills pit, Shackleton rim, Haworth, Malapert, de Gerlache, Amundsen, and Nobile.

Coordinate decisions remain in each site's `coord_source`:

- Jezero and Gale use rover landing coordinates from NASA Mars24, not crater centers. Different geographic meanings are not averaged together.
- Marius Hills uses the LROC Pits Atlas location, not the IAU center of the unrelated Marius crater.
- Utopia uses the Viking 2 landing position. Arsia Mons uses the Gazetteer's MDIM 2.1 coordinate network.
- Lunar IAU anchors represent named features. They are not claimed to be official centers of the 15 × 15 km candidate regions announced by NASA in 2022, or confirmed future landings.
- Shackleton's coordinate and mean rim elevation follow the cited LOLA publication; a rim-center coordinate is not a crater-floor measurement.
- Country and continent assignments use Natural Earth 50m point-in-polygon rules. Missing assignments remain missing. Antarctic bases without a matching polygon are not silently forced into Argentina's country filter.
- Wikipedia/Wikidata coordinate fallbacks are explicitly identified. Río Cuarto's impact origin remains disputed; map-derived impact classification is not a geological ruling on that debate.

See the [per-site source register](docs/resources/sources-by-site.csv) and the source fields in the catalogs and measurement files.

## Public deployment and API sharing

**Definitive public URL: https://hexastra.pages.dev/**

The website and its API run entirely on Cloudflare Pages and Pages Functions. The production configuration is `pages/wrangler.production.toml`; its project is `hexastra`. **No Mac, cloudflared tunnel, PostgreSQL server, or paid database is needed to use the published demo.**

| Resource | Public URL |
|---|---|
| Browser-selected language | https://hexastra.pages.dev/ |
| English interface | https://hexastra.pages.dev/?lang=en |
| Spanish interface | https://hexastra.pages.dev/?lang=es |
| Advanced mode in English | https://hexastra.pages.dev/classic.html?mode=advanced&lang=en |
| Earth API health | https://hexastra.pages.dev/api/earth/health |
| Planetary API health | https://hexastra.pages.dev/api/planetary/health |
| Earth API documentation | https://hexastra.pages.dev/api/earth/docs |
| Planetary API documentation | https://hexastra.pages.dev/api/planetary/docs |

### Standalone runtime

`pages/lib/standalone.mjs` serves the verified catalogs and computes rankings from the versioned data in `data/cloudflare/`. It preserves the reference TASI method:

- Published input values, source records, geological comparisons, and terrain Mahalanobis distances come from the Python reference APIs.
- Terrain gamma remains adjustable through `exp(-gamma * D_M)`.
- Environment/volatile scales are recomputed from the selected region, **before masking**, as in the Python engine.
- Weights are renormalized over available components; missing evidence is not treated as zero. Filtering, valid zero scores, coverage, and tie-breaking are preserved.
- Repeated source dictionaries are omitted from the ranking response to keep it small. Complete sourced measurements remain at the candidate and target-vector endpoints.
- The hosted demo accepts its 14 verified catalog vectors or their `target_id`. It rejects altered/custom vectors rather than silently applying a precomputed comparison to different inputs.

`/health` reports `catalog_origin: cloudflare_snapshot`, the export date, and `requires_local_services: false`. This is a dated, sourced catalog release, not an assertion that imagery or scientific measurements are being ingested live.

The runtime was checked against 60 captured Python API scenarios spanning all 14 targets, four presets, regional scales, gamma, masking, missing components, and zero weights. The fixtures are versioned in `pages/tests/fixtures/reference-parity.json`.

### Update the data and publish

Export from healthy reference APIs after reviewing the scientific data changes:

```bash
python3 scripts/export_pages_snapshot.py \
  --planetary-url http://127.0.0.1:8766 \
  --earth-url http://127.0.0.1:8767
./services/run_tests.sh
npx wrangler@3 login
./scripts/deploy_pages.sh main
```

The exporter performs read-only HTTP requests. It does not load, rebuild, or export the shared database. It writes the public catalog, source records, vectors, comparison evidence, and a SHA-256 manifest. Review a changed snapshot and capture independent expectations with `python3 scripts/capture_parity_fixtures.py --earth-url http://127.0.0.1:8767` when the verified reference data changes. Do not rewrite expected results merely to hide a failure.

The deployment script stages only the frontend, assets, versioned data, and edge functions. It does not publish the video workspace, credentials, Python virtual environments, or private configuration. Scientific raster downloads and ingestion remain separate update tasks; the public site stays available when the development machine is off.

Cloudflare's Workers Free allowance, checked November 15, 2026, is **100,000 dynamic requests/day and 10 ms CPU/request**. Static-asset requests have separate free handling. This demo uses static catalog assets and a small JavaScript query/ranking runtime; it does not provision paid containers, D1, or a persistent database. Limits still apply; see [Workers limits](https://developers.cloudflare.com/workers/platform/limits/) and [static-asset billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/).

The earlier `pages/wrangler.globo.toml` and `scripts/share.sh` tunnel workflow is retained for development/reference deployments. It is not used by the definitive `hexastra.pages.dev` site. Private development credentials remain outside the repository.

## Interface languages

`js/i18n.js` and `js/locales/en.js` localize the immersive, guided, and advanced interfaces, including dialogs, accessibility labels, mission history, catalog descriptions, presets, explanations, map-layer help, and numeric/date formatting. Priority is:

1. Explicit `?lang=en` or `?lang=es`.
2. A manual preference stored as `hexastra.language`.
3. The first supported browser language; English is the fallback.

The language selector updates the current page without discarding the mission or custom weights. Internal navigation preserves an explicit language choice. API identifiers, scientific values, geographic proper names, units, URLs, and original citation records are not rewritten as translated data. Original source records remain verbatim; surrounding interface explanations are localized.

## English presentation demos and video-production agent

The presentation recordings show the actual app in English, with no mocked API results:

| Demo | GIF | MP4 |
|---|---|---|
| Guided mission: Mars → Arsia Mons → terrain → Argentina → result | https://hexastra.pages.dev/assets/demo/guided-en.gif | https://hexastra.pages.dev/assets/demo/guided-en.mp4 |
| Advanced comparison: weights, filters, layers, and evidence | https://hexastra.pages.dev/assets/demo/advanced-en.gif | https://hexastra.pages.dev/assets/demo/advanced-en.mp4 |

Record them again with Playwright Chromium and FFmpeg installed:

```bash
python3 scripts/record_demos.py --url https://hexastra.pages.dev --language en
```

The script captures real interactions, preserves map attribution, and exports looping GIFs below 10 MB plus MP4 copies. PDFs generally show a static image rather than playing a GIF; use the PNG poster with a public GIF/MP4 link when distributing a PDF. `--language es` records the Spanish interface. For video-compositor inputs matching the original 1280 × 720 recordings, add `--height 720`.

The [video-production agent](tools/video-agent/README.md) includes the [agent brief](tools/video-agent/AGENT.md), the final reviewed Spanish 180-second plan, and the actual compositor/alignment/export source used for the refined Ignacio video. It prepares an external working directory; supplied PDFs, licensed narration, full media builds, and credentials are not bundled into the repository.

## Original work, external resources, and submission permissions

HexAstra's application integration, comparison workflows, and implementation of the team's proposed TASI index are team work developed with disclosed AI assistance. External datasets, libraries, basemaps, fonts, textures, publications, and production tools remain the work of their respective authors.

**The resource register is not a certificate that every permission has been cleared.** Before checking **Confirm All Work is Original** in the submission form:

1. List every external resource actually used in **NASA Data** and **Space Agency Partner & Other Data**, including code, text, images, fonts, and linked demonstration materials. Cite sources even when they are open source or freely available.
2. Confirm the provenance and usage rights of the supplied logo and all presentation backgrounds/images. The PDF's Canva metadata identifies an authoring tool; it does not identify the license of every included asset.
3. Check restrictions and redistribution terms for each resource, particularly Mars Climate Database, COMNAP data, and Esri imagery. A public URL or citation alone does not grant permission. Retain required licenses and attribution.
4. Confirm the ElevenLabs plan and terms applicable **when the narration was generated**, and replace the audio if necessary.
5. Complete the **Use of Super Intelligence** disclosure with the team's actual use of AI tools and human review. Do not invent usage records or claim that generated illustrations are scientific observations.

The authoritative submission and reuse conditions are the [Space Apps legal terms](https://www.spaceappschallenge.org/legal/) and [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/). Listing a resource does not establish compatibility with all submission terms.

### ElevenLabs narration

Checked November 15, 2026: ElevenLabs advertises **Starter at USD 1 for the first month, then USD 6/month**, before applicable taxes, with commercial use. The account checkout and applicable terms determine the actual offer. See [Studio pricing](https://elevenlabs.io/studio) and the [publishing/license explanation](https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform).

Paid-plan rights apply to content **generated during the paid subscription**, subject to the service terms, applicable product restrictions, and rights to the input material. Upgrading does not retroactively grant commercial rights to audio generated on the free plan. To use paid-plan rights for the current pitch narration, regenerate it while the subscription is active and retain the generation and subscription records. The free plan permits noncommercial publication with its required attribution, including `elevenlabs.io` or `11.ai` in the title. Beta services can have separate restrictions.

The video's selected voice is **Ignacio — Compassionate and Sincere**. Its plan-specific permission remains unconfirmed until the account/generation record is checked. Paying for a voice plan does not resolve rights to unrelated presentation images or datasets. Audio generated during a paid subscription retains its commercial license after cancellation, subject to the applicable terms; see [subscription-end policy](https://elevenlabs.io/docs/help-center/account/general/what-happens-to-my-content-after-my-subscription-ends).

### Resource register for the submission form

Use the resource name below as **Link Text** and copy the complete URL. Shared NASA/partner products may be relevant to both data fields; explain their actual role. The CSV includes a short usage description for each entry.

- [Submission resource register](docs/resources/submission-resources.csv): NASA data, partner/other resources, video/PDF tools, and AI assistance.
- [Per-site source register](docs/resources/sources-by-site.csv): specific catalog, measurement, coordinate, and literature references.

The links point to public resource pages, documentation, identifiers, or files. Downloading some scientific products requires an account. Publisher access controls and automated-request blocking do not establish that the underlying resource is private or freely redistributable. Follow each provider's terms.

#### NASA Data

| Link Text | Full URL |
|---|---|
| NASA GIBS | https://nasa-gibs.github.io/gibs-api-docs/ |
| MODIS MOD13Q1 v6.1 | https://doi.org/10.5067/MODIS/MOD13Q1.061 |
| MODIS MOD44W v6.1 | https://doi.org/10.5067/MODIS/MOD44W.061 |
| NASA AppEEARS | https://appeears.earthdatacloud.nasa.gov/ |
| NASA / METI ASTER GDEM v3 | https://www.opentopodata.org/ |
| NASA LRO / LOLA — LDEM 118 m | https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif |
| NASA LRO / Diviner derived data | https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/ |
| NASA LRO / Diviner polar resource product | https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/dlre_prp_south.tab |
| NASA Mars Odyssey / GRS water-equivalent hydrogen | https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.tab |
| NASA Mars Global Surveyor MOLA / ESA Mars Express HRSC | https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_dem_global_200m |
| NASA GISS Mars24 — Landers | https://www.giss.nasa.gov/tools/mars24/help/landers.html |
| NASA NSSDC — Earth Fact Sheet | https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html |
| NASA NSSDC — Moon Fact Sheet | https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html |
| NASA NSSDC — Mars Fact Sheet | https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html |
| NASA Trek | https://trek.nasa.gov/ |
| NASA SEDAC / CIESIN / ITOS — gROADS v1 | https://doi.org/10.7927/H4VD6WCT |
| NASA SEDAC / CIESIN — GPWv4 Population Count rev. 11 | https://doi.org/10.7927/H4JW8BX5 |
| NASA — Seven Possible Cave Skylights on Mars | https://science.nasa.gov/resource/seven-possible-cave-skylights-on-mars/ |
| NASA — Artemis candidate landing regions (2022) | https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/ |
| NASA NTRS — Shackleton / Zuber et al. 2012 | https://ntrs.nasa.gov/citations/20120013758 |
| NASA NTRS — Río Cuarto | https://ntrs.nasa.gov/citations/19940011723 |
| NASA — Pavonis Mons / Mars Global Surveyor | https://science.nasa.gov/photojournal/pavonis-mons/ |

#### Space Agency Partner & Other Data

| Link Text | Full URL |
|---|---|
| ESA Permafrost_cci L4 v5.0 — CEDA | https://catalogue.ceda.ac.uk/uuid/d235665772ec4b558e9a89ac85595e71/ |
| Mars Climate Database — LMD / ESA / CNES | https://www-mars.lmd.jussieu.fr/mars/access.html |
| MGS MOLA / Mars Express HRSC blended DEM 200 m — USGS | https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_dem_global_200m |
| Open-Meteo Historical Weather API | https://open-meteo.com/en/docs/historical-weather-api |
| Copernicus / ECMWF ERA5 | https://confluence.ecmwf.int/pages/viewpage.action?pageId=488287070 |
| OpenTopoData — ASTER GDEM | https://www.opentopodata.org/ |
| Natural Earth | https://www.naturalearthdata.com/ |
| Macrostrat API | https://macrostrat.org/api |
| Macrostrat — Peters et al. 2018 | https://doi.org/10.1029/2018GC007467 |
| USGS Geologic Map of Mars — SIM 3292 | https://pubs.usgs.gov/sim/3292/ |
| USGS Unified Geologic Map of the Moon | https://astrogeology.usgs.gov/search/map/unified_geologic_map_of_the_moon_1_5m_2020 |
| Impact Earth — Osinski et al. 2022 | https://doi.org/10.1016/j.earscirev.2022.104112 |
| McSween, Taylor & Wyatt 2009 | https://doi.org/10.1126/science.1165871 |
| OurAirports Open Data | https://davidmegginson.github.io/ourairports-data/ |
| OpenStreetMap | https://www.openstreetmap.org/copyright |
| Overpass API | https://wiki.openstreetmap.org/wiki/Overpass_API |
| Nominatim | https://nominatim.org/ |
| IAU / USGS Gazetteer of Planetary Nomenclature | https://planetarynames.wr.usgs.gov/ |
| Smithsonian Global Volcanism Program | https://volcano.si.edu/ |
| COMNAP Antarctic Facilities — PGC archive | https://github.com/PolarGeospatialCenter/comnap-antarctic-facilities |
| SCAR Composite Gazetteer of Antarctica | https://placenames.aq/ |
| IGN Argentina — Active volcanoes | https://www.ign.gob.ar/NuestrasActividades/Geografia/DatosArgentina/VolcanesActivos |
| UNESCO — Ischigualasto / Talampaya | https://whc.unesco.org/en/list/966/ |
| Ischigualasto Provincial Park | https://www.ischigualasto.gob.ar/?page_id=507 |
| Wikipedia | https://www.wikipedia.org/ |
| Wikidata — Campo de Piedra Pómez | https://www.wikidata.org/wiki/Q23833026 |
| UNSCEAR 2024 Report, volume II | https://www.unscear.org/unscear/uploads/documents/unscear-reports/UNSCEAR_2024_Report_Vol.II.pdf#page=52 |
| Zhang et al. 2020 — Chang’e-4 lunar radiation | https://doi.org/10.1126/sciadv.aaz1334 |
| Hassler et al. 2014 — Mars surface radiation | https://doi.org/10.1126/science.1244797 |
| Ledoit & Wolf 2004 | https://www.ledoit.net/Well-conditioned2004.pdf |
| Haruyama et al. 2009 — Lunar lava-tube skylight | https://doi.org/10.1029/2009GL040635 |
| JAXA / ISAS — Lunar hole discovery | https://www.isas.jaxa.jp/j/topics/topics/2009/1105.shtml |
| ESA Mars Express — Medusae Fossae water ice | https://www.esa.int/ESA_Multimedia/Images/2024/01/Mars_Express_radar_data_indicating_heaps_of_water_ice_at_Mars_s_equator |
| Munguira et al. 2024 — Jezero meteorology | https://doi.org/10.1029/2024JE008385 |
| Leaflet | https://leafletjs.com/ |
| Three.js | https://threejs.org/ |
| Earth3D — mitchcamza | https://github.com/mitchcamza/Earth3D |
| Solar System Scope — Planet textures | https://www.solarsystemscope.com/textures/ |
| OpenPlanetaryMap — Basemaps | https://openplanetarymap.org/docs/basemaps/ |
| OpenPlanetaryMap / WhereOnMars / CARTO | https://github.com/openplanetary/opm-website/wiki/OPM-Basemaps |
| Esri World Imagery | https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer |
| Google Fonts — Montserrat | https://fonts.google.com/specimen/Montserrat |
| Google Fonts — Open Sans | https://fonts.google.com/specimen/Open+Sans |
| esbuild | https://esbuild.github.io/ |
| FastAPI | https://fastapi.tiangolo.com/ |
| Uvicorn | https://www.uvicorn.org/ |
| Pydantic | https://docs.pydantic.dev/ |
| HTTPX | https://www.python-httpx.org/ |
| NumPy | https://numpy.org/ |
| Psycopg 3 | https://www.psycopg.org/psycopg3/ |
| PostgreSQL | https://www.postgresql.org/ |
| PostGIS | https://postgis.net/ |
| Rasterio | https://rasterio.readthedocs.io/ |
| Pyogrio | https://pyogrio.readthedocs.io/ |
| Shapely | https://shapely.readthedocs.io/ |
| PyShp | https://github.com/GeospatialPython/pyshp |
| GDAL | https://gdal.org/ |
| pytest | https://docs.pytest.org/ |
| eval_type_backport | https://pypi.org/project/eval-type-backport/ |
| Docker | https://www.docker.com/ |
| Cloudflare Pages | https://developers.cloudflare.com/pages/ |
| Cloudflare Tunnel | https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/ |
| Python | https://www.python.org/ |
| Impeccable — design-review playbooks | https://github.com/pbakaus/impeccable |

#### Video and PDF production — if submitted

| Link Text | Full URL |
|---|---|
| Canva | https://www.canva.com/ |
| ElevenLabs — Ignacio | https://elevenlabs.io/ |
| FFmpeg | https://ffmpeg.org/ |
| OpenCV | https://opencv.org/ |
| Pillow | https://python-pillow.org/ |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper |
| Playwright | https://playwright.dev/ |
| Poppler | https://poppler.freedesktop.org/ |
| ReportLab | https://www.reportlab.com/ |
| Google Fonts — Mulish | https://fonts.google.com/specimen/Mulish |
| Google Fonts — League Spartan | https://fonts.google.com/specimen/League+Spartan |

#### AI assistance — also disclose in Use of Super Intelligence

| Link Text | Full URL |
|---|---|
| OpenAI Codex | https://openai.com/codex/ |
| Anthropic Claude | https://www.anthropic.com/claude |
| Grok | https://grok.com/ |
| OpenAI Whisper models | https://github.com/openai/whisper |
| edge-tts | https://github.com/rany2/edge-tts |

### Scope and attribution notes

- **Solar System Scope:** Earth, cloud, Mars, and Moon textures under CC BY 4.0. See [full visual credits](assets/globe/CREDITS.md). Textures are not scientific measurements.
- **Three.js:** MIT license retained in `js/vendor/THREE-LICENSE.txt`. Other dependencies retain their own licenses.
- **Earth3D:** visual reference; HexAstra implements its own integration, projection, selection, and TASI panels. Its demonstration analytics are not incorporated.
- **Impeccable:** design-review playbooks were consulted; its design-system decisions do not override HexAstra's brand. Credit: https://github.com/pbakaus/impeccable (Apache-2.0).
- **Natural Earth:** public-domain boundaries. **OpenStreetMap:** attribution and ODbL obligations apply.
- **Macrostrat:** attribute the API and underlying geological map sources recorded in the measurement provenance.
- **Mars Climate Database:** scientific-use conditions apply; do not label it an unrestricted CC-licensed dataset.
- **COMNAP:** the cited archive has educational/noncommercial conditions and requires attribution; review compatibility with the intended submission and reuse.
- **Esri imagery:** provider-specific terms and attribution apply; it is not public-domain imagery.
- **PDF/video:** the PDF was provided by the team and authored with Canva. Image and logo provenance still needs confirmation. Narration uses ElevenLabs. The montage's music was synthesized locally rather than downloaded as a third-party track; this does not establish rights to unrelated supplied imagery.
- **AI assistance:** Codex and Claude assisted with development, documentation, narration scripts, and production automation. The team supplied a Grok research record for pitch preparation; confirm its final scope. ElevenLabs synthetic narration and local Whisper speech alignment were used in video production. State actual assistance and human review in the submission's SI field.
- **Not ingested as datasets:** CRISM spectra, Sentinel products, CSA radar, JAXA GSMaP, and CONAE data are not claimed merely because they appear in the challenge's resource list. The retired Lunar Landing Site API is not a data source for current results.

## Repository guide

| Path | Purpose |
|---|---|
| `index.html`, `js/immersive.js`, `css/immersive.css` | Immersive application |
| `classic.html`, `js/app.js`, `js/easy.js` | Classic advanced and guided interfaces |
| `js/globe.mjs`, `js/globe-data.mjs` | 3D rendering and coordinate projection |
| `js/api.js`, `js/config.js` | API client and service configuration |
| `services/planetary/` | Moon/Mars catalog, vectors, references, ingestion |
| `services/earth/` | Earth catalog, masking, TASI, and ingestion |
| `contracts/feature_vector.schema.json` | Shared API vector contract |
| `data/measurements/` | Versioned sourced measurements |
| `db/` | Database schema, integration, snapshot export, and tests |
| `pages/`, `data/cloudflare/`, `scripts/deploy_pages.sh` | Standalone Cloudflare site, versioned data, and APIs |
| `scripts/export_pages_snapshot.py` | Read-only export from verified reference APIs |
| `scripts/record_demos.py`, `assets/demo/` | Real English presentation recordings |
| `tools/video-agent/` | Reproducible pitch-production agent and source |
| `js/i18n.js`, `js/locales/en.js` | Browser/manual English–Spanish localization |
| `docs/desafio.md` | Saved official challenge text |
| `docs/marca.md`, `DESIGN.md`, `PRODUCT.md` | Brand, interface, and product specifications |
| `docs/propuestas/G.md` | Implemented categorical geology method |
| `docs/propuestas/practicidad.md` | Earth-access data and interpretation |
| `docs/propuestas/vo-hielo.md` | Mask and ice-product definitions and limitations |
| `docs/resources/` | External resource and source registers |
| `AGENTS.md`, `CLAUDE.md` | Contributor and agent rules |

Documentation filenames and provenance identifiers remain stable so existing code and measurement references continue to resolve. Outdated debugging audits, temporary integration reports, unfinished reconciliation plans, and their dedicated visual-review captures have been removed; the current behavior and durable methodology are documented here and in the linked guides.
