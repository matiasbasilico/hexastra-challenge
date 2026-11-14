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

Una herramienta de evidencia, no una landing. El fondo azul noche de la portada sostiene dos mapas (la Tierra y el destino) que son los protagonistas, y una ficha que explica el par: qué se parece, cuánto, qué no y qué dato falta. La marca vive en detalles precisos (el cian del foco y la selección, los colores de cada cuerpo, el puntaje de violeta a óxido), no en ornamento. Modo: Operate en el avanzado; el fácil guía en tres pasos.

## Colors

- **Fondo:** `noche` en todo; `noche-2` para paneles, fichas y controles; `linea` para divisores y bordes. No hay tema claro.
- **Acento único de interfaz:** `cian` (foco, selección, enlaces, acción primaria con texto `noche`). `cian-brillo` es su hover.
- **Semánticos (solo cuando significan algo):** Tierra `celeste`, Marte `marte`, Luna `luna`; puntaje de `violeta` (poco parecido) a `marte` (muy parecido), nunca rojo/verde; calidad del dato: medido `cian`, modelado `celeste`, a completar `sol`, siempre con la palabra.
- `violeta` y `azul-orbita` no se usan en texto chico (contraste 3,9 y 4,6): solo gráficos o cifras de 24 px o más.

## Typography

Montserrat 700 para titulares y la marca escrita; Montserrat 600 en mayúsculas con 0,14 em solo para la única etiqueta superior de la pantalla. Open Sans 400/600 para texto y datos; las cifras en Open Sans 600 con `tabular-nums` y la unidad al lado. No se suma una tercera familia.

## Layout

- Contenedor hasta 1520 px con gutter de 40 px (24 px bajo 60 rem, 16 px bajo 40 rem).
- **Comparativa lado a lado siempre:** Tierra | destino con los dos mapas a la vez y los puntos marcados; bajo 560 px los mapas se apilan, más anchos, y siguen visibles a la vez.
- Avanzado: barra compacta de controles arriba de los mapas; lista de sitios, mapa de la Tierra, mapa del destino y ficha del par con alto fijo y scroll interno; la búsqueda completa va debajo.
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
- **Texto de literatura:** bloque con borde punteado celeste, rotulado «Documentado en la literatura», separado del puntaje.

## Do's and Don'ts

- Do: todo dato desde la API, con su fuente; lo null como «A completar».
- Do: foco visible cian inmediato, `prefers-reduced-motion` respetado, 320 px sin scroll horizontal.
- Don't: colores fuera de `css/brand.css`, una tercera tipografía, el logo recoloreado o sobre fondos claros.
- Don't: más de una etiqueta superior por pantalla, cajas dentro de cajas, sombras decorativas.
- Don't: esconder la comparativa Tierra | destino ni mezclar el texto de literatura con el puntaje.
