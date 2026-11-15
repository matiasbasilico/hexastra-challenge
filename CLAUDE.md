# HexAstra — repository rules for every agent

Every agent working in this repository, including coordinators, subagents, and Orca worktrees, must read this file. If a task-specific instruction conflicts with these rules, these rules take precedence; when they do not resolve an uncertainty, ask the user rather than assume.

## 1. Primary objective

NASA Space Apps 2026 — *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*. The full official text and resource list are in [`docs/desafio.md`](docs/desafio.md).

> Use open NASA and other space-agency data to **identify and characterize new terrestrial analogs** for candidate permanent lunar bases and Martian landing/exploration sites, and present the findings as a map, visualization, or other tool.

Every task must move the project toward this objective. The challenge explicitly asks us to:

- **Go beyond appearance:** justify each analogy with data, by dimension.
- **Explain what matches, how closely, and what differs.** A site can be a strong geological analog and a poor thermal analog.
- **Seek less-studied analogs**, rather than rediscover Atacama, Haughton, Iceland, Hawaii, or Antarctica; these provide baselines.
- **Combine datasets and respect scale:** a crater or valley, not an entire desert.
- **Connect the analogy to exploration:** instruments, operations, resources, and risks that can be tested there.
- **Recognize Earth's limits:** gravity, lunar vacuum, thin Martian atmosphere, and radiation. Display quantified differences separately from similarity scoring.

Challenge dimensions and their representation in **V = [G, T, E, Vo, O]** (`contracts/feature_vector.schema.json`):

| Challenge dimension | Component |
|---|---|
| Geology, mineralogy, materials | **G** |
| Terrain, elevation, slope, roughness, craters | **T** |
| Temperature, illumination, extremes | **E** |
| Water, ice, permafrost, resources; dust and wind | **Vo** |
| Landing, mobility, operations, construction | **O** |
| Biology/habitability, caves/subsurface | No dedicated component yet; propose one before adding it |

## 2. Established decisions

Do not reopen these decisions without the user:

- **Score: TASI only** (`services/earth/tasi.py`). Do not implement the printed document's S formula, which combines a Gaussian comparison with a geometric mean.
- **MVP: API-driven point map.** Earth uses Three.js 3D, visually inspired by Earth3D and authorized on November 14, 2026. Leaflet retains the 2D Earth view and planetary maps. Selecting a globe point opens its TASI comparison. No H3 grid, Cesium, or migration to Next/MapLibre.
- **Do not modify** the `~/Desarrollo/nasa/nasa` monorepo, its PostgreSQL instance on port 5432, or the older project folders.
- **Database:** this repository's PostgreSQL/PostGIS container is `hexastra-db`, at `127.0.0.1:55432` (`docker compose up -d db`). Authorized integration rebuilds it from versioned base catalogs and `data/measurements/*.jsonl` using `db/load.py`. APIs use PostgreSQL when `HEXASTRA_DATABASE_URL` is set; otherwise they use a `catalog.merged.json` snapshot from `db/export.py`, or the base catalog. `/health` reports `catalog_origin`.
- **Immersive variant, authorized November 14, 2026:** `index.html` opens with the full Earth globe and its points. Mission, list, help, and comparison controls reveal floating panels. Selecting a site opens Earth | destination, with both positions marked and synchronized, plus the analogy and limits. Desktop places them side by side; mobile places the globe above the destination/details without overlap. This is the user's requested exception to showing a comparison immediately on arrival. `classic.html` preserves the previous guided and advanced interfaces.
- **Similarity without a counterpart:** G and O score only when both the target and Earth site have comparable values. One-sided data can be loaded, but changing `tasi.py` formulas requires a proposal and the user's approval.
- **Publishing, updated with user authorization on November 15, 2026:** the definitive demonstration is https://hexastra.pages.dev/. Cloudflare Pages Functions serve versioned API evidence and calculate rankings without a Mac, tunnel, or database. `scripts/deploy_pages.sh` uses `pages/wrangler.production.toml` by default. Python services remain the development/reference implementation; `scripts/share.sh` is an optional legacy development workflow. Preserve parity and provenance when refreshing the snapshot.
- **Visual identity:** follow [`docs/marca.md`](docs/marca.md) and [`css/brand.css`](css/brand.css): midnight-blue background, cyan accent, Montserrat + Open Sans, unchanged `assets/brand/` logo, violet-to-rust score scale, and semantic body colors. Design tools, including Hallmark, may inform structure but must not replace the palette, typography, or logo.

