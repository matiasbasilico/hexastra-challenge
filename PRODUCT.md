# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primario: el jurado de NASA Space Apps Challenge 2026 y el propio equipo HexAstra.** Tienen minutos, no horas: necesitan entender qué sitio de la Tierra se parece a un destino de la Luna o de Marte, cuánto, en qué no, y de dónde sale cada dato. Confirmado por el usuario el 14/11/2026.
- El modo fácil (3 pasos) es la puerta de entrada; el modo avanzado (comparativa lado a lado) es la evidencia que el jurado revisa.

## Product Purpose

Identificar y caracterizar análogos terrestres nuevos, poco estudiados, de las posibles bases lunares permanentes y de los sitios de aterrizaje y exploración en Marte, con datos abiertos de NASA y de otras agencias (desafío oficial: `docs/desafio.md`). El éxito es que alguien pueda justificar una analogía con datos, por dimensión, y ver qué no se puede imitar en la Tierra.

## Positioning

- No es un mapa de análogos famosos: busca los menos estudiados (Atacama, Haughton, Islandia, Hawái y la Antártida sirven como línea de base, no como hallazgo).
- La analogía se justifica por dimensión con la matriz V = [G, T, E, Vo, O] y el índice TASI (propuesta del equipo), con cobertura explícita: un componente sin dato en los dos lados no puntúa.
- Lo que la Tierra no puede imitar (gravedad, vacío lunar, atmósfera marciana fina, radiación) se muestra como brecha cuantificada, fuera del puntaje.

## Operating Context

- Demo en vivo y link público (Cloudflare Pages) con servicios en la Mac del equipo vía túnel o proxy del mismo origen.
- Flujo principal: elegir destino (Luna o Marte), elegir un enfoque de misión, buscar en el mundo o por continente y país, y leer el par Tierra | destino con su ficha.
- Modo avanzado: arranca con los pares documentados en la literatura (`GET {earth}/examples`) y permite la búsqueda completa sobre los sitios del catálogo.

## Capabilities and Constraints

- Front estático vanilla (HTML, CSS, JS): Tierra en globo Three.js inspirado en Earth3D, con alternativa Leaflet 2D; destinos en Leaflet. Puntos de la API, sin framework, sin Cesium, sin grilla H3 (`CLAUDE.md` §2). Cambio de vista terrestre autorizado por el usuario el 14/11/2026.
- Al tocar un punto del globo se abre un modal con el sitio, su destino, el puntaje TASI, por qué se parece, en qué no y los componentes sin datos. Si el par no tiene puntaje, se indica; nunca hereda el de otro sitio. La ficha lateral y ambos puntos siguen sincronizados.
- **Todo el contenido sale de la API** (planetary-service y earth-service sobre PostGIS): sitios, destinos, ranking TASI, why/breaks, método y presets (`/method`), valores físicos de referencia (`/bodies`), ejemplos (`/examples`). El front solo tiene textos de interfaz.
- Sin servicios, la página avisa «servicio no disponible» y no muestra datos.
- La comparativa lado a lado Tierra | destino, con los dos puntos marcados y sincronizados, es decisión de producto: ningún rediseño la saca ni la esconde.
- Contratos que no se rompen: `js/api.js`, `js/config.js` y los ids que lee el JS.
- Radiación de referencia en `/bodies`: Tierra, promedio exterior modelado por UNSCEAR 2024; Luna, medición Chang'e-4/LND publicada por Zhang et al. (2020); Marte, RAD/MSL. La fuente explicita la conversión diaria, el contexto y la diferencia entre dosis efectiva y equivalente; no son mediciones del sitio elegido ni entran en TASI.

## Brand Commitments

- Identidad HexAstra según `docs/marca.md` y `css/brand.css`: fondo azul noche, acento cian, Montserrat + Open Sans, logo de `assets/brand/` sin modificar, puntaje de violeta a óxido, cuerpos con su color (Tierra celeste, Marte óxido, Luna gris) y calidad del dato con su color y su palabra. Ninguna herramienta de diseño reemplaza paleta, tipografía ni logo.
- Voz: español rioplatense claro, honesta («qué se parece, cuánto, qué no, y qué dato falta»), sin cifras sin fuente.

## Evidence on Hand

- Catálogo terrestre de 60 sitios y destinos de la Luna y Marte servidos por la API, cada uno con su fuente de coordenadas.
- Cinco pares documentados en la literatura con fuentes (`services/earth/data/literature_examples.json`, vía `/examples`).
- Valores NSSDC y RAD/MSL con fuente en `/bodies`.
- No hay testimonios, usuarios, métricas de uso ni premios: no se inventan.

## Product Principles

1. Nada inventado: todo valor lleva fuente; lo no verificado se muestra como «dato a completar».
2. Decir qué se parece, cuánto y qué no, por dimensión, antes que dar un número solo.
3. La comparación Tierra | destino siempre a la vista.
4. Lo que la Tierra no puede imitar se ve, pero no entra al puntaje.
5. Escala local (un cráter, un valle), no regiones enteras.

## Accessibility & Inclusion

Contraste mínimo 4,5:1 en texto (el violeta y el azul órbita solo en gráficos o texto grande), foco visible, movimiento reducido respetado, y uso en celular a 320 px sin scroll horizontal.
