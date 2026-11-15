# Datos oficiales en los ejemplos de la demo

Auditoría del 14/11/2026 (America/Argentina/Buenos_Aires). Se consultaron las APIs y la base existente en modo de solo lectura; no se cargó ni exportó la base compartida y no se modificó la fórmula TASI.

La demo usaba `catalog.json`, aunque la base ya contenía las mediciones integradas de los agentes. Ahora los dos servicios leen PostgreSQL con `default_transaction_read_only=on`. En los cinco pares documentados ya hay comparación de terreno (T), clima/iluminación (E) y volátiles (V).

| Sitio terrestre | Destino | Componentes con dato |
|---|---|---|
| campo-piedra-pomez | medusae-fossae | T, E, V |
| laguna-negra | jezero | T, E, V |
| payun-matru | pavonis-mons | T, E, V |
| ischigualasto | gale | T, E, V |
| laguna-antofagasta | jezero | T, E, V |

Las fuentes y la calidad de cada medición se conservan en los registros existentes, incluidos el DEM HRSC–MOLA de NASA/ESA/USGS, LOLA y los productos térmicos con su método y sus límites. Los modelos se identifican como tales; no se convierten en mediciones in situ. Ver `data/measurements/te-planetario.jsonl` y las fuentes de «Detalle de los datos y fuentes» de cada comparación.

En esa auditoría, G y O no estaban conectados: el motor sólo aceptaba espectros para G y faltaba una contraparte operacional para O. La integración del 15 de noviembre, descrita abajo, habilita G categórico y presenta el acceso terrestre como contexto.

## Integración G y O (15 nov 2026)

G v0 usa las categorías de mapas de `g-mapas.jsonl`: tipo de roca y origen por impacto. El TASI promedia sólo los bloques comparables y muestra su cobertura (1/2 no equivale a 2/2 de evidencia). No usa espectros CRISM/M3 ni inventa mineralogía. Jezero, Medusae Fossae, Meridiani y Utopia conservan G sin puntaje por falta de contraparte verificable; la geología terrestre disponible se muestra como contexto.

O presenta rutas, aeródromos y población de `o-tierra.jsonl`, con unidades y fuentes. No entra en la similitud porque no hay una contraparte equivalente en Marte o la Luna. Los avisos de datos pendientes se reservan a componentes sin información; los datos de un solo lado se identifican como contexto fuera del puntaje.

Ambas APIs complementan huecos del catálogo al leer esos dos datasets versionados, preservando mediciones existentes no nulas y su procedencia. No se ejecuta `db/load.py` ni `db/export.py` ni se escribe en PostgreSQL.
