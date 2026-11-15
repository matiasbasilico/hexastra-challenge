---
name: HexAstra
description: Earth analogs for the Moon and Mars, with sourced evidence and explicit physical limits.
colors:
  noche: "#070915"
  noche-2: "#121830"
  linea: "#2A3250"
  texto: "#F6F7FE"
  texto-2: "#A9B0CA"
  cian: "#65D0EA"
  cian-brillo: "#56B2DE"
  marte: "#D87E4E"
  violeta: "#8651D3"
  azul-orbita: "#2B77E1"
  celeste: "#729CD8"
  sol: "#D4964E"
  luna: "#B6AEB7"
typography:
  display:
    fontFamily: "Montserrat, system-ui, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 700
    lineHeight: 1.1
  headline:
    fontFamily: "Montserrat, system-ui, sans-serif"
    fontSize: "1.44rem"
    fontWeight: 700
    lineHeight: 1.15
  title:
    fontFamily: "Montserrat, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.2
  label:
    fontFamily: "Montserrat, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    letterSpacing: "0.14em"
  body:
    fontFamily: "Open Sans, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  data:
    fontFamily: "Open Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    fontFeature: "tnum"
rounded:
  control: "8px"
  card: "10px"
  chip: "999px"
spacing:
  2xs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  2xl: "64px"
components:
  button:
    backgroundColor: "{colors.noche-2}"
    textColor: "{colors.texto}"
    rounded: "{rounded.control}"
    height: "40px"
  button-primary:
    backgroundColor: "{colors.cian}"
    textColor: "{colors.noche}"
    rounded: "{rounded.control}"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.cian-brillo}"
    textColor: "{colors.noche}"
  panel:
    backgroundColor: "{colors.noche-2}"
    textColor: "{colors.texto}"
    rounded: "{rounded.card}"
  chip-a-completar:
    textColor: "{colors.sol}"
    rounded: "{rounded.chip}"
  chip-medido:
    textColor: "{colors.cian}"
    rounded: "{rounded.chip}"
  chip-menos-estudiado:
    textColor: "{colors.cian-brillo}"
    rounded: "{rounded.chip}"
---

# HexAstra design system

The visual identity is defined by [`docs/marca.md`](docs/marca.md) and [`css/brand.css`](css/brand.css). This document applies it to interface behavior. The brand guide takes precedence over design-tool suggestions. Existing token and component identifiers retain their spelling to preserve code references.

## Overview

HexAstra is an evidence tool. In `index.html`, full 3D Earth is the canvas. Site points open comparisons; mission, list, and help controls reveal floating panels. Preserve the complete planetary volume and position it so Earth and its selected destination remain visible. The brand appears through cyan focus/selection, body colors, and the violet-to-rust score scale. `classic.html` retains advanced and guided workflows.

## Colors

- Use `noche` for the overall background, `noche-2` for panels/cards/controls, and `linea` for dividers and borders. There is no light theme.
- Cyan is the sole interface accent: focus, selection, links, and the primary action with midnight-colored text. `cian-brillo` supplies hover emphasis.
- Semantic colors identify Earth (`celeste`), Mars (`marte`), the Moon (`luna`), low-to-high similarity (`violeta` to `marte`), and data quality. Always pair meaning with text; never use a red/green similarity scale.
- Reserve `violeta` and `azul-orbita` for graphics or suitably large text; do not use them for small body text.

## Typography

Use Montserrat 700 for headings and the wordmark. Montserrat 600 uppercase with 0.14 em tracking is reserved for the screen's single top label. Use Open Sans 400/600 for prose and data, with tabular numerals and adjacent units. Do not add a third interface typeface.

## Layout

