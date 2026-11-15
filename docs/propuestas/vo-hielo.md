# Vegetation/water mask and ice-product methodology

This guide documents the versioned `vo-mascara.jsonl` and `vo-hielo.jsonl` products and their current limitations. It does not change `services/earth/tasi.py`. Counts refer to the repository files on November 15, 2026; live availability is determined by the catalog served by the APIs.

## Part A — vegetation and inland-water mask

When enabled, `tasi.viability_mask` excludes an Earth site if `ndvi > 0.15` or `has_liquid_water = 1`. Unknown values do not exclude the site, but produce an availability flag. This is a configurable screening convention, not a universal statement that vegetated or water-bearing places cannot be useful analogs.

| Feature | Official product | Statistic or decision rule |
|---|---|---|
| `ndvi` | MODIS Terra [MOD13Q1 v061](https://doi.org/10.5067/MODIS/MOD13Q1.061), 250 m, 16-day composites, through [NASA AppEEARS](https://appeears.earthdatacloud.nasa.gov/) | Site pixel; mean over January 1, 2015–December 31, 2024, using `pixel_reliability = 0` good-quality composites. Exclude marginal quality, snow/ice, and clouds. Fewer than 23 good composites leaves null. Notes include count, median, and p90. |
| `has_liquid_water` | MODIS [MOD44W v061](https://doi.org/10.5067/MODIS/MOD44W.061), annual 250 m land/water mask, through AppEEARS | Site pixel, `seven_class`, 2015–2023. Assign 1 if inland water, class 3 or 5, occurs in at least half the years; otherwise 0. Ocean classes 0, 6, and 7 do not count as inland water. |

Ephemeral water, class 4, and water in the surrounding 3 × 3 cells are documented in notes rather than substituted for water at the actual point. If the site pixel is ocean in at least half the years, leave the feature **null**, not zero: the coordinate or coastline resolution needs review.

MOD44W was chosen as an official Earthdata product with a defined inland-water class and resolution compatible with the NDVI product. This pipeline does not claim Sentinel-2 ingestion.

### File coverage and checks

| Feature | Records with values | Null records |
|---|---:|---:|
| `ndvi` | 44 | 16 |
| `has_liquid_water` | 56 | 4 |

The file contains 120 records and 100 non-null values. Quality filtering, cloud/snow coverage, and coastline ambiguity cause gaps. Null records retain their reasons rather than being silently filled.

Control cases from the recorded products:

- **Lake Natron:** water = 1; the site pixel is shallow inland water in all nine annual observations.
- **Salar de Uyuni:** water = 0; eight years are land, with shallow water only in 2022. This captures the majority-year rule rather than denying seasonal flooding.
- **Laguna de Antofagasta:** water = 0; the point and its 3 × 3 neighborhood are land in the nine observations. At 250 m this does not prove the absence of a nearby small lake.
- **Badwater:** water = 0 under the majority-year rule, despite the temporary water classification in 2023.
- **Coastal/ocean-classified coordinates:** preserve null and a coordinate-review note instead of claiming the site is dry.

An annual mean NDVI threshold can exclude sparse arid shrubland and can be biased toward the season with valid observations. Median and p90 are retained for interpretation; the documented threshold is not silently changed. The application lets users remove the mask.

## Part B — ice and permafrost on the three bodies

### Raw quantities

These product-specific features use `comparable: false`. Their units and meanings must not be mixed directly in similarity scoring.

| Body | Feature | Product | Quantity |
|---|---|---|---|
| Earth | `permafrost_fraction` | [ESA Permafrost_cci L4 v5.0, PFR](https://catalogue.ceda.ac.uk/uuid/d235665772ec4b558e9a89ac85595e71/), through CEDA | Permafrost area fraction of the sampled 0.01° cell, averaged over 2019–2023. Model-derived product using MODIS LST, ERA5, and CryoGrid. |
| Moon | `moon_ice_stable_frac` | LRO Diviner Polar Resource Products v2, `LRO-L-DLRE-5-PRP-V2.0`, [PDS table](https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/dlre_prp_south.tab) | Fraction of sampled approximately 240 m triangles within 5 km of the site with modeled ice stability to a depth of 2.87 m. |
| Moon | `moon_ice_surface_frac` | Same Diviner product | Fraction with `ice_depth = 0`, modeled surface stability. |
| Moon | `moon_ice_depth_min_m` | Same Diviner product | Shallowest reported stability depth. |
| Moon | `moon_prp_code_m1_frac` | Same Diviner product | Fraction with the undocumented `ice_depth = -1` code; not silently interpreted as detected ice. |
| Mars | `mars_grs_h2o_wt_pct` | Mars Odyssey GRS `ODY-M-GRS-5-ELEMENTS-V1.0`, [PDS smoothed table](https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.tab) | Water-equivalent hydrogen weight percent in the upper approximately one meter, smoothed to 5° × 5° bins. |

The permafrost dataset has limited geographic coverage. The recorded Andes and other out-of-coverage sites remain null rather than being assigned zero permafrost. Polar Diviner products do not cover Marius Hills at 14° N; its corresponding polar-resource values remain null.

### Common indicator: `water_ice_indicator`

The intended meaning is **the fraction of site area where water ice could remain thermally stable in the upper approximately 1–3 m**. This asks about persistence if ice were present, not whether ice has been detected.

| Body | Current mapping | Status |
|---|---|---|
| Earth | `water_ice_indicator = permafrost_fraction` | Derived proxy; 12 non-null values. Preserve its physical and geographic limitations. |
| Moon | No numeric indicator loaded | Null: PRP v2 includes `ice_depth = -1` in very cold triangles, but the cited metadata does not establish its interpretation. Raw quantities and uncertainty bounds remain available. |
| Mars | No numeric indicator loaded | Null: GRS hydrogen can reflect hydrated minerals or adsorbed water rather than stable ice. Converting hydrogen weight percent to an ice-area fraction would invent a different quantity. |

The file has **169 records, 55 non-null**: 12 permafrost fractions, 12 Earth indicator values, six values in each of the four lunar raw fields, and seven Martian GRS values. There are no non-null lunar or Martian `water_ice_indicator` records in this file.

Current consequences:

- The indicator does not change planetary similarity by itself because the target side remains unavailable. TASI requires comparable information on both sides.
- A future confirmed target indicator would need a documented cross-body definition and comparability review before integration.
- Earth cells and lunar 5 km neighborhoods have different support areas. A shared label does not remove resolution differences.
- Earth permafrost and lunar sublimation stability involve different physics. Neither implies the presence or accessibility of extractable water ice.
- Out-of-coverage values remain null; precipitation or other shared metrics can still contribute according to the active method.

### Validation

The producer tests check recorded products against published ranges and physical ordering:

- Mars GRS values fall within the published water-equivalent hydrogen range cited in the records. This validates the raw product, not a stable-ice interpretation.
- Very cold lunar polar triangles and warmer illuminated terrain show the expected ordering of modeled stability depths. The unexplained `-1` code remains unresolved rather than reclassified from intuition.
- Continuous-permafrost reference sites retain the sampled product fractions; temperate fill cells and out-of-coverage locations are not converted to invented zero values.

Full source strings, quality flags, and notes remain in each JSONL record.

## Reproduction

Run each producer's fetch and build stages sequentially:

```bash
services/.venv/bin/python services/earth/scripts/ingest_mask.py fetch
services/.venv/bin/python services/earth/scripts/ingest_mask.py build
services/.venv/bin/python services/earth/scripts/ingest_permafrost.py fetch
services/.venv/bin/python services/earth/scripts/ingest_permafrost.py build
services/.venv/bin/python services/planetary/scripts/ingest_ice.py fetch
services/.venv/bin/python services/planetary/scripts/ingest_ice.py build
```

Small reproducible subsets are versioned under `services/*/data/raw/`. Full source downloads and caches remain ignored by Git. Fetching products can require provider credentials or acceptance of their terms. Generating a measurement file does not authorize loading the shared database; follow the [integration rules](../../data/measurements/README.md).
