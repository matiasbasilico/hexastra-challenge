# Earth access and operational context

**Current behavior, November 15, 2026:** the immersive site details show sourced road, airfield, and population measurements. These describe planning context on Earth. They are not treated as planetary similarity when the target has no equivalent operational measurement.

The stable filename is retained because ingestion scripts and measurement provenance refer to it. Earlier unfinished proposals for a separate practicality score, a new chart, and alternative ranking are not part of the current interface.

## Why context and similarity differ

TASI asks how closely an Earth site resembles a destination. Access data help ask what a terrestrial field campaign might involve. Roads and airports on Earth have no equivalent catalog measurement at Jezero or Shackleton. Combining them into similarity would favor convenient locations and could hide scientifically useful remote analogs.

The O dimension is still part of the feature vector. It can contribute to TASI only when an equivalent quantity is available on both sides. Existing one-sided access measurements remain useful without claiming that equivalence.

## Inputs

The producer is `services/earth/scripts/ingest_accessibility.py`. Its versioned output is `data/measurements/o-tierra.jsonl`: **240 records, 232 non-null**. The four operational fields use `comparable: false`.

Distances are geodesic straight-line distances on WGS84, not travel distances or route estimates.

| Feature | Unit | Definition | Source |
|---|---|---|---|
| `dist_road_km` | km | Nearest mapped road segment | [NASA SEDAC gROADS v1](https://doi.org/10.7927/H4VD6WCT) |
| `dist_airport_km` | km | Nearest open airfield with a runway; exclude heliports and closed facilities | [OurAirports](https://davidmegginson.github.io/ourairports-data/) |
| `dist_airport_scheduled_km` | km | Nearest qualifying airfield with scheduled service | OurAirports |
| `population_50km` | people | Sum of 30-arcsecond population cells whose centers lie within 50 km | [NASA SEDAC GPWv4 revision 11, 2020](https://doi.org/10.7927/H4JW8BX5) |
| `elevation` | m | Existing catalog elevation, displayed with its own source | ASTER GDEM v3 through OpenTopoData |

OurAirports provides the global airfield catalog because the challenge's official resources do not provide the required worldwide airfield list. Download the complete cited dataset rather than inventing a nearby airport.

## Interpretation limits

- Straight lines can cross water, mountain ranges, or restricted land; a short distance does not establish practical access.
- gROADS v1 represents roads from 1980–2010, with country-dependent completeness and no Antarctic road coverage. Missing coverage is not a measured absence of infrastructure.
- OurAirports is collaborative. A runway may be missing, inactive, or unsuitable for a specific aircraft; an entry does not establish permission to land.
- GPWv4 distributes census population within administrative units. Estimates near sparsely inhabited regions such as the Puna can be coarse and do not locate actual support facilities.
- These data do not establish permits, protected-area access, seasonal availability, travel costs, safety, or mission suitability.
- Preserve nulls and original source notes. Antarctic road/population gaps must not become invented zero values.

## Implementation references

- `services/earth/accessibility.py`: access measurements and an internal, tested practicality helper. Its presence does not mean a separate P score or chart is exposed in the application.
- `services/earth/scripts/ingest_accessibility.py`: reproducible data producer.
- `data/measurements/o-tierra.jsonl`: values, units, quality, and provenance.
- The README's [TASI method](../../README.md#tasi-the-implemented-method) and [resource register](../../README.md#resource-register-for-the-submission-form): scoring context and external credits.

No formula change, database load, or new frontend control is required to document these measurements.
