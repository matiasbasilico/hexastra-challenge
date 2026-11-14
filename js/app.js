/* HexAstra — modo avanzado: comparativa lado a lado Tierra | destino (Luna o Marte).
 *
 * Todo el contenido sale de la API (js/api.js):
 *   - sitios terrestres:  GET {earth}/candidates
 *   - destinos:           GET {planetary}/sites?body=moon|mars
 *   - ranking y par:      POST {earth}/tasi  (el par es el destino elegido + el resultado TASI)
 *   - método y presets:   GET {earth}/method
 * El front no tiene cifras, sitios ni fórmulas propias. Sin servicios, muestra que no están disponibles.
 */
(function () {
  "use strict";

  const COMPONENT_KEYS = ["G", "T", "E", "V", "O"];
  // Mercator web no llega a los polos: los sitios del polo sur lunar se dibujan en este borde.
  const MERCATOR_MAX_LAT = 85.05;

  const state = {
    api: null,
    apiOk: false,
    earthMap: null,
    marsMap: null,
    layers: {},
    sites: {},            // sitios terrestres de /candidates, por id
    earthMarkers: {},
    targets: [],          // destinos de /sites (Luna y Marte)
    destMarkers: {},      // puntos de los destinos en el mapa derecho
    target: null,         // destino elegido
    targetMarker: null,
    rightBody: "mars",
    selectedId: null,
    rankIds: [],
    lastTasi: null,
    regions: null,
    method: null,
    examples: [],         // pares documentados en la literatura (GET {earth}/examples)
    details: {},          // ficha completa del sitio (GET {earth}/candidates/{id}), con features
    vectors: {},          // vector del destino (GET {planetary}/sites/{id}/vector)
    tasiByTarget: {},     // POST /tasi por destino con los pesos y γ por defecto del servicio
  };

  // Métricas que se comparan lado a lado: clave en el sitio terrestre (features) y en el destino
  // (vector), con la etiqueta de interfaz. Los valores y unidades vienen de la API.
  const METRIC_ROWS = [
    { label: "Relieve relativo", earth: "relative_relief", comp: "T", target: "relative_relief_m" },
    { label: "Pendiente", earth: "slope", comp: "T", target: "slope_deg" },
    { label: "Rugosidad", earth: "roughness", comp: "T", target: "roughness_m" },
    { label: "Temperatura media", earth: "temp_mean", comp: "E", target: "temp_mean" },
    { label: "Amplitud térmica diaria", earth: "temp_diurnal_range", comp: "E", target: "temp_diurnal_range" },
    { label: "Iluminación", earth: "illumination_pct", comp: "E", target: "illumination_pct" },
    { label: "Precipitación anual", earth: "precip_mm", comp: "Vo", target: "precip_mm" },
    { label: "Indicador de hielo", earth: "water_ice_indicator", comp: "Vo", target: "water_ice_indicator" },
  ];
  const UNIT_LABELS = { degC: "°C", deg: "°", percent: "%", "mm/year": "mm/año", mm: "mm", m: "m", index_0_1: "", unitless: "" };
  const QUALITY_LABELS = {
    measured: ["dato medido", "ok"],
    derived: ["derivado", "ok"],
    modeled: ["modelado", "model"],
    convention: ["convención", "model"],
    derived_from_published_range: ["de rango publicado", "model"],
  };

  const $ = (sel) => document.querySelector(sel);

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function explain() {
    return window.HexastraExplain;
  }

  /* ---------- Movimiento de los mapas ---------- */

  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function flyOpts(duration) {
    return reducedMotion() ? { animate: false } : { duration: duration };
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

  function clampLatLng(lat, lon) {
    return [Math.max(-MERCATOR_MAX_LAT, Math.min(MERCATOR_MAX_LAT, Number(lat))), Number(lon)];
  }

  /* ---------- Íconos ---------- */

  function divIcon(kind, active) {
    return L.divIcon({
      className: "",
      html: '<div class="pin ' + kind + (active ? " active" : "") + '"></div>',
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });
  }

  function rankIcon(n, active) {
    return L.divIcon({
      className: "",
      html: '<div class="pin rank' + (active ? " active" : "") + '">' + n + "</div>",
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });
  }

  function targetIcon(body) {
    return L.divIcon({
      className: "",
      html: '<div class="pin target ' + (body === "moon" ? "moon" : "mars") + '"></div>',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });
  }

  function isLessStudied(site) {
    return site.known_level === "lesser-known" || !!site.highlight_less_studied;
  }

  // Un solo lugar decide el ícono de cada sitio terrestre: los puntuados conservan su número
  // de ranking y solo el seleccionado se resalta (anillo cian), sin perder el número.
  function earthIconFor(sid) {
    const active = sid === state.selectedId;
    const rank = state.rankIds.indexOf(sid);
    if (rank !== -1) return rankIcon(rank + 1, active);
    const s = state.sites[sid];
    return divIcon(s && isLessStudied(s) ? "menos" : "earth", active);
  }

  function refreshEarthIcons() {
    Object.entries(state.earthMarkers).forEach(([sid, marker]) => {
      marker.setIcon(earthIconFor(sid));
      marker.setZIndexOffset(sid === state.selectedId ? 1000 : 0);
    });
  }

  /* ---------- Mapas ---------- */

  function initMaps() {
    const earth = L.map("map-earth", { zoomControl: true, minZoom: 2, maxZoom: 12, worldCopyJump: true }).setView([20, 0], 2);
    const mars = L.map("map-mars", { zoomControl: true, minZoom: 1, maxZoom: 8, worldCopyJump: true }).setView([0, 0], 2);

    const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    });
    const esri = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Teselas: Esri, Maxar, Earthstar Geographics",
      maxZoom: 18,
    });
    // Mapa base según el control (por defecto satelital, que convive con el fondo noche de la marca).
    ($("#layer-esri") && $("#layer-esri").checked ? esri : osm).addTo(earth);

    const gibsDate = $("#gibs-date").value;
    const gibsTrueColor = L.tileLayer(
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
      { date: gibsDate, attribution: "NASA GIBS / EOSDIS, MODIS Terra True Color", maxZoom: 12, maxNativeZoom: 9, opacity: 0.95 }
    );
    const gibsLst = L.tileLayer(
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Land_Surface_Temp_Day/default/{date}/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png",
      { date: gibsDate, attribution: "NASA GIBS / EOSDIS, MODIS Terra LST (día)", maxZoom: 12, maxNativeZoom: 7, opacity: 0.7 }
    );
    const opm = L.tileLayer(
      "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png",
      { attribution: 'OpenPlanetaryMap, <a href="http://openplanetarymap.org/basemaps/mars/opm-mars-basemap-v0-2/">OPM Mars Basemap v0.2</a>', maxZoom: 8, maxNativeZoom: 9 }
    );
    const mola = L.tileLayer("https://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/mola-color/{z}/{x}/{y}.png", {
      attribution: "WhereOnMars / Carto, MOLA color (relieve sombreado)", maxZoom: 8, maxNativeZoom: 6, tms: true,
    });
    const marsShaded = L.tileLayer(
      "https://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/celestia_mars-shaded-16k_global/{z}/{x}/{y}.png",
      { attribution: "WhereOnMars / Carto, Celestia Mars shaded", maxZoom: 8, maxNativeZoom: 5, tms: true }
    );
    const opmMoon = L.tileLayer(
      "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png",
      { attribution: "OpenPlanetaryMap, OPM Moon Basemap v0.1", maxZoom: 8, maxNativeZoom: 9 }
    );
    opm.addTo(mars);

    state.earthMap = earth;
    state.marsMap = mars;
    state.layers = { osm, esri, gibsTrueColor, gibsLst, opm, mola, marsShaded, opmMoon };
    const resizeMaps = () => { earth.invalidateSize(); mars.invalidateSize(); };
    window.addEventListener("resize", resizeMaps);
    setTimeout(resizeMaps, 200);

    $("#layer-osm").addEventListener("change", () => setEarthBase($("#layer-osm").checked ? "osm" : "esri"));
    $("#layer-esri").addEventListener("change", () => setEarthBase($("#layer-esri").checked ? "esri" : "osm"));
    $("#layer-gibs-tc").addEventListener("change", () => toggleOverlay(gibsTrueColor, $("#layer-gibs-tc").checked, earth));
    $("#layer-gibs-lst").addEventListener("change", () => toggleOverlay(gibsLst, $("#layer-gibs-lst").checked, earth));
    $("#gibs-date").addEventListener("change", () => {
      const d = $("#gibs-date").value;
      [gibsTrueColor, gibsLst].forEach((ly) => {
        ly.options.date = d;
        if (earth.hasLayer(ly)) { earth.removeLayer(ly); ly.addTo(earth); }
      });
    });
    $("#layer-opm").addEventListener("change", () => setMarsBase("opm"));
    $("#layer-mola").addEventListener("change", () => setMarsBase("mola"));
    $("#layer-shaded").addEventListener("change", () => setMarsBase("shaded"));

    function setEarthBase(which) {
      const useEsri = which === "esri";
      if (!earth.hasLayer(useEsri ? esri : osm)) (useEsri ? esri : osm).addTo(earth);
      if (earth.hasLayer(useEsri ? osm : esri)) earth.removeLayer(useEsri ? osm : esri);
      $("#layer-esri").checked = useEsri;
      $("#layer-osm").checked = !useEsri;
    }
    function setMarsBase(which) {
      [opm, mola, marsShaded].forEach((ly) => { if (mars.hasLayer(ly)) mars.removeLayer(ly); });
      $("#layer-opm").checked = which === "opm";
      $("#layer-mola").checked = which === "mola";
      $("#layer-shaded").checked = which === "shaded";
      if (state.rightBody === "mars") (which === "mola" ? mola : which === "shaded" ? marsShaded : opm).addTo(mars);
    }
  }

  function toggleOverlay(layer, on, map) {
    if (on && !map.hasLayer(layer)) layer.addTo(map);
    if (!on && map.hasLayer(layer)) map.removeLayer(layer);
  }

  // Mapa derecho: Marte o Luna según el destino, con sus puntos y el destino elegido resaltado.
  function setRightBody(body) {
    const map = state.marsMap;
    const Lrs = state.layers;
    const marsLayers = [Lrs.opm, Lrs.mola, Lrs.marsShaded];
    state.rightBody = body;
    const label = $("#map-right-label");
    if (body === "moon") {
      marsLayers.forEach((ly) => { if (map.hasLayer(ly)) map.removeLayer(ly); });
      if (!map.hasLayer(Lrs.opmMoon)) Lrs.opmMoon.addTo(map);
      if (label) label.textContent = "Luna (la proyección Mercator comprime el polo sur)";
    } else {
      if (map.hasLayer(Lrs.opmMoon)) map.removeLayer(Lrs.opmMoon);
      if (!marsLayers.some((ly) => map.hasLayer(ly))) {
        ($("#layer-mola").checked ? Lrs.mola : $("#layer-shaded").checked ? Lrs.marsShaded : Lrs.opm).addTo(map);
      }
      if (label) label.textContent = "Marte";
    }
    Object.entries(state.destMarkers).forEach(([id, m]) => {
      const t = state.targets.find((x) => x.id === id);
      if (t && t.body === body) m.addTo(map);
      else if (map.hasLayer(m)) map.removeLayer(m);
    });
    if (state.targetMarker) {
      if (state.target && state.target.body === body) state.targetMarker.addTo(map);
      else if (map.hasLayer(state.targetMarker)) map.removeLayer(state.targetMarker);
    }
    setTimeout(() => map.invalidateSize(), 150);
  }

  function addDestMarkers() {
    state.targets.forEach((t) => {
      if (t.lat == null || t.lon == null) return;
      const m = L.marker(clampLatLng(t.lat, t.lon), { icon: divIcon(t.body === "moon" ? "moon" : "mars", false), title: t.name });
      m.bindTooltip(t.short_name || t.name);
      m.on("click", () => {
        $("#finder-target").value = t.id;
        chooseTarget(t);
      });
      state.destMarkers[t.id] = m;
    });
  }

  // Marca y centra el destino elegido en el mapa derecho, sin tocar el sitio terrestre elegido.
  function focusTarget(t) {
    if (!t || t.lat == null || t.lon == null || !state.marsMap) return;
    state.target = t;
    if (state.targetMarker) state.marsMap.removeLayer(state.targetMarker);
    state.targetMarker = L.marker(clampLatLng(t.lat, t.lon), {
      icon: targetIcon(t.body),
      title: t.name,
      alt: "Destino elegido: " + t.name,
      zIndexOffset: 1000,
      keyboard: true,
    });
    state.targetMarker.bindTooltip(t.short_name || t.name, { permanent: true, direction: "top", offset: [0, -12] });
    setRightBody(t.body);
    safeFly(state.marsMap, clampLatLng(t.lat, t.lon), t.body === "moon" ? 4 : 5, flyOpts(0.8));
  }

  function chooseTarget(t) {
    state.lastTasi = null;
    state.rankIds = [];
    refreshEarthIcons();
    renderSiteList();
    focusTarget(t);
    if (state.selectedId) renderSitePanel(state.selectedId);
  }

  /* ---------- Sitios terrestres (de /candidates) ---------- */

  function placeLine(site) {
    const country = site.country_name ? site.country_name + (site.country_iso ? " (" + site.country_iso + ")" : "") : "";
    return [country, site.continent || ""].filter(Boolean).join(", ");
  }

  function addSite(site) {
    if (!site || !site.id) return;
    state.sites[site.id] = Object.assign({}, state.sites[site.id] || {}, site);
    if (state.earthMarkers[site.id] || site.lat == null || site.lon == null || !state.earthMap) return;
    const m = L.marker([site.lat, site.lon], { icon: earthIconFor(site.id), title: site.name });
    m.on("click", () => selectSite(site.id));
    m.bindTooltip(site.short_name || site.name);
    m.addTo(state.earthMap);
    state.earthMarkers[site.id] = m;
  }

  function siteButton(site, extra) {
    const rank = state.rankIds.indexOf(site.id);
    const match = currentMatch(site.id);
    return (
      '<button type="button" class="site-btn' + (state.selectedId === site.id ? " active" : "") + '" data-id="' + escapeHtml(site.id) + '">' +
        '<span class="name">' + (rank !== -1 ? (rank + 1) + ". " : "") + escapeHtml(site.name) + "</span>" +
        (extra || "") +
        '<span class="meta">' + escapeHtml(placeLine(site)) +
          (match && match.score != null ? ", TASI " + escapeHtml(explain().formatScore(match.score)) + " de 100" : "") +
        "</span>" +
        (isLessStudied(site) ? '<span class="badge menos">Menos estudiado</span>' : "") +
      "</button>"
    );
  }

  function exampleFor(siteId) {
    return state.examples.find((e) => e.earth_id === siteId) || null;
  }

  function targetName(id) {
    const t = state.targets.find((x) => x.id === id);
    return t ? (t.short_name || t.name) : id;
  }

  function renderSiteList() {
    const box = $("#site-buttons");
    const sites = Object.values(state.sites);
    if (!sites.length) {
      box.innerHTML = "<p class='placeholder-msg'>No hay sitios terrestres en el catálogo de la API.</p>";
      return;
    }
    const examples = state.examples
      .filter((e) => state.sites[e.earth_id])
      .map((e) => siteButton(state.sites[e.earth_id],
        '<span class="pair-line">con ' + escapeHtml((e.target_ids || []).map(targetName).join(" y ")) + "</span>"))
      .join("");
    // Después el ranking vigente (en su orden) y el resto del catálogo, por nombre.
    const ranked = state.rankIds.map((id) => state.sites[id]).filter(Boolean);
    const rest = sites.filter((s) => state.rankIds.indexOf(s.id) === -1)
      .sort((a, b) => String(a.name).localeCompare(String(b.name), "es"));
    box.innerHTML =
      (examples ? "<h3 class='sitelist-group'>Pares documentados en la literatura</h3>" + examples : "") +
      "<h3 class='sitelist-group'>" + (ranked.length ? "Ranking TASI y resto del catálogo" : "Todo el catálogo") +
        " (" + sites.length + " sitios)</h3>" +
      ranked.concat(rest).map((site) => siteButton(site)).join("");
    box.querySelectorAll(".site-btn").forEach((btn) => {
      btn.addEventListener("click", () => selectSite(btn.getAttribute("data-id"), true));
    });
  }

  // Al elegir un sitio de los pares documentados, el destino pasa a ser el de su par.
  function selectSite(id, fromList) {
    const site = state.sites[id];
    if (!site) return;
    const ex = exampleFor(id);
    if (fromList && ex && ex.target_ids && ex.target_ids.length && (!state.target || ex.target_ids.indexOf(state.target.id) === -1)) {
      const t = state.targets.find((x) => x.id === ex.target_ids[0]);
      if (t) {
        $("#finder-target").value = t.id;
        state.lastTasi = null;
        state.rankIds = [];
        focusTarget(t);
      }
    }
    state.selectedId = id;
    refreshEarthIcons();
    renderSiteList();
    if (site.lat != null && site.lon != null) safeFly(state.earthMap, [site.lat, site.lon], 8, flyOpts(0.9));
    keepTargetInView();
    renderSitePanel(id);
  }

  function keepTargetInView() {
    const t = state.target;
    if (!t || !state.marsMap || !hasSize(state.marsMap)) return;
    const ll = clampLatLng(t.lat, t.lon);
    if (!state.marsMap.getBounds().contains(ll)) state.marsMap.panTo(ll, flyOpts(0.6));
  }

  /* ---------- Ficha del sitio y del par ---------- */

  function currentMatch(id) {
    return ((state.lastTasi && state.lastTasi.matches) || []).find((m) => m.site && m.site.id === id) || null;
  }

  // Fracción 0–1 del puntaje para la escala de color violeta → óxido del manual.
  function scoreFraction(score) {
    const n = Number(score);
    if (score == null || Number.isNaN(n)) return "0";
    return Math.max(0, Math.min(1, n / 100)).toFixed(3);
  }

  function fact(label, value, status) {
    const tag = status === "measured"
      ? "<span class='tag ok'>dato medido</span>"
      : status === "placeholder"
        ? "<span class='tag warn'>dato a completar</span>"
        : "";
    return "<div class='fact'><dt>" + escapeHtml(label) + " " + tag + "</dt><dd>" + value + "</dd></div>";
  }

  function pairBlock(match, source) {
    const t = state.target;
    if (!t) {
      return "<h3>Destino</h3><p class='muted'>Elegí un destino en el buscador de arriba para ver el par en el mapa de la derecha.</p>";
    }
    const body = t.body === "moon" ? "Luna" : "Marte";
    const html = "<h3>Comparado con " + escapeHtml(t.short_name || t.name) + " (" + body + ")</h3>";
    if (!match) {
      return html + "<p class='muted'>Todavía no hay puntaje TASI de este sitio frente a ese destino.</p>";
    }
    const ex = explain().explainMatch(match);
    return html +
      "<div class='score-hero' style='--s:" + scoreFraction(match.score) + "'><div class='num score-color'>" + escapeHtml(explain().formatScore(match.score)) +
      "</div><p>de 100, índice TASI frente a " + escapeHtml(t.short_name || t.name) +
      (source === "por defecto" ? ", con los pesos y γ por defecto del servicio" : ", con los pesos de tu búsqueda") + ".</p>" +
      "<span class='score-bar' aria-hidden='true'><span></span></span></div>" +
      "<p><strong>Por qué se parece.</strong> " + escapeHtml(ex.why || "Sin componentes con dato.") + "</p>" +
      "<p><strong>En qué no.</strong> " + escapeHtml(ex.breaks) + "</p>" +
      (ex.missing.length
        ? "<p class='pair-missing'>" + ex.missing.map((k) => "<span class='tag warn'>Dato a completar: " + escapeHtml(k) + "</span>").join(" ") + "</p>"
        : "");
  }

  function componentsBlock(match) {
    if (!match) return "";
    const comps = match.components || {};
    const rows = COMPONENT_KEYS.map((k) => {
      const c = comps[k] || {};
      const label = explain().COMPONENT_LABELS[k];
      if (c.score == null || c.available === false) {
        return "<li class='comp-row'><span class='comp-name'>" + escapeHtml(label) + "</span><span class='tag warn'>sin dato</span>" +
          (c.reason ? "<span class='comp-reason'>" + escapeHtml(c.reason) + "</span>" : "") + "</li>";
      }
      return "<li class='comp-row' style='--s:" + scoreFraction(c.score) + "'><span class='comp-name'>" + escapeHtml(label) + "</span>" +
        "<span class='comp-score'>" + escapeHtml(explain().formatScore(c.score)) + " de 100</span>" +
        "<span class='score-bar' aria-hidden='true'><span></span></span></li>";
    }).join("");
    const used = (match.coverage && match.coverage.available_components) || [];
    return "<h3>Componentes TASI</h3><ul class='comp-list'>" + rows + "</ul>" +
      "<p class='muted'>Cobertura: " + used.length + " de 5 componentes con dato en los dos lados. Los pesos se renormalizan sobre esos.</p>";
  }

  // Convierte las URL de un texto de fuente en enlaces, escapando todo lo demás.
  function linkify(text) {
    const parts = String(text).split(/(https?:\/\/[^\s)]+)/g);
    return parts.map((p, i) => i % 2
      ? '<a href="' + escapeHtml(p) + '" target="_blank" rel="noopener">' + escapeHtml(p.replace(/^https?:\/\//, "").slice(0, 60)) + "</a>"
      : escapeHtml(p)).join("");
  }

  function unitText(unit) {
    if (unit == null) return "";
    return UNIT_LABELS[unit] != null ? UNIT_LABELS[unit] : unit;
  }

  function valueCell(item) {
    if (!item || item.value == null) return "<td><span class='tag warn'>a completar</span></td>";
    const unit = unitText(item.unit);
    const q = QUALITY_LABELS[item.quality];
    const n = Number(item.value);
    const shown = Number.isNaN(n) ? escapeHtml(item.value) : escapeHtml(n.toLocaleString("es-AR", { maximumFractionDigits: 2 }));
    return "<td><span class='cmp-value'>" + shown + (unit ? (unit === "%" || unit === "°" ? "" : " ") + escapeHtml(unit) : "") + "</span>" +
      (q ? " <span class='tag " + q[1] + "'>" + escapeHtml(q[0]) + "</span>" : "") + "</td>";
  }

  // Tabla lado a lado: datos del sitio (features de /candidates/{id}) y del destino (vector de /sites/{id}/vector).
  function dataTable(detail, vector) {
    const feats = (detail && detail.features) || {};
    const comps = (vector && vector.components) || {};
    const rows = METRIC_ROWS.map((r) => {
      const t = ((comps[r.comp] || (r.comp === "Vo" ? comps.V : null) || {}).metrics || {})[r.target];
      return "<tr><th scope='row'>" + escapeHtml(r.label) + "</th>" + valueCell(feats[r.earth]) + valueCell(t) + "</tr>";
    }).join("");
    return "<h3>Datos lado a lado</h3>" +
      "<table class='cmp-table'><thead><tr><th scope='col'>Métrica</th><th scope='col'>Sitio</th><th scope='col'>Destino</th></tr></thead>" +
      "<tbody>" + rows + "</tbody></table>" +
      "<p class='muted'>Valores de la API (earth /candidates y planetary /sites/…/vector). Lo que no tiene dato queda «a completar».</p>";
  }

  function literatureBlock(ex) {
    if (!ex) return "";
    const sources = (ex.sources || []).map((src) =>
      "<li><a href='" + escapeHtml(src.url) + "' target='_blank' rel='noopener'>" + escapeHtml(src.label || src.url) + "</a></li>").join("");
    return "<section class='literature' aria-label='Documentado en la literatura'>" +
      "<h3>Documentado en la literatura</h3>" +
      "<p class='muted'>Texto de la fuente del par, sin puntaje: no sale de TASI.</p>" +
      (ex.why_es ? "<p><strong>Por qué se parece.</strong> " + escapeHtml(ex.why_es) + "</p>" : "") +
      (ex.breaks_es ? "<p><strong>En qué no.</strong> " + escapeHtml(ex.breaks_es) + "</p>" : "") +
      (sources ? "<p class='muted'>Fuentes:</p><ul class='literature-sources'>" + sources + "</ul>" : "") +
      (ex.wikipedia_only ? "<p><span class='tag warn'>Solo Wikipedia: fuente de último recurso</span></p>" : "") +
      "</section>";
  }

  async function ensureDetails(siteId, target) {
    const api = state.api;
    const jobs = [];
    if (!state.details[siteId]) jobs.push(api.getCandidate(siteId).then((d) => { state.details[siteId] = d; }));
    if (target && !state.vectors[target.id]) jobs.push(api.getTargetVector(target.id).then((v) => { state.vectors[target.id] = v; }));
    if (target && !state.tasiByTarget[target.id]) {
      jobs.push((async () => {
        const vector = state.vectors[target.id] || (await api.getTargetVector(target.id));
        state.vectors[target.id] = vector;
        state.tasiByTarget[target.id] = await api.rankAnalogs({
          targetVector: vector,
          weights: (state.method && state.method.default_weights) || undefined,
          gamma: state.method ? state.method.default_gamma : undefined,
          top: Object.keys(state.sites).length || 100,
          applyMask: true,
        });
      })());
    }
    await Promise.all(jobs);
  }

  // El puntaje del par: el del último ranking si incluye el sitio; si no, el de /tasi con los
  // pesos y γ por defecto del servicio para ese destino.
  function matchFor(siteId) {
    const fromSearch = currentMatch(siteId);
    if (fromSearch) return { match: fromSearch, discarded: null, source: "búsqueda" };
    const data = state.target && state.tasiByTarget[state.target.id];
    if (!data) return { match: null, discarded: null, source: null };
    const match = (data.matches || []).find((m) => m.site && m.site.id === siteId) || null;
    const discarded = (data.discarded || []).find((d) => d.id === siteId) || null;
    return { match: match, discarded: discarded, source: "por defecto" };
  }

  async function renderSitePanel(id) {
    const site = state.sites[id];
    if (!site) return;
    const target = state.target;
    paintSitePanel(id, true);
    try {
      await ensureDetails(id, target);
    } catch (e) {
      if (state.selectedId === id) paintSitePanel(id, false, e.message);
      return;
    }
    if (state.selectedId === id && state.target === target) paintSitePanel(id, false);
  }

  function paintSitePanel(id, loading, error) {
    const site = state.sites[id];
    const target = state.target;
    const ex = exampleFor(id);
    const exOk = ex && target && (ex.target_ids || []).indexOf(target.id) !== -1;
    const found = matchFor(id);
    const mask = (found.match && found.match.mask) || {};
    $("#panel").innerHTML =
      '<div class="panel-head"><h2>Sitio</h2></div>' +
      '<div class="panel-body">' +
        "<p class='kicker'>" + escapeHtml(placeLine(site)) + "</p>" +
        (isLessStudied(site) ? "<p><span class='badge menos'>Menos estudiado</span></p>" : "") +
        "<h3 class='site-title'>" + escapeHtml(site.name) + "</h3>" +
        (site.summary ? "<p class='lead'>" + escapeHtml(site.summary) + "</p>" : "") +
        '<dl class="facts">' +
          fact("Coordenadas", Number(site.lat).toFixed(5) + "°, " + Number(site.lon).toFixed(5) + "°", site.coord_source ? "measured" : "placeholder") +
          fact("País", escapeHtml(site.country_name || "a completar") + (site.country_iso ? " (" + escapeHtml(site.country_iso) + ")" : ""), "") +
        "</dl>" +
        (loading ? "<p class='muted' role='status'>Cargando datos del sitio, del destino y el puntaje TASI…</p>" : "") +
        (error ? "<p class='caution'>No pudimos cargar los datos del par: " + escapeHtml(error) + "</p>" : "") +
        (mask.unknown_flags && mask.unknown_flags.length
          ? "<p class='caution'>Máscara incompleta: " + escapeHtml(mask.unknown_flags.join(", ")) + ". El sitio no se descartó.</p>"
          : "") +
        (found.discarded ? "<p class='caution'>La máscara M(x) descarta este sitio frente a este destino, así que no tiene puntaje TASI.</p>" : "") +
        pairBlock(found.match, found.source) +
        (!loading && target ? dataTable(state.details[id], state.vectors[target.id]) : "") +
        componentsBlock(found.match) +
        (exOk ? literatureBlock(ex) : "") +
        "<h3>Fuente de las coordenadas</h3>" +
        "<p class='sources'>" + linkify(site.coord_source || "A completar: el catálogo no trae la fuente de este punto.") + "</p>" +
      "</div>";
  }

  /* ---------- Buscador (TASI) ---------- */

  function tasiWeightsFromUI() {
    const weights = {};
    document.querySelectorAll("#finder-features input[data-w]").forEach((rng) => {
      const on = document.querySelector('#finder-features input[data-feat="' + rng.dataset.w + '"]');
      weights[rng.dataset.w] = on && !on.checked ? 0 : (Number(rng.value) || 0) / 100;
    });
    return weights;
  }

  function fillCountrySelect(continentName) {
    const sel = $("#finder-country");
    if (!sel || !state.regions) return;
    const current = sel.value;
    sel.innerHTML = "<option value=''>Todos los países</option>";
    const continents = state.regions.continents || [];
    (continentName ? continents.filter((c) => c.name === continentName) : continents).forEach((cont) => {
      (cont.countries || []).forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.iso;
        opt.textContent = c.name + " (" + c.iso + ")";
        sel.appendChild(opt);
      });
    });
    sel.value = current && Array.from(sel.options).some((o) => o.value === current) ? current : "";
    sel.disabled = false;
  }

  function populateFinder() {
    const sel = $("#finder-target");
    sel.innerHTML = "";
    [["moon", "Luna"], ["mars", "Marte"]].forEach(([body, name]) => {
      const list = state.targets.filter((s) => s.body === body);
      if (!list.length) return;
      const optg = document.createElement("optgroup");
      optg.label = name;
      list.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        optg.appendChild(opt);
      });
      sel.appendChild(optg);
    });
    sel.disabled = !state.targets.length;

    // Pesos iniciales, γ y umbral de NDVI salen de GET {earth}/method.
    const defaults = (state.method && state.method.default_weights) || {};
    const box = $("#finder-features");
    box.innerHTML = COMPONENT_KEYS.map((k) => {
      const w = Number(defaults[k]) || 0;
      const label = escapeHtml(explain().COMPONENT_LABELS[k]);
      return (
        '<div class="feat-row">' +
          '<label><input type="checkbox" data-feat="' + k + '"' + (w > 0 ? " checked" : "") + "> " + label + "</label>" +
          '<input type="range" min="0" max="100" step="5" value="' + Math.round(w * 100) + '" data-w="' + k + '" aria-label="Peso de ' + label + '">' +
          '<span data-wv="' + k + '">' + w.toFixed(2).replace(".", ",") + "</span>" +
        "</div>"
      );
    }).join("");
    box.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const w = box.querySelector('input[data-w="' + cb.dataset.feat + '"]');
        if (w) w.disabled = !cb.checked;
      });
    });
    box.querySelectorAll("input[type=range]").forEach((rng) => {
      rng.addEventListener("input", () => {
        const sp = box.querySelector('[data-wv="' + rng.dataset.w + '"]');
        if (sp) sp.textContent = (Number(rng.value) / 100).toFixed(2).replace(".", ",");
      });
    });

    const csel = $("#finder-continent");
    csel.innerHTML = "<option value=''>Todos los continentes</option>";
    ((state.regions && state.regions.continents) || []).forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.name;
      opt.textContent = c.name;
      csel.appendChild(opt);
    });
    csel.disabled = false;
    csel.addEventListener("change", () => fillCountrySelect(csel.value));
    fillCountrySelect("");

    const gamma = $("#finder-gamma");
    const gval = $("#finder-gamma-val");
    if (state.method && state.method.default_gamma != null) gamma.value = state.method.default_gamma;
    const sync = () => { gval.textContent = Number(gamma.value).toFixed(1).replace(".", ","); };
    gamma.addEventListener("input", sync);
    sync();
    const ndvi = $("#finder-mask-ndvi");
    if (ndvi && state.method && state.method.ndvi_threshold != null) {
      ndvi.textContent = String(state.method.ndvi_threshold).replace(".", ",");
    }
    $("#btn-buscar").disabled = !state.targets.length;
  }

  async function runSearch() {
    const out = $("#finder-results");
    const api = state.api;
    if (!state.apiOk || !api) {
      out.innerHTML = "<p class='caution'>" + escapeHtml(unavailableText()) + "</p>";
      return;
    }
    const targetId = $("#finder-target").value;
    const weights = tasiWeightsFromUI();
    if (Object.values(weights).every((w) => !w)) {
      out.innerHTML = "<p class='caution'>Dejá al menos un componente TASI con peso mayor que cero.</p>";
      return;
    }
    out.innerHTML = "<p class='muted' role='status'>Buscando…</p>";
    try {
      const chosen = state.targets.find((x) => x.id === targetId);
      if (chosen) focusTarget(chosen);
      const targetVector = await api.getTargetVector(targetId);
      const data = await api.rankAnalogs({
        targetVector: targetVector,
        weights: weights,
        gamma: Number($("#finder-gamma").value),
        top: 8,
        continent: $("#finder-continent").value || undefined,
        country: $("#finder-country").value || undefined,
        applyMask: $("#finder-mask").checked,
      });
      state.lastTasi = data;
      const scored = (data.matches || []).filter((m) => m.score != null);
      scored.forEach((m) => addSite(m.site));
      state.rankIds = scored.map((m) => m.site.id);
      refreshEarthIcons();
      renderSiteList();
      if (scored.length && hasSize(state.earthMap)) {
        state.earthMap.fitBounds(scored.map((m) => [m.site.lat, m.site.lon]), { padding: [28, 28], maxZoom: 6 });
      }
      out.innerHTML = renderRanking(data, targetId);
      out.querySelectorAll(".rank-item").forEach((btn) => {
        btn.addEventListener("click", () => selectSite(btn.dataset.id));
      });
      if (state.selectedId) renderSitePanel(state.selectedId);
    } catch (e) {
      out.innerHTML = "<p class='caution'>Falló la consulta a los servicios: " + escapeHtml(e.message) + "</p>";
    }
  }

  function renderRanking(data, targetId) {
    const items = (data.matches || []).map((m, i) => {
      const used = (m.coverage && m.coverage.available_components) || [];
      const skipped = (m.weights && m.weights.skipped) || [];
      const flags = (m.mask && m.mask.unknown_flags) || [];
      return (
        '<li><button type="button" class="rank-item" data-id="' + escapeHtml(m.site.id) + '">' +
          "<strong>" + (i + 1) + ". " + escapeHtml(m.site.name) + "</strong> <span class='score'>" +
          (m.score == null ? "sin puntaje" : escapeHtml(explain().formatScore(m.score)) + " de 100") +
          "</span><span class='score-bar' style='--s:" + scoreFraction(m.score) + "' aria-hidden='true'><span></span></span>" +
          "<span class='muted'>" + escapeHtml(placeLine(m.site)) +
          ". Usó: " + escapeHtml(used.join(", ") || "ninguno") +
          (skipped.length ? ". Omitió: " + escapeHtml(skipped.join(", ")) : "") + ".</span>" +
          (flags.length ? "<p class='rank-flags'>Máscara incompleta: " + escapeHtml(flags.join(", ")) + ".</p>" : "") +
        "</button></li>"
      );
    }).join("");
    const discarded = data.n_discarded_by_mask || 0;
    return (
      "<p class='muted'>Destino: <strong>" + escapeHtml((data.target && data.target.name) || targetId) + "</strong>. " +
      "TASI con γ = " + escapeHtml(String(data.gamma).replace(".", ",")) + ", " + escapeHtml(String(data.n_scored)) + " candidatos puntuados" +
      (discarded ? ", " + discarded + " descartados por la máscara" : "") + ".</p>" +
      (items ? "<ol class='rank-list'>" + items + "</ol>" : "<p class='muted'>No hay análogos con estos filtros.</p>")
    );
  }

  /* ---------- Conexión ---------- */

  function unavailableText() {
    return (window.HexastraAPIStub && window.HexastraAPIStub.message) ||
      "Los servicios no están disponibles en este momento.";
  }

  function markDown(status) {
    state.apiOk = false;
    status.textContent = unavailableText();
    status.className = "api-status down";
    return false;
  }

  async function detectApi() {
    const status = $("#api-status");
    const api = window.HexastraAPI;
    state.api = api;
    if (!api || typeof api.health !== "function") return markDown(status);
    try {
      const h = await api.health();
      if (!h.ok) return markDown(status);
      state.apiOk = true;
      status.textContent = "Servicios conectados: planetary " + h.urls.planetary + ", earth " + h.urls.earth + ".";
      status.className = "api-status ok";
      return true;
    } catch (e) {
      return markDown(status);
    }
  }

  async function initFinder() {
    const ok = await detectApi();
    if (!ok) {
      $("#finder-target").disabled = true;
      $("#btn-buscar").disabled = true;
      $("#site-buttons").innerHTML = "<p class='placeholder-msg'>" + escapeHtml(unavailableText()) + "</p>";
      return;
    }
    const api = state.api;
    try {
      const [moon, mars, regions, candidates, method, examples] = await Promise.all([
        api.getTargets("moon"),
        api.getTargets("mars"),
        api.getRegions(),
        api.getCandidates(),
        api.getMethod(),
        api.getExamples().catch(() => ({ examples: [] })),
      ]);
      state.targets = [].concat(moon || [], mars || []);
      state.regions = regions;
      state.method = method;
      state.examples = (examples && examples.examples) || [];
      (candidates.sites || []).forEach(addSite);
      state.examples.forEach((e) => { if (e.site) addSite(e.site); });
      renderSiteList();
      addDestMarkers();
      populateFinder();
      $("#btn-buscar").addEventListener("click", runSearch);
      $("#finder-target").addEventListener("change", () => {
        const t = state.targets.find((x) => x.id === $("#finder-target").value);
        if (t) chooseTarget(t);
      });
      // Arranque: el primer par documentado (sitio + su destino marcados); si no hay, el primer destino de la API.
      const firstExample = state.examples.find((e) => state.sites[e.earth_id] && (e.target_ids || []).length);
      if (firstExample) {
        selectSite(firstExample.earth_id, true);
      } else {
        const first = state.targets.find((x) => x.id === $("#finder-target").value);
        if (first) focusTarget(first);
      }
    } catch (e) {
      const status = $("#api-status");
      status.textContent = "Los servicios respondieron /health pero falló una consulta del catálogo: " + e.message;
      status.className = "api-status down";
    }
  }

  /* ---------- Diálogo «Cómo se calcula» (contenido de GET {earth}/method) ---------- */

  function methodHtml(m) {
    const presets = (m.presets || []).map((p) =>
      "<tr><th scope='row'>" + escapeHtml(p.title_es) + "</th>" +
      COMPONENT_KEYS.map((k) => "<td>" + escapeHtml(String(Math.round(((p.weights || {})[k] || 0) * 100))) + "</td>").join("") + "</tr>"
    ).join("");
    const catalog = m.catalog || {};
    return (
      "<p><strong>" + escapeHtml(m.name_es || m.index) + ".</strong> " + escapeHtml(m.status_es || "") + "</p>" +
      "<h3>Pasos</h3><ol class='method-steps'>" + (m.steps_es || []).map((s) => "<li>" + escapeHtml(s) + "</li>").join("") + "</ol>" +
      "<h3>Enfoques y pesos (%)</h3>" +
      "<table class='easy-table'><thead><tr><th scope='col'>Enfoque</th>" +
      COMPONENT_KEYS.map((k) => "<th scope='col'>" + k + "</th>").join("") + "</tr></thead><tbody>" + presets + "</tbody></table>" +
      "<p class='muted'>γ por defecto: " + escapeHtml(String(m.default_gamma).replace(".", ",")) +
      ". Umbral de NDVI de la máscara: " + escapeHtml(String(m.ndvi_threshold).replace(".", ",")) +
      ". Catálogo: " + escapeHtml(String(catalog.n_sites)) + " sitios (origen " + escapeHtml(catalog.origin || "a completar") + ").</p>"
    );
  }

  async function renderMethod() {
    const box = $("#method-body");
    if (!box || box.dataset.loaded === "1") return;
    box.innerHTML = "<p class='muted' role='status'>Cargando el método desde el servicio…</p>";
    try {
      const m = state.method || (await window.HexastraAPI.getMethod());
      state.method = m;
      box.dataset.loaded = "1";
      box.innerHTML = methodHtml(m);
    } catch (e) {
      box.innerHTML = "<p class='caution'>" + escapeHtml(e.message || unavailableText()) + "</p>";
    }
  }

  function openMethod() {
    $("#modal-bg").classList.add("open");
    renderMethod();
  }

  function bindModal() {
    const bg = $("#modal-bg");
    $("#btn-metodo").addEventListener("click", openMethod);
    $("#btn-fuentes").addEventListener("click", () => {
      openMethod();
      $("#fuentes-anchor").scrollIntoView();
    });
    bg.addEventListener("click", (e) => {
      if (e.target === bg || e.target.classList.contains("close")) bg.classList.remove("open");
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") bg.classList.remove("open");
    });
  }

  try {
    initMaps();
    bindModal();
    initFinder();
  } catch (err) {
    $("#panel").innerHTML = "<p class='placeholder-msg'>No se pudo iniciar el modo avanzado: " + escapeHtml(err.message) + "</p>";
  }

  window.HexastraApp = {
    invalidateMaps: function () {
      if (state.earthMap) state.earthMap.invalidateSize();
      if (state.marsMap) state.marsMap.invalidateSize();
      // Al mostrar el modo avanzado, el destino elegido vuelve al centro del mapa derecho.
      if (state.target && state.marsMap && hasSize(state.marsMap)) {
        state.marsMap.setView(clampLatLng(state.target.lat, state.target.lon), state.target.body === "moon" ? 4 : 5, { animate: false });
      }
    },
    showMethodModal: openMethod,
    selectSite: function (id) {
      if (state.sites[id]) selectSite(id);
    },
    getMethod: function () { return state.method; },
  };
})();