## 3. Data integrity

1. **Never invent** coordinates, elevations, temperatures, spectra, or other values. Do not average conflicting sources to conceal disagreement.
2. **Every value needs `source`:** dataset, product/version, URL, and retrieval date in America/Buenos_Aires. Wikipedia is a labeled last resort.
3. **Unverified values remain `null`**, with `quality: "placeholder"` or `"unavailable"` and the required pending-data note, `"a completar"`. Do not admit a site without a verified coordinate; list it in the report.
4. Use honest `quality`: `measured`, `derived`, `modeled` (such as ERA5 or MCD), `convention`, `derived_from_published_range`, or `placeholder`/`unavailable`.
5. **Comparability:** use the same definition on Earth and the target, such as a 7 × 7 terrain grid at 120 m. Document scale or quantity differences in `note`, including 200 m DEMs or surface versus air temperature.
6. TASI renormalizes weights over available components and reports coverage. Preserve this behavior; never fill gaps to increase scores.
7. **Validate each new pipeline against a published value** before integration, for example Bradbury Landing at −4501 m or Jezero MEDA at 209–225 K.
8. Never expose secrets in the repository or conversation. Store Earthdata credentials in `~/.netrc` and other private settings in `~/.config/hexastra/*.env`.

## 4. Source priority

Use sources in this order. Use an external source only when the official source lacks the required data, and document the reason.

1. **Official challenge resources** ([saved text](docs/desafio.md)):
   - NASA Earthdata Search / Worldview: MODIS, ASTER, NASADEM, EMIT, SMAP, and related Earth products.
   - NASA PDS and LRO: LROC, LOLA, Diviner, including polar/resource products, LEND, Mini-RF; Martian MOLA, CRISM, THEMIS, GRS/neutron products.
   - CSA: RCM and RADARSAT-1 C-band radar.
   - ESA: Copernicus Data Space/Sentinel and ESA Open Science Catalog, including Permafrost_cci.
   - JAXA: G-Portal precipitation/GSMaP, snow, and vegetation products.
2. Mission-derived agency/institute products: USGS Astrogeology, IAU/USGS Gazetteer, LMD/ESA/CNES Mars Climate Database, NASA GISS Mars24.
3. Recognized open resources: Smithsonian GVP, Earth Impact Database, Natural Earth, OpenStreetMap, GHSL, COMNAP, and papers with DOI identifiers.
4. Wikipedia, only as a last resort and labeled in `coord_source` or `source`.

Respect every non-governmental provider's usage conditions. A source's presence on the challenge resource list does not establish that the application has ingested it. See the README's external-resource register for actual use.

## 5. Development workflow

- **One agent, one task, one worktree, one PR.** No commits on `main`, merges, or force pushes. Write small, descriptive commits in Spanish using `feat:`, `fix:`, `docs:`, `test:`, or `chore:`.
- **New data:** each agent owns `data/measurements/<agent>.jsonl` and its reproducible ingestion script. Follow the [measurement rules](data/measurements/README.md). Do not edit base catalogs, another agent's data, or run `db/export.py`. Do not run `db/load.py` against the shared database; tests use their own temporary database. The coordinator performs integration.
- **Tests:** keep `./services/run_tests.sh` passing, with meaningful schema, provenance, and null-handling tests for new data.
- **Final report:** provide the loaded site × feature × value × source table, remaining nulls and reasons, validation results, and unresolved questions.
- **Do not stop** the demonstration on ports 8765/8766/8767. Use other ports for verification.

## 6. Quick reference

- Start frontend/services: `./run_all.sh` (8765 frontend, 8766 planetary, 8767 Earth).
- Database integration: `docker compose up -d db`, then `services/.venv/bin/python db/load.py` only for the authorized database. Set `HEXASTRA_DATABASE_URL` to run against PostgreSQL.
- Tests: `./services/run_tests.sh` (planetary, Earth, and `db/tests`).
- Share: `./scripts/deploy_pages.sh` and `./scripts/share.sh <pages-url>`. See the README for the immersive deployment configuration and dedicated ports.
- Current architecture, decisions, source register, and coordinate conventions: [`README.md`](README.md). Measurement definitions: [`data/measurements/README.md`](data/measurements/README.md) and `docs/propuestas/`.
