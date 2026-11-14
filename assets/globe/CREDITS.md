# Globo terrestre de HexAstra

Referencia visual: [Earth3D, de mitchcamza](https://github.com/mitchcamza/Earth3D). La integración con Leaflet, la proyección de puntos y el modal TASI son una implementación propia en `js/globe.mjs`; no se incorpora la analítica ni el código de esa demo.

`earth-day.jpg` es la textura Earth Day Map 2K de **Solar System Scope**, distribuida bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Descargada sin cambios desde el [archivo usado por Earth3D](https://github.com/mitchcamza/Earth3D/blob/main/static/textures/2k_earth_daymap.jpg). Fuente y condiciones: https://www.solarsystemscope.com/textures/. Consulta: 2026-11-14 (America/Argentina/Buenos_Aires).

Es una imagen ilustrativa, no un dataset de mediciones ni una capa científica de NASA. No modifica coordenadas, componentes ni puntajes. Los sitios conservan las fuentes de las APIs de HexAstra.

Three.js 0.167.0 se distribuye bajo MIT. Licencia completa en `js/vendor/THREE-LICENSE.txt`. El bundle se reconstruye con `npm ci && npm run build:globe`; se versiona para mantener el despliegue estático actual sin un build obligatorio en producción.