- **Immersive:** `100dvw × 100dvh`, without page scrolling. Keep the whole globe inside the canvas. Floating elements have 32 px margins, reduced to 20 px below 1100 px and 16 px on mobile.
- **Selected site:** Earth on the left, floating destination/details on the right. Below 760 px, stack globe above details without overlap; long detail content scrolls inside its panel. Closing restores the full canvas and focus to the selected point.
- **Classic:** maximum 1520 px content width, with 40 px gutters, 24 px below 60 rem, and 16 px below 40 rem.
- At desktop sizes from 960 × 640 px, use a compact header and viewport-height workspace, with internal scrolling for lists/details. Smaller classic windows return to document flow.
- Advanced mode uses a compact control bar, site list, Earth map, destination map, and pair details. Keep search status near the workspace footer. Weight controls open in a contained dialog rather than an overflowing popover.
- Put long methodological explanations in the calculation help rather than the main workspace. Physical limits open in a focus-contained dialog with Escape dismissal and focus restoration.

## Depth and shape

Use tonal depth from `noche` to `noche-2` and `linea` borders instead of decorative shadows. Avoid nested bordered boxes. Controls have an 8 px radius; panels/cards use 10 px; chips are pills. Map pins are circular, with a midnight border and a 3 px cyan selected ring.

## Components

### Shared controls

- **Button:** 40 px high, panel background, divider-colored border. Hover adds cyan text/border. Primary action is cyan with midnight text.
- **Segmented control:** panel background; cyan active selection, or the body's semantic color where appropriate.
- **Chip:** semantic text and border, without a filled background.
- **Selectable row:** panel background and divider border. Selection adds 12% cyan fill and a cyan border.
- **Score:** Montserrat 700 in the violet-to-rust scale, with a 4 px gradient bar. Include units, coverage, and an understandable label.
- **Map:** dark frame, body label and colored point, Leaflet controls styled with the panel background. Layer menus explain the meaning and limitations of available layers.

### Earth globe

Use illustrative, credited Solar System Scope textures, a restrained cyan atmosphere, and site pins consistent with the 2D map. Earth3D is a visual reference, not the source of scientific measurements.

Rotate at the sidereal rate of **23.9345 hours per revolution**. Pause manually, during interaction, and while mission/comparison workflows are open. Disable automatic movement with reduced-motion preferences. Rotation does not claim current astronomical orientation or illumination.

Selection centers the actual site coordinate and keeps its position aligned with the texture. Provide accessible keyboard and zoom controls. Fall back to Leaflet without WebGL.

### Ranking emphasis and visibility

Up to five sites with the highest positive TASI scores emit two soft, staggered cyan rings. Update them when destination, focus, region, or mask changes; remove the old pulse while recalculating. This is ranking emphasis, not an absolute strong-analogy threshold. Reduced-motion users receive a fixed ring.

The default comparable-only visual filter hides sites without a valid score for the active destination/region/mask. A floating control and mission setting can disable it. Unscored sites then appear smaller and subdued, without pulses. A valid zero score remains comparable. For a site outside the region, the comparison can offer to remove that filter and compute the pair.

### Mission setup

- Mars and Moon use square cards, each with a textured 3D sphere, semantic body color, cyan selection, and a checkmark. Native radio semantics preserve keyboard operation. A shared canvas renders both cards; spherical image fallbacks remain available without WebGL.
- Use three steps: celestial body, destination, and focus. Completed steps show the selected body/destination and a checkmark rather than repeating generic labels.
- Focus choices are illustrated cards for balanced, terrain, climate, and robot testing. Region and filtering settings have a dedicated tab within the final step.
- Back preserves the draft. Closing discards it. Only completing the final action applies a mission.
- Every step, including open region/filter options, must fit the viewport with close/back/continue controls visible. Cards remain usable from 320 px and respect mobile safe areas.
- Destination details use catalog descriptions, terrain, coordinates, and a dated, linked historical milestone. Distinguish landing, orbital observation, publication, and announcement. The 2022 lunar candidate-region announcement is not a landing. All 14 current targets have a sourced milestone; any future unverified date remains pending rather than invented.

### Comparison panel

Show site identity, marked destination map, TASI, coverage, why it matches, where it differs, and expandable data/source details. Keep the terrestrial globe interactive. Open with pointer or keyboard, close with Escape or the close control, and preserve both marked positions. The classic interface retains its point dialog.

