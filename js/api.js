/**
 * Hexastra API calls layer
 * =============================================================================
 * Contrato estable para el front avanzado (js/app.js) y para el "easy mode"
 * que se construye en paralelo. Este archivo es la única capa de HTTP hacia
 * los microservicios. No pinta UI ni toca estilos.
 *
 * Servicios:
 *   planetary-service  (Moon/Mars catalog + feature vectors)  default :8766
 *   earth-service      (global Earth candidates + TASI)        default :8767
 *
 * Resolución de URLs (primera que exista gana), sin barra final:
 *   1. localStorage.HEXASTRA_PLANETARY_URL / localStorage.HEXASTRA_EARTH_URL
 *   2. window.HEXASTRA_CONFIG.planetaryUrl / earthUrl  (js/config.js)
 *   3. http://127.0.0.1:8766  y  http://127.0.0.1:8767
 *
 * El vector que circula entre getTargetVector y rankAnalogs cumple
 * contracts/feature_vector.schema.json
 *   components: { G, T, E, Vo, O }
 *   cada componente: { available, score_ready, reason, vector, vector_labels,
 *                      metrics: { name: { value, unit, source, is_real, quality } } }
 *
 * Funciones exportadas (también en window.HexastraAPI):
 *
 *   getServiceUrls()
 *     -> { planetary, earth }
 *
 *   health()
 *     -> Promise<{ planetary: object|null, earth: object|null, ok: boolean }>
 *     GET {planetary}/health y GET {earth}/health
 *
 *   getTargets(body)
 *     -> Promise<Array<SiteSummary>>
 *     body: "moon" | "mars"
 *     GET {planetary}/sites?body=
 *     SiteSummary: { id, name, short_name, body, lat, lon, coord_source, summary, tags }
 *
 *   getTargetVector(id)
 *     -> Promise<FeatureVector>
 *     GET {planetary}/sites/{id}/vector
 *
 *   getRegions()
 *     -> Promise<{ continents: Array<{ name: string,
 *          countries: Array<{ iso: string, name: string, count: number }> }> }>
 *     GET {earth}/regions
 *     continent names are Natural Earth CONTINENT values
 *     iso is ISO-3166-1 alpha-2
 *
 *   getFeatured()
 *     -> Promise<{ n, note, sites: Array<CandidateSummary> }>
 *     GET {earth}/featured
 *     Sitios base / atajos (featured=true), ordenados por featured_rank.
 *     Incluye análogos famosos como línea de base (Atacama, Hawái, Dry Valleys,
 *     Canarias, Devon Island/Haughton) y candidatos argentinos de la Puna.
 *     CandidateSummary añade: featured, featured_label, featured_rank, featured_note,
 *     highlight_less_studied, analog_types, country_iso, country_name, continent.
 *
 *   getCandidates({ continent, country }?)
 *     -> Promise<{ n, continent, country, sites: Array<CandidateSummary> }>
 *     GET {earth}/candidates?continent=&country=
 *     country: ISO-3166-1 alpha-2 (e.g. "AR")
 *
 *   rankAnalogs({ targetVector, weights, gamma, top, continent, country, applyMask })
 *     -> Promise<TasiResponse>
 *     POST {earth}/tasi
 *     targetVector: FeatureVector from getTargetVector (required)
 *     weights: { G, T, E, V, O }  (V maps to component Vo). Optional; default 0.2 each.
 *              Missing/unavailable components are dropped and the rest is renormalized.
 *     gamma: number, default 1.  Used in S_T = exp(-gamma * D_Mahalanobis)
 *     top: integer, default 5
 *     continent: Natural Earth continent name, optional
 *     country: ISO-3166-1 alpha-2, optional
 *     applyMask: boolean, default true  (NDVI > 0.15 or liquid water discards a site)
 *
 *     TasiResponse: {
 *       index: "TASI",
 *       formula, gamma, apply_mask, target, filter,
 *       n_candidates, n_discarded_by_mask, n_scored,
 *       matches: [{ site, score (0-100 or null), score_0_1, components, weights, coverage, mask }],
 *       discarded: [{ id, name, mask }]
 *     }
 *
 * Errores: las funciones rechazan con Error cuyo message incluye el status HTTP
 * y el detalle de FastAPI cuando está disponible.
 */
