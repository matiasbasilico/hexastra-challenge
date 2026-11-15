---
name: HexAstra
description: Análogos terrestres de la Luna y Marte, con datos citados y la brecha de lo que la Tierra no puede imitar.
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

# HexAstra — sistema de diseño

La fuente de verdad de la identidad es [`docs/marca.md`](docs/marca.md) y sus tokens [`css/brand.css`](css/brand.css). Este archivo los traduce a reglas para pantallas nuevas; si algo choca, manda el manual. Ninguna herramienta (Hallmark, Impeccable u otra) cambia paleta, tipografía ni logo.

## Overview

Una herramienta de evidencia. En la variante inmersiva (`index.html`) la Tierra 3D completa es el lienzo y todos los sitios del catálogo están marcados. Los controles son piezas flotantes: elegir un punto abre la comparación, y misión, lista y explicación se revelan al presionarlas. El planeta conserva su volumen completo y se acomoda para que el sitio y el destino permanezcan visibles. La marca vive en el cian del foco y la selección, los colores de cada cuerpo y el puntaje de violeta a óxido. La variante clásica (`classic.html`) conserva el avanzado y el fácil de tres pasos.

## Colors

- **Fondo:** `noche` en todo; `noche-2` para paneles, fichas y controles; `linea` para divisores y bordes. No hay tema claro.
- **Acento único de interfaz:** `cian` (foco, selección, enlaces, acción primaria con texto `noche`). `cian-brillo` es su hover.
- **Semánticos (solo cuando significan algo):** Tierra `celeste`, Marte `marte`, Luna `luna`; puntaje de `violeta` (poco parecido) a `marte` (muy parecido), nunca rojo/verde; calidad del dato: medido `cian`, modelado `celeste`, a completar `sol`, siempre con la palabra.
- `violeta` y `azul-orbita` no se usan en texto chico (contraste 3,9 y 4,6): solo gráficos o cifras de 24 px o más.

## Typography

Montserrat 700 para titulares y la marca escrita; Montserrat 600 en mayúsculas con 0,14 em solo para la única etiqueta superior de la pantalla. Open Sans 400/600 para texto y datos; las cifras en Open Sans 600 con `tabular-nums` y la unidad al lado. No se suma una tercera familia.

## Layout

- **Inmersivo:** lienzo de 100dvw × 100dvh, sin scroll de página. Globo completo, sin corte por los bordes, piezas flotantes con margen de 32 px (20 px bajo 1100, 16 px en celular). Los puntos son círculos discretos; el seleccionado muestra su posición en el ranking y un anillo cian.
- **Con un sitio seleccionado:** globo Tierra a la izquierda y ficha flotante del destino a la derecha, ambos puntos marcados. Bajo 760 px, globo arriba y ficha debajo, sin superposición; solo el detalle de la ficha se desplaza. Cerrar recupera el lienzo completo y devuelve el foco al punto.
- **Clásico:** contenedor hasta 1520 px con gutter de 40 px (24 px bajo 60 rem, 16 px bajo 40 rem).
- Escritorio desde 960 × 640 px: cabecera compacta y espacio de trabajo ajustado al alto disponible, sin scroll de página; listas y fichas largas se desplazan dentro de sus paneles. En ventanas menores vuelve el flujo de documento.
- Los límites físicos se abren desde «Límites de la Tierra» en un diálogo con foco contenido, cierre con Escape y retorno al botón. Los lugares destacados del modo fácil son desplegables.
- Avanzado: barra compacta de controles arriba de los mapas; lista de sitios, mapa de la Tierra, mapa del destino y ficha del par con scroll interno; el resumen de búsqueda queda al pie.
- Espacios generosos y textos largos fuera de la pantalla principal (el detalle del método vive en «Cómo se calcula»).

## Elevation & Depth

Plano y tonal: la profundidad sale del paso `noche` → `noche-2` y de bordes `linea`, sin sombras. Sin cajas anidadas: un panel no contiene otro panel con borde.

## Shapes

Radio 8 px en controles, 10 px en paneles y fichas, píldora en chips. Pines de mapa circulares con borde `noche` y anillo cian de 3 px al seleccionarse.

## Components

