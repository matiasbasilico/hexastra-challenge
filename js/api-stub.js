/* Hexastra — cliente local de la API (fallback si js/api.js no está).
 *
 * Contrato que el front (js/easy.js) espera en window.HexastraAPI:
 *
 *   getTargets(body) -> Promise<Target[]>
 *     body: "moon" | "mars"
 *     Target: { id, name, short_name, body, lat, lon, summary, tags, geology_class,
 *               missing_features: string[] }
 *
 *   getTargetVector(id) -> Promise<TargetVector>
 *     { id, name, short_name, body, lat, lon, summary, geology_class, tags,
 *       features: { [key]: { value, unit, is_real, quality, source, note, comparable } },
 *       missing: string[],
 *       paired_earth_ids?: string[] }
 *
 *   getRegions() -> Promise<{ continents: { id, name, countries: { id, name }[] }[] }>
 *
 *   rankAnalogs({ targetVector, weights, gamma, top, continent, country })
 *     weights: { G, T, E, V, O }  (o Vo) que suman 1
 *     continent / country: id de getRegions(), o null / "world" para no filtrar
 *     -> { target, weights, gamma, source, catalog_note, matches: [{
 *           site: { id, name, short_name, body, lat, lon, country, country_name,
 *                   continent, continent_name, province, summary },
 *           score: number|null,          // 0–100
 *           why: string,                 // una línea
 *           breaks: string,              // una línea
 *           missing: string[],
 *           components: { G, T, E, V, O },  // 0–1 o null
 *           used_features: string[],
 *           qualitative_flags: string[]
 *        }] }
 *
 * Este stub lee data/catalog.json y data/sites.json. No inventa mediciones.
 * La geología entra solo como clase cualitativa (sin firmas espectrales).
 * La elevación absoluta no entra en el puntaje: no es comparable entre cuerpos.
 */
