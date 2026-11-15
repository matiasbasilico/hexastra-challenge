// Tests de js/explain.js y del contrato de marcado del front. Corre con: node --test js/tests
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync, existsSync } from "node:fs";
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

test("classic.html conserva los ids que leen app.js y easy.js", () => {
  const html = readFileSync(join(ROOT, "classic.html"), "utf8");
  const ids = [
    "mode-easy", "mode-advanced", "btn-metodo", "btn-fuentes", "easy-app",
    "layer-osm", "layer-esri", "layer-gibs-tc", "layer-gibs-lst", "gibs-date",
    "layer-opm", "layer-mola", "layer-shaded", "api-status", "finder-target",
    "finder-features", "finder-region", "finder-mission", "finder-gamma",
    "finder-gamma-val", "finder-mask", "btn-buscar", "finder-results",
    "site-buttons", "map-earth", "map-mars", "map-right-label", "panel",
    "modal-bg", "fuentes-anchor", "limits-rows", "limits-notes", "method-body", "finder-mask-ndvi",
  ];
  for (const id of ids) assert.ok(html.includes(`id="${id}"`), `falta #${id}`);
  // explain.js tiene que cargarse antes que app.js y easy.js, que lo usan.
  const order = ["js/config.js", "js/api.js", "js/api-stub.js", "js/explain.js", "js/limits.js", "js/app.js", "js/easy.js"].map((s) => html.indexOf(`src="${s}"`));
  assert.ok(order.every((i, k) => i > 0 && (k === 0 || i > order[k - 1])), "orden de scripts roto");
});

test("la tabla de lo que la Tierra no puede imitar sale de /bodies: classic.html no trae cifras", () => {
  const html = readFileSync(join(ROOT, "classic.html"), "utf8");
  const start = html.indexOf('<section class="limits"');
  const table = html.slice(start, html.indexOf("</section>", start));
  assert.ok(!/\d,\d/.test(table), "quedó una cifra escrita a mano en la tabla de límites");
  assert.match(table, /id="limits-rows"/);
  const limits = readFileSync(join(ROOT, "js", "limits.js"), "utf8");
  assert.match(limits, /getBodies\(\)/);
  assert.match(limits, /A completar/);
});

test("limits.js formatea en es-AR y escribe los valores muy chicos en notación científica", async () => {
  const src = readFileSync(join(ROOT, "js", "limits.js"), "utf8");
  const ctx = {};
  new Function("window", "document", src)(ctx, undefined);
  const { formatValue } = ctx.HexastraLimits;
  assert.equal(formatValue(3.73), "3,73");
  assert.equal(formatValue(1014), "1014");
  assert.equal(formatValue(3e-12), "3×10<sup>−12</sup>");
  assert.equal(formatValue(0.001), "1×10<sup>−3</sup>");
  assert.equal(formatValue(0.009), "9×10<sup>−3</sup>");
  assert.equal(formatValue(null), null);
});

test("la tabla conserva la dosis lunar y el día solar, con fuentes y sin pendientes", () => {
  const src = readFileSync(join(ROOT, "js", "limits.js"), "utf8");
  const bodies = JSON.parse(readFileSync(join(ROOT, "services", "planetary", "data", "bodies.json"), "utf8"));
  const elements = { "limits-rows": {}, "limits-notes": {} };
  const ctx = {};
  const document = { readyState: "loading", addEventListener() {}, getElementById: (id) => elements[id] };
  new Function("window", "document", src)(ctx, document);
  ctx.HexastraLimits.render(bodies);
  const rows = elements["limits-rows"].innerHTML;
  assert.match(rows, /9×10<sup>−4<\/sup>/);
  assert.match(rows, /1,369/);
  assert.match(rows, /708,7/);
  assert.match(rows, /día solar/);
  assert.doesNotMatch(rows, /A completar/);
  assert.match(elements["limits-notes"].innerHTML, /UNSCEAR/);
  assert.match(elements["limits-notes"].innerHTML, /PMC7518862/);
  assert.match(elements["limits-notes"].innerHTML, /magnitudes distintas/);
});

