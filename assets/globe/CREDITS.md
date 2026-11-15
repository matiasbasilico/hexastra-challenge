# HexAstra globe and planet credits

Visual reference: [Earth3D by mitchcamza](https://github.com/mitchcamza/Earth3D). HexAstra implements its own Leaflet integration, point projection, selection, and TASI panels in `js/globe.mjs`. It does not incorporate that demonstration's analytics or application JavaScript.

`earth-day.jpg` is **Solar System Scope**'s Earth Day Map 2K texture, distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It was downloaded unchanged from the [copy used by Earth3D](https://github.com/mitchcamza/Earth3D/blob/main/static/textures/2k_earth_daymap.jpg). Source and conditions: https://www.solarsystemscope.com/textures/. Retrieved November 14, 2026, America/Argentina/Buenos_Aires.

`earth-clouds.jpg` is Earth Clouds 2K, by the same author under the same license, downloaded unchanged from the [copy used by Earth3D](https://github.com/mitchcamza/Earth3D/blob/main/static/textures/2k_earth_clouds.jpg). It is a fixed illustrative cloud layer, not current weather imagery. Retrieved November 14, 2026, America/Argentina/Buenos_Aires.

`mars.jpg` and `moon.jpg` are Solar System Scope's Mars and Moon 2K textures, under CC BY 4.0, downloaded unchanged from https://www.solarsystemscope.com/textures/download/2k_mars.jpg and https://www.solarsystemscope.com/textures/download/2k_moon.jpg. They are rendered as spheres in the selection cards with Three.js. Retrieved November 14, 2026, America/Argentina/Buenos_Aires.

These textures are illustrations, not NASA measurement datasets or scientific layers. They do not change coordinates, component values, or TASI scores. Site measurements retain the provenance supplied by the HexAstra APIs.

Three.js 0.167.0 is distributed under the MIT license. The complete license is retained in `js/vendor/THREE-LICENSE.txt`. Rebuild the versioned static bundle with `npm ci && npm run build:globe`.