- **Botón:** 40 px de alto, `noche-2` con borde `linea`; hover con borde y texto cian. Primario cian con texto noche.
- **Segmentado (modo, cuerpo, mapa base):** contenedor `noche-2`, opción activa en cian (o en el color del cuerpo para Luna/Marte).
- **Chip:** píldora con borde y texto del color semántico, sin relleno.
- **Fila seleccionable (sitio, resultado, destino):** `noche-2` con borde `linea`; seleccionada con fondo cian al 12 % y borde cian.
- **Puntaje:** cifra Montserrat 700 coloreada en la escala violeta → óxido y barra de 4 px con el mismo degradado.
- **Mapa:** marco `noche-2` con etiqueta del cuerpo y su punto de color; controles de Leaflet en `noche-2`.
- **Globo terrestre:** textura ilustrativa de Earth3D con crédito visible, halo cian tenue y los mismos pines del mapa 2D. En la vista inmersiva rota a velocidad sideral real (23,9345 h por vuelta), con pausa manual, durante la interacción y al abrir una misión o comparativa. Con movimiento reducido queda detenido. La selección centra el sitio y mantiene su longitud sobre la textura. Flechas y controles de zoom accesibles, movimiento reducido respetado. Sin WebGL vuelve a Leaflet.
- **Mayor similitud:** hasta cinco sitios con los mayores TASI positivos de la misión emiten dos anillos cian suaves, con fases escalonadas. Se actualizan con destino, enfoque, región y máscara; al recalcular desaparece el pulso anterior. Es una posición relativa en el ranking, no un umbral de analogía fuerte. Con movimiento reducido se muestra un anillo fijo.
- **Selección de mundo:** Marte y Luna en cards cuadradas, cada una con una esfera 3D texturada, color de cuerpo y selección cian con tilde. Radios nativos accesibles, también operables con teclado. Un canvas compartido renderiza ambas cards; sin WebGL se mantienen las imágenes esféricas. La configuración tiene tres pasos: mundo, destino y enfoque. Atrás conserva el borrador y cerrar lo descarta; solo el último paso aplica la misión. Cada paso entra completo en el viewport, incluidos región y filtros abiertos.
- **Ficha del destino:** descripción breve, tipo de terreno y coordenadas desde el catálogo; contexto histórico con fecha y enlace a NASA cuando está verificado. Las regiones anunciadas en 2022 se identifican como un anuncio histórico, no como aterrizajes. Las fechas ausentes quedan a completar. La ficha no incorpora datos al cálculo TASI.
- **Comparables:** filtro visual activo por defecto, disponible en un botón flotante y en la misión. Oculta los sitios sin TASI para el destino, región y máscara actuales. Al quitarlo, esos puntos se muestran más pequeños y tenues, sin pulso. Un puntaje válido de cero sigue siendo comparable. Si el sitio está fuera de la región, la ficha permite quitar ese filtro y calcular el par.
- **Responsive:** cards cuadradas desde 320 px, controles dentro del viewport y áreas seguras de móviles con notch. En horizontal se conserva Tierra | destino lado a lado con ficha compacta; en vertical se apilan, con scroll solo en sus piezas. La misión avanza por pantallas completas sin scroll, manteniendo cierre y acciones visibles en cada paso.
- **Ficha flotante del punto:** sitio, mapa del destino marcado, TASI grande, cobertura, explicación de analogía y brecha, componentes sin datos en chips dorados y datos/fuentes plegables. Se abre con clic o teclado, permite seguir girando la Tierra y se cierra con Escape o Cerrar. El clásico conserva el modal del punto.
- **Texto de literatura:** bloque con borde punteado celeste, rotulado «Documentado en la literatura», separado del puntaje.

## Do's and Don'ts

- Do: todo dato desde la API, con su fuente; lo null como «A completar».
- Do: foco visible cian inmediato, `prefers-reduced-motion` respetado, 320 px sin scroll horizontal.
- Don't: colores fuera de `css/brand.css`, una tercera tipografía, el logo recoloreado o sobre fondos claros.
- Don't: más de una etiqueta superior por pantalla, cajas dentro de cajas, sombras decorativas.
- Don't: esconder un lado de la comparativa mientras hay un sitio seleccionado ni mezclar el texto de literatura con el puntaje. En el arranque inmersivo se muestra solo el globo, según el pedido del usuario.

### Fuentes del contexto de misión y rotación

- NASA GISS, [Mars24 — Mars Lander Missions](https://www.giss.nasa.gov/tools/mars24/help/landers.html), actualizado 2023-12-09: Perseverance (18/02/2021), Curiosity (06/08/2012, UTC), Opportunity (25/01/2004) y Viking 2 (03/09/1976).
- NASA, [comunicado 22-089](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/), 19/08/2022: anuncio histórico de regiones candidatas cercanas al polo sur. Los puntos del catálogo son anclas geográficas, no sitios de aterrizaje confirmados.
- NASA NSSDCA, [Earth Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html), actualizado 15/11/2024: período de rotación sideral de 23,9345 horas. La animación reproduce esa velocidad; no representa la orientación astronómica ni la iluminación actuales.

Consulta de las tres fuentes: 14/11/2026 (America/Argentina/Buenos_Aires). Contexto editorial de interfaz; no son nuevas mediciones ni cambian los puntajes.
