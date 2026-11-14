/* Hexastra — Modo fácil (asistente de 3 pasos). */
(function () {
  "use strict";

  const STEP_LABELS = ["Elegí destino", "¿Qué te importa?", "¿Dónde buscar?"];

  const state = {
    api: null,
    step: 1,
    body: null,
    targets: { moon: [], mars: [] },
    targetId: null,
    targetVector: null,
    presetId: null,
    // Presets, pesos y γ salen de GET {earth}/method: el front no guarda parámetros del cálculo.
    method: null,
    methodError: null,
    regions: { continents: [] },
    scope: "world",
    continent: "",
    country: "",
    results: null,
    selectedResultId: null,
    loadingTargets: false,
    searching: false,
    error: null,
    map: null,
    markers: {},
    featuredMarker: null,
    tileOsm: null,
    tileEsri: null,
    stub: null,
    featured: null,
    featuredId: null,
    featuredOnly: false,
    reverseResults: null,
    destMap: null,
    destLayers: {},
    destBody: null,
    destMarkers: {}
  };

  // Mercator web no llega a los polos: el polo sur lunar queda comprimido en este borde.
  const MERCATOR_MAX_LAT = 85.05;


  const $ = function (sel, root) { return (root || document).querySelector(sel); };
  const $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function api() {
    return state.api || window.HexastraAPI;
  }

  function presets() {
    return ((state.method && state.method.presets) || []).map(function (p) {
      return { id: p.id, title: p.title_es || p.id, lead: p.lead_es || "", weights: p.weights || {} };
    });
  }

  function currentPreset() {
    const list = presets();
    return list.find(function (p) { return p.id === state.presetId; }) || list[0] ||
      { id: null, title: "Pesos del servicio", lead: "", weights: (state.method && state.method.default_weights) || {} };
  }

  function methodGamma() {
    return state.method && state.method.default_gamma != null ? Number(state.method.default_gamma) : undefined;
  }

  function currentTarget() {
    const list = state.targets[state.body] || [];
    return list.find(function (t) { return t.id === state.targetId; }) || null;
  }

  function stubApi() {
    return state.stub || window.HexastraAPIStub || null;
  }

  async function callApi(method, args) {
    args = args || [];
    const live = api();
    const stub = stubApi();
    const hasLive = live && typeof live[method] === "function" && live.source !== "stub";
    if (hasLive) {
      try {
        return await live[method].apply(live, args);
      } catch (err) {
        if (stub && typeof stub[method] === "function") {
          return stub[method].apply(stub, args);
        }
        throw err;
      }
    }
    const fn = (live && live[method]) || (stub && stub[method]);
    if (typeof fn !== "function") throw new Error("No está disponible " + method + ".");
    return fn.apply(live || stub, args);
  }

  async function loadFeatured() {
    return normalizeFeatured(await callApi("getFeatured", []));
  }

  function normalizeFeatured(raw) {
    if (!raw) return { source: "unknown", groups: [] };
    if (Array.isArray(raw.groups)) {
      return { source: raw.source || "api", groups: raw.groups };
    }
    const places = raw.places || raw.sites || (Array.isArray(raw) ? raw : []);
    const groups = [
      { id: "world", name: "Mundo", places: [] },
      { id: "argentina", name: "Argentina", places: [] }
    ];
    places.forEach(function (p) {
      const g = p.group === "argentina" || p.country_iso === "AR" || p.country === "AR" ? groups[1] : groups[0];
      // «Análogo clásico» = sitio que el catálogo marca como conocido (known_level de la API).
      g.places.push(Object.assign({}, p, { classic: p.classic || p.known_level === "known" }));
    });
    return { source: raw.source || "api", groups: groups };
  }

  function allFeaturedPlaces() {
    const groups = (state.featured && state.featured.groups) || [];
    const out = [];
    groups.forEach(function (g) { (g.places || []).forEach(function (p) { out.push(p); }); });
    return out;
  }

  function featuredById(id) {
    return allFeaturedPlaces().find(function (p) {
      return p.id === id || (p.aliases || []).indexOf(id) !== -1 || p.catalog_id === id;
    }) || null;
  }

  function featuredMatchIds() {
    const ids = {};
    allFeaturedPlaces().forEach(function (p) {
      ids[p.id] = true;
      if (p.catalog_id) ids[p.catalog_id] = true;
      (p.aliases || []).forEach(function (a) { ids[a] = true; });
    });
    return ids;
  }

  function isEasy() {
    return document.body.classList.contains("mode-easy");
  }

  function setMode(mode) {
    const easy = mode === "easy";
    document.body.classList.toggle("mode-easy", easy);
    document.body.classList.toggle("mode-advanced", !easy);
    const easyBtn = $("#mode-easy");
    const advBtn = $("#mode-advanced");
    if (easyBtn) {
      easyBtn.setAttribute("aria-selected", easy ? "true" : "false");
      easyBtn.classList.toggle("is-active", easy);
    }
    if (advBtn) {
      advBtn.setAttribute("aria-selected", easy ? "false" : "true");
      advBtn.classList.toggle("is-active", !easy);
    }
    const easyApp = $("#easy-app");
    if (easyApp) easyApp.hidden = !easy;
    if (easy) invalidateEasyMap();
    requestAnimationFrame(function () {
      if (!easy && window.HexastraApp && typeof window.HexastraApp.invalidateMaps === "function") {
        window.HexastraApp.invalidateMaps();
      }
    });
    setTimeout(function () {
      if (!easy && window.HexastraApp && window.HexastraApp.invalidateMaps) {
        window.HexastraApp.invalidateMaps();
      }
    }, 200);
  }

  function buildShell() {
    const root = $("#easy-app");
    if (!root) return;
    root.innerHTML =
      '<div class="easy">' +
        '<div class="easy-layout">' +
          '<div class="easy-side">' +
        '<nav class="easy-steps" aria-label="Pasos del modo fácil">' +
          '<ol class="easy-stepper" id="easy-stepper"></ol>' +
        '</nav>' +
        '<details class="easy-featured" aria-label="Lugares destacados">' +
          '<summary>Lugares destacados</summary>' +
          '<div class="easy-featured-head">' +
            '<p>Atajos a sitios de referencia. Tocá uno para ir al mapa. Los que dicen «análogo clásico» (Antártida, Atacama, Hawái, Haughton…) están muy estudiados: el desafío pide también buscar análogos menos conocidos.</p>' +
          '</div>' +
          '<div id="easy-featured-groups"></div>' +
          '<div id="easy-featured-panel" class="easy-feat-panel" hidden></div>' +
        '</details>' +
          '<section class="easy-main" id="easy-main" aria-live="polite"></section>' +
          '</div>' +
          '<section class="easy-compare" id="easy-compare" aria-labelledby="easy-compare-title">' +
            '<h2 class="visually-hidden" id="easy-compare-title">Comparación lado a lado</h2>' +
            '<div class="easy-maps">' +
              '<div class="easy-map-wrap">' +
                '<div class="easy-map-label">' +
                  '<h3>Tierra</h3>' +
                  '<div class="easy-map-tools">' +
                    '<button type="button" class="easy-map-btn is-active" id="easy-basemap-sat" aria-pressed="true">Satélite</button>' +
                    '<button type="button" class="easy-map-btn" id="easy-basemap-osm" aria-pressed="false">Mapa</button>' +
                  '</div>' +
                '</div>' +
                '<div id="easy-map-earth" class="easy-map" role="application" aria-label="Mapa de la Tierra"></div>' +
              '</div>' +
              '<div class="easy-map-wrap easy-map-wrap-dest">' +
                '<div class="easy-map-label">' +
                  '<h3 id="easy-dest-label">Luna</h3>' +
                '</div>' +
                '<div id="easy-map-dest" class="easy-map easy-map-dest" role="application" aria-label="Mapa del destino"></div>' +
              '</div>' +
            '</div>' +
            '<p class="easy-map-hint" id="easy-map-hint">El mapa muestra el mundo. Cuando haya resultados, tocá un número para ir a ese lugar.</p>' +
            '<p class="easy-map-hint" id="easy-dest-note"></p>' +
            '<div class="easy-pair" id="easy-pair" aria-live="polite"></div>' +
          '</section>' +
        '</div>' +
      '</div>' +
      '<div class="easy-modal-bg" id="easy-calc-bg" hidden role="dialog" aria-modal="true" aria-labelledby="easy-calc-title">' +
        '<div class="easy-modal" role="document">' +
          '<button type="button" class="easy-close" id="easy-calc-close">Cerrar</button>' +
          '<h2 id="easy-calc-title">Cómo se calcula este puntaje</h2>' +
          '<div id="easy-calc-body"></div>' +
        '</div>' +
      '</div>';
    renderStepper();
    initMap();
    initDestMap();
    renderPair();
    $("#easy-basemap-sat").addEventListener("click", function () { setBasemap("sat"); });
    $("#easy-basemap-osm").addEventListener("click", function () { setBasemap("osm"); });
    $("#easy-calc-close").addEventListener("click", closeCalc);
    $("#easy-calc-bg").addEventListener("click", function (e) {
      if (e.target === $("#easy-calc-bg")) closeCalc();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeCalc();
    });
  }

  function invalidateEasyMap() {
    const maps = [state.map, state.destMap].filter(Boolean);
    if (!maps.length) return;
    requestAnimationFrame(function () { maps.forEach(function (m) { m.invalidateSize(); }); });
    setTimeout(function () { maps.forEach(function (m) { m.invalidateSize(); }); }, 200);
  }

  function observeMapSize(map, element) {
    if (typeof ResizeObserver === "undefined") return;
    // La ficha puede crecer al elegir un resultado sin que cambie el tamaño de la ventana.
    new ResizeObserver(function () {
      if (element.clientWidth && element.clientHeight) map.invalidateSize({ pan: false });
    }).observe(element);
  }

  function renderFeatured() {
    const box = $("#easy-featured-groups");
    if (!box) return;
    if (!state.featured) {
      box.innerHTML = '<p class="easy-status">Estamos cargando los lugares destacados…</p>';
      return;
    }
    const groups = state.featured.groups || [];
    if (!groups.length) {
      box.innerHTML = state.featured.error
        ? '<p class="easy-status easy-status-warn" role="status">' + escapeHtml(state.featured.error) + "</p>"
        : '<p class="easy-status">No hay lugares destacados disponibles.</p>';
      return;
    }
    box.innerHTML = groups.map(function (g) {
      const chips = (g.places || []).map(function (pl) {
        const pending = pl.status === "pending_service" || pl.lat == null || pl.lon == null;
        const sel = state.featuredId === pl.id ? " is-selected" : "";
        const klass = "easy-feat-chip" + sel + (pending ? " is-pending" : "") + (pl.classic ? " is-classic" : "");
        const badges = (pl.classic ? '<span class="easy-chip">Análogo clásico</span>' : "") +
          (pending ? '<span class="easy-chip easy-chip-warn">Cargando del servicio</span>' : "");
        return (
          '<button type="button" class="' + klass + '" data-id="' + escapeHtml(pl.id) + '"' +
            (pending ? ' aria-disabled="false"' : "") + ">" +
            '<span class="easy-feat-name">' + escapeHtml(pl.short_name || pl.name) + "</span>" +
            badges +
          "</button>"
        );
      }).join("");
      return '<div class="easy-feat-group"><h3>' + escapeHtml(g.name) + "</h3><div class=\"easy-feat-chips\">" + chips + "</div></div>";
    }).join("");
    $$(".easy-feat-chip", box).forEach(function (btn) {
      btn.addEventListener("click", function () { selectFeatured(btn.getAttribute("data-id")); });
    });
    renderFeaturedPanel();
    invalidateEasyMap();
  }

  function renderFeaturedPanel() {
    const panel = $("#easy-featured-panel");
    if (!panel) return;
    const pl = state.featuredId ? featuredById(state.featuredId) : null;
    if (!pl) {
      panel.hidden = true;
      panel.innerHTML = "";
      return;
    }
    const pending = pl.status === "pending_service" || pl.lat == null || pl.lon == null;
    const place = [pl.province, pl.country_name || pl.country].filter(Boolean).join(", ");
    const t = currentTarget();
    const compareHint = t
      ? "Vamos a mostrar cómo queda este lugar frente a " + (t.short_name || t.name) + " en el ranking TASI."
      : "Para comparar, elegí primero un destino en la Luna o en Marte (paso 1).";
    panel.hidden = false;
    panel.innerHTML =
      '<div class="easy-feat-card">' +
        '<div class="easy-feat-card-head">' +
          "<h3>" + escapeHtml(pl.name) + "</h3>" +
          '<button type="button" class="easy-link" id="easy-feat-close">Cerrar</button>' +
        "</div>" +
        '<p class="easy-feat-meta">' + (place ? "<span>" + escapeHtml(place) + "</span>" : "") +
          (pl.classic ? ' <span class="easy-chip">Análogo clásico</span>' : "") +
          (pl.highlight_less_studied ? ' <span class="easy-chip easy-chip-menos">Menos estudiado</span>' : "") +
        "</p>" +
        "<p>" + escapeHtml(pl.summary || "") + "</p>" +
        (pl.coord_source ? '<p class="easy-note">Coordenadas: ' + escapeHtml(pl.coord_source) + "</p>" : "") +
        (pending ? '<p class="easy-status easy-status-warn">El servicio todavía no trae coordenadas para este lugar: dato a completar.</p>' : "") +
        '<p class="easy-lead-mini">' + escapeHtml(compareHint) + "</p>" +
        '<div class="easy-actions easy-actions-inline">' +
          '<button type="button" class="easy-btn easy-btn-primary" id="easy-feat-compare"' +
            (pending || !state.targetId ? " disabled" : "") + ">Comparar con el destino</button>" +
        "</div>" +
        '<div id="easy-feat-reverse"></div>' +
      "</div>";
    const close = $("#easy-feat-close");
    if (close) close.addEventListener("click", function () {
      state.featuredId = null;
      state.reverseResults = null;
      clearFeaturedMarker();
      renderFeatured();
      renderPair();
    });
    const cmp = $("#easy-feat-compare");
    if (cmp) cmp.addEventListener("click", function () { compareFeatured(pl); });
    if (state.reverseResults) renderReverseInto($("#easy-feat-reverse"));
  }

  // Leaflet no puede animar un mapa oculto (tamaño 0): en ese caso salta sin animación.
  function hasSize(map) {
    const size = map.getSize();
    return size.x > 0 && size.y > 0;
  }

  function safeFly(map, latlng, zoom, opts) {
    if (!hasSize(map) || (opts && opts.animate === false)) map.setView(latlng, zoom, { animate: false });
    else map.flyTo(latlng, zoom, opts);
  }

  function safeFitBounds(map, bounds, opts) {
    if (!hasSize(map)) return;
    if (opts && opts.animate === false) map.fitBounds(bounds, opts);
    else map.flyToBounds(bounds, opts);
  }

  function flyOpts() {
    return prefersReducedMotion() ? { animate: false } : { duration: 0.8 };
  }

  function featuredIcon(active) {
    return L.divIcon({
      className: "",
      html: '<div class="easy-pin easy-pin-feat' + (active ? " is-active" : "") + '"></div>',
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });
  }

  function plotFeaturedSites() {
    if (!state.map || !state.featured) return;
    if (state.featuredPins) state.map.removeLayer(state.featuredPins);
    state.featuredPins = L.layerGroup().addTo(state.map);
    allFeaturedPlaces().forEach(function (site) {
      if (site.lat == null || site.lon == null) return;
      const marker = L.marker([site.lat, site.lon], { icon: featuredIcon(false), title: site.name });
      marker.hexastraSite = site;
      marker.on("click", function () { selectFeatured(site.id); });
      marker.bindTooltip(site.short_name || site.name);
      marker.addTo(state.featuredPins);
    });
  }

  function clearFeaturedMarker() {
    if (state.map && state.featuredMarker) {
      state.map.removeLayer(state.featuredMarker);
      state.featuredMarker = null;
    }
  }

  function selectFeatured(id) {
    const pl = featuredById(id);
    if (!pl) return;
    state.featuredId = pl.id;
    state.reverseResults = null;
    renderFeatured();
    renderPair();
    if (pl.lat == null || pl.lon == null) return;
    if (state.map) {
      clearFeaturedMarker();
      const marker = L.marker([pl.lat, pl.lon], {
        icon: featuredIcon(true),
        title: pl.name,
        zIndexOffset: 600,
        keyboard: true,
        alt: pl.name
      }).addTo(state.map);
      marker.hexastraSite = pl;
      marker.bindTooltip(pl.short_name || pl.name);
      state.featuredMarker = marker;
      const z = Math.abs(pl.lat) > 70 ? 5 : 7;
      safeFly(state.map, [pl.lat, pl.lon], z, flyOpts());
      invalidateEasyMap();
    }
    const panel = $("#easy-featured-panel");
    if (panel && typeof panel.scrollIntoView === "function") {
      panel.scrollIntoView({ block: "nearest", behavior: prefersReducedMotion() ? "auto" : "smooth" });
    }
  }

  function renderReverseInto(el) {
    if (!el || !state.reverseResults) return;
    const data = state.reverseResults;
    const matches = data.matches || [];
    const t = data.target || {};
    let list;
    if (data.error) {
      list = '<p class="easy-status easy-status-error">' + escapeHtml(data.error) + "</p>";
    } else if (!matches.length) {
      list = '<p class="easy-status">No encontramos destinos de la Luna o de Marte comparables con estos datos.</p>';
    } else {
      list = '<ol class="easy-rank easy-rank-compact">' + matches.map(function (m, i) {
        const site = m.site || {};
        const body = site.body === "moon" ? "Luna" : site.body === "mars" ? "Marte" : "";
        const score = m.score == null ? "—" : Number(m.score).toLocaleString("es-AR", {
          maximumFractionDigits: 1,
          minimumFractionDigits: Number(m.score) % 1 ? 1 : 0
        });
        return (
          '<li><button type="button" class="easy-result" data-rev-id="' + escapeHtml(site.id) + '" data-body="' + escapeHtml(site.body || "") + '">' +
            scoreBlock(m.score, score) +
            '<div class="easy-result-body">' +
              '<p class="easy-result-rank"><span class="num">' + (i + 1) + "</span>" + (body ? "<span>" + body + "</span>" : "") + "</p>" +
              "<h3>" + escapeHtml(site.name) + "</h3>" +
              resultExplain(m) +
            "</div></button></li>"
        );
      }).join("") + "</ol>";
    }
    el.innerHTML =
      '<div class="easy-results-head">' +
        "<h3>Frente a " + escapeHtml(t.short_name || t.name || "el destino") + "</h3>" +
        '<p class="easy-lead-mini">Puntaje TASI de 0 a 100 de este lugar frente al destino elegido, con el enfoque del paso 2.</p>' +
      "</div>" +
      list +
      (data.catalog_note ? '<p class="easy-note">' + escapeHtml(data.catalog_note) + "</p>" : "");
    $$("[data-rev-id]", el).forEach(function (btn) {
      btn.addEventListener("click", function () {
        adoptPlanetaryTarget(btn.getAttribute("data-rev-id"), btn.getAttribute("data-body"));
      });
    });
  }

  async function adoptPlanetaryTarget(id, body) {
    if (!id) return;
    if (body === "moon" || body === "mars") state.body = body;
    if (!state.targets[state.body] || !state.targets[state.body].length) {
      await loadTargets(state.body);
    }
    state.targetId = id;
    state.results = null;
    state.selectedResultId = null;
    focusDestination();
    renderPair();
    try { state.targetVector = await callApi("getTargetVector", [id]); }
    catch (e) { state.targetVector = null; }
    goStep(1);
    const t = currentTarget();
    const recap = t ? "Dejamos elegido " + (t.short_name || t.name) + " como destino. Podés seguir al paso 2 y buscar análogos en la Tierra." : "Destino actualizado.";
    const pane = $("#easy-main");
    if (pane) {
      const note = document.createElement("p");
      note.className = "easy-status";
      note.textContent = recap;
      pane.insertBefore(note, pane.firstChild);
    }
  }

  async function compareFeatured(pl) {
    const box = $("#easy-feat-reverse");
    if (box) box.innerHTML = '<p class="easy-status" role="status">Estamos comparando este lugar con el destino elegido…</p>';
    state.reverseResults = null;
    try {
      state.reverseResults = await compareAgainstSelectedTarget(pl, currentPreset().weights);
    } catch (err) {
      state.reverseResults = {
        target: pl,
        matches: [],
        error: err && err.code === "NO_LOCAL_VECTOR"
          ? "Elegí primero un destino en el paso 1."
          : ("No pudimos completar la comparación. " + (err && err.message ? err.message : ""))
      };
    }
    renderFeaturedPanel();
  }

  async function compareAgainstSelectedTarget(pl, weights) {
    if (!state.targetId) {
      const err = new Error("NO_TARGET");
      err.code = "NO_LOCAL_VECTOR";
      throw err;
    }
    let vector = state.targetVector;
    if (!vector || vector.id !== state.targetId) {
      vector = await callApi("getTargetVector", [state.targetId]);
      state.targetVector = vector;
    }
    const data = await callApi("rankAnalogs", [{
      targetVector: vector,
      weights: weights,
      gamma: methodGamma(),
      top: 80,
      featuredOnly: false
    }]);
    const ids = featuredMatchIds();
    const want = {};
    want[pl.id] = true;
    if (pl.catalog_id) want[pl.catalog_id] = true;
    (pl.aliases || []).forEach(function (a) { want[a] = true; });
    const matches = ((data && data.matches) || []).filter(function (m) {
      const id = m.site && m.site.id;
      return id && (want[id] || ids[id] && (id === pl.id || id === pl.catalog_id));
    });
    const t = currentTarget() || { id: state.targetId };
    return {
      target: { id: t.id, name: t.name || t.short_name, short_name: t.short_name || t.name, body: t.body },
      matches: matches.length ? matches : [],
      catalog_note: matches.length
        ? ""
        : ("No apareció " + (pl.short_name || pl.name) + " en el ranking TASI frente a este destino (puede faltarle dato en los componentes o quedar fuera por la máscara).")
    };
  }

  function renderStepper() {

    const ol = $("#easy-stepper");
    if (!ol) return;
    ol.innerHTML = STEP_LABELS.map(function (label, i) {
      const n = i + 1;
      const status = n < state.step ? "is-done" : n === state.step ? "is-current" : "";
      const aria = n === state.step ? ' aria-current="step"' : "";
      return (
        '<li class="easy-step ' + status + '"' + aria + ">" +
          '<button type="button" class="easy-step-btn" data-step="' + n + '"' +
            (n > state.step && !canJumpTo(n) ? " disabled" : "") + ">" +
            '<span class="easy-step-num" aria-hidden="true">' + n + "</span>" +
            '<span class="easy-step-label">' + escapeHtml(label) + "</span>" +
          "</button>" +
        "</li>"
      );
    }).join("");
    $$(".easy-step-btn", ol).forEach(function (btn) {
      btn.addEventListener("click", function () {
        const n = Number(btn.getAttribute("data-step"));
        if (canJumpTo(n)) goStep(n);
      });
    });
  }

  function canJumpTo(n) {
    if (n <= state.step) return true;
    if (n === 2) return !!state.targetId;
    if (n === 3) return !!state.targetId && !!state.presetId;
    return false;
  }

  function goStep(n) {
    state.step = n;
    if (n < 3) {
      // Mantener resultados si solo se vuelve a mirar, pero al editar filtros se recalcan.
    }
    if (n < 3) state.selectedResultId = state.selectedResultId;
    renderStepper();
    renderMain();
    const heading = $("#easy-step-title");
    if (heading) heading.focus();
  }

  function renderMain() {
    const main = $("#easy-main");
    if (!main) return;
    if (state.step === 1) renderStep1(main);
    else if (state.step === 2) renderStep2(main);
    else renderStep3(main);
  }

  function tagList(target) {
    const tags = target.tags || [];
    const bits = [];
    if (tags.indexOf("artemis-iii") !== -1) bits.push('<span class="easy-chip">Artemis III</span>');
    else if (tags.indexOf("artemis-cercano") !== -1) bits.push('<span class="easy-chip">Cerca de Artemis</span>');
    if (target.missing_features && target.missing_features.length) {
      bits.push('<span class="easy-chip easy-chip-warn">Hay datos a completar</span>');
    }
    return bits.join("");
  }

  function renderStep1(main) {
    const body = state.body || "moon";
    const list = state.targets[body] || [];
    let cards;
    if (state.loadingTargets) {
      cards = '<p class="easy-status" role="status">Estamos cargando los destinos…</p>';
    } else if (state.error && !list.length) {
      cards = '<p class="easy-status easy-status-error" role="alert">' + escapeHtml(state.error) + "</p>";
    } else if (!list.length) {
      cards = '<p class="easy-status">No hay destinos cargados para este cuerpo en el catálogo.</p>';
    } else {
      cards = '<div class="easy-cards" role="list">' + list.map(function (t) {
        const sel = t.id === state.targetId ? " is-selected" : "";
        return (
          '<button type="button" class="easy-card easy-card-dest' + sel + '" role="listitem" data-id="' +
          escapeHtml(t.id) + '" aria-pressed="' + (t.id === state.targetId ? "true" : "false") + '">' +
            '<div class="easy-card-body">' +
              '<div class="easy-card-chips">' + tagList(t) + "</div>" +
              "<h3>" + escapeHtml(t.short_name || t.name) + "</h3>" +
              '<p class="easy-card-name">' + escapeHtml(t.name) + "</p>" +
              "<p>" + escapeHtml(t.summary || "") + "</p>" +
            "</div>" +
          "</button>"
        );
      }).join("") + "</div>";
    }

    main.innerHTML =
      '<div class="easy-pane">' +
        '<h2 class="easy-title" id="easy-step-title" tabindex="-1">Elegí destino</h2>' +
        '<p class="easy-lead">Primero el cuerpo, después un sitio. Mostramos solo lugares que están en el catálogo, con la descripción que figura en los datos.</p>' +
        '<div class="easy-body-toggle" role="tablist" aria-label="Cuerpo del destino">' +
          '<button type="button" role="tab" id="easy-body-moon" aria-selected="' + (body === "moon" ? "true" : "false") + '" class="' + (body === "moon" ? "is-active" : "") + '">Luna</button>' +
          '<button type="button" role="tab" id="easy-body-mars" aria-selected="' + (body === "mars" ? "true" : "false") + '" class="' + (body === "mars" ? "is-active" : "") + '">Marte</button>' +
        "</div>" +
        cards +
        '<div class="easy-actions">' +
          '<button type="button" class="easy-btn easy-btn-primary" id="easy-next-1"' +
            (state.targetId ? "" : " disabled") + ">Siguiente: qué te importa</button>" +
        "</div>" +
      "</div>";

    $("#easy-body-moon").addEventListener("click", function () { chooseBody("moon"); });
    $("#easy-body-mars").addEventListener("click", function () { chooseBody("mars"); });
    $$(".easy-card-dest", main).forEach(function (btn) {
      btn.addEventListener("click", function () { chooseTarget(btn.getAttribute("data-id")); });
    });
    $("#easy-next-1").addEventListener("click", function () {
      if (state.targetId) goStep(2);
    });
  }

  async function chooseBody(body) {
    const changed = state.body !== body;
    state.body = body;
    if (changed) {
      state.targetId = null;
      state.targetVector = null;
      state.results = null;
    }
    renderStepper();
    renderMain();
    setDestBody(body);
    renderPair();
    if (!state.targets[body].length) {
      await loadTargets(body);
      if (state.body === body) {
        renderMain();
        renderDestMarkers();
      }
    }
  }

  async function chooseTarget(id) {
    state.targetId = id;
    state.results = null;
    state.selectedResultId = null;
    renderMain();
    focusDestination();
    renderPair();
    try {
      state.targetVector = await api().getTargetVector(id);
    } catch (err) {
      state.targetVector = null;
      state.error = "No pude cargar los datos de ese destino. " + (err && err.message ? err.message : "");
      renderMain();
    }
  }

  function renderStep2(main) {
    const t = currentTarget();
    main.innerHTML =
      '<div class="easy-pane">' +
        '<h2 class="easy-title" id="easy-step-title" tabindex="-1">¿Qué te importa?</h2>' +
        recapLine(t, null) +
        '<p class="easy-lead">Elegí un enfoque. Cada uno es un juego de pesos del índice TASI (geología, terreno, clima, volátiles y operación) que define el servicio.</p>' +
        (state.methodError ? '<p class="easy-status easy-status-error" role="alert">' + escapeHtml(state.methodError) + "</p>" : "") +
        '<div class="easy-presets" role="list">' +
          presets().map(function (p) {
            const sel = p.id === state.presetId ? " is-selected" : "";
            return (
              '<button type="button" class="easy-card easy-card-preset' + sel + '" role="listitem" data-id="' +
              p.id + '" aria-pressed="' + (p.id === state.presetId ? "true" : "false") + '">' +
                '<h3>' + escapeHtml(p.title) + "</h3>" +
                "<p>" + escapeHtml(p.lead) + "</p>" +
                weightsRow(p.weights) +
              "</button>"
            );
          }).join("") +
        "</div>" +
        '<div class="easy-actions">' +
          '<button type="button" class="easy-btn" id="easy-back-2">Volver</button>' +
          '<button type="button" class="easy-btn easy-btn-primary" id="easy-next-2"' + (presets().length ? "" : " disabled") + '>Siguiente: dónde buscar</button>' +
        "</div>" +
      "</div>";
    $$(".easy-card-preset", main).forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.presetId = btn.getAttribute("data-id");
        state.results = null;
        renderMain();
      });
    });
    $("#easy-back-2").addEventListener("click", function () { goStep(1); });
    $("#easy-next-2").addEventListener("click", function () { goStep(3); });
  }

  function continentOptions() {
    const continents = (state.regions.continents || []);
    return '<option value="">Elegí un continente</option>' + continents.map(function (c) {
      return '<option value="' + escapeHtml(c.id) + '"' + (state.continent === c.id ? " selected" : "") + ">" +
        escapeHtml(c.name) + "</option>";
    }).join("");
  }

  function normalizeRegions(raw) {
    const continents = (raw && raw.continents) || [];
    return {
      continents: continents.map(function (c) {
        const id = c.id || String(c.name || "").toLowerCase().replace(/\s+/g, "-");
        return {
          id: id,
          name: c.name || id,
          countries: (c.countries || []).map(function (co) {
            const iso = (co.iso || co.id || "").toString();
            return { id: iso, name: co.name || iso, iso: iso };
          })
        };
      })
    };
  }

  function selectedContinent() {
    return (state.regions.continents || []).find(function (c) { return c.id === state.continent; }) || null;
  }

  function countryOptions() {
    const cont = selectedContinent();
    if (!cont) return '<option value="">Primero elegí un continente</option>';
    if (!cont.countries || !cont.countries.length) {
      return '<option value="">No hay países con datos en este continente</option>';
    }
    return '<option value="all">Todos los países de ' + escapeHtml(cont.name) + "</option>" +
      cont.countries.map(function (c) {
        return '<option value="' + escapeHtml(c.id) + '"' + (state.country === c.id ? " selected" : "") + ">" +
          escapeHtml(c.name) + "</option>";
      }).join("");
  }

  function scopeRecap() {
    if (state.scope === "world") return "el mundo entero";
    const cont = selectedContinent();
    const cname = cont ? cont.name : state.continent;
    if (state.country && state.country !== "all") {
      const country = (cont && cont.countries || []).find(function (c) { return c.id === state.country; });
      return (country ? country.name : state.country) + " (" + cname + ")";
    }
    return cname || "el continente elegido";
  }

  function renderStep3(main) {
    const t = currentTarget();
    const preset = currentPreset();
    const showResults = !!state.results || state.searching || (state.error && state.step === 3);
    const countryDisabled = state.scope !== "region" || !state.continent;
    const cont = selectedContinent();
    const noCountries = state.scope === "region" && cont && (!cont.countries || !cont.countries.length);

    let resultsHtml = "";
    if (state.searching) {
      resultsHtml = '<p class="easy-status" role="status">Estamos comparando el destino con los lugares de la Tierra…</p>';
    } else if (state.results) {
      resultsHtml = renderResultsBlock();
    } else if (state.error && showResults) {
      resultsHtml = '<p class="easy-status easy-status-error" role="alert">' + escapeHtml(state.error) + "</p>";
    }

    main.innerHTML =
      '<div class="easy-pane">' +
        '<h2 class="easy-title" id="easy-step-title" tabindex="-1">¿Dónde buscar?</h2>' +
        recapLine(t, preset) +
        '<p class="easy-lead">Podés buscar en el mundo entero o filtrar por continente y, después, por país. El filtro usa las regiones que entrega el servicio (o el catálogo local).</p>' +
        '<div class="easy-scope" role="radiogroup" aria-label="Alcance de la búsqueda">' +
          '<label class="easy-scope-card' + (state.scope === "world" ? " is-selected" : "") + '" id="easy-scope-world">' +
            '<input type="radio" name="easy-scope" value="world"' + (state.scope === "world" ? " checked" : "") + ">" +
            "<strong>Mundo entero</strong>" +
            "<span>Todos los lugares terrestres del catálogo.</span>" +
          "</label>" +
          '<label class="easy-scope-card' + (state.scope === "region" ? " is-selected" : "") + '" id="easy-scope-region">' +
            '<input type="radio" name="easy-scope" value="region"' + (state.scope === "region" ? " checked" : "") + ">" +
            "<strong>Filtrar por región</strong>" +
            "<span>Elegí un continente y, si hay datos, un país.</span>" +
          "</label>" +
        "</div>" +
        '<div class="easy-filters' + (state.scope === "region" ? "" : " is-hidden") + '">' +
          '<label class="easy-field">' +
            '<span>Continente</span>' +
            '<select id="easy-continent"' + (state.scope === "region" ? "" : " disabled") + ">" +
              continentOptions() +
            "</select>" +
          "</label>" +
          '<label class="easy-field">' +
            '<span>País</span>' +
            '<select id="easy-country"' + (countryDisabled ? " disabled" : "") + ">" +
              countryOptions() +
            "</select>" +
          "</label>" +
        "</div>" +
        (noCountries && !state.results && !state.searching ? '<p class="easy-status">En este catálogo no hay países con datos en ese continente.</p>' : "") +
        '<label class="easy-check">' +
          '<input type="checkbox" id="easy-featured-only"' + (state.featuredOnly ? " checked" : "") + ">" +
          "<span>Buscar solo entre destacados</span>" +
        "</label>" +
        '<p class="easy-note">Si está marcado, el ranking se limita a los atajos de la tira (los que ya tengan datos comparables).</p>' +
        '<div class="easy-actions">' +
          '<button type="button" class="easy-btn" id="easy-back-3">Volver</button>' +
          '<button type="button" class="easy-btn easy-btn-primary" id="easy-search"' +
            (state.scope === "region" && !state.continent ? " disabled" : "") +
            ">Buscar análogos</button>" +
        "</div>" +
        '<div id="easy-results">' + resultsHtml + "</div>" +
      "</div>";

    $$(".easy-scope-card", main).forEach(function (lab) {
      lab.addEventListener("click", function (e) {
        e.preventDefault();
        const inp = lab.querySelector("input");
        if (!inp) return;
        const next = inp.value;
        if (state.scope === next) return;
        state.scope = next;
        if (state.scope === "world") {
          state.continent = "";
          state.country = "";
        }
        state.results = null;
        clearMarkers();
        renderMain();
      });
    });
    const contSel = $("#easy-continent");
    if (contSel) {
      contSel.addEventListener("change", function () {
        state.continent = contSel.value;
        state.country = "";
        state.results = null;
        clearMarkers();
        renderMain();
      });
    }
    const ctrySel = $("#easy-country");
    if (ctrySel) {
      ctrySel.addEventListener("change", function () {
        state.country = ctrySel.value;
        state.results = null;
        clearMarkers();
        renderMain();
      });
    }
    const featOnly = $("#easy-featured-only");
    if (featOnly) {
      featOnly.addEventListener("change", function () {
        state.featuredOnly = featOnly.checked;
        state.results = null;
        clearMarkers();
        renderMain();
      });
    }
    $("#easy-back-3").addEventListener("click", function () { goStep(2); });
    $("#easy-search").addEventListener("click", runSearch);

    const calc = $("#easy-open-calc");
    if (calc) calc.addEventListener("click", openCalc);
    $$(".easy-result", main).forEach(function (btn) {
      btn.addEventListener("click", function () { selectResult(btn.getAttribute("data-id")); });
      btn.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectResult(btn.getAttribute("data-id"));
        }
      });
    });
    if (state.results) plotResults(state.results);
  }

  // Fracción 0–1 para la escala de color del puntaje (violeta → óxido, docs/marca.md).
  function scoreFraction(score) {
    const n = Number(score);
    if (score == null || Number.isNaN(n)) return "0";
    return Math.max(0, Math.min(1, n / 100)).toFixed(3);
  }

  function scoreBlock(raw, shown) {
    return '<div class="easy-score" style="--s:' + scoreFraction(raw) + '" aria-label="Coincidencia ' + escapeHtml(String(shown)) + ' de 100">' +
      '<span class="easy-score-num score-color">' + escapeHtml(String(shown)) + "</span>" +
      '<span class="easy-score-den">de 100</span>' +
      '<span class="score-bar" aria-hidden="true"><span></span></span>' +
    "</div>";
  }

  function resultExplain(m) {
    const ex = explainMatch(m);
    return (ex.why ? '<p class="easy-why"><strong>Por qué se parece.</strong> ' + escapeHtml(ex.why) + "</p>" : "") +
      (ex.breaks ? '<p class="easy-breaks"><strong>En qué no.</strong> ' + escapeHtml(ex.breaks) + "</p>" : "") +
      missingBadges(ex.missing);
  }

  function recapLine(t, preset) {
    const parts = [];
    if (t) parts.push("<div><dt>Destino</dt><dd>" + escapeHtml(t.short_name || t.name) + "</dd></div>");
    if (preset) parts.push("<div><dt>Enfoque</dt><dd>" + escapeHtml(preset.title) + "</dd></div>");
    return parts.length ? '<dl class="easy-recap">' + parts.join("") + "</dl>" : "";
  }

  function weightsRow(w) {
    return '<dl class="easy-weights" aria-label="Pesos del índice TASI">' +
      ["G", "T", "E", "V", "O"].map(function (k) {
        return "<div><dt>" + k + "</dt><dd class='num'>" + Math.round((w[k] || 0) * 100) + "</dd></div>";
      }).join("") +
      "</dl>";
  }

  function missingBadges(list) {
    if (!list || !list.length) return "";
    const shown = list.slice(0, 4);
    return '<p class="easy-missing">' +
      shown.map(function (m) {
        return '<span class="easy-chip easy-chip-warn">Dato a completar: ' + escapeHtml(labelMissing(m)) + "</span>";
      }).join(" ") +
      (list.length > 4 ? '<span class="easy-chip easy-chip-warn">+' + (list.length - 4) + " más</span>" : "") +
      "</p>";
  }

  function labelMissing(key) {
    const map = {
      slope: "pendiente",
      roughness: "rugosidad",
      temp_mean: "temperatura media",
      temp_diurnal_range: "amplitud térmica",
      illumination_pct: "iluminación",
      water_ice_indicator: "hielo o volátiles",
      precip_mm: "precipitación",
      "composición mineralógica": "composición mineralógica",
      elevation: "elevación"
    };
    return map[key] || key;
  }

  function emptyMessage() {
    if (state.scope === "region" && state.country && state.country !== "all") {
      return "No encontramos análogos en este país con estos datos.";
    }
    if (state.scope === "region" && state.continent) {
      return "No encontramos análogos en este continente con estos datos.";
    }
    if (state.featuredOnly) {
      return "No encontramos análogos entre los lugares destacados con estos datos.";
    }
    return "No encontramos análogos con estos datos.";
  }

  function renderResultsBlock() {
    const data = state.results;
    if (!data) return "";
    const matches = data.matches || [];
    const t = data.target || currentTarget() || {};
    let list;
    if (!matches.length) {
      list = '<p class="easy-status" role="status">' + emptyMessage() + "</p>";
    } else {
      list = '<ol class="easy-rank">' + matches.map(function (m, i) {
        const site = m.site || {};
        const active = site.id === state.selectedResultId ? " is-selected" : "";
        const place = [site.province, site.country_name || site.country].filter(Boolean).join(", ");
        const score = m.score == null ? "—" : Number(m.score).toLocaleString("es-AR", {
          maximumFractionDigits: 1,
          minimumFractionDigits: Number(m.score) % 1 ? 1 : 0
        });
        return (
          '<li>' +
            '<button type="button" class="easy-result' + active + '" data-id="' + escapeHtml(site.id) + '">' +
              scoreBlock(m.score, score) +
              '<div class="easy-result-body">' +
                '<p class="easy-result-rank"><span class="num">' + (i + 1) + "</span>" + (place ? "<span>" + escapeHtml(place) + "</span>" : "") +
                  (site.highlight_less_studied || site.known_level === "lesser-known" ? ' <span class="easy-chip easy-chip-menos">Menos estudiado</span>' : "") +
                "</p>" +
                "<h3>" + escapeHtml(site.name) + "</h3>" +
                resultExplain(m) +
              "</div>" +
            "</button>" +
          "</li>"
        );
      }).join("") + "</ol>";
    }

    const note = data.catalog_note
      ? '<p class="easy-note">' + escapeHtml(data.catalog_note) + "</p>"
      : "";

    return (
      '<div class="easy-results-head">' +
        "<h3>Resultados para " + escapeHtml(t.short_name || t.name || "el destino") +
          " en " + escapeHtml(scopeRecap()) + "</h3>" +
        '<p class="easy-lead-mini">El número es una coincidencia de 0 a 100 según lo que elegiste. Hacé clic en un lugar para ir hasta ahí en el mapa.</p>' +
        '<p><button type="button" class="easy-link" id="easy-open-calc">Ver cómo se calcula</button></p>' +
      "</div>" +
      list +
      note
    );
  }

  async function runSearch() {
    state.searching = true;
    state.error = null;
    state.results = null;
    state.selectedResultId = null;
    clearMarkers();
    renderMain();
    try {
      let vector = state.targetVector;
      if (!vector || vector.id !== state.targetId) {
        vector = await callApi("getTargetVector", [state.targetId]);
        state.targetVector = vector;
      }
      const continent = state.scope === "region" ? state.continent || null : null;
      const country = state.scope === "region" && state.country && state.country !== "all"
        ? state.country
        : null;
      const data = await callApi("rankAnalogs", [{
        targetVector: vector,
        weights: currentPreset().weights,
        gamma: methodGamma(),
        top: state.featuredOnly ? 80 : 10,
        continent: continent,
        country: country,
        featuredOnly: !!state.featuredOnly,
        siteIds: state.featuredOnly ? Object.keys(featuredMatchIds()) : null
      }]);
      let results = data || { matches: [] };
      if (state.featuredOnly && results.matches) {
        const ids = featuredMatchIds();
        results = Object.assign({}, results, {
          matches: results.matches.filter(function (m) { return m.site && ids[m.site.id]; })
        });
        if (!results.catalog_note) {
          results.catalog_note = "El filtro «solo destacados» dejó únicamente los atajos de la tira que el ranking pudo puntuar.";
        }
      }
      state.results = results;
      if (state.results.matches && state.results.matches.length) {
        state.selectedResultId = state.results.matches[0].site.id;
      }
    } catch (err) {
      state.error = "No pudimos completar la búsqueda. " +
        (err && err.message ? err.message : "Probá de nuevo en un rato.");
      state.results = null;
    } finally {
      state.searching = false;
      renderMain();
      renderPair();
      const res = $("#easy-results");
      if (res && (state.results || state.error) && typeof res.scrollIntoView === "function") {
        res.scrollIntoView({ block: "start", behavior: prefersReducedMotion() ? "auto" : "smooth" });
      }
    }
  }

  function initMap() {
    const el = $("#easy-map-earth");
    if (!el || typeof L === "undefined") return;
    const map = L.map(el, {
      zoomControl: false,
      minZoom: 2,
      maxZoom: 12,
      worldCopyJump: true
    }).setView([20, 0], 2);
    L.control.zoom({ position: "bottomright" }).addTo(map);

    state.tileOsm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18
    });
    state.tileEsri = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        attribution: "Teselas: Esri, Maxar, Earthstar Geographics",
        maxZoom: 18
      }
    );
    state.tileEsri.addTo(map);
    state.map = map;
    if (window.HexastraGlobe) {
      state.globe = window.HexastraGlobe.attach(map, {
        tools: $(".easy-map-tools"),
        getContext: (marker) => ({
          site: marker.hexastraSite,
          target: currentTarget(),
          match: ((state.results && state.results.matches) || []).find(function (m) {
            return m.site && m.site.id === marker.hexastraSite?.id;
          }) || null,
        }),
      });
    }
    observeMapSize(map, el);
    setTimeout(function () { map.invalidateSize(); }, 200);
  }

  function setBasemap(which) {
    if (!state.map) return;
    const sat = which === "sat";
    if (sat) {
      if (!state.map.hasLayer(state.tileEsri)) state.tileEsri.addTo(state.map);
      if (state.map.hasLayer(state.tileOsm)) state.map.removeLayer(state.tileOsm);
    } else {
      if (!state.map.hasLayer(state.tileOsm)) state.tileOsm.addTo(state.map);
      if (state.map.hasLayer(state.tileEsri)) state.map.removeLayer(state.tileEsri);
    }
    const satBtn = $("#easy-basemap-sat");
    const osmBtn = $("#easy-basemap-osm");
    if (satBtn) {
      satBtn.classList.toggle("is-active", sat);
      satBtn.setAttribute("aria-pressed", sat ? "true" : "false");
    }
    if (osmBtn) {
      osmBtn.classList.toggle("is-active", !sat);
      osmBtn.setAttribute("aria-pressed", !sat ? "true" : "false");
    }
  }

  /* ---------- Mapa del destino (Luna o Marte), al lado del de la Tierra ---------- */

  function initDestMap() {
    const el = $("#easy-map-dest");
    if (!el || typeof L === "undefined") return;
    const map = L.map(el, { zoomControl: false, minZoom: 1, maxZoom: 8, worldCopyJump: true }).setView([0, 0], 1);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    state.destLayers = {
      mars: L.tileLayer(
        "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png",
        { attribution: "OpenPlanetaryMap, OPM Mars Basemap v0.2", maxZoom: 8, maxNativeZoom: 9 }
      ),
      moon: L.tileLayer(
        "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png",
        { attribution: "OpenPlanetaryMap, OPM Moon Basemap v0.1", maxZoom: 8, maxNativeZoom: 9 }
      )
    };
    state.destMap = map;
    observeMapSize(map, el);
    setDestBody(state.body || "moon");
    setTimeout(function () { map.invalidateSize(); }, 200);
  }

  function clampLat(lat) {
    return Math.max(-MERCATOR_MAX_LAT, Math.min(MERCATOR_MAX_LAT, Number(lat)));
  }

  function setDestBody(body) {
    const map = state.destMap;
    if (!map || !body) return;
    const changed = state.destBody !== body;
    state.destBody = body;
    Object.keys(state.destLayers).forEach(function (k) {
      const ly = state.destLayers[k];
      if (k === body) { if (!map.hasLayer(ly)) ly.addTo(map); }
      else if (map.hasLayer(ly)) map.removeLayer(ly);
    });
    const label = $("#easy-dest-label");
    if (label) label.textContent = body === "mars" ? "Marte" : "Luna";
    const compare = $("#easy-compare");
    if (compare) compare.setAttribute("data-body", body);
    const note = $("#easy-dest-note");
    if (note) {
      note.textContent = body === "moon"
        ? "Luna en proyección Mercator: el polo sur queda comprimido contra el borde inferior y los sitios polares se dibujan en el límite de 85° S. Las coordenadas de la ficha son las reales."
        : "";
      note.hidden = body !== "moon";
    }
    if (changed) map.setView([0, 0], 1);
    renderDestMarkers();
  }

  function destIcon(active) {
    return L.divIcon({
      className: "",
      html: '<div class="easy-pin easy-pin-dest ' + (state.destBody === "mars" ? "mars" : "moon") + (active ? " is-active" : "") + '"></div>',
      iconSize: active ? [22, 22] : [12, 12],
      iconAnchor: active ? [11, 11] : [6, 6]
    });
  }

  function renderDestMarkers() {
    const map = state.destMap;
    if (!map) return;
    Object.keys(state.destMarkers).forEach(function (id) { map.removeLayer(state.destMarkers[id]); });
    state.destMarkers = {};
    const list = state.targets[state.destBody] || [];
    list.forEach(function (t) {
      if (t.lat == null || t.lon == null) return;
      const active = t.id === state.targetId;
      const marker = L.marker([clampLat(t.lat), t.lon], {
        icon: destIcon(active),
        title: t.name,
        alt: "Destino: " + t.name,
        keyboard: true,
        zIndexOffset: active ? 800 : 0
      }).addTo(map);
      marker.bindTooltip(t.short_name || t.name, { permanent: active, direction: "top", offset: [0, -10] });
      marker.on("click", function () {
        if (state.step !== 1) goStep(1);
        chooseTarget(t.id);
      });
      state.destMarkers[t.id] = marker;
    });
  }

  function focusDestination() {
    const t = currentTarget();
    if (state.body && state.body !== state.destBody) setDestBody(state.body);
    else renderDestMarkers();
    if (!t || !state.destMap || t.lat == null || t.lon == null) return;
    safeFly(state.destMap, [clampLat(t.lat), t.lon], 4, flyOpts());
  }

  /* ---------- Ficha del par: destino | sitio terrestre ---------- */

  function formatScore(score) {
    return window.HexastraExplain.formatScore(score);
  }

  function explainMatch(m) {
    return window.HexastraExplain.explainMatch(m, labelMissing);
  }

  function selectedMatch() {
    const matches = (state.results && state.results.matches) || [];
    return matches.find(function (m) { return m.site && m.site.id === state.selectedResultId; }) || null;
  }

  function renderPair() {
    const box = $("#easy-pair");
    if (!box) return;
    const t = currentTarget();
    const m = selectedMatch();
    const feat = !m && state.featuredId ? featuredById(state.featuredId) : null;
    const bodyName = t ? (t.body === "mars" ? "Marte" : "Luna") : "";
    const dest = t
      ? "<p class='easy-pair-side'>" + escapeHtml(bodyName) + "</p>" +
        "<h3>" + escapeHtml(t.short_name || t.name) + "</h3>" +
        "<p class='easy-pair-coord num'>" + coordText(t.lat, t.lon) + "</p>" +
        (t.missing_features && t.missing_features.length
          ? "<p class='easy-missing'>" + t.missing_features.slice(0, 3).map(function (f) {
              return "<span class='easy-chip easy-chip-warn'>Dato a completar: " + escapeHtml(labelMissing(f)) + "</span>";
            }).join(" ") + "</p>"
          : "")
      : "<p class='easy-pair-side'>Destino</p><p class='easy-pair-empty'>Elegí un sitio de la Luna o de Marte en el paso 1, o tocá un punto del mapa de la derecha.</p>";
    let earth;
    if (m) {
      const site = m.site;
      const place = [site.province, site.country_name || site.country].filter(Boolean).join(", ");
      earth = "<p class='easy-pair-side'>Tierra</p>" +
        "<h3>" + escapeHtml(site.name) + "</h3>" +
        "<p class='easy-pair-coord num'>" + coordText(site.lat, site.lon) + "</p>" +
        (place ? "<p class='easy-pair-place'>" + escapeHtml(place) + "</p>" : "") +
        (site.highlight_less_studied || site.known_level === "lesser-known" ? "<p><span class='easy-chip easy-chip-menos'>Menos estudiado</span></p>" : "");
    } else if (feat) {
      earth = "<p class='easy-pair-side'>Tierra</p><h3>" + escapeHtml(feat.name) + "</h3>" +
        (feat.lat != null ? "<p class='easy-pair-coord num'>" + coordText(feat.lat, feat.lon) + "</p>" : "") +
        "<p class='easy-pair-empty'>Lugar destacado, sin puntaje frente a este destino todavía.</p>";
    } else {
      earth = "<p class='easy-pair-side'>Tierra</p><p class='easy-pair-empty'>" +
        (t ? "Buscá análogos en el paso 3 y elegí uno de la lista o del mapa." : "Primero el destino; después buscamos en la Tierra.") +
        "</p>";
    }
    let detail = "";
    if (m) {
      const ex = explainMatch(m);
      detail =
        "<div class='easy-pair-score' style='--s:" + scoreFraction(m.score) + "'><span class='easy-score-num score-color'>" + escapeHtml(formatScore(m.score)) + "</span><span class='easy-score-den'>de 100, índice TASI</span>" +
        "<span class='score-bar' aria-hidden='true'><span></span></span></div>" +
        "<dl class='easy-pair-why'>" +
          "<div><dt>Por qué se parece</dt><dd>" + escapeHtml(ex.why || "Sin componentes con dato.") + "</dd></div>" +
          "<div><dt>En qué no</dt><dd>" + escapeHtml(ex.breaks) + "</dd></div>" +
        "</dl>" +
        (ex.missing.length ? "<p class='easy-missing'>" + ex.missing.map(function (k) {
          return "<span class='easy-chip easy-chip-warn'>Dato a completar: " + escapeHtml(k) + "</span>";
        }).join(" ") + "</p>" : "") +
        "<p><button type='button' class='easy-link' id='easy-pair-calc'>Ver cómo se calcula</button></p>";
    }
    box.innerHTML =
      "<div class='easy-pair-grid'>" +
        "<div class='easy-pair-col is-earth'>" + earth + "</div>" +
        "<div class='easy-pair-col " + (t ? "is-" + t.body : "is-dest-empty") + "'>" + dest + "</div>" +
      "</div>" + detail;
    const calc = $("#easy-pair-calc");
    if (calc) calc.addEventListener("click", openCalc);
  }

  function coordText(lat, lon) {
    if (lat == null || lon == null) return "coordenadas a completar";
    const la = Number(lat);
    const lo = Number(lon);
    const fmt = function (v) { return Math.abs(v).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
    return fmt(la) + "° " + (la < 0 ? "S" : "N") + ", " + fmt(lo) + "° " + (lo < 0 ? "O" : "E");
  }

  function rankIcon(n, active) {
    return L.divIcon({
      className: "",
      html: '<div class="easy-pin' + (active ? " is-active" : "") + '">' + n + "</div>",
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });
  }

  function clearMarkers() {
    if (!state.map) return;
    Object.keys(state.markers).forEach(function (id) {
      state.map.removeLayer(state.markers[id]);
    });
    state.markers = {};
    if (state.map && !state.results) {
      state.map.setView([20, 0], 2);
    }
    renderPair();
  }

  function plotResults(data) {
    if (!state.map) return;
    if (state.featuredPins) {
      state.map.removeLayer(state.featuredPins);
      state.featuredPins = null;
    }
    Object.keys(state.markers).forEach(function (id) {
      state.map.removeLayer(state.markers[id]);
    });
    state.markers = {};
    const matches = (data && data.matches) || [];
    const latlngs = [];
    matches.forEach(function (m, i) {
      const site = m.site;
      if (site.lat == null || site.lon == null) return;
      const marker = L.marker([site.lat, site.lon], {
        icon: rankIcon(i + 1, site.id === state.selectedResultId),
        title: site.name,
        keyboard: true,
        alt: "Análogo " + (i + 1) + ": " + site.name
      }).addTo(state.map);
      marker.hexastraSite = site;
      marker.bindTooltip(site.short_name || site.name);
      marker.on("click", function () { selectResult(site.id); });
      state.markers[site.id] = marker;
      latlngs.push([site.lat, site.lon]);
    });
    if (latlngs.length === 1) {
      safeFly(state.map, latlngs[0], 6, flyOpts());
    } else if (latlngs.length > 1) {
      safeFitBounds(state.map, L.latLngBounds(latlngs).pad(0.4), Object.assign(flyOpts(), { maxZoom: 6 }));
    } else {
      state.map.setView([20, 0], 2);
    }
    const hint = $("#easy-map-hint");
    if (hint) {
      hint.textContent = matches.length
        ? "Tocá un número en el mapa o una tarjeta de la lista para ir a ese lugar."
        : "No hay análogos para marcar en el mapa con este filtro.";
    }
  }

  function selectResult(id) {
    state.selectedResultId = id;
    const matches = (state.results && state.results.matches) || [];
    const hit = matches.find(function (m) { return m.site.id === id; });
    $$(".easy-result").forEach(function (btn) {
      const on = btn.getAttribute("data-id") === id;
      btn.classList.toggle("is-selected", on);
    });
    Object.keys(state.markers).forEach(function (mid, i) {
      const matchIndex = matches.findIndex(function (m) { return m.site.id === mid; });
      const marker = state.markers[mid];
      if (marker && matchIndex >= 0) {
        marker.setIcon(rankIcon(matchIndex + 1, mid === id));
      }
    });
    if (hit && state.map) {
      safeFly(state.map, [hit.site.lat, hit.site.lon], 8, flyOpts());
    }
    renderPair();
    // En pantallas angostas la comparación queda arriba: la traemos a la vista para ver los dos puntos.
    const narrow = window.matchMedia && window.matchMedia("(max-width: 900px)").matches;
    const target = narrow ? $("#easy-compare") : document.querySelector('.easy-result[data-id="' + id + '"]');
    if (target && typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ block: narrow ? "start" : "nearest", behavior: prefersReducedMotion() ? "auto" : "smooth" });
    }
  }

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function openCalc() {
    const bg = $("#easy-calc-bg");
    const body = $("#easy-calc-body");
    if (!bg || !body) return;
    const preset = currentPreset();
    const t = currentTarget() || (state.results && state.results.target) || {};
    const W = preset.weights;
    const selected = ((state.results && state.results.matches) || [])
      .find(function (m) { return m.site.id === state.selectedResultId; });
    const labels = window.HexastraExplain.COMPONENT_LABELS;
    const compLine = function (key) {
      const w = Number(W[key]) || 0;
      let shown = "—";
      if (selected) {
        const sc = window.HexastraExplain.componentScore((selected.components || {})[key]);
        shown = sc == null ? "sin dato (se omitió y se repartieron los pesos)" : formatScore(Math.round(sc * 10) / 10) + " de 100";
      }
      return "<tr><th scope='row'>" + escapeHtml(labels[key]) + "</th><td>" +
        Math.round(w * 100).toLocaleString("es-AR") + " %</td><td>" + escapeHtml(shown) + "</td></tr>";
    };
    const m = state.method;
    const methodText = m
      ? "<p><strong>" + escapeHtml(m.name_es || m.index) + ".</strong> " + escapeHtml(m.status_es || "") + "</p>" +
        "<ol class='method-steps'>" + (m.steps_es || []).map(function (st) { return "<li>" + escapeHtml(st) + "</li>"; }).join("") + "</ol>"
      : "<p class='easy-status easy-status-error'>" + escapeHtml(state.methodError || "No pudimos cargar el método del servicio.") + "</p>";

    body.innerHTML =
      methodText +
      "<p><strong>Destino:</strong> " + escapeHtml(t.name || "—") + "<br>" +
      "<strong>Enfoque:</strong> " + escapeHtml(preset.title) + "</p>" +
      (selected ? "" : "<p class='easy-note'>Elegí un lugar de la lista para ver el desglose de ese puntaje.</p>") +
      "<table class='easy-table'><thead><tr><th>Componente</th><th>Peso</th><th>" +
      (selected ? "En " + escapeHtml(selected.site.name) : "Puntaje") +
      "</th></tr></thead><tbody>" +
      ["G", "T", "E", "V", "O"].map(compLine).join("") +
      "</tbody></table>" +
      '<p><button type="button" class="easy-btn" id="easy-go-advanced">Abrir modo avanzado</button></p>';

    bg.hidden = false;
    bg.classList.add("is-open");
    const go = $("#easy-go-advanced");
    if (go) {
      go.addEventListener("click", function () {
        closeCalc();
        setMode("advanced");
        if (selected && window.HexastraApp && typeof window.HexastraApp.selectSite === "function") {
          window.HexastraApp.selectSite(selected.site.id);
        }
        if (window.HexastraApp && typeof window.HexastraApp.showMethodModal === "function") {
          window.HexastraApp.showMethodModal();
        }
        $("#mode-advanced").focus();
      });
    }
    $("#easy-calc-close").focus();
  }

  function closeCalc() {
    const bg = $("#easy-calc-bg");
    if (!bg) return;
    bg.hidden = true;
    bg.classList.remove("is-open");
  }

  async function loadTargets(body) {
    state.loadingTargets = true;
    state.error = null;
    try {
      const list = await callApi("getTargets", [body]);
      state.targets[body] = Array.isArray(list) ? list : [];
    } catch (err) {
      state.targets[body] = [];
      state.error = "No pudimos cargar los destinos. Recargá la página. " +
        (err && err.message ? err.message : "");
    } finally {
      state.loadingTargets = false;
    }
  }

  async function boot() {
    const ready = window.HEXASTRA_API_READY;
    if (ready && typeof ready.then === "function") {
      try {
        state.api = await ready;
      } catch (e) {
        state.api = window.HexastraAPI || null;
      }
    } else {
      state.api = window.HexastraAPI || null;
    }
    state.stub = window.HexastraAPIStub || null;
    if (!api() || typeof api().getTargets !== "function") {
      if (state.stub && typeof state.stub.getTargets === "function") {
        state.api = state.stub;
      }
    }
    if (!api() || typeof api().getTargets !== "function") {
      const root = $("#easy-app");
      if (root) {
        root.innerHTML = '<div class="easy"><p class="easy-status easy-status-error">No pude cargar la API del buscador. Falta js/api.js y tampoco arrancó el respaldo local.</p></div>';
      }
      return;
    }

    buildShell();
    setMode("easy");

    $("#mode-easy").addEventListener("click", function () { setMode("easy"); });
    $("#mode-advanced").addEventListener("click", function () { setMode("advanced"); });

    try {
      state.method = await callApi("getMethod", []);
      state.presetId = presets().length ? presets()[0].id : null;
    } catch (err) {
      state.method = null;
      state.methodError = "No pudimos cargar el método del servicio. " + (err && err.message ? err.message : "");
    }

    try {
      const regions = await callApi("getRegions", []);
      state.regions = normalizeRegions(regions);
    } catch (err) {
      state.regions = { continents: [] };
    }

    try {
      state.featured = await loadFeatured();
    } catch (err) {
      state.featured = { source: "error", groups: [], error: err && err.message };
    }
    renderFeatured();

    state.body = "moon";
    plotFeaturedSites();
    state.loadingTargets = true;
    renderMain();
    await loadTargets("moon");
    renderMain();
    focusDestination();
    renderPair();
    invalidateEasyMap();
    setTimeout(invalidateEasyMap, 400);
    // Precargar Marte en silencio para que el cambio de pestaña sea inmediato.
    loadTargets("mars").then(function () {
      if (state.destBody === "mars") renderDestMarkers();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
