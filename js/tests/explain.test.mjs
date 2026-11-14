// Tests de js/explain.js y del contrato de marcado del front. Corre con: node --test js/tests
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..");
const { explainMatch, componentScore, formatScore } = require("../explain.js");

// Forma real de /tasi (earth-service): componentes con score 0–100, available y reason.
const liveMatch = {
  score: 47.4,
  components: {
    G: { score: null, available: false, reason: "No sourced spectral vector." },
    T: { score: 80.5, available: true, reason: null },
    E: { score: 0.09, available: true, reason: null },
    V: { score: 61.67, available: true, reason: null },
    O: { score: null, available: false, reason: "No comparable metric." },
  },
};

test("sin why/breaks del servicio, usa el componente con dato más alto y el más bajo", () => {
  const ex = explainMatch(liveMatch);
  assert.equal(ex.why, "Lo más parecido es terreno (T), 80,5 de 100.");
  assert.equal(ex.breaks, "Lo menos parecido es clima e iluminación (E), 0,1 de 100.");
});

test("los componentes sin dato quedan como dato a completar, no como cero", () => {
  const ex = explainMatch(liveMatch);
  assert.deepEqual(ex.missing, ["geología (G)", "operación (O)"]);
  assert.ok(!ex.why.includes("geología"));
});

test("respeta why, breaks y missing cuando los manda el servicio o el respaldo local", () => {
  const ex = explainMatch(
    { why: "Ignimbritas y relieve eólico.", breaks: "La gravedad no se emula.", missing: ["slope"], components: liveMatch.components },
    (k) => (k === "slope" ? "pendiente" : k)
  );
  assert.equal(ex.why, "Ignimbritas y relieve eólico.");
  assert.equal(ex.breaks, "La gravedad no se emula.");
  assert.deepEqual(ex.missing, ["pendiente"]);
});

test("con un solo componente con dato no inventa en qué se separa", () => {
  const ex = explainMatch({ components: { V: { score: 70, available: true }, G: { score: null, available: false } } });
  assert.equal(ex.why, "Lo más parecido es volátiles o hielo (V), 70 de 100.");
  assert.match(ex.breaks, /un solo componente con dato/);
  assert.deepEqual(ex.missing, ["geología (G)"]);
});

test("sin componentes devuelve textos vacíos y nada a completar", () => {
  assert.deepEqual(explainMatch({}), { why: "", breaks: "", missing: [] });
  assert.deepEqual(explainMatch(null), { why: "", breaks: "", missing: [] });
});

test("componentScore acepta la forma del respaldo local (0–1) y la del servicio (0–100)", () => {
  assert.equal(componentScore(0.5), 50);
  assert.equal(componentScore(73), 73);
  assert.equal(componentScore({ score: 12.3, available: true }), 12.3);
  assert.equal(componentScore({ score: null, available: false }), null);
  assert.equal(componentScore(undefined), null);
});

test("formatScore usa coma decimal y no muestra NaN", () => {
  assert.equal(formatScore(53.68), "53,7");
  assert.equal(formatScore(52), "52");
  assert.equal(formatScore(null), "sin puntaje");
  assert.equal(formatScore("x"), "sin puntaje");
});

test("index.html conserva los ids que leen app.js y easy.js", () => {
  const html = readFileSync(join(ROOT, "index.html"), "utf8");
  const ids = [
    "mode-easy", "mode-advanced", "btn-metodo", "btn-fuentes", "easy-app",
    "layer-osm", "layer-esri", "layer-gibs-tc", "layer-gibs-lst", "gibs-date",
    "layer-opm", "layer-mola", "layer-shaded", "api-status", "finder-target",
    "finder-features", "finder-continent", "finder-country", "finder-gamma",
    "finder-gamma-val", "finder-mask", "btn-buscar", "finder-results",
    "site-buttons", "map-earth", "map-mars", "map-right-label", "panel",
    "modal-bg", "fuentes-anchor",
  ];
  for (const id of ids) assert.ok(html.includes(`id="${id}"`), `falta #${id}`);
  // explain.js tiene que cargarse antes que app.js y easy.js, que lo usan.
  const order = ["js/config.js", "js/api.js", "js/api-stub.js", "js/explain.js", "js/app.js", "js/easy.js"].map((s) => html.indexOf(`src="${s}"`));
  assert.ok(order.every((i, k) => i > 0 && (k === 0 || i > order[k - 1])), "orden de scripts roto");
});

test("la tabla de lo que la Tierra no puede imitar cita su fuente y no inventa la radiación", () => {
  const html = readFileSync(join(ROOT, "index.html"), "utf8");
  assert.match(html, /nssdc\.gsfc\.nasa\.gov/);
  assert.match(html, /consultadas el 14\/11\/2026/);
  assert.match(html, /Radiación en superficie<\/th><td colspan="3"[^>]*><span class="chip chip-warn">Dato a completar/);
});

test("el modo avanzado ya no toma el par de paired_mars_ids", () => {
  const app = readFileSync(join(ROOT, "js", "app.js"), "utf8");
  assert.ok(!/paired_mars_ids\.(map|includes)/.test(app), "app.js vuelve a usar paired_mars_ids para el par");
  assert.match(app, /function focusTarget\(/);
});
