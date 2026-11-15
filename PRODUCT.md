# Product

<!-- impeccable:product-schema 1 -->

## Platform

Web.

## Users

- **Primary users:** NASA Space Apps Challenge 2026 judges and Team HexAstra, confirmed by the team on November 14, 2026. They have minutes to understand which Earth site resembles a lunar or Martian target, how closely, where the analogy fails, and where each value comes from.
- The immersive interface opens with full-screen 3D Earth. Users explore sites through globe points or a floating list; selecting one reveals the comparison. The classic interface retains guided and advanced modes.

## Product purpose

Identify and characterize new, less-studied terrestrial analogs for candidate permanent lunar bases and Martian landing/exploration sites using open NASA and other agency data. The [official challenge](docs/desafio.md) defines the objective. Success means a user can justify an analogy with evidence by dimension and understand what Earth cannot reproduce.

## Positioning

- Seek less-studied analogs. Familiar sites such as Atacama, Haughton, Iceland, Hawaii, and Antarctica serve as baselines, not new discoveries.
- Explain similarity by dimension using **V = [G, T, E, Vo, O]** and TASI, the team's proposed index. Report coverage; a component requires comparable data on both sides.
- Show gravity, lunar vacuum, the thin Martian atmosphere, and radiation differences separately from the similarity score.

## Operating context

- The definitive public demonstration runs entirely on Cloudflare Pages/Functions with a verified, versioned catalog snapshot. No local computer or tunnel is required. Python APIs remain the development/reference implementation.
- Main flow: choose Moon or Mars, choose a destination, choose a mission focus, optionally filter by continent/country, then inspect the Earth | destination comparison.
- `index.html` uses the globe as its full canvas. Mission, list, help, and comparison panels open on demand. `classic.html` retains the earlier interface and a direct advanced-mode entry.
- The advanced interface can begin from published literature pairs (`GET {earth}/examples`) and supports searches across the full candidate catalog.

## Capabilities and constraints

- Static vanilla HTML/CSS/JavaScript frontend. Earth uses Three.js, visually inspired by Earth3D, with a Leaflet 2D fallback. Planetary maps use Leaflet. There is no Cesium, H3 grid, or framework migration; see `CLAUDE.md`.
- Selecting a globe point opens the site, destination map, TASI score, similarity explanation, differences, available evidence, and sources. The globe remains visible and interactive. Unavailable pairs never inherit another site's or mission's score.
- **Scientific content comes from the APIs:** catalogs, target vectors, ranking, explanations, method/presets (`/method`), physical references (`/bodies`), and literature examples (`/examples`). The frontend supplies interface copy and presentation.
- Without services, display a clear unavailability state rather than fabricated points or scores.
- After selection, Earth and target remain visible with synchronized marked positions. Closing the comparison restores the full globe.
- Geological categories are sourced map interpretations, not measured spectra. Earth access information is planning context; it is not a planetary counterpart.
- Keep `js/api.js`, `js/config.js`, and JavaScript-dependent element IDs compatible.
- `/bodies` radiation references include UNSCEAR 2024 for modeled Earth outdoor exposure, Zhang et al. (2020) for Chang'e-4/LND on the Moon, and RAD/MSL for Mars. Preserve source-specific definitions, daily conversions, and effective-versus-equivalent-dose differences. These are not site-specific measurements or similarity terms.

## Brand commitments

Follow [`docs/marca.md`](docs/marca.md) and `css/brand.css`: midnight background, cyan accent, Montserrat + Open Sans, unchanged brand logo, violet-to-rust score scale, and semantic body/data-quality colors with written labels. Tools must not replace the palette, typefaces, or logo.

The application supports clear, honest English and Rioplatense Spanish, selected from the browser or a saved manual preference. Documentation is in English. Avoid unsourced figures, unsupported claims of global novelty, or measured savings that have not been demonstrated.

## Evidence on hand

- 60 Earth candidates and 14 Moon/Mars targets, each with coordinate provenance.
- Five published literature pairs in `services/earth/data/literature_examples.json`, exposed through `/examples`.
- Versioned terrain, environment, geology, masking, ice, and Earth-access measurements in `data/measurements/`.
- Sourced physical reference values in `/bodies`.
- No verified testimonials, usage metrics, awards, or measured cost reductions; do not invent them.

## Product principles

1. Never invent values. Preserve sources and honest missing-data states.
2. Explain what matches, how closely, and what differs before relying on a single score.
3. Keep Earth and destination visible together after selection.
4. Show physical analogy limits separately from similarity.
5. Work at site scale—a crater, valley, or local terrain—not an entire region.
6. Keep evidence coverage distinct from similarity and mission suitability.

## Accessibility and inclusion

Maintain text contrast of at least 4.5:1, visible focus, keyboard operation, reduced-motion support, and a usable 320 px layout without horizontal page scrolling. Keep essential mission actions visible within the viewport.
