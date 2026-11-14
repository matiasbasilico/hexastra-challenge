/* Hexastra — Análogos argentinos (NASA Space Apps 2026) */
(function () {
  "use strict";

  const SCORING = {
    tMars: -59,
    tScale: 80,
    diurnalRef: 58,
    precipScale: 500,
    elevScale: 4000,
    weights: { temperatura: 0.2, amplitud_termica: 0.2, aridez: 0.35, altitud_uv_proxy: 0.25 },
  };

  const state = {
    data: null,
    selectedId: null,
    charts: { bars: null, radar: null },
    layers: {},
    earthMap: null,
    marsMap: null,
    earthMarkers: {},
    marsMarkers: {},
    moonMarkers: {},
    rightBody: "mars",
    apiBase: null,
    apiOk: false,
    catalog: null,
    rankIds: [],
    regions: null,
    lastTasi: null,
    remoteEarth: {},
    target: null,
    targetMarker: null,
  };

  // Mercator web no llega a los polos: los sitios del polo sur lunar se dibujan en este borde.
  const MERCATOR_MAX_LAT = 85.05;

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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

  function flyOpts(duration) {
    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    return reduce ? { animate: false } : { duration: duration };
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const $ = (sel) => document.querySelector(sel);

  function clamp01(x) {
    return Math.max(0, Math.min(1, x));
  }
  function scoreTemp(t) {
    return clamp01(1 - Math.abs(t - SCORING.tMars) / SCORING.tScale);
  }
  function scoreDiurnal(dt) {
    return clamp01(1 - Math.abs(dt - SCORING.diurnalRef) / SCORING.diurnalRef);
  }
  function scoreAridity(p) {
    return clamp01(1 - p / SCORING.precipScale);
  }
  function scoreElev(z) {
    return clamp01(z / SCORING.elevScale);
  }
  function pct(x) {
    return (x * 100).toFixed(0) + "\u00a0%";
  }
  function fmt(n, digits, unit) {
    if (n === null || n === undefined || Number.isNaN(n)) return "—";
    const s = Number(n).toLocaleString("es-AR", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
    return unit ? s + " " + unit : s;
  }

  function compute(site) {
    const t = scoreTemp(site.climate.t2m_mean_C);
    const d = scoreDiurnal(site.climate.mean_diurnal_range_C);
    const a = scoreAridity(site.climate.mean_annual_precipitation_mm);
    const h = scoreElev(site.elevation_m.value);
    const w = SCORING.weights;
    return {
      temperatura: t,
      amplitud_termica: d,
      aridez: a,
      altitud_uv_proxy: h,
      index: w.temperatura * t + w.amplitud_termica * d + w.aridez * a + w.altitud_uv_proxy * h,
    };
  }

  function tag(status) {
    if (status === "measured") {
      return '<span class="tag ok">dato medido</span>';
    }
    return '<span class="tag warn">valor de ejemplo / a completar</span>';
  }

  function divIcon(kind, active) {
    const cls = "pin " + kind + (active ? " active" : "");
    return L.divIcon({
      className: "",
      html: '<div class="' + cls + '"></div>',
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });
  }

  function initMaps() {
    const earth = L.map("map-earth", { zoomControl: true, minZoom: 2, maxZoom: 12, worldCopyJump: true }).setView([20, 0], 2);
    const mars = L.map("map-mars", { zoomControl: true, minZoom: 2, maxZoom: 8, worldCopyJump: true }).setView([5, -20], 3);

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

    const gibsDate = $("#gibs-date").value || "2026-11-10";
    const gibsTrueColor = L.tileLayer(
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
      {
        date: gibsDate,
        attribution: "NASA GIBS / EOSDIS — MODIS Terra True Color",
        maxZoom: 12,
        maxNativeZoom: 9,
        opacity: 0.95,
      }
    );
    const gibsLst = L.tileLayer(
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Land_Surface_Temp_Day/default/{date}/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png",
      {
        date: gibsDate,
        attribution: "NASA GIBS / EOSDIS — MODIS Terra LST (día)",
        maxZoom: 12,
        maxNativeZoom: 7,
        opacity: 0.7,
      }
    );

    const opm = L.tileLayer(
      "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png",
      {
        attribution: 'OpenPlanetaryMap — <a href="http://openplanetarymap.org/basemaps/mars/opm-mars-basemap-v0-2/">OPM Mars Basemap v0.2</a>',
        maxZoom: 8,
        maxNativeZoom: 9,
      }
    );
    const mola = L.tileLayer("https://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/mola-color/{z}/{x}/{y}.png", {
      attribution: "WhereOnMars / Carto — MOLA color (shaded relief)",
      maxZoom: 8,
      maxNativeZoom: 6,
      tms: true,
    });
    const marsShaded = L.tileLayer(
      "https://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/celestia_mars-shaded-16k_global/{z}/{x}/{y}.png",
      {
        attribution: "WhereOnMars / Carto — Celestia Mars shaded",
        maxZoom: 8,
        maxNativeZoom: 5,
        tms: true,
      }
    );
    const opmMoon = L.tileLayer(
      "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png",
      {
        attribution: 'OpenPlanetaryMap — OPM Moon Basemap v0.1',
        maxZoom: 8,
        maxNativeZoom: 9,
      }
    );
    opm.addTo(mars);

    state.earthMap = earth;
    state.marsMap = mars;
    state.layers = { osm, esri, gibsTrueColor, gibsLst, opm, mola, marsShaded, opmMoon };
    state.setRightBase = setMarsBase;
    const resizeMaps = () => { earth.invalidateSize(); mars.invalidateSize(); };
    window.addEventListener("resize", resizeMaps);
    setTimeout(resizeMaps, 200);

    $("#layer-osm").addEventListener("change", () => toggleBaseEarth());
    $("#layer-esri").addEventListener("change", () => toggleBaseEarth());
    $("#layer-gibs-tc").addEventListener("change", () => toggleOverlay(gibsTrueColor, $("#layer-gibs-tc").checked, earth));
    $("#layer-gibs-lst").addEventListener("change", () => toggleOverlay(gibsLst, $("#layer-gibs-lst").checked, earth));
    $("#gibs-date").addEventListener("change", () => {
      const d = $("#gibs-date").value;
      gibsTrueColor.options.date = d;
      gibsLst.options.date = d;
      if (earth.hasLayer(gibsTrueColor)) {
        earth.removeLayer(gibsTrueColor);
        gibsTrueColor.addTo(earth);
      }
      if (earth.hasLayer(gibsLst)) {
        earth.removeLayer(gibsLst);
        gibsLst.addTo(earth);
      }
    });
    $("#layer-opm").addEventListener("change", () => setMarsBase("opm"));
    $("#layer-mola").addEventListener("change", () => setMarsBase("mola"));
    $("#layer-shaded").addEventListener("change", () => setMarsBase("shaded"));

    function toggleBaseEarth() {
      const useEsri = $("#layer-esri").checked;
      if (useEsri) {
        if (!earth.hasLayer(esri)) esri.addTo(earth);
        if (earth.hasLayer(osm)) earth.removeLayer(osm);
        $("#layer-osm").checked = false;
      } else {
        if (!earth.hasLayer(osm)) osm.addTo(earth);
        if (earth.hasLayer(esri)) earth.removeLayer(esri);
        $("#layer-osm").checked = true;
      }
    }
    function setMarsBase(which) {
      [opm, mola, marsShaded].forEach((ly) => {
        if (mars.hasLayer(ly)) mars.removeLayer(ly);
      });
      $("#layer-opm").checked = which === "opm";
      $("#layer-mola").checked = which === "mola";
      $("#layer-shaded").checked = which === "shaded";
      (which === "mola" ? mola : which === "shaded" ? marsShaded : opm).addTo(mars);
    }
  }

  function toggleOverlay(layer, on, map) {
    if (on && !map.hasLayer(layer)) layer.addTo(map);
    if (!on && map.hasLayer(layer)) map.removeLayer(layer);
  }

  function addMarkers(data) {
    data.earth_sites.forEach((site) => {
      const kind = site.highlight_less_studied ? "menos" : "earth";
      const m = L.marker([site.lat, site.lon], { icon: divIcon(kind, false), title: site.name }).addTo(state.earthMap);
      m.on("click", () => selectSite(site.id));
      m.bindTooltip(site.short_name);
      state.earthMarkers[site.id] = m;
    });
    data.mars_sites.forEach((site) => {
      const m = L.marker([site.lat, site.lon], { icon: divIcon("mars", false), title: site.name }).addTo(state.marsMap);
      m.on("click", () => {
        const t = ((state.catalog && state.catalog.sites) || []).find((x) => x.id === site.id);
        if (t) {
          $("#finder-target").value = t.id;
          state.lastTasi = null;
          focusTarget(t);
        } else {
          safeFly(state.marsMap, [site.lat, site.lon], 5, flyOpts(0.8));
        }
      });
      m.bindTooltip(site.short_name);
      state.marsMarkers[site.id] = m;
    });
  }

  function renderList(data) {
    const box = $("#site-buttons");
    box.innerHTML = "";
    data.earth_sites.forEach((site) => {
      const scores = compute(site);
      const btn = document.createElement("button");
      btn.className = "site-btn" + (state.selectedId === site.id ? " active" : "");
      btn.type = "button";
      btn.innerHTML =
        '<span class="name">' +
        site.name +
        "</span>" +
        '<span class="meta">' +
        site.province +
        ", índice ambiental " +
        pct(scores.index) +
        "</span>" +
        (site.highlight_less_studied ? '<span class="badge menos">Menos estudiado</span>' : '<span class="badge">Candidato</span>');
      btn.addEventListener("click", () => selectSite(site.id));
      box.appendChild(btn);
    });
  }

  function selectSite(id) {
    state.selectedId = id;
    const site = state.data.earth_sites.find((s) => s.id === id);
    if (!site) return;
    renderList(state.data);

    refreshEarthIcons();
    // El par sale del destino elegido en el buscador (y del ranking TASI), no de paired_mars_ids.
    safeFly(state.earthMap, [site.lat, site.lon], 8, flyOpts(0.9));
    keepTargetInView();
    renderPanel(site);
  }

  function renderPanel(site) {
    const scores = compute(site);
    const match = currentMatch(site.id);

    const q = site.qualitative_scores;
    $("#panel").innerHTML =
      '<div class="panel-head"><h2>Sitio</h2></div>' +
      '<div class="panel-body">' +
      "<p class='kicker'>" +
      site.province +
      "</p>" +
      (site.highlight_less_studied ? "<p><span class='badge menos'>Menos estudiado</span></p>" : "") +
      "<h3 style='margin-top:0.2rem'>" +
      site.name +
      "</h3>" +
      "<p class='lead'>" +
      site.summary +
      "</p>" +
      '<dl class="facts">' +
      fact("Coordenadas", site.lat.toFixed(5) + "°, " + site.lon.toFixed(5) + "°", "measured") +
      fact("Elevación (SRTM 30 m)", fmt(site.elevation_m.value, 0, "m s.n.m."), site.elevation_m.status) +
      fact("Temp. media 1991–2020", fmt(site.climate.t2m_mean_C, 2, "°C"), "measured") +
      fact("Amplitud diaria media", fmt(site.climate.mean_diurnal_range_C, 2, "°C"), "measured") +
      fact("Mín. / máx. absolutos", fmt(site.climate.t2m_abs_min_C, 1, "°C") + " / " + fmt(site.climate.t2m_abs_max_C, 1, "°C"), "measured") +
      fact("Precipitación media anual", fmt(site.climate.mean_annual_precipitation_mm, 1, "mm"), "measured") +
      "</dl>" +
      (site.climate.precip_caution ? '<p class="caution">' + site.climate.precip_caution + "</p>" : "") +
      "<h3>Por qué se parece</h3><p>" +
      site.why_analogous +
      "</p>" +
      "<h3>Dónde se corta la analogía</h3><p>" +
      site.analogy_breaks +
      "</p>" +
      "<p class='muted'>Marte tiene 3,73 m/s² de gravedad media frente a 9,82 m/s² en la Tierra, y ~6,36 mbar de presión frente a ~1013 mbar a nivel del mar terrestre (NASA NSSDC Mars Fact Sheet). Esas diferencias no se pueden emular acá.</p>" +
      pairBlock(match) +
      '<div class="score-hero"><div class="num">' +
      pct(scores.index) +
      "</div><p>Índice ambiental cuantitativo (temperatura, amplitud, aridez y proxy de altitud/UV). No incluye geología ni relieve. Es una fórmula transparente del prototipo, no una métrica validada.</p></div>" +
      '<div class="charts"><div class="chart-box"><canvas id="chart-bars"></canvas></div><div class="chart-box"><canvas id="chart-radar"></canvas></div></div>' +
      "<h3>Cómo se calcula el puntaje</h3>" +
      "<p>Las cuatro barras verdes se calculan con datos de esta corrida. Las cuatro ámbar son juicios cualitativos del equipo y están marcadas como <em>valor de ejemplo / a completar</em>.</p>" +
      '<div class="formula">' +
      "temperatura = max(0, 1 − |T_media − (−59 °C)| / 80)<br>" +
      "amplitud = max(0, 1 − |amplitud_diaria − 58 °C| / 58)<br>" +
      "aridez = max(0, 1 − P_anual_mm / 500)<br>" +
      "altitud/UV (proxy) = min(1, elevación_m / 4000)<br>" +
      "índice = 0,20·temp + 0,20·amplitud + 0,35·aridez + 0,25·altitud<br>" +
      "Valores de referencia de Marte: promedio global −59 °C y rango diurno de Viking 1 = 58 °C (NASA NSSDC). La precipitación líquida de Marte se toma como 0 mm/año." +
      "</div>" +
      "<p>En este sitio: temp " +
      pct(scores.temperatura) +
      ", amplitud " +
      pct(scores.amplitud_termica) +
      ", aridez " +
      pct(scores.aridez) +
      ", altitud/UV " +
      pct(scores.altitud_uv_proxy) +
      ".</p>" +
      "<h3>Descripción</h3><p>" +
      site.description +
      "</p>" +
      "<h3>Fuentes</h3><div class='sources'><ul>" +
      sourceItems(site) +
      "</ul><p class='muted'>" +
      site.coord_source +
      "</p><p class='muted'>" +
      site.elevation_m.source +
      "</p><p class='muted'>" +
      site.climate.source_temperature +
      " " +
      site.climate.source_precipitation +
      "</p></div>" +
      "</div>";

    drawCharts(scores, q);
  }

  // Fracción 0–1 del puntaje para la escala de color violeta → óxido del manual.
  function scoreFraction(score) {
    const n = Number(score);
    if (score == null || Number.isNaN(n)) return 0;
    return Math.max(0, Math.min(1, n / 100)).toFixed(3);
  }

  function currentMatch(id) {
    return ((state.lastTasi && state.lastTasi.matches) || []).find((m) => m.site && m.site.id === id) || null;
  }

  // Ficha del par: destino elegido frente a este sitio, con lo que se parece, lo que no y lo que falta.
  function pairBlock(match) {
    const t = state.target;
    if (!t) {
      return "<h3>Destino</h3><p class='muted'>Elegí un destino en el buscador de arriba para ver el par en el mapa de la derecha.</p>";
    }
    const body = t.body === "moon" ? "Luna" : "Marte";
    let html = "<h3>Comparado con " + escapeHtml(t.short_name || t.name) + " (" + body + ")</h3>";
    if (!match) {
      return html + "<p class='muted'>Este sitio no está en el último ranking TASI frente a ese destino. Corré «Buscar análogos en la Tierra» para puntuarlo.</p>";
    }
    const ex = window.HexastraExplain.explainMatch(match);
    html +=
      "<div class='score-hero' style='--s:" + scoreFraction(match.score) + "'><div class='num score-color'>" + escapeHtml(window.HexastraExplain.formatScore(match.score)) +
      "</div><p>de 100, índice TASI frente a " + escapeHtml(t.short_name || t.name) + ".</p>" +
      "<span class='score-bar' aria-hidden='true'><span></span></span></div>" +
      "<p><strong>Por qué se parece.</strong> " + escapeHtml(ex.why || "Sin componentes con dato.") + "</p>" +
      "<p><strong>En qué no.</strong> " + escapeHtml(ex.breaks) + "</p>" +
      (ex.missing.length
        ? "<p class='pair-missing'>" + ex.missing.map((k) => "<span class='tag warn'>Dato a completar: " + escapeHtml(k) + "</span>").join(" ") + "</p>"
        : "");
    return html;
  }

  function fact(label, value, status) {
    return "<div class='fact'><dt>" + label + " " + tag(status) + "</dt><dd>" + value + "</dd></div>";
  }
  function sourceItems(site) {
    return site.sources
      .map((s) => '<li><a href="' + s.url + '" target="_blank" rel="noopener">' + s.label + "</a></li>")
      .join("");
  }

  function drawCharts(scores, qualitative) {
    const labels = [
      "Temperatura",
      "Amplitud térmica",
      "Aridez",
      "Altitud / UV (proxy)",
      "Geología *",
      "Relieve *",
      "Sales *",
      "Vulcanismo *",
    ];
    const values = [
      scores.temperatura,
      scores.amplitud_termica,
      scores.aridez,
      scores.altitud_uv_proxy,
      qualitative.geologia.value,
      qualitative.relieve.value,
      qualitative.sales.value,
      qualitative.vulcanismo.value,
    ].map((v) => Math.round(v * 1000) / 10);
    // Colores del sistema (css/tokens.css y css/style.css): dato medido vs. valor de ejemplo.
    const ink = css("--color-ink");
    const muted = css("--color-muted");
    const rule = css("--color-rule");
    const measured = css("--color-earth");
    const example = css("--color-warn-ink");
    const font = { family: css("--font-body") || "serif" };
    const colors = [measured, measured, measured, measured, example, example, example, example];

    if (state.charts.bars) state.charts.bars.destroy();
    if (state.charts.radar) state.charts.radar.destroy();

    state.charts.bars = new Chart($("#chart-bars"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Puntaje (0–100)",
            data: values,
            backgroundColor: colors,
            borderWidth: 0,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: { display: true, text: "Dimensiones (verde: dato; ámbar: ejemplo)", color: ink, font: Object.assign({ size: 12 }, font) },
          tooltip: {
            callbacks: {
              afterLabel: (ctx) => (ctx.dataIndex < 4 ? "Calculado con datos de esta corrida" : "Valor de ejemplo / a completar"),
            },
          },
        },
        scales: {
          x: { min: 0, max: 100, ticks: { color: muted, font: font }, grid: { color: rule } },
          y: { ticks: { color: ink, font: Object.assign({ size: 11 }, font) }, grid: { display: false } },
        },
      },
    });

    state.charts.radar = new Chart($("#chart-radar"), {
      type: "radar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Sitio (mezcla dato + ejemplo)",
            data: values,
            borderColor: css("--color-accent"),
            backgroundColor: "transparent",
            borderWidth: 2,
            pointBackgroundColor: colors,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: ink, font: font } },
          title: { display: true, text: "Radar: las ramas ámbar son preliminares", color: ink, font: Object.assign({ size: 12 }, font) },
        },
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { color: muted, backdropColor: "transparent", stepSize: 25 },
            grid: { color: rule },
            angleLines: { color: rule },
            pointLabels: { color: ink, font: Object.assign({ size: 10 }, font) },
          },
        },
      },
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

  function targetLatLng(t) {
    return [Math.max(-MERCATOR_MAX_LAT, Math.min(MERCATOR_MAX_LAT, Number(t.lat))), Number(t.lon)];
  }

  // Marca y centra el destino elegido en el mapa derecho (Marte o Luna).
  function focusTarget(t) {
    if (!t || t.lat == null || t.lon == null || !state.marsMap) return;
    state.target = t;
    if (state.targetMarker) state.marsMap.removeLayer(state.targetMarker);
    state.targetMarker = L.marker(targetLatLng(t), {
      icon: targetIcon(t.body),
      title: t.name,
      alt: "Destino elegido: " + t.name,
      zIndexOffset: 1000,
      keyboard: true,
    });
    state.targetMarker.bindTooltip(t.short_name || t.name, { permanent: true, direction: "top", offset: [0, -12] });
    setRightBody(t.body, t);
    if (state.selectedId) {
      const local = state.data && (state.data.earth_sites || []).find((s) => s.id === state.selectedId);
      if (local) renderPanel(local);
      else if (state.remoteEarth[state.selectedId]) renderRemotePanel(state.remoteEarth[state.selectedId], currentMatch(state.selectedId));
    }
  }

  function keepTargetInView() {
    const t = state.target;
    if (!t || !state.marsMap) return;
    const ll = targetLatLng(t);
    if (!state.marsMap.getBounds().contains(ll)) if (hasSize(state.marsMap)) state.marsMap.panTo(ll, flyOpts(0.6));
  }

  function rankIcon(n, active) {
    return L.divIcon({
      className: "",
      html: '<div class="pin rank' + (active ? " active" : "") + '">' + n + "</div>",
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });
  }

  function setRightBody(body, targetSite) {
    const map = state.marsMap;
    const Lrs = state.layers;
    const marsLayers = [Lrs.opm, Lrs.mola, Lrs.marsShaded];
    const label = $("#map-right-label");
    state.rightBody = body;
    if (body === "moon") {
      marsLayers.forEach((ly) => { if (map.hasLayer(ly)) map.removeLayer(ly); });
      if (Lrs.opmMoon && !map.hasLayer(Lrs.opmMoon)) Lrs.opmMoon.addTo(map);
      if (label) label.textContent = "Luna (la proyección Mercator comprime el polo sur)";
      Object.values(state.marsMarkers).forEach((m) => { if (map.hasLayer(m)) map.removeLayer(m); });
      Object.values(state.moonMarkers).forEach((m) => m.addTo(map));
    } else {
      if (Lrs.opmMoon && map.hasLayer(Lrs.opmMoon)) map.removeLayer(Lrs.opmMoon);
      Object.values(state.moonMarkers).forEach((m) => { if (map.hasLayer(m)) map.removeLayer(m); });
      Object.values(state.marsMarkers).forEach((m) => m.addTo(map));
      if (!map.hasLayer(Lrs.opm) && !map.hasLayer(Lrs.mola) && !map.hasLayer(Lrs.marsShaded)) {
        Lrs.opm.addTo(map);
      }
      if (label) label.textContent = "Marte";
    }
    if (state.targetMarker) {
      if (state.target && state.target.body === body) state.targetMarker.addTo(map);
      else if (map.hasLayer(state.targetMarker)) map.removeLayer(state.targetMarker);
    }
    if (targetSite) {
      safeFly(map, targetLatLng(targetSite), body === "moon" ? 4 : 5, flyOpts(0.8));
    }
    setTimeout(() => map.invalidateSize(), 150);
  }

  function tasiWeightsFromUI() {
    const weights = { G: 0.2, T: 0.2, E: 0.2, V: 0.2, O: 0.2 };
    document.querySelectorAll("#finder-features input[data-w]").forEach((rng) => {
      const on = document.querySelector('#finder-features input[data-feat="' + rng.dataset.w + '"]');
      weights[rng.dataset.w] = on && !on.checked ? 0 : (Number(rng.value) || 0) / 10;
    });
    return weights;
  }

  function fillCountrySelect(continentName) {
    const sel = $("#finder-country");
    if (!sel || !state.regions) return;
    const current = sel.value;
    sel.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "Todos los países";
    sel.appendChild(all);
    const continents = state.regions.continents || [];
    const list = continentName
      ? continents.filter((c) => c.name === continentName)
      : continents;
    list.forEach((cont) => {
      (cont.countries || []).forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.iso;
        opt.textContent = c.name + " (" + c.iso + ")";
        sel.appendChild(opt);
      });
    });
    if (current && Array.from(sel.options).some((o) => o.value === current)) {
      sel.value = current;
    } else {
      sel.value = "";
    }
    sel.disabled = false;
  }

  function populateFinder(targets, regions) {
    const sel = $("#finder-target");
    sel.innerHTML = "";
    const groups = { moon: "Luna", mars: "Marte" };
    Object.keys(groups).forEach((body) => {
      const optg = document.createElement("optgroup");
      optg.label = groups[body];
      targets.filter((s) => s.body === body).forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        optg.appendChild(opt);
      });
      sel.appendChild(optg);
    });
    if (targets.some((s) => s.id === "shackleton-rim")) sel.value = "shackleton-rim";
    sel.disabled = false;

    const box = $("#finder-features");
    box.innerHTML = "";
    const comps = [
      { id: "G", name: "G · geología / espectro", def: 2, hint: "solo si hay espectros reales" },
      { id: "T", name: "T · topografía (Mahalanobis)", def: 2, hint: "relieve relativo, pendiente, rugosidad" },
      { id: "E", name: "E · régimen térmico", def: 2, hint: "temperatura y amplitud" },
      { id: "V", name: "V · volátiles / aridez", def: 2, hint: "precipitación u hielo" },
      { id: "O", name: "O · operacional", def: 2, hint: "solo con métrica comparable" },
    ];
    comps.forEach((c) => {
      const row = document.createElement("div");
      row.className = "feat-row";
      row.innerHTML =
        '<label><input type="checkbox" data-feat="' + c.id + '" checked> ' +
        c.name + " <span class='muted'>(" + c.hint + ")</span></label>" +
        '<input type="range" min="0" max="40" step="1" value="' + Math.round(c.def * 10) + '" data-w="' + c.id + '">' +
        '<span data-wv="' + c.id + '">' + c.def.toFixed(1) + "</span>";
      box.appendChild(row);
    });
    box.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const w = box.querySelector('input[data-w="' + cb.dataset.feat + '"]');
        if (w) w.disabled = !cb.checked;
      });
    });
    box.querySelectorAll("input[type=range]").forEach((rng) => {
      rng.addEventListener("input", () => {
        const sp = box.querySelector('[data-wv="' + rng.dataset.w + '"]');
        if (sp) sp.textContent = (Number(rng.value) / 10).toFixed(1);
      });
    });

    const csel = $("#finder-continent");
    if (csel) {
      csel.innerHTML = "";
      const optAll = document.createElement("option");
      optAll.value = "";
      optAll.textContent = "Todos los continentes";
      csel.appendChild(optAll);
      (regions && regions.continents ? regions.continents : []).forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.name;
        opt.textContent = c.name;
        csel.appendChild(opt);
      });
      csel.disabled = false;
      csel.addEventListener("change", () => fillCountrySelect(csel.value));
    }
    fillCountrySelect("");
    const gamma = $("#finder-gamma");
    const gval = $("#finder-gamma-val");
    if (gamma && gval) {
      const sync = () => { gval.textContent = Number(gamma.value).toFixed(1); };
      gamma.addEventListener("input", sync);
      sync();
    }
    $("#btn-buscar").disabled = false;
  }

  function ensureEarthMarker(site) {
    if (!site || !site.id || !state.earthMap) return;
    if (state.earthMarkers[site.id]) return;
    const remote = {
      id: site.id,
      name: site.name,
      short_name: site.short_name || site.name,
      lat: site.lat,
      lon: site.lon,
      highlight_less_studied: site.known_level === "lesser-known" || site.highlight_less_studied,
      continent: site.continent,
      country_iso: site.country_iso,
      country_name: site.country_name,
      analog_types: site.analog_types,
      summary: site.summary,
    };
    state.remoteEarth[site.id] = remote;
    const kind = remote.highlight_less_studied ? "menos" : "earth";
    const m = L.marker([site.lat, site.lon], { icon: divIcon(kind, false), title: site.name });
    m.on("click", () => selectSiteOrRemote(site.id));
    m.bindTooltip(remote.short_name);
    m.addTo(state.earthMap);
    state.earthMarkers[site.id] = m;
  }

  function renderRemotePanel(site, match) {
    const comps = (match && match.components) || {};
    const rows = ["G", "T", "E", "V", "O"].map((k) => {
      const c = comps[k] || {};
      const val = c.score == null ? "nulo" : c.score.toLocaleString("es-AR") + " / 100";
      const why = c.available ? "" : ": " + (c.reason || "sin dato");
      return "<li><strong>" + k + "</strong>: " + val + (why ? "<span class='muted'>" + why + "</span>" : "") + "</li>";
    }).join("");
    const mask = (match && match.mask) || {};
    $("#panel").innerHTML =
      '<div class="panel-head"><h2>Sitio</h2></div>' +
      '<div class="panel-body">' +
      "<p class='kicker'>" +
      escapeHtml([site.country_name ? site.country_name + (site.country_iso ? " (" + site.country_iso + ")" : "") : "", site.continent || ""].filter(Boolean).join(", ")) +
      "</p>" +
      (site.highlight_less_studied ? "<p><span class='badge menos'>Menos estudiado</span></p>" : "") +
      "<h3 style='margin-top:0.2rem'>" + site.name + "</h3>" +
      (site.summary ? "<p class='lead'>" + site.summary + "</p>" : "") +
      "<p class='muted'>Candidato del catálogo mundial (earth-service). Las fichas narrativas largas de esta columna siguen disponibles para los sitios estáticos de la Argentina.</p>" +
      '<dl class="facts">' +
      fact("Coordenadas", Number(site.lat).toFixed(5) + "°, " + Number(site.lon).toFixed(5) + "°", "measured") +
      fact("País", (site.country_name || "—") + (site.country_iso ? " (" + site.country_iso + ")" : ""), "measured") +
      fact("Tipos", (site.analog_types || []).join(", ") || "—", "measured") +
      (match && match.score != null ? fact("TASI", match.score.toLocaleString("es-AR") + " / 100", "measured") : "") +
      "</dl>" +
      (mask.unknown_flags && mask.unknown_flags.length ? "<p class='caution'>Máscara incompleta: " + mask.unknown_flags.join(", ") + ". El sitio no se descartó.</p>" : "") +
      pairBlock(match) +
      "<h3>Componentes TASI</h3><ul>" + rows + "</ul>" +
      "</div>";
  }

  function selectSiteOrRemote(id) {
    const local = state.data && (state.data.earth_sites || []).find((s) => s.id === id);
    if (local) {
      selectSite(id);
      return;
    }
    const site = state.remoteEarth[id];
    if (!site) return;
    state.selectedId = id;
    refreshEarthIcons();
    safeFly(state.earthMap, [site.lat, site.lon], 8, flyOpts(0.9));
    const match = ((state.lastTasi && state.lastTasi.matches) || []).find((m) => m.site.id === id);
    renderRemotePanel(site, match);
  }

  // Un solo lugar decide el ícono de cada sitio terrestre: los puntuados conservan su número
  // de ranking y solo el seleccionado se resalta (anillo cian), sin perder el número.
  function earthIconFor(sid) {
    const active = sid === state.selectedId;
    const rank = state.rankIds.indexOf(sid);
    if (rank !== -1) return rankIcon(rank + 1, active);
    const s = ((state.data && state.data.earth_sites) || []).find((x) => x.id === sid) || state.remoteEarth[sid];
    return divIcon(s && s.highlight_less_studied ? "menos" : "earth", active);
  }

  function refreshEarthIcons() {
    Object.entries(state.earthMarkers).forEach(([sid, marker]) => {
      marker.setIcon(earthIconFor(sid));
      marker.setZIndexOffset(sid === state.selectedId ? 1000 : 0);
    });
  }

  function resetEarthIcons() {
    state.rankIds = [];
    refreshEarthIcons();
  }

  function highlightRanks(matches) {
    resetEarthIcons();
    const scored = matches.filter((m) => m.score != null);
    state.rankIds = scored.map((m) => m.site.id);
    scored.forEach((m) => ensureEarthMarker(m.site));
    refreshEarthIcons();
    if (scored.length && state.earthMap) {
      const pts = scored.map((m) => [m.site.lat, m.site.lon]);
      try {
        state.earthMap.fitBounds(pts, { padding: [28, 28], maxZoom: 6 });
      } catch (e) { /* ignore */ }
    }
  }

  async function detectApi() {
    const status = $("#api-status");
    const api = window.HexastraAPI;
    if (!api) {
      state.apiOk = false;
      if (status) {
        status.textContent = "Falta js/api.js. El mapa estático sigue andando.";
        status.className = "api-status down";
      }
      return false;
    }
    try {
      const h = await api.health();
      state.apiOk = !!h.ok;
      state.apiBase = h.urls || api.getServiceUrls();
      if (h.ok) {
        if (status) {
          status.textContent = "Servicios conectados · planetary " + h.urls.planetary + " · earth " + h.urls.earth;
          status.className = "api-status ok";
        }
        return true;
      }
      const missing = [];
      if (!h.planetary) missing.push("planetary-service :8766");
      if (!h.earth) missing.push("earth-service :8767");
      if (status) {
        status.textContent = "Servicios no disponibles (" + missing.join(", ") + "). El mapa sigue andando. Levantá ./run_all.sh";
        status.className = "api-status down";
      }
      return false;
    } catch (e) {
      state.apiOk = false;
      if (status) {
        status.textContent = "No pude hablar con los servicios. El mapa sigue andando. Levantá ./run_all.sh";
        status.className = "api-status down";
      }
      return false;
    }
  }

  async function runSearch() {
    const out = $("#finder-results");
    const api = window.HexastraAPI;
    if (!state.apiOk || !api) {
      out.innerHTML = "<p class='caution'>No pude hablar con los servicios. Levantalos con <code>./run_all.sh</code> (planetary :8766, earth :8767, front :8765) y recargá. El mapa estático no se interrumpe.</p>";
      return;
    }
    const targetId = $("#finder-target").value;
    const weights = tasiWeightsFromUI();
    if (Object.values(weights).every((w) => !w)) {
      out.innerHTML = "<p class='caution'>Dejá al menos un componente TASI con peso mayor que cero.</p>";
      return;
    }
    const continent = ($("#finder-continent") && $("#finder-continent").value) || undefined;
    const country = ($("#finder-country") && $("#finder-country").value) || undefined;
    const gamma = $("#finder-gamma") ? Number($("#finder-gamma").value) : 1;
    const applyMask = $("#finder-mask") ? $("#finder-mask").checked : true;
    out.innerHTML = "<p class='muted'>Buscando…</p>";
    try {
      const targetVector = await api.getTargetVector(targetId);
      const chosen = ((state.catalog && state.catalog.sites) || []).find((x) => x.id === targetId) || targetVector;
      if (chosen) focusTarget(chosen);
      const data = await api.rankAnalogs({
        targetVector: targetVector,
        weights: weights,
        gamma: gamma,
        top: 8,
        continent: continent,
        country: country,
        applyMask: applyMask,
      });
      state.lastTasi = data;
      highlightRanks(data.matches || []);
      if (state.selectedId) focusTarget(state.target);
      const items = (data.matches || []).map((m, i) => {
        const used = (m.coverage && m.coverage.available_components) || [];
        const skipped = (m.weights && m.weights.skipped) || [];
        const flags = (m.mask && m.mask.unknown_flags) || [];
        const parts = ["G", "T", "E", "V", "O"].map((k) => {
          const c = (m.components || {})[k] || {};
          return k + " " + (c.score == null ? "—" : c.score);
        }).join(" · ");
        return (
          '<li><button type="button" class="rank-item" data-id="' + m.site.id + '">' +
          "<strong>" + (i + 1) + ". " + escapeHtml(m.site.name) + "</strong> <span class='score'>" +
          (m.score == null ? "sin puntaje" : m.score.toLocaleString("es-AR") + " de 100") +
          "</span><span class='score-bar' style='--s:" + scoreFraction(m.score) + "' aria-hidden='true'><span></span></span><span class='muted'>" +
          (m.site.country_iso || "") + (m.site.continent ? " · " + m.site.continent : "") +
          " · usó: " + (used.join(", ") || "—") +
          (skipped.length ? " · omitió: " + skipped.join(", ") : "") +
          "<br>" + parts +
          "</span>" +
          (flags.length ? "<p class='rank-flags'>Máscara incompleta: " + flags.join(", ") + ".</p>" : "") +
          "</button></li>"
        );
      }).join("");
      const discardedN = data.n_discarded_by_mask || 0;
      out.innerHTML =
        "<p class='muted'>Objetivo: <strong>" + ((data.target && data.target.name) || targetId) +
        "</strong> · TASI · gamma=" + data.gamma +
        " · candidatos " + data.n_scored +
        (discardedN ? " · descartados por M(x): " + discardedN : "") +
        "</p><ol class='rank-list'>" + items + "</ol>" +
        "<p class='muted'>G (espectro) y O (operacional) quedan nulos si no hay dato real comparable. S_T usa distancia de Mahalanobis sobre relieve relativo, pendiente y rugosidad, no la cota absoluta. Si solo entra la precipitación (0 mm por convención en Luna/Marte), el ranking refleja sobre todo quién es más árido.</p>";
      out.querySelectorAll(".rank-item").forEach((btn) => {
        btn.addEventListener("click", () => selectSiteOrRemote(btn.dataset.id));
      });
    } catch (e) {
      out.innerHTML = "<p class='caution'>Falló la consulta a los servicios (" + e.message + "). El mapa sigue disponible.</p>";
    }
  }

  async function initFinder() {
    const ok = await detectApi();
    if (!ok) {
      if ($("#finder-target")) $("#finder-target").disabled = true;
      if ($("#btn-buscar")) $("#btn-buscar").disabled = true;
      return;
    }
    const api = window.HexastraAPI;
    try {
      const [moon, mars, regions, candidates] = await Promise.all([
        api.getTargets("moon"),
        api.getTargets("mars"),
        api.getRegions(),
        api.getCandidates(),
      ]);
      const targets = [].concat(moon || [], mars || []);
      state.catalog = { sites: targets };
      state.regions = regions;
      populateFinder(targets, regions);
      (moon || []).forEach((s) => {
        const lat = Math.max(-85.05, Math.min(85.05, s.lat));
        const m = L.marker([lat, s.lon], { icon: divIcon("moon", false), title: s.name });
        m.bindTooltip(s.short_name || s.name);
        state.moonMarkers[s.id] = m;
      });
      (candidates.sites || []).forEach((s) => ensureEarthMarker(s));
      $("#btn-buscar").addEventListener("click", runSearch);
      $("#finder-target").addEventListener("change", () => {
        const s = (state.catalog.sites || []).find((x) => x.id === $("#finder-target").value);
        state.lastTasi = null;
        if (s) focusTarget(s);
      });
      const first = targets.find((x) => x.id === $("#finder-target").value);
      if (first) focusTarget(first);
    } catch (e) {
      const status = $("#api-status");
      if (status) {
        status.textContent = "Los servicios contestaron /health pero falló una consulta de catálogo (" + e.message + ").";
        status.className = "api-status down";
      }
    }
  }

  // Las notas a y b de la tabla de límites abren el bloque plegado de fuentes.
  function bindLimitNotes() {
    const box = document.querySelector(".limits-sources");
    document.querySelectorAll(".limits-table sup a").forEach((link) => {
      link.addEventListener("click", () => { if (box) box.open = true; });
    });
  }

  function bindModal() {
    bindLimitNotes();
    const bg = $("#modal-bg");
    $("#btn-metodo").addEventListener("click", () => bg.classList.add("open"));
    $("#btn-fuentes").addEventListener("click", () => {
      bg.classList.add("open");
      $("#fuentes-anchor").scrollIntoView();
    });
    bg.addEventListener("click", (e) => {
      if (e.target === bg || e.target.classList.contains("close")) bg.classList.remove("open");
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") bg.classList.remove("open");
    });
  }

  async function main() {
    initMaps();
    bindModal();
    const res = await fetch("data/sites.json");
    if (!res.ok) {
      $("#panel").innerHTML = "<p class='placeholder-msg'>No pude cargar data/sites.json. ¿Estás sirviendo la carpeta con un servidor local?</p>";
      return;
    }
    const data = await res.json();
    state.data = data;
    addMarkers(data);
    renderList(data);
    if (state.earthMap) state.earthMap.setView([20, 0], 2);
    initFinder();
  }

  main().catch((err) => {
    console.error(err);
    $("#panel").innerHTML = "<p class='placeholder-msg'>Error al iniciar el prototipo. Mirá la consola del navegador.</p>";
  });

  window.HexastraApp = {
    invalidateMaps: function () {
      if (state.earthMap) state.earthMap.invalidateSize();
      if (state.marsMap) state.marsMap.invalidateSize();
      // Al mostrar el modo avanzado, el destino elegido vuelve al centro del mapa derecho.
      if (state.target && state.marsMap && hasSize(state.marsMap)) {
        state.marsMap.setView(targetLatLng(state.target), state.target.body === "moon" ? 4 : 5, { animate: false });
      }
    },
    showMethodModal: function () {
      const bg = $("#modal-bg");
      if (bg) bg.classList.add("open");
    },
    selectSite: function (id) {
      selectSite(id);
    }
  };
})();
