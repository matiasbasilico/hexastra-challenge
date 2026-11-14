/* Hexastra — Modo fácil (asistente de 3 pasos). */
(function () {
  "use strict";

  const PRESETS = [
    {
      id: "equilibrado",
      title: "Equilibrado",
      lead: "Un poco de todo: terreno, clima, hielo y condiciones para operar.",
      weights: { G: 0.2, T: 0.2, E: 0.2, V: 0.2, O: 0.2 }
    },
    {
      id: "terreno",
      title: "Que el terreno se parezca",
      lead: "Prioriza la forma del paisaje, la pendiente y la geología.",
      weights: { G: 0.35, T: 0.45, E: 0.05, V: 0.05, O: 0.1 }
    },
    {
      id: "clima",
      title: "Que el clima sea extremo",
      lead: "Prioriza temperatura, amplitud térmica, iluminación y sequedad o hielo.",
      weights: { G: 0.05, T: 0.1, E: 0.5, V: 0.25, O: 0.1 }
    },
    {
      id: "robots",
      title: "Para probar robots",
      lead: "Prioriza pendientes, rugosidad y restricciones para moverse u operar.",
      weights: { G: 0.1, T: 0.3, E: 0.1, V: 0.1, O: 0.4 }
    }
  ];

  const STEP_LABELS = ["Elegí destino", "¿Qué te importa?", "¿Dónde buscar?"];

  const state = {
    api: null,
    step: 1,
    body: null,
    targets: { moon: [], mars: [] },
    targetId: null,
    targetVector: null,
    presetId: "equilibrado",
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
    reverseResults: null
  };

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

  function currentPreset() {
    return PRESETS.find(function (p) { return p.id === state.presetId; }) || PRESETS[0];
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
    const live = api();
    const stub = stubApi();
    if (live && typeof live.getFeatured === "function" && live.source !== "stub") {
      try {
        return normalizeFeatured(await live.getFeatured());
      } catch (e) { /* fallback */ }
    }
    if (live && typeof live.getServiceUrls === "function") {
      try {
        const urls = live.getServiceUrls();
        if (urls && urls.earth) {
          const r = await fetch(String(urls.earth).replace(/\/$/, "") + "/featured", { cache: "no-store" });
          if (r.ok) return normalizeFeatured(await r.json());
        }
      } catch (e) { /* servicio todavía no tiene /featured */ }
    }
    if (stub && typeof stub.getFeatured === "function") {
      return normalizeFeatured(await stub.getFeatured());
    }
    throw new Error("No pude cargar los lugares destacados.");
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
      const g = p.group === "argentina" || p.country === "AR" || p.country_name === "Argentina" ? groups[1] : groups[0];
      g.places.push(p);
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
    requestAnimationFrame(function () {
      if (easy && state.map) {
        state.map.invalidateSize();
      }
      if (!easy && window.HexastraApp && typeof window.HexastraApp.invalidateMaps === "function") {
        window.HexastraApp.invalidateMaps();
      }
    });
    setTimeout(function () {
      if (easy && state.map) state.map.invalidateSize();
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
        '<nav class="easy-steps" aria-label="Pasos del modo fácil">' +
          '<ol class="easy-stepper" id="easy-stepper"></ol>' +
        '</nav>' +
        '<section class="easy-featured" aria-label="Lugares destacados">' +
          '<div class="easy-featured-head">' +
            '<h2>Lugares destacados</h2>' +
            '<p>Atajos a sitios de referencia. Tocá uno para ir al mapa. Los que dicen «análogo clásico» (Antártida, Atacama, Hawái, Haughton…) están muy estudiados: el desafío pide también buscar análogos menos conocidos.</p>' +
          '</div>' +
          '<div id="easy-featured-groups"></div>' +
          '<div id="easy-featured-panel" class="easy-feat-panel" hidden></div>' +
        '</section>' +
        '<div class="easy-layout">' +
          '<section class="easy-main" id="easy-main" aria-live="polite"></section>' +
          '<section class="easy-map-wrap" aria-label="Mapa mundial de la Tierra">' +
            '<div class="easy-map-label">' +
              '<h2>Tierra · vista mundial</h2>' +
              '<div class="easy-map-tools">' +
                '<button type="button" class="easy-map-btn is-active" id="easy-basemap-sat" aria-pressed="true">Satélite</button>' +
                '<button type="button" class="easy-map-btn" id="easy-basemap-osm" aria-pressed="false">Mapa</button>' +
              '</div>' +
            '</div>' +
            '<div id="easy-map-earth" class="easy-map" role="application" aria-label="Mapa mundial"></div>' +
            '<p class="easy-map-hint" id="easy-map-hint">El mapa muestra el mundo. Cuando haya resultados, tocá un número para ir a ese lugar.</p>' +
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
    if (!state.map) return;
    requestAnimationFrame(function () { state.map.invalidateSize(); });
    setTimeout(function () { if (state.map) state.map.invalidateSize(); }, 200);
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
      box.innerHTML = '<p class="easy-status">No hay lugares destacados disponibles.</p>';
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
    const canCompare = !pending && (pl.has_features || !!state.targetId);
    const compareHint = pl.has_features
      ? "Busca sitios de la Luna y de Marte que se parezcan a este lugar."
      : (state.targetId
        ? "Este lugar todavía no tiene un vector local; vamos a mostrar cómo se compara con el destino que ya elegiste, si el ranking lo incluye."
        : "Para comparar, elegí primero un destino en la Luna o en Marte (paso 1), o esperá a que el servicio entregue el vector de este lugar.");
    panel.hidden = false;
    panel.innerHTML =
      '<div class="easy-feat-card">' +
        '<div class="easy-feat-card-head">' +
          "<h3>" + escapeHtml(pl.name) + "</h3>" +
          '<button type="button" class="easy-link" id="easy-feat-close">Cerrar</button>' +
        "</div>" +
        '<p class="easy-feat-meta">' + escapeHtml(place || "") +
          (pl.classic ? ' · <span class="easy-chip">Análogo clásico</span>' : "") +
          (pl.highlight_less_studied ? ' · <span class="easy-chip">Menos estudiado</span>' : "") +
        "</p>" +
        "<p>" + escapeHtml(pl.summary || "") + "</p>" +
        (pl.coord_source ? '<p class="easy-note">Coordenadas: ' + escapeHtml(pl.coord_source) + "</p>" : "") +
        (pending
          ? '<p class="easy-status easy-status-warn">Todavía no hay coordenadas ni vector en el catálogo local. Cuando el servicio de la Tierra publique este lugar, lo vamos a poder usar como atajo completo.</p>'
          : (!pl.has_features
            ? '<p class="easy-note">Podés ir al mapa. Los datos para el puntaje TASI de este sitio todavía no están en el catálogo local (dato a completar / cargando del servicio).</p>'
            : "")) +
        '<p class="easy-lead-mini">' + escapeHtml(compareHint) + "</p>" +
        '<div class="easy-actions easy-actions-inline">' +
          '<button type="button" class="easy-btn easy-btn-primary" id="easy-feat-compare"' +
            (pending && !state.targetId ? " disabled" : "") + ">Comparar con Luna/Marte</button>" +
        "</div>" +
        '<div id="easy-feat-reverse"></div>' +
      "</div>";
    const close = $("#easy-feat-close");
    if (close) close.addEventListener("click", function () {
      state.featuredId = null;
      state.reverseResults = null;
      clearFeaturedMarker();
      renderFeatured();
    });
    const cmp = $("#easy-feat-compare");
    if (cmp) cmp.addEventListener("click", function () { compareFeatured(pl); });
    if (state.reverseResults) renderReverseInto($("#easy-feat-reverse"));
  }

  function featuredIcon(active) {
    return L.divIcon({
      className: "",
      html: '<div class="easy-pin easy-pin-feat' + (active ? " is-active" : "") + '"></div>',
      iconSize: [22, 22],
      iconAnchor: [11, 11]
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
      marker.bindTooltip(pl.short_name || pl.name);
      state.featuredMarker = marker;
      const z = Math.abs(pl.lat) > 70 ? 5 : 7;
      state.map.flyTo([pl.lat, pl.lon], z, { duration: 0.8 });
      invalidateEasyMap();
    }
    const panel = $("#easy-featured-panel");
    if (panel && typeof panel.scrollIntoView === "function") {
      panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
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
            '<div class="easy-score"><span class="easy-score-num">' + escapeHtml(String(score)) + '</span><span class="easy-score-den">/ 100</span></div>' +
            '<div class="easy-result-body">' +
              '<p class="easy-result-rank">#' + (i + 1) + (body ? " · " + body : "") + "</p>" +
              "<h3>" + escapeHtml(site.name) + "</h3>" +
              (m.why ? '<p class="easy-why"><strong>Por qué se parece.</strong> ' + escapeHtml(m.why) + "</p>" : "") +
              (m.breaks ? '<p class="easy-breaks"><strong>En qué no.</strong> ' + escapeHtml(m.breaks) + "</p>" : "") +
              missingBadges(m.missing) +
            "</div></button></li>"
        );
      }).join("") + "</ol>";
    }
    el.innerHTML =
      '<div class="easy-results-head">' +
        "<h3>Luna y Marte, comparados con " + escapeHtml(t.short_name || t.name || "este lugar") + "</h3>" +
        (data.fallback
          ? '<p class="easy-lead-mini">El servicio todavía no arma el ranking inverso. Mostramos cómo queda este lugar frente al destino que elegiste.</p>'
          : '<p class="easy-lead-mini">Puntaje 0–100: qué tanto se parece cada destino al lugar terrestre. Tocá uno para usarlo como destino del buscador.</p>') +
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
    if (box) box.innerHTML = '<p class="easy-status" role="status">Estamos comparando este lugar con la Luna y con Marte…</p>';
    state.reverseResults = null;
    const weights = currentPreset().weights;
    const live = api();
    const stub = stubApi();
    try {
      let data = null;
      if (live && typeof live.rankTargetsFromEarth === "function" && live.source !== "stub") {
        try {
          data = await live.rankTargetsFromEarth({ earthId: pl.catalog_id || pl.id, weights: weights, gamma: 0.75, top: 10 });
        } catch (e) { data = null; }
      }
      if (!data && stub && typeof stub.rankTargetsFromEarth === "function" && pl.has_features) {
        data = await stub.rankTargetsFromEarth({ earthId: pl.catalog_id || pl.id, weights: weights, gamma: 0.75, top: 10 });
      }
      if (!data) {
        data = await compareAgainstSelectedTarget(pl, weights);
        data.fallback = true;
      }
      state.reverseResults = data;
    } catch (err) {
      state.reverseResults = {
        target: pl,
        matches: [],
        error: err && err.code === "NO_LOCAL_VECTOR"
          ? "Este lugar todavía no tiene un vector en el catálogo local. Elegí un destino en el paso 1 para ver al menos esa comparación, o esperá al servicio."
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
      gamma: 0.75,
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
        ? ("Comparación de " + (pl.short_name || pl.name) + " frente a " + (t.short_name || t.name || "el destino") + ", porque el ranking inverso todavía no está en el servicio.")
        : ("No apareció " + (pl.short_name || pl.name) + " en el ranking frente a este destino. Puede faltar el vector de este lugar en el catálogo."),
      fallback: true
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
            '<div class="easy-card-visual easy-visual-' + escapeHtml(t.body) + '" aria-hidden="true"></div>' +
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
        '<p class="easy-kicker">Paso 1 de 3</p>' +
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
    if (!state.targets[body].length) {
      await loadTargets(body);
      if (state.body === body) renderMain();
    }
  }

  async function chooseTarget(id) {
    state.targetId = id;
    state.results = null;
    renderMain();
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
        '<p class="easy-kicker">Paso 2 de 3' + (t ? " · " + escapeHtml(t.short_name || t.name) : "") + "</p>" +
        '<h2 class="easy-title" id="easy-step-title" tabindex="-1">¿Qué te importa?</h2>' +
        '<p class="easy-lead">Elegí un enfoque. Por detrás armamos los pesos del índice TASI (geología, terreno, clima, volátiles y operación). En este modo no mostramos las fórmulas.</p>' +
        '<div class="easy-presets" role="list">' +
          PRESETS.map(function (p) {
            const sel = p.id === state.presetId ? " is-selected" : "";
            return (
              '<button type="button" class="easy-card easy-card-preset' + sel + '" role="listitem" data-id="' +
              p.id + '" aria-pressed="' + (p.id === state.presetId ? "true" : "false") + '">' +
                '<h3>' + escapeHtml(p.title) + "</h3>" +
                "<p>" + escapeHtml(p.lead) + "</p>" +
              "</button>"
            );
          }).join("") +
        "</div>" +
        '<div class="easy-actions">' +
          '<button type="button" class="easy-btn" id="easy-back-2">Volver</button>' +
          '<button type="button" class="easy-btn easy-btn-primary" id="easy-next-2">Siguiente: dónde buscar</button>' +
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
        '<p class="easy-kicker">Paso 3 de 3' +
          (t ? " · " + escapeHtml(t.short_name || t.name) : "") +
          " · " + escapeHtml(preset.title) +
        "</p>" +
        '<h2 class="easy-title" id="easy-step-title" tabindex="-1">¿Dónde buscar?</h2>' +
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
              '<div class="easy-score" aria-label="Coincidencia ' + escapeHtml(String(score)) + ' de 100">' +
                '<span class="easy-score-num">' + escapeHtml(String(score)) + "</span>" +
                '<span class="easy-score-den">/ 100</span>' +
              "</div>" +
              '<div class="easy-result-body">' +
                '<p class="easy-result-rank">#' + (i + 1) + (place ? " · " + escapeHtml(place) : "") +
                  (site.highlight_less_studied ? ' · <span class="easy-chip">Menos estudiado</span>' : "") +
                "</p>" +
                "<h3>" + escapeHtml(site.name) + "</h3>" +
                '<p class="easy-why"><strong>Por qué se parece.</strong> ' + escapeHtml(m.why || "") + "</p>" +
                '<p class="easy-breaks"><strong>En qué no.</strong> ' + escapeHtml(m.breaks || "") + "</p>" +
                missingBadges(m.missing) +
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
        gamma: 0.75,
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
      const res = $("#easy-results");
      if (res && (state.results || state.error) && typeof res.scrollIntoView === "function") {
        res.scrollIntoView({ block: "start", behavior: "smooth" });
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
  }

  function plotResults(data) {
    if (!state.map) return;
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
      marker.bindTooltip(site.short_name || site.name);
      marker.on("click", function () { selectResult(site.id); });
      state.markers[site.id] = marker;
      latlngs.push([site.lat, site.lon]);
    });
    if (latlngs.length === 1) {
      state.map.flyTo(latlngs[0], 6, { duration: 0.8 });
    } else if (latlngs.length > 1) {
      state.map.flyToBounds(L.latLngBounds(latlngs).pad(0.4), { duration: 0.8, maxZoom: 6 });
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
      state.map.flyTo([hit.site.lat, hit.site.lon], 8, { duration: 0.8 });
    }
    const selectedBtn = document.querySelector('.easy-result[data-id="' + id + '"]');
    if (selectedBtn && typeof selectedBtn.scrollIntoView === "function") {
      selectedBtn.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
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
    const compLine = function (key, label) {
      const w = W[key];
      let s = "—";
      if (selected && selected.components && selected.components[key] != null) {
        s = Math.round(selected.components[key] * 100) + " / 100";
      } else if (selected) {
        s = "sin dato (se omitió y se repartieron los pesos)";
      }
      return "<tr><th scope='row'>" + label + "</th><td>" +
        (w * 100).toLocaleString("es-AR") + " %</td><td>" + s + "</td></tr>";
    };

    body.innerHTML =
      "<p>El modo fácil usa el índice TASI: una suma ponderada de cinco componentes " +
      "(geología G, terreno T, régimen térmico E, volátiles V y operación O). " +
      "Los pesos salen del enfoque que elegiste. Si un componente no tiene datos, se omite y los pesos se reparten entre los que sí tienen. " +
      "No es una métrica científica validada.</p>" +
      "<p><strong>Destino:</strong> " + escapeHtml(t.name || "—") + "<br>" +
      "<strong>Enfoque:</strong> " + escapeHtml(preset.title) + "</p>" +
      (selected ? "" : "<p class='easy-note'>Elegí un lugar de la lista para ver el desglose de ese puntaje.</p>") +
      "<table class='easy-table'><thead><tr><th>Componente</th><th>Peso</th><th>" +
      (selected ? "En " + escapeHtml(selected.site.name) : "Puntaje") +
      "</th></tr></thead><tbody>" +
      compLine("G", "Geología (G)") +
      compLine("T", "Terreno y rugosidad (T)") +
      compLine("E", "Clima e iluminación (E)") +
      compLine("V", "Volátiles / hielo (V)") +
      compLine("O", "Operación (O)") +
      "</tbody></table>" +
      (selected && selected.qualitative_flags && selected.qualitative_flags.length
        ? "<p class='easy-note'>" + escapeHtml(selected.qualitative_flags.join(" · ")) + "</p>"
        : "") +
      "<p>La elevación absoluta no entra en la comparación entre cuerpos: no se mide igual en la Tierra, la Luna y Marte.</p>" +
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
      const regions = await callApi("getRegions", []);
      state.regions = normalizeRegions(regions);
    } catch (err) {
      state.regions = { continents: [] };
    }

    try {
      state.featured = await loadFeatured();
    } catch (err) {
      state.featured = { source: "error", groups: [] };
    }
    renderFeatured();

    state.body = "moon";
    state.loadingTargets = true;
    renderMain();
    await loadTargets("moon");
    renderMain();
    invalidateEasyMap();
    setTimeout(invalidateEasyMap, 400);
    // Precargar Marte en silencio para que el cambio de pestaña sea inmediato.
    loadTargets("mars");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