(function (global) {
  "use strict";

  const CONTINENTS = [
    { id: "africa", name: "África" },
    { id: "antarctica", name: "Antártida" },
    { id: "asia", name: "Asia" },
    { id: "europe", name: "Europa" },
    { id: "north-america", name: "América del Norte" },
    { id: "oceania", name: "Oceanía" },
    { id: "south-america", name: "América del Sur" }
  ];

  const GROUPS = {
    T: ["slope", "roughness"],
    E: ["temp_mean", "temp_diurnal_range", "illumination_pct"],
    V: ["water_ice_indicator", "precip_mm"],
    O: ["slope"]
  };

  const FEATURE_LABELS = {
    slope: "pendiente",
    roughness: "rugosidad",
    temp_mean: "temperatura media",
    temp_diurnal_range: "amplitud térmica",
    illumination_pct: "iluminación",
    water_ice_indicator: "hielo o volátiles",
    precip_mm: "precipitación",
    elevation: "elevación"
  };

  let cache = null;

  function continentOfCountry(name) {
    if (!name) return null;
    const n = String(name).toLowerCase();
    if (n === "argentina") return { id: "south-america", name: "América del Sur" };
    return null;
  }

  function countrySlug(name) {
    if (!name) return null;
    return String(name)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  async function load() {
    if (cache) return cache;
    const [catRes, sitesRes] = await Promise.all([
      fetch("data/catalog.json", { cache: "no-store" }),
      fetch("data/sites.json", { cache: "no-store" })
    ]);
    if (!catRes.ok) {
      throw new Error("No pude cargar data/catalog.json");
    }
    const catalog = await catRes.json();
    const sitesDoc = sitesRes.ok ? await sitesRes.json() : { earth_sites: [], mars_sites: [] };
    const earthById = {};
    (sitesDoc.earth_sites || []).forEach(function (s) {
      earthById[s.id] = s;
    });
    const marsById = {};
    (sitesDoc.mars_sites || []).forEach(function (s) {
      marsById[s.id] = s;
    });

    const sites = (catalog.sites || []).map(function (s) {
      const extra = earthById[s.id] || {};
      const countryName = extra.country || s.country || null;
      const cont = continentOfCountry(countryName);
      const pairedFromEarth = extra.paired_mars_ids || [];
      return Object.assign({}, s, {
        country: countrySlug(countryName),
        country_name: countryName,
        continent: cont ? cont.id : (s.continent || null),
        continent_name: cont ? cont.name : null,
        province: extra.province || s.province || null,
        why_analogous: extra.why_analogous || null,
        analogy_breaks: extra.analogy_breaks || null,
        paired_ids: pairedFromEarth,
        highlight_less_studied: !!extra.highlight_less_studied
      });
    });

    // Pares inversos: un destino de Marte/Luna apunta a los terrestres que lo listan.
    const reversePairs = {};
    sites.forEach(function (s) {
      (s.paired_ids || []).forEach(function (pid) {
        if (!reversePairs[pid]) reversePairs[pid] = [];
        reversePairs[pid].push(s.id);
      });
    });
    sites.forEach(function (s) {
      if (reversePairs[s.id]) s.paired_earth_ids = reversePairs[s.id];
    });

    cache = { catalog: catalog, sites: sites, earthById: earthById, marsById: marsById };
    return cache;
  }

  function missingFeatures(site) {
    const feats = site.features || {};
    return Object.keys(feats).filter(function (k) {
      const f = feats[k];
      return !f || f.value === null || f.value === undefined;
    });
  }

  function hasValue(site, key) {
    const f = site.features && site.features[key];
    if (!f || f.value === null || f.value === undefined) return false;
    if (key === "roughness" && f.comparable === false) return false;
    return true;
  }

  function rawValue(site, key) {
    return site.features[key].value;
  }

  function transform(key, value) {
    if (key === "precip_mm" || key === "roughness") return Math.log1p(Math.max(0, Number(value)));
    return Number(value);
  }

  function firstSentence(text) {
    if (!text) return "";
    const clean = String(text).replace(/\s+/g, " ").trim();
    const m = clean.match(/^(.+?[.!?])(\s|$)/);
    return m ? m[1] : clean;
  }

  function fmtNum(n, digits, unit) {
    if (n === null || n === undefined || Number.isNaN(n)) return "—";
    const s = Number(n).toLocaleString("es-AR", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    });
    return unit ? s + "\u00a0" + unit : s;
  }

  function mean(arr) {
    if (!arr.length) return 0;
    return arr.reduce(function (a, b) { return a + b; }, 0) / arr.length;
  }

  function stdev(arr) {
    if (arr.length < 2) return 0;
    const m = mean(arr);
    const v = arr.reduce(function (a, b) { return a + (b - m) * (b - m); }, 0) / arr.length;
    return Math.sqrt(v);
  }

  function identity(n) {
    const m = [];
    for (let i = 0; i < n; i++) {
      m[i] = [];
      for (let j = 0; j < n; j++) m[i][j] = i === j ? 1 : 0;
    }
    return m;
  }

  function regularizedCov(rows, nFeat) {
    const n = rows.length;
    const mu = [];
    for (let j = 0; j < nFeat; j++) {
      mu[j] = mean(rows.map(function (r) { return r[j]; }));
    }
    const cov = identity(nFeat);
    for (let i = 0; i < nFeat; i++) {
      for (let j = 0; j < nFeat; j++) {
        let s = 0;
        for (let r = 0; r < n; r++) s += (rows[r][i] - mu[i]) * (rows[r][j] - mu[j]);
        cov[i][j] = (n > 1 ? s / (n - 1) : 0);
      }
    }
    // Shrinkage hacia la identidad, para que sea invertible con pocos sitios.
    const eps = 0.15;
    for (let i = 0; i < nFeat; i++) {
      for (let j = 0; j < nFeat; j++) {
        cov[i][j] = (1 - eps) * cov[i][j] + (i === j ? eps : 0);
        if (i === j && cov[i][j] < 1e-6) cov[i][j] = 1e-6;
      }
    }
    return cov;
  }

  function invert(matrix) {
    const n = matrix.length;
    const a = matrix.map(function (row, i) {
      return row.concat(identity(n)[i]);
    });
    for (let i = 0; i < n; i++) {
      let max = i;
      for (let k = i + 1; k < n; k++) {
        if (Math.abs(a[k][i]) > Math.abs(a[max][i])) max = k;
      }
      const tmp = a[i]; a[i] = a[max]; a[max] = tmp;
      const piv = a[i][i];
      if (!isFinite(piv) || Math.abs(piv) < 1e-12) return null;
      for (let j = 0; j < 2 * n; j++) a[i][j] /= piv;
      for (let k = 0; k < n; k++) {
        if (k === i) continue;
        const f = a[k][i];
        for (let j = 0; j < 2 * n; j++) a[k][j] -= f * a[i][j];
      }
    }
    return a.map(function (row) { return row.slice(n); });
  }

  function mahalanobis(x, y, inv) {
    const n = x.length;
    const d = [];
    for (let i = 0; i < n; i++) d[i] = x[i] - y[i];
    const tmp = [];
    for (let i = 0; i < n; i++) {
      let s = 0;
      for (let j = 0; j < n; j++) s += inv[i][j] * d[j];
      tmp[i] = s;
    }
    let q = 0;
    for (let i = 0; i < n; i++) q += d[i] * tmp[i];
    return Math.sqrt(Math.max(0, q));
  }

  function euclid(x, y) {
    let s = 0;
    for (let i = 0; i < x.length; i++) s += (x[i] - y[i]) * (x[i] - y[i]);
    return Math.sqrt(s);
  }

  function familyOf(geology) {
    if (!geology) return null;
    const g = String(geology).toLowerCase();
    if (g.indexOf("volcanic") === 0) return "volcanic";
    if (g.indexOf("lacustrine") === 0) return "lacustrine";
    if (g.indexOf("sedimentary") === 0) return "sedimentary";
    if (g.indexOf("impact") === 0) return "impact";
    return g.split("_")[0];
  }

  function geologyScore(target, cand) {
    if (!target.geology_class || !cand.geology_class) {
      return { score: null, flag: "composición mineralógica: dato a completar" };
    }
    if (target.geology_class === cand.geology_class) {
      return { score: 1, flag: "geología cualitativa (sin firmas espectrales)" };
    }
    if (familyOf(target.geology_class) && familyOf(target.geology_class) === familyOf(cand.geology_class)) {
      return { score: 0.5, flag: "geología cualitativa (sin firmas espectrales)" };
    }
    return { score: 0, flag: "geología cualitativa (sin firmas espectrales)" };
  }

  function normalizeKey(key, target, population) {
    const vals = [];
    if (hasValue(target, key)) vals.push(transform(key, rawValue(target, key)));
    population.forEach(function (s) {
      if (hasValue(s, key)) vals.push(transform(key, rawValue(s, key)));
    });
    const m = mean(vals);
    const sd = stdev(vals);
    const scale = sd > 1e-9 ? sd : 1;
    return function (site) {
      if (!hasValue(site, key)) return null;
      return (transform(key, rawValue(site, key)) - m) / scale;
    };
  }

  function componentScore(keys, target, cand, population, gamma) {
    const used = keys.filter(function (k) { return hasValue(target, k) && hasValue(cand, k); });
    if (!used.length) return { score: null, used: [] };
    const norms = {};
    used.forEach(function (k) { norms[k] = normalizeKey(k, target, population); });
    const x = used.map(function (k) { return norms[k](target); });
    const y = used.map(function (k) { return norms[k](cand); });
    let dist;
    const rows = [];
    population.forEach(function (s) {
      const row = [];
      for (let i = 0; i < used.length; i++) {
        if (!hasValue(s, used[i])) return;
        row.push(norms[used[i]](s));
      }
      rows.push(row);
    });
    if (rows.length >= 3 && used.length >= 1) {
      const cov = regularizedCov(rows.concat([x]), used.length);
      const inv = invert(cov);
      dist = inv ? mahalanobis(x, y, inv) : euclid(x, y);
    } else {
      dist = euclid(x, y);
    }
    const g = typeof gamma === "number" && isFinite(gamma) ? gamma : 0.75;
    return { score: Math.exp(-g * dist), used: used };
  }

  function featurePhrase(key, target, cand) {
    const label = FEATURE_LABELS[key] || key;
    const t = rawValue(target, key);
    const c = rawValue(cand, key);
    if (key === "precip_mm") {
      return label + " (" + fmtNum(c, 1, "mm/año") + " frente a " + fmtNum(t, 1, "mm/año") + " en el destino)";
    }
    if (key === "temp_mean" || key === "temp_diurnal_range") {
      return label + " (" + fmtNum(c, 1, "°C") + " frente a " + fmtNum(t, 1, "°C") + ")";
    }
    if (key === "slope") {
      return label + " (" + fmtNum(c, 1, "°") + " frente a " + fmtNum(t, 1, "°") + ")";
    }
    return label + " (" + fmtNum(c, 1) + " frente a " + fmtNum(t, 1) + ")";
  }

  function joinEs(parts) {
    if (!parts.length) return "";
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return parts[0] + " y " + parts[1];
    return parts.slice(0, -1).join(", ") + " y " + parts[parts.length - 1];
  }

  function isPaired(target, cand) {
    return (cand.paired_ids || []).indexOf(target.id) !== -1 ||
      (target.paired_earth_ids || []).indexOf(cand.id) !== -1;
  }

  function whyLine(target, cand, usedFeatures) {
    if (isPaired(target, cand) && cand.why_analogous) {
      return firstSentence(cand.why_analogous);
    }
    const bits = usedFeatures.map(function (k) { return featurePhrase(k, target, cand); });
    if (!bits.length) {
      return "Hay pocos datos comparables entre este lugar y el destino; no alcanza para afirmar una analogía.";
    }
    return "Se parecen en " + joinEs(bits) + ".";
  }

  function breaksLine(target, cand, missing) {
    if (isPaired(target, cand) && cand.analogy_breaks) {
      return firstSentence(cand.analogy_breaks);
    }
    let line = "Ningún sitio terrestre imita la gravedad, la atmósfera ni la radiación del destino.";
    if (missing && missing.length) {
      line += " En esta comparación faltan datos de " + joinEs(missing.map(function (k) {
        return FEATURE_LABELS[k] || k;
      })) + ".";
    }
    return line;
  }

  function toTarget(site) {
    return {
      id: site.id,
      name: site.name,
      short_name: site.short_name,
      body: site.body,
      lat: site.lat,
      lon: site.lon,
      summary: site.summary,
      tags: site.tags || [],
      geology_class: site.geology_class || null,
      missing_features: missingFeatures(site)
    };
  }

  async function getTargets(body) {
    const db = await load();
    return db.sites.filter(function (s) { return s.body === body; }).map(toTarget);
  }

  async function getTargetVector(id) {
    const db = await load();
    const site = db.sites.find(function (s) { return s.id === id; });
    if (!site) throw new Error("No encuentro el destino «" + id + "».");
    return {
      id: site.id,
      name: site.name,
      short_name: site.short_name,
      body: site.body,
      lat: site.lat,
      lon: site.lon,
      summary: site.summary,
      geology_class: site.geology_class || null,
      tags: site.tags || [],
      features: site.features || {},
      missing: missingFeatures(site),
      paired_earth_ids: site.paired_earth_ids || []
    };
  }

  async function getRegions() {
    const db = await load();
    const byCont = {};
    db.sites.filter(function (s) { return s.body === "earth"; }).forEach(function (s) {
      if (!s.continent || !s.country) return;
      if (!byCont[s.continent]) byCont[s.continent] = {};
      byCont[s.continent][s.country] = s.country_name;
    });
    return {
      continents: CONTINENTS.map(function (c) {
        const countries = byCont[c.id] || {};
        return {
          id: c.id,
          name: c.name,
          countries: Object.keys(countries).sort().map(function (id) {
            return { id: id, name: countries[id] };
          })
        };
      })
    };
  }

  function weightMap(weights) {
    const w = weights || {};
    return {
      G: Number(w.G) || 0,
      T: Number(w.T) || 0,
      E: Number(w.E) || 0,
      V: Number(w.V != null ? w.V : w.Vo) || 0,
      O: Number(w.O) || 0
    };
  }

  async function rankAnalogs(opts) {
    opts = opts || {};
    const db = await load();
    const tv = opts.targetVector;
    if (!tv || !tv.id) throw new Error("Falta el vector del destino.");
    const target = db.sites.find(function (s) { return s.id === tv.id; });
    if (!target) throw new Error("No encuentro el destino «" + tv.id + "» en el catálogo local.");

    const continent = opts.continent && opts.continent !== "world" ? opts.continent : null;
    const country = opts.country && opts.country !== "all" ? opts.country : null;
    const gamma = typeof opts.gamma === "number" ? opts.gamma : 0.75;
    const top = typeof opts.top === "number" ? opts.top : 10;
    const W = weightMap(opts.weights);

    let candidates = db.sites.filter(function (s) { return s.body === "earth"; });
    if (continent) {
      const cslug = String(continent).toLowerCase();
      candidates = candidates.filter(function (s) {
        return s.continent === continent ||
          s.continent === cslug ||
          (s.continent_name && s.continent_name.toLowerCase() === cslug);
      });
    }
    if (country) {
      const cslug = String(country).toLowerCase();
      candidates = candidates.filter(function (s) {
        return s.country === cslug || s.country === country ||
          (s.country_name && s.country_name.toLowerCase() === cslug) ||
          (cslug === "ar" && s.country === "argentina");
      });
    }
    const featuredIds = featuredIdSet(opts.siteIds || (opts.featuredOnly ? featuredAliasIds() : null));
    if (featuredIds) {
      candidates = candidates.filter(function (s) { return featuredIds[s.id]; });
    }

    const matches = candidates.map(function (cand) {
      const g = geologyScore(target, cand);
      const t = componentScore(GROUPS.T, target, cand, candidates, gamma);
      const e = componentScore(GROUPS.E, target, cand, candidates, gamma);
      const v = componentScore(GROUPS.V, target, cand, candidates, gamma);
      const o = componentScore(GROUPS.O, target, cand, candidates, gamma);
      const comps = { G: g.score, T: t.score, E: e.score, V: v.score, O: o.score };
      const flags = [];
      if (g.flag) flags.push(g.flag);
      const used = [].concat(t.used || [], e.used || [], v.used || [], o.used || []);
      const missing = [];
      Object.keys(GROUPS).forEach(function (k) {
        GROUPS[k].forEach(function (f) {
          if (!hasValue(target, f) || !hasValue(cand, f)) {
            if (missing.indexOf(f) === -1) missing.push(f);
          }
        });
      });
      if (!target.geology_class || !cand.geology_class) {
        missing.push("composición mineralógica");
      }

      let wSum = 0;
      let acc = 0;
      let any = false;
      Object.keys(comps).forEach(function (k) {
        if (comps[k] === null || comps[k] === undefined) return;
        const wk = W[k] || 0;
        if (wk <= 0) return;
        wSum += wk;
        acc += wk * comps[k];
        any = true;
      });
      const tasi = any && wSum > 0 ? acc / wSum : null;
      const score = tasi === null ? null : Math.round(Math.max(0, Math.min(1, tasi)) * 1000) / 10;

      return {
        site: {
          id: cand.id,
          name: cand.name,
          short_name: cand.short_name,
          body: "earth",
          lat: cand.lat,
          lon: cand.lon,
          country: cand.country,
          country_name: cand.country_name,
          continent: cand.continent,
          continent_name: cand.continent_name,
          province: cand.province,
          summary: cand.summary,
          highlight_less_studied: cand.highlight_less_studied
        },
        score: score,
        why: whyLine(target, cand, used),
        breaks: breaksLine(target, cand, missing.filter(function (k) { return k !== "elevation"; })),
        missing: missing,
        components: comps,
        used_features: used,
        qualitative_flags: flags
      };
    }).filter(function (m) { return m.score !== null; });

    matches.sort(function (a, b) { return b.score - a.score; });

    const earthCount = db.sites.filter(function (s) { return s.body === "earth"; }).length;
    return {
      target: { id: target.id, name: target.name, short_name: target.short_name, body: target.body },
      weights: W,
      gamma: gamma,
      source: "stub",
      catalog_note: opts.featuredOnly
        ? "En el catálogo local, de los destacados solo tienen vector comparable Campo de Piedra Pómez y Payún Matrú. El resto se ve en la tira, pero todavía no entra al puntaje."
        : ("El catálogo local de este prototipo tiene " + earthCount +
          " lugares terrestres, todos en Argentina. No inventamos sitios de otros países."),
      matches: matches.slice(0, top)
    };
  }

  /* Destacados: atajos curatorados. Coordenadas solo con fuente citada.
     has_features = true únicamente si el lugar está en data/catalog.json. */
  const FEATURED = [
    {
      id: "mcmurdo-dry-valleys",
      name: "Valles secos de McMurdo",
      short_name: "McMurdo",
      group: "world",
      country: "AQ",
      country_name: "Antártida",
      continent: "antarctica",
      continent_name: "Antártida",
      lat: -77.61666667,
      lon: 163.0,
      coord_source: "Punto de Taylor Valley, uno de los valles secos principales. Wikipedia EN «Taylor Valley»: 77°37′S 163°00′E. https://en.wikipedia.org/wiki/Taylor_Valley",
      summary: "Valles hiperárdios de Tierra Victoria, sin cubierta de hielo; análogo polar clásico de Marte frío y seco. El pin marca Taylor Valley, no todo el sistema de valles.",
      classic: true,
      aliases: ["taylor-valley", "university-valley"]
    },
    {
      id: "haughton",
      name: "Cráter Haughton",
      short_name: "Haughton",
      group: "world",
      country: "CA",
      country_name: "Canadá",
      continent: "north-america",
      continent_name: "América del Norte",
      lat: 75.38333333,
      lon: -89.66666667,
      coord_source: "Wikipedia EN «Haughton impact crater»: 75.38333333°N, 89.66666667°W (PASSC: N 75°22′, W 89°41′). https://en.wikipedia.org/wiki/Haughton_impact_crater",
      summary: "Cráter de impacto en la isla Devon (Nunavut), sede del Haughton–Mars Project. Análogo polar y de cráter muy estudiado.",
      classic: true,
      aliases: ["haughton"]
    },
    {
      id: "devon-island",
      name: "Isla Devon (FMARS)",
      short_name: "Isla Devon",
      group: "world",
      country: "CA",
      country_name: "Canadá",
      continent: "north-america",
      continent_name: "América del Norte",
      lat: 75.4313194,
      lon: -89.8233861,
      coord_source: "Flashline Mars Arctic Research Station, Haynes Ridge. Wikipedia EN «Flashline Mars Arctic Research Station» e INTERACT GIS: 75.4313194°N, 89.8233861°W. https://en.wikipedia.org/wiki/Flashline_Mars_Arctic_Research_Station",
      summary: "Hábitat de analogía operacional de The Mars Society en la isla Devon, sobre una cresta que mira al cráter Haughton. El pin es la estación, no el centro de la isla.",
      classic: true,
      aliases: ["fmars", "devon-island", "mcgill-arctic"]
    },
    {
      id: "canarias-timanfaya",
      name: "Canarias (Timanfaya, Lanzarote)",
      short_name: "Timanfaya",
      group: "world",
      country: "ES",
      country_name: "España",
      continent: "europe",
      continent_name: "Europa",
      lat: 29.0141,
      lon: -13.78,
      coord_source: "Centro del Parque Nacional de Timanfaya en el visor Natura 2000 de Biodiversidad Canarias (Gobierno de Canarias), lugar ES0000141: 29,014100°N, 13,780000°O. https://www.biodiversidadcanarias.es/inatura/espacios/ES0000141",
      summary: "Malpaís y conos de las erupciones de 1730–1736 en Lanzarote. Atajo a Timanfaya; Teide (Tenerife) es otro análogo canario, no está pinado acá.",
      classic: true,
      aliases: ["timanfaya", "lanzarote", "teide"]
    },
    {
      id: "kilauea",
      name: "Kīlauea",
      short_name: "Kīlauea",
      group: "world",
      country: "US",
      country_name: "Estados Unidos",
      continent: "oceania",
      continent_name: "Oceanía",
      lat: 19.42109747,
      lon: -155.28676243,
      coord_source: "Wikipedia EN «Kīlauea»: 19.42109747°N, 155.28676243°W. https://en.wikipedia.org/wiki/Kīlauea",
      summary: "Volcán en escudo activo de Hawái, análogo volcánico clásico (coladas, tubos de lava) y muy estudiado.",
      classic: true,
      aliases: ["kilauea"]
    },
    {
      id: "mauna-kea",
      name: "Mauna Kea",
      short_name: "Mauna Kea",
      group: "world",
      country: "US",
      country_name: "Estados Unidos",
      continent: "oceania",
      continent_name: "Oceanía",
      lat: 19.82,
      lon: -155.47,
      coord_source: "Smithsonian Global Volcanism Program, volcán 332030, y USGS Hawaiian Volcano Observatory: 19.82°N, 155.47°W. https://volcano.si.edu/volcano.cfm?vn=332030 https://www.usgs.gov/volcanoes/mauna-kea",
      summary: "El volcán más alto de Hawái. Análogo clásico de alta montaña y de ambiente seco en altura; también muy estudiado.",
      classic: true,
      aliases: ["mauna-kea", "maunakea"]
    },
    {
      id: "atacama-yungay",
      name: "Atacama (Yungay)",
      short_name: "Atacama",
      group: "world",
      country: "CL",
      country_name: "Chile",
      continent: "south-america",
      continent_name: "América del Sur",
      lat: -24.069867,
      lon: -69.866033,
      coord_source: "Kuhlman & McKay, Lunar and Planetary Science XXXVIII (2007), abstract 2251, GPS −24.069867, −69.866033 (núcleo hiperárido). https://www.lpi.usra.edu/meetings/lpsc2007/pdf/2251.pdf",
      summary: "Sitio clásico de astrobiología en el núcleo hiperárido del Desierto de Atacama. El pin es Yungay, no todo el desierto. No confundir con la ciudad de Yungay en el Biobío.",
      classic: true,
      aliases: ["yungay-atacama", "atacama", "valle-de-la-luna-chile"]
    },
    {
      id: "campo-piedra-pomez",
      name: "Campo de Piedra Pómez",
      short_name: "Piedra Pómez",
      group: "argentina",
      country: "AR",
      country_name: "Argentina",
      continent: "south-america",
      continent_name: "América del Sur",
      province: "Catamarca",
      lat: -26.659722,
      lon: -67.514167,
      coord_source: "Centro del área protegida 26°39′35″S 67°30′51″O. Wikipedia/Wikidata Q23833026. Ya está en data/catalog.json.",
      summary: "Yardangs en ignimbrita de la Puna catamarqueña; analogía eólica con Medusae Fossae.",
      classic: false,
      aliases: ["campo-piedra-pomez"]
    },
    {
      id: "payun-matru",
      name: "Payunia (Payún Matrú)",
      short_name: "Payunia",
      group: "argentina",
      country: "AR",
      country_name: "Argentina",
      continent: "south-america",
      continent_name: "América del Sur",
      province: "Mendoza",
      lat: -36.422,
      lon: -69.241,
      coord_source: "Smithsonian GVP, volcán 357066: 36.422°S, 69.241°W. https://volcano.si.edu/volcano.cfm?vn=357066. Ya está en data/catalog.json.",
      summary: "Campo volcánico basáltico de La Payunia, Mendoza, con coladas muy largas; analogía con Tharsis.",
      classic: false,
      aliases: ["payun-matru", "payunia"]
    },
    {
      id: "laguna-diamante",
      name: "Laguna Diamante",
      short_name: "Laguna Diamante",
      group: "argentina",
      country: "AR",
      country_name: "Argentina",
      continent: "south-america",
      continent_name: "América del Sur",
      province: "Catamarca",
      lat: -26.016667,
      lon: -67.033333,
      coord_source: "Albarracín et al., Photochemistry and Photobiology (2016), Table 1, Laguna Diamante, Catamarca: 26°01′S, 67°02′W. doi:10.1111/php.12555. Es la laguna de la caldera del Galán, no Laguna del Diamante (Mendoza).",
      summary: "Laguna hipersalina y alcalina en la caldera del volcán Galán, Puna de Catamarca. Se estudia como lago de altura (HAAL); análogo menos citado que Atacama o Hawái.",
      classic: false,
      aliases: ["laguna-diamante", "laguna-del-diamante"]
    },
    {
      id: "laguna-socompa",
      name: "Laguna Socompa",
      short_name: "Socompa",
      group: "argentina",
      country: "AR",
      country_name: "Argentina",
      continent: "south-america",
      continent_name: "América del Sur",
      province: "Salta",
      lat: -24.533333,
      lon: -68.2,
      coord_source: "Albarracín et al., Photochemistry and Photobiology (2016), Table 1, Laguna Socompa, Salta: 24°32′S, 68°12′W. doi:10.1111/php.12555. El pin es la laguna, no la cumbre del volcán (GVP 355109: 24.396°S, 68.246°W).",
      summary: "Laguna de altura al pie del volcán Socompa, en la Puna salteña, usada como laboratorio de extremófilos (HAAL). El volcán queda al sudoeste; no mezclamos las dos cotas.",
      classic: false,
      aliases: ["socompa", "laguna-socompa"]
    }
  ];

  const FEATURED_CATALOG_IDS = ["campo-piedra-pomez", "payun-matru"];

  function featuredAliasIds() {
    const out = {};
    FEATURED.forEach(function (p) {
      out[p.id] = true;
      (p.aliases || []).forEach(function (a) { out[a] = true; });
    });
    return out;
  }

  function featuredIdSet(ids) {
    if (!ids) return null;
    if (ids === true) return featuredAliasIds();
    const out = {};
    const all = featuredAliasIds();
    (Array.isArray(ids) ? ids : Object.keys(ids)).forEach(function (id) {
      out[id] = true;
      FEATURED.forEach(function (p) {
        if (p.id === id || (p.aliases || []).indexOf(id) !== -1) {
          out[p.id] = true;
          (p.aliases || []).forEach(function (a) { out[a] = true; });
        }
      });
      if (all[id]) out[id] = true;
    });
    return out;
  }

  async function getFeatured() {
    const db = await load();
    const catalogIds = {};
    db.sites.forEach(function (s) {
      if (s.body === "earth") catalogIds[s.id] = s;
    });
    const places = FEATURED.map(function (p) {
      const inCat = catalogIds[p.id] || (p.aliases || []).map(function (a) { return catalogIds[a]; }).filter(Boolean)[0];
      const hasFeatures = !!(inCat && inCat.features);
      const pending = p.lat == null || p.lon == null;
      return {
        id: p.id,
        name: p.name,
        short_name: p.short_name,
        group: p.group,
        country: p.country,
        country_name: p.country_name,
        continent: p.continent,
        continent_name: p.continent_name,
        province: p.province || null,
        lat: pending ? null : p.lat,
        lon: pending ? null : p.lon,
        coord_source: p.coord_source || null,
        summary: p.summary,
        classic: !!p.classic,
        highlight_less_studied: !p.classic && p.group === "argentina" && !hasFeatures,
        status: pending ? "pending_service" : "ready",
        has_features: hasFeatures,
        aliases: p.aliases || [],
        catalog_id: inCat ? inCat.id : null
      };
    });
    return {
      source: "stub",
      groups: [
        { id: "world", name: "Mundo", places: places.filter(function (p) { return p.group === "world"; }) },
        { id: "argentina", name: "Argentina", places: places.filter(function (p) { return p.group === "argentina"; }) }
      ]
    };
  }

  async function rankTargetsFromEarth(opts) {
    opts = opts || {};
    const db = await load();
    const earthId = opts.earthId || opts.earthSiteId || (opts.earthVector && opts.earthVector.id);
    if (!earthId) throw new Error("Falta el id del lugar terrestre.");
    const feat = FEATURED.filter(function (p) { return p.id === earthId || (p.aliases || []).indexOf(earthId) !== -1; })[0];
    const earth = db.sites.find(function (s) {
      return s.body === "earth" && (s.id === earthId || (feat && (feat.aliases || []).indexOf(s.id) !== -1));
    });
    if (!earth) {
      const err = new Error("Este destacado todavía no tiene un vector en el catálogo local.");
      err.code = "NO_LOCAL_VECTOR";
      throw err;
    }
    const body = opts.body || null;
    let candidates = db.sites.filter(function (s) {
      return s.body === "moon" || s.body === "mars";
    });
    if (body === "moon" || body === "mars") {
      candidates = candidates.filter(function (s) { return s.body === body; });
    }
    const gamma = typeof opts.gamma === "number" ? opts.gamma : 0.75;
    const top = typeof opts.top === "number" ? opts.top : 10;
    const W = weightMap(opts.weights);
    const matches = candidates.map(function (cand) {
      const g = geologyScore(earth, cand);
      const tsc = componentScore(GROUPS.T, earth, cand, candidates, gamma);
      const e = componentScore(GROUPS.E, earth, cand, candidates, gamma);
      const v = componentScore(GROUPS.V, earth, cand, candidates, gamma);
      const o = componentScore(GROUPS.O, earth, cand, candidates, gamma);
      const comps = { G: g.score, T: tsc.score, E: e.score, V: v.score, O: o.score };
      const used = [].concat(tsc.used || [], e.used || [], v.used || [], o.used || []);
      const missing = [];
      Object.keys(GROUPS).forEach(function (k) {
        GROUPS[k].forEach(function (f) {
          if (!hasValue(earth, f) || !hasValue(cand, f)) {
            if (missing.indexOf(f) === -1) missing.push(f);
          }
        });
      });
      let wSum = 0, acc = 0, any = false;
      Object.keys(comps).forEach(function (k) {
        if (comps[k] == null) return;
        const wk = W[k] || 0;
        if (wk <= 0) return;
        wSum += wk;
        acc += wk * comps[k];
        any = true;
      });
      const tasi = any && wSum > 0 ? acc / wSum : null;
      const score = tasi == null ? null : Math.round(Math.max(0, Math.min(1, tasi)) * 1000) / 10;
      return {
        site: {
          id: cand.id,
          name: cand.name,
          short_name: cand.short_name,
          body: cand.body,
          lat: cand.lat,
          lon: cand.lon,
          summary: cand.summary,
          geology_class: cand.geology_class
        },
        score: score,
        why: whyLine(earth, cand, used),
        breaks: breaksLine(earth, cand, missing.filter(function (k) { return k !== "elevation"; })),
        missing: missing,
        components: comps,
        used_features: used,
        qualitative_flags: g.flag ? [g.flag] : []
      };
    }).filter(function (m) { return m.score !== null; });
    matches.sort(function (a, b) { return b.score - a.score; });
    return {
      direction: "earth-to-planetary",
      target: { id: earth.id, name: earth.name, short_name: earth.short_name, body: "earth" },
      weights: W,
      gamma: gamma,
      source: "stub",
      catalog_note: "Ranking inverso local: comparamos este lugar de la Tierra con los sitios de la Luna y de Marte que están en el catálogo. No inventamos mediciones.",
      matches: matches.slice(0, top)
    };
  }

  const stub = {
    getTargets: getTargets,
    getTargetVector: getTargetVector,
    getRegions: getRegions,
    rankAnalogs: rankAnalogs,
    getFeatured: getFeatured,
    rankTargetsFromEarth: rankTargetsFromEarth,
    featuredAliasIds: featuredAliasIds,
    source: "stub"
  };

  global.HexastraAPIStub = stub;
  if (!global.HexastraAPI) {
    global.HexastraAPI = stub;
  } else {
    ["getFeatured", "rankTargetsFromEarth", "featuredAliasIds"].forEach(function (k) {
      if (typeof global.HexastraAPI[k] !== "function") global.HexastraAPI[k] = stub[k];
    });
  }
  if (typeof global.__hexastraResolveApi === "function") {
    global.__hexastraResolveApi(global.HexastraAPI);
  }
})(window);