Do not inherit another pair's score. Present one-sided measurements in their proper context. Keep literature narratives visually distinct with a dashed light-blue boundary and a written literature label; they do not become score inputs.

### Onboarding and first mission

On first visit, introduce HexAstra, its purpose, and three short usage instructions, with a mission-selection action. Closing stores `hexastra.onboarding.v1=seen` in that browser's origin-specific local storage. The full project help remains available. Onboarding does not block interaction after dismissal and respects reduced motion.

The initial globe has **no active mission**. The header invites mission selection, the catalog remains explorable, and ranking starts only after completing setup. Launching selects the highest valid TASI result, centers Earth, and opens its details. A temporary hint near another visible point explains how to switch sites; hide it on interaction and do not repeat it over a manual selection.

The welcome links to the official [team page](https://www.spaceappschallenge.org/2026/find-a-team/hexastra/) and [challenge](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/). Do not invent team biographies or membership.

### TASI explanation

The TASI label opens an explanation by hover, focus, or touch. Define G, T, E, Vo, and O and reflect the actual comparison state from the same API response, including valid zero scores and absent values. Escape closes the explanation without dismissing the comparison.

## Responsive behavior and accessibility

In landscape, preserve the Earth | destination workspace with compact details; in portrait, stack the views and scroll only their long contents. Keep the mission wizard within the viewport. Preserve native controls, accessible labels, immediate visible cyan focus, keyboard operation, and reduced motion. At 320 px, do not introduce horizontal page scrolling.

## Implementation rules

- Obtain scientific values and their sources from the APIs. Keep nulls honest.
- Preserve the brand palette, typefaces, and logo.
- Keep a single top label per screen, avoid nested boxes, and do not add decorative shadows.
- Never hide one side of an open comparison or merge a literature narrative into the computed score.
- The immersive initial state intentionally shows the globe before a comparison is selected.

## Sources for mission history and rotation

Retrieved November 14, 2026, America/Argentina/Buenos_Aires. These are editorial references for interface context, not additional TASI measurements.

- [NASA GISS Mars24 — Mars Lander Missions](https://www.giss.nasa.gov/tools/mars24/help/landers.html), updated December 9, 2023: Perseverance, February 18, 2021; Curiosity, August 6, 2012 UTC; Opportunity, January 25, 2004; Viking 2, September 3, 1976.
- [NASA release 22-089](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/), August 19, 2022: historical candidate south-polar regions. Catalog points are geographic anchors, not confirmed landing sites.
- [NASA NSSDCA Earth Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html), updated November 15, 2024: 23.9345-hour sidereal rotation period.
- [NASA Pavonis Mons, PIA05243](https://science.nasa.gov/photojournal/pavonis-mons/), January 18, 2004: publication of a Mars Global Surveyor/MOC image acquired in December 2003. The displayed milestone is publication, not landing.
- [NASA Seven Possible Cave Skylights on Mars](https://science.nasa.gov/resource/seven-possible-cave-skylights-on-mars/), September 21, 2007: Mars Odyssey/THEMIS observations of possible pits in Arsia Mons.
- [ESA Medusae Fossae radar publication](https://www.esa.int/ESA_Multimedia/Images/2024/01/Mars_Express_radar_data_indicating_heaps_of_water_ice_at_Mars_s_equator), January 18, 2024: Mars Express/MARSIS material, not a surface visit.
- [JAXA/ISAS SELENE/Kaguya discovery](https://www.isas.jaxa.jp/j/topics/topics/2009/1105.shtml), November 5, 2009: Marius Hills pit publication.

## Language selection

Support English and Rioplatense Spanish, with explicit URL language, saved manual preference, then browser detection. Keep the compact language selector keyboard-accessible in both interfaces. Switching language preserves the active mission and weights. Reserve enough room at 320 px; collapse the adjacent wordmark text before cutting off controls. Localize descriptions, explanations, dates, numbers, and accessible names while retaining scientific source records and API identifiers.
