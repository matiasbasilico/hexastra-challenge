# Revisión con Impeccable: modo avanzado

Skill [Impeccable](https://github.com/pbakaus/impeccable) v4.9.1 (Apache-2.0), clonada fuera del repo en `~/orca/workspaces/_vendor/impeccable` y seguida leyendo sus playbooks (`SKILL.md` y `reference/*.md`). Fecha: 14/11/2026.

- **init:** [`PRODUCT.md`](../../PRODUCT.md), a partir de `CLAUDE.md` y `docs/desafio.md`; el usuario confirmó el usuario principal (jurado de NASA Space Apps y el equipo).
- **document:** [`DESIGN.md`](../../DESIGN.md), que traduce `docs/marca.md`. El manual manda: Impeccable no cambió paleta, tipografía ni logo.
- **critique:** `⚠️ DEGRADED: single-context`. El playbook pide dos subagentes aislados; no se pidieron subagentes, así que A (revisión de diseño) y B (detector) corrieron en este mismo contexto, A antes de leer el detector.
- **Detector:** `impeccable detect --json` sobre una copia renderizada del modo avanzado (con el primer par cargado) y sobre la URL de la página con los servicios en 19502 y 19503.

## Critique (heurísticas de Nielsen, 0 a 4)

| # | Heurística | Antes | Después | Qué cambió |
|---|---|---|---|---|
| 1 | Visibilidad del estado | 3 | 3 | Estado de servicios corto; carga del par anunciada. |
| 2 | Lenguaje del usuario | 2 | 3 | γ, NDVI y M(x) pasaron a «Opciones avanzadas»; los códigos de la máscara se leen en palabras. Las razones de cada componente siguen en inglés porque vienen así de la API (marcadas `lang="en"`). |
| 3 | Control y libertad | 3 | 3 | Menús que se cierran con Escape o tocando afuera. |
| 4 | Consistencia | 3 | 3 | Capas en el mismo menú en los dos mapas. |
| 5 | Prevención de errores | 2 | 3 | G y O (y cualquier componente sin dato para el destino) quedan deshabilitados con «sin datos todavía». |
| 6 | Reconocer antes que recordar | 2 | 3 | Peso efectivo en % tras renormalizar, en lugar de «2.0». |
| 7 | Flexibilidad | 3 | 3 | Misión por presets de `/method` y «Pesos propios» al mover a mano. |
| 8 | Estética y minimalismo | 1 | 3 | Barra de 3 desplegables; pesos, opciones técnicas y capas plegados; ficha más corta con desglose y fuentes plegables; sin cajas anidadas. |
| 9 | Errores y recuperación | 3 | 3 | «Servicio no disponible» claro en cada zona. |
| 10 | Ayuda | 3 | 3 | «Cómo se calcula» con el contenido de `/method`. |
| | **Total** | **25/40** | **30/40** | |

**Carga cognitiva (8 ítems):**
- **Antes, 4 fallas (alta):** foco único, opciones mínimas (7 capas y 5 pesos siempre visibles), revelado progresivo y una ficha sin agrupar.
- **Después, 1 falla (baja):** la lista de 65 sitios sigue siendo larga, aunque agrupada en «Pares documentados en la literatura» y «Todo el catálogo».

## Audit (técnico, 0 a 4 por dimensión)

| Dimensión | Antes | Después | Hallazgo clave |
|---|---|---|---|
| Accesibilidad | 3 | 3 | Foco cian visible; texto en inglés de la API sin `lang` (corregido); controles nativos (`details`, `select`). |
| Rendimiento | 3 | 3 | Sin Chart.js; un `POST /tasi` por destino en caché. |
| Tema | 4 | 4 | Solo tokens de `css/brand.css` (lo valida un test). |
| Responsive | 3 | 3 | 320 px sin scroll horizontal; mapas apilados bajo 560 px. |
| Integridad de la implementación | 3 | 4 | Detector limpio en el avanzado. |
| **Total** | **16/20** | **17/20** | |

## Hallazgos P0–P3

**Antes**

- **P1, prevención de errores:** los pesos de G y O se podían mover aunque ningún destino tiene esos datos; el control no tenía efecto y engañaba.
- **P1, minimalismo:** 8 controles de capas y el formulario completo, con γ, máscara y textos largos, competían con la comparativa.
- **P2, reconocimiento:** pesos crudos («0,20») sin el porcentaje que realmente pesa después de renormalizar.
- **P2, lenguaje:** las razones de los componentes llegaban en inglés sin `lang`, y la máscara mostraba códigos (`ndvi_unavailable`).
- **P2, ficha recargada:** cuatro chips «Dato a completar», una tabla, un bloque de componentes repetido y avisos en caja.
- **P3, detector `side-tab` / `border-accent-on-rounded`:** borde superior de 3 px sobre radio de 10 px en la tabla de límites.
- **P3, lista del avanzado:** franja cian de 3 px a la izquierda del sitio activo (el craft-floor la marca como tic).

**Después**

- Resueltos todos los anteriores: G y O deshabilitados con «sin datos todavía», peso efectivo en %, barra de 3 desplegables, menús plegados, ficha agrupada, `lang="en"` en el texto de la API, máscara en palabras, borde de 3 px fuera (el título de la tabla de límites pasó al dorado del sol, el color del manual para esa brecha) y selección sin franja lateral.
- **Queda, P3:** las razones de los componentes siguen en inglés en la API; habría que traducirlas en earth-service.
- **Queda, falso positivo por decisión de marca:** el detector marca Open Sans como «overused-font», pero la tipografía la fija `docs/marca.md` («the brief wins»).
- **Conflicto registrado:** el craft-floor de Impeccable prohíbe las etiquetas superiores (eyebrow). El manual de marca exige una sola por pantalla («NASA SPACE APPS · EQUIPO»), así que queda esa y ninguna otra; la del país arriba del título de la ficha pasó abajo del título.

## Detector, antes y después

| Objetivo | Antes | Después |
|---|---|---|
| Modo avanzado renderizado | 1 warning (`side-tab`) | 0 |
| Modo avanzado, `--scope layout` | 0 | 0 |
| Página (URL, modo fácil) | 2 warnings (`border-accent-on-rounded`, `overused-font`) | 1 (`overused-font`, impuesto por la marca) |