test("nada inventado en el front: sin sites.json, sin el índice viejo, sin presets ni γ propios", () => {
  const app = readFileSync(join(ROOT, "js", "app.js"), "utf8");
  const easy = readFileSync(join(ROOT, "js", "easy.js"), "utf8");
  const html = readFileSync(join(ROOT, "classic.html"), "utf8");
  for (const [name, src] of [["app.js", app], ["easy.js", easy], ["index.html", html]]) {
    assert.ok(!/sites\.json|catalog\.json|qualitative_scores|paired_mars_ids/.test(src), name + " usa datos del prototipo viejo");
    assert.ok(!/índice ambiental|\btMars\b|\bdiurnalRef\b|\bprecipScale\b|\belevScale\b/.test(src), name + " conserva el índice ambiental propio");
  }
  assert.ok(!/weights:\s*\{\s*G:\s*0\.\d/.test(easy), "easy.js tiene pesos de presets escritos a mano");
  assert.ok(!/gamma:\s*0\.75/.test(easy), "easy.js tiene un γ propio");
  assert.match(easy, /callApi\("getMethod"/);
  assert.match(app, /api\.getCandidates\(\)/);
  assert.ok(!/chart\.js/i.test(html), "Chart.js se cargaba solo para el índice viejo");
});

test("sin servicios, api-stub.js avisa que no están disponibles y no trae datos", async () => {
  const src = readFileSync(join(ROOT, "js", "api-stub.js"), "utf8");
  assert.ok(!/fetch\(|lat:|lon:|coord_source/.test(src), "el respaldo vuelve a tener datos o a leer archivos");
  const ctx = {};
  new Function("window", "module", src)(ctx, undefined);
  const stub = ctx.HexastraAPIStub;
  for (const m of ["getTargets", "rankAnalogs", "getMethod", "getBodies", "getFeatured", "getCandidates"]) {
    await assert.rejects(stub[m](), (e) => e.code === "SERVICE_UNAVAILABLE" && /no está disponible/.test(e.message));
  }
});

test("el avanzado arranca con los pares documentados de /examples, con su texto rotulado aparte", () => {
  const app = readFileSync(join(ROOT, "js", "app.js"), "utf8");
  assert.match(app, /api\.getExamples\(\)/);
  assert.match(app, /Documentado en la literatura/);
  assert.match(app, /getTargetVector\(target\.id\)/);
  assert.match(app, /why_es/);
  const html = readFileSync(join(ROOT, "classic.html"), "utf8");
  assert.ok(html.indexOf('id="finder-target"') < html.indexOf('class="workspace"'), "la barra de controles va arriba de los mapas");
});

test("avanzado minimalista: tres desplegables, pesos y opciones plegados, capas en un menú por mapa", () => {
  const html = readFileSync(join(ROOT, "classic.html"), "utf8");
  for (const id of ["finder-target", "finder-region", "finder-mission"]) assert.match(html, new RegExp('<select id="' + id + '"'));
  assert.match(html, /<details class="adv-menu" id="weights-menu">\s*<summary>Ajustar pesos<\/summary>/);
  assert.match(html, /<details class="adv-menu" id="options-menu">\s*<summary>Opciones avanzadas<\/summary>/);
  assert.ok(!/<details class="adv-menu"[^>]*open/.test(html), "los menús arrancan cerrados");
  assert.equal((html.match(/<details class="layers-menu"/g) || []).length, 2, "un menú Capas por mapa");
  const app = readFileSync(join(ROOT, "js", "app.js"), "utf8");
  assert.match(app, /sin datos todavía/);
  assert.match(app, /function refreshEffectiveWeights\(/);
  assert.match(app, /function componentAvailable\(/);
});

test("los archivos del prototipo viejo ya no están en data/", () => {
  for (const f of ["sites.json", "catalog.json", "climate-era5-1991-2020.json", "earth-sites.geojson", "mars-sites.geojson"]) {
    assert.ok(!existsSync(join(ROOT, "data", f)), "sigue data/" + f);
  }
});

test("la identidad sigue el manual de marca: brand.css primero, logo y favicons, sin otras familias", () => {
  const html = readFileSync(join(ROOT, "classic.html"), "utf8");
  const brand = html.indexOf('href="css/brand.css"');
  assert.ok(brand > 0 && brand < html.indexOf('href="css/style.css"'), "brand.css tiene que cargarse antes");
  assert.match(html, /src="assets\/brand\/hexastra-logo-512\.png"/);
  assert.match(html, /assets\/brand\/favicon-32\.png/);
  assert.ok(!/Hanken|Newsreader|IBM\+Plex/.test(html), "quedó una familia que no es de la marca");
  for (const f of ["style.css", "easy.css", "tokens.css"]) {
    const css = readFileSync(join(ROOT, "css", f), "utf8");
    assert.ok(!/oklch\(|#[0-9a-fA-F]{6}\b/.test(css), `${f} tiene un color fuera de brand.css`);
  }
});

test("los pines del avanzado conservan el número de ranking al elegir un sitio", () => {
  const app = readFileSync(join(ROOT, "js", "app.js"), "utf8");
  assert.match(app, /function earthIconFor\(/);
  assert.ok(!/rankIcon\(i \+ 1, true\)/.test(app), "todos los pines quedan resaltados a la vez");
  assert.ok(!/marker\.setIcon\(divIcon\(kind, sid === id\)\)/.test(app), "elegir un sitio vuelve a borrar el número");
});

test("el modo avanzado ya no toma el par de paired_mars_ids", () => {
  const app = readFileSync(join(ROOT, "js", "app.js"), "utf8");
  assert.ok(!/paired_mars_ids\.(map|includes)/.test(app), "app.js vuelve a usar paired_mars_ids para el par");
  assert.match(app, /function focusTarget\(/);
});
