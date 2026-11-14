# Manual de marca — HexAstra

Fuente de verdad de la identidad visual. Todo front, slide, gráfico o captura del proyecto lo respeta. Si una herramienta de diseño (por ejemplo Hallmark) propone otro tema, manda este manual: se puede tomar la estructura, nunca la paleta ni la tipografía.

Piezas de origen: el logo ([`assets/brand/hexastra-logo.png`](../assets/brand/hexastra-logo.png)) y la portada ([`docs/marca/referencia-portada.jpg`](marca/referencia-portada.jpg)). Todos los colores están **medidos en esas imágenes** (14 de noviembre de 2026), no elegidos a ojo. Los tokens están en [`css/brand.css`](../css/brand.css).

## 1. Logo

![Logo HexAstra](../assets/brand/hexastra-logo-512.png)

Parche de misión: obelisco de Buenos Aires sobre la Tierra de noche, Luna y Marte a los lados, satélite, galaxia, cinta celeste y blanca con el Sol de Mayo, y la palabra HexAstra.

- **Archivos:** `hexastra-logo.png` (original 1254 px), `hexastra-logo-512.png` (web), `apple-touch-icon.png` (180), `favicon-64.png` y `favicon-32.png`.
- **Fondo:** siempre sobre `--hx-noche` o negro. No ponerlo sobre fotos ni sobre fondos claros.
- **Tamaño mínimo:** 96 px de ancho en pantalla. Por debajo, usar solo la palabra HexAstra en Montserrat 700.
- **Aire:** dejar alrededor al menos un cuarto del ancho del logo libre.
- **No:** recortarlo, deformarlo, recolorearlo, ponerle sombras ni rehacer la palabra con otra letra.

## 2. Color

### Base (de la portada)

| Token | Hex | Uso | Contraste sobre `--hx-noche` |
|---|---|---|---|
| `--hx-noche` | `#070915` | Fondo de todo | — |
| `--hx-noche-2` | `#121830` | Paneles, tarjetas, fichas (derivado del fondo) | — |
| `--hx-linea` | `#2A3250` | Divisores y bordes (como la barra de la portada) | 1,58 (decorativo) |
| `--hx-texto` | `#F6F7FE` | Titulares y texto principal | 18,56 |
| `--hx-texto-2` | `#A9B0CA` | Texto secundario, pies, ayudas | 9,21 |
| `--hx-cian` | `#65D0EA` | **Acento principal:** subtítulos, enlaces, foco, etiqueta superior | 11,11 |

### De la imagen de la portada (red hexagonal sobre el terreno)

| Token | Hex | Uso | Contraste |
|---|---|---|---|
| `--hx-marte` | `#D87E4E` | Marte, puntaje alto ("muy parecido") | 6,62 |
| `--hx-violeta` | `#8651D3` | Puntaje bajo ("poco parecido"), nodos de la red | 3,90 → **solo gráficos o texto ≥ 24 px** |
| `--hx-cian-brillo` | `#56B2DE` | Líneas de la red, brillos, "menos estudiado" | 8,33 |

### Del logo (Argentina)

| Token | Hex | Uso | Contraste |
|---|---|---|---|
| `--hx-azul-orbita` | `#2B77E1` | Anillos, bordes destacados, botón primario con texto blanco grande | 4,56 → texto ≥ 18 px |
| `--hx-celeste` | `#729CD8` | La Tierra en mapas y leyendas; dato modelado | 7,05 |
| `--hx-sol` | `#D4964E` | "Dato a completar", avisos, la brecha de lo que la Tierra no imita | 7,81 |
| `--hx-luna` | `#B6AEB7` | La Luna en mapas y leyendas | 9,19 |

### Reglas de color

- **Fondo oscuro siempre** (azul noche, como pide el documento del proyecto). No hay tema claro en la app. Para imprimir, la marca va sobre blanco solo en texto negro + un acento.
- **Escala de puntaje:** de violeta (poco parecido) a naranja óxido (muy parecido), el mismo par de colores que la red de la portada. Nunca rojo/verde.
- **Cuerpos:** la Tierra en celeste, Marte en óxido y la Luna en gris luna, en mapas, chips y leyendas, siempre con nombre escrito (el color no es la única señal).
- **Calidad del dato:** medido en cian, modelado en celeste y a completar en dorado del sol, siempre con la palabra en el chip.
- El cian es el único acento de interfaz. Óxido, violeta, celeste, sol y luna son **semánticos**: solo aparecen cuando significan algo.

## 3. Tipografía

| Rol | Familia | Peso | Ejemplo en la portada |
|---|---|---|---|
| Titulares, marca escrita | **Montserrat** | 700 | "HexAstra" |
| Subtítulos | Montserrat | 500, en `--hx-cian` | "Análogos terrestres de la Luna y Marte" |
| Etiqueta superior | Montserrat | 600, mayúsculas, espaciado 0,14 em, en `--hx-cian` | "NASA SPACE APPS · EQUIPO" |
| Texto y datos | **Open Sans** | 400 y 600 | "Mapa interactivo para entrenamiento…" |

- Las dos familias vienen de Google Fonts (`css/brand.css`). No se suma una tercera.
- Una sola etiqueta superior por pantalla (la de la marca o la sección principal), no arriba de cada título. Es un rasgo de la portada, no un adorno repetible.
- Cifras con unidad y fuente: los datos se escriben en Open Sans 600, con la unidad al lado.

## 4. Imagen y recursos gráficos

- **Motivo de marca:** la red de líneas finas entre nodos (hexágonos) sobre el terreno, en cian y violeta brillantes. Se usa como textura sutil o para unir puntos análogos (Tierra ↔ Luna/Marte), nunca como relleno decorativo sin sentido.
- **Fotografía e imágenes de satélite:** reales y con crédito (NASA, ESA, JAXA, USGS…). No usar imágenes generadas por IA como si fueran datos.
- **Mapas:** los mapas base tienen que convivir con el fondo noche (versiones oscuras o satelitales). Los puntos se marcan con el color del cuerpo y un anillo `--hx-cian` cuando están seleccionados.

## 5. Voz

- En español rioplatense claro, sin jerga innecesaria.
- Honesta: dice qué se parece, cuánto, qué no, y qué dato falta. Nada de cifras sin fuente.
- El objetivo se dice simple: "Análogos terrestres de la Luna y Marte".

## 6. Checklist antes de publicar

- [ ] Fondo `--hx-noche`, acento `--hx-cian` y solo colores de esta lista.
- [ ] Montserrat para titulares y Open Sans para texto, sin otras familias.
- [ ] Logo sin modificar, sobre fondo oscuro y con aire.
- [ ] Texto con contraste ≥ 4,5:1 (violeta y azul órbita solo grandes o en gráficos).
- [ ] Puntaje de violeta a óxido; cuerpos y calidad del dato con su color y su palabra.
- [ ] Comparativa Tierra | destino visible (decisión de producto, `CLAUDE.md`).