(function (root) {
  "use strict";

  function trimSlash(url) {
    return String(url || "").replace(/\/$/, "");
  }

  function fromStorage(key) {
    try {
      if (root.localStorage) {
        const v = root.localStorage.getItem(key);
        if (v) return trimSlash(v);
      }
    } catch (e) { /* private mode */ }
    return null;
  }

  function getServiceUrls() {
    const cfg = root.HEXASTRA_CONFIG || {};
    return {
      planetary:
        fromStorage("HEXASTRA_PLANETARY_URL") ||
        trimSlash(cfg.planetaryUrl) ||
        "http://127.0.0.1:8766",
      earth:
        fromStorage("HEXASTRA_EARTH_URL") ||
        trimSlash(cfg.earthUrl) ||
        "http://127.0.0.1:8767",
    };
  }

  async function request(url, options) {
    const r = await fetch(url, Object.assign({ cache: "no-store" }, options || {}));
    if (!r.ok) {
      let detail = r.statusText;
      try {
        const body = await r.json();
        if (body && body.detail) {
          detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        }
      } catch (e) { /* keep statusText */ }
      const err = new Error(r.status + " " + detail);
      err.status = r.status;
      throw err;
    }
    return r.json();
  }

  async function health() {
    const urls = getServiceUrls();
    const out = { planetary: null, earth: null, ok: false };
    try {
      const p = await request(urls.planetary + "/health");
      if (p && p.ok) out.planetary = p;
    } catch (e) { out.planetaryError = e.message; }
    try {
      const e = await request(urls.earth + "/health");
      if (e && e.ok) out.earth = e;
    } catch (e) { out.earthError = e.message; }
    out.ok = !!(out.planetary && out.earth);
    out.urls = urls;
    return out;
  }

  async function getTargets(body) {
    if (body !== "moon" && body !== "mars") {
      return Promise.reject(new Error("getTargets(body) espera 'moon' o 'mars'"));
    }
    const urls = getServiceUrls();
    const data = await request(urls.planetary + "/sites?body=" + encodeURIComponent(body));
    return data.sites || [];
  }

  async function getTargetVector(id) {
    if (!id) return Promise.reject(new Error("getTargetVector(id) requiere un id"));
    const urls = getServiceUrls();
    return request(urls.planetary + "/sites/" + encodeURIComponent(id) + "/vector");
  }

  async function getRegions() {
    const urls = getServiceUrls();
    return request(urls.earth + "/regions");
  }

  // Método TASI en ejecución: pasos, presets, pesos y γ por defecto, umbral de NDVI y origen del catálogo.
  async function getMethod() {
    const urls = getServiceUrls();
    return request(urls.earth + "/method");
  }

  // Valores físicos de referencia por cuerpo (NSSDC, RAD/MSL) con fuente; lo no verificado llega null.
  async function getBodies() {
    const urls = getServiceUrls();
    return request(urls.planetary + "/bodies");
  }

  // Pares Tierra–destino documentados en la literatura (why_es, breaks_es, fuentes), sin puntaje.
  async function getExamples() {
    const urls = getServiceUrls();
    return request(urls.earth + "/examples");
  }

  async function getCandidate(id) {
    if (!id) return Promise.reject(new Error("getCandidate(id) requiere un id"));
    const urls = getServiceUrls();
    return request(urls.earth + "/candidates/" + encodeURIComponent(id));
  }

  async function getFeatured() {
    const urls = getServiceUrls();
    return request(urls.earth + "/featured");
  }

  // El modo fácil identifica continentes con un slug ("south-america", ver
  // normalizeRegions en js/easy.js); earth-service filtra por el nombre de
  // Natural Earth ("South America"). Un nombre ya válido pasa sin cambios.
  function continentName(value) {
    const text = String(value || "").trim();
    if (!text || /\s|[A-Z]/.test(text)) return text;
    return text
      .split("-")
      .map(function (word) { return word.charAt(0).toUpperCase() + word.slice(1); })
      .join(" ");
  }

  async function getCandidates(opts) {
    const urls = getServiceUrls();
    const q = new URLSearchParams();
    opts = opts || {};
    if (opts.continent) q.set("continent", continentName(opts.continent));
    if (opts.country) q.set("country", opts.country);
    const qs = q.toString();
    return request(urls.earth + "/candidates" + (qs ? "?" + qs : ""));
  }

  async function rankAnalogs(opts) {
    opts = opts || {};
    if (!opts.targetVector || !opts.targetVector.components) {
      return Promise.reject(new Error("rankAnalogs requiere targetVector (getTargetVector)"));
    }
    const urls = getServiceUrls();
    const payload = {
      target: opts.targetVector,
      weights: opts.weights || { G: 0.2, T: 0.2, E: 0.2, V: 0.2, O: 0.2 },
      gamma: opts.gamma == null ? 1 : Number(opts.gamma),
      top: opts.top == null ? 5 : Number(opts.top),
      apply_mask: opts.applyMask == null ? true : !!opts.applyMask,
    };
    if (opts.continent) payload.continent = continentName(opts.continent);
    if (opts.country) payload.country = opts.country;
    return request(urls.earth + "/tasi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  const api = {
    getServiceUrls: getServiceUrls,
    health: health,
    getTargets: getTargets,
    getTargetVector: getTargetVector,
    getRegions: getRegions,
    getFeatured: getFeatured,
    getCandidates: getCandidates,
    getCandidate: getCandidate,
    getExamples: getExamples,
    rankAnalogs: rankAnalogs,
    getMethod: getMethod,
    getBodies: getBodies,
  };

  root.HexastraAPI = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : this);
