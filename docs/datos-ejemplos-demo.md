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

Las fuentes y la calidad de cada medición se conservan en los registros existentes, incluidos el DEM HRSC–MOLA de NASA/ESA/USGS, LOLA y los productos térmicos con su método y sus límites. Los modelos se identifican como tales; no se convierten en mediciones in situ. Ver `data/measurements/te-planetario.jsonl` y las fuentes de «Datos lado a lado y fuentes» de cada comparación.

G y O no se completaron artificialmente: el motor actual exige espectros/mineralogía comparables para G y todavía no tiene una contraparte operacional implementada para O. Una descripción de un ejemplo, una clase geológica o una facilidad de acceso terrestre no reemplaza esas métricas. Para habilitarlas se necesita una propuesta de definición y correspondencia, fuentes para ambos cuerpos y validación independiente; no basta con rellenar un nulo.
