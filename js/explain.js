/* Hexastra — explicación de un resultado TASI (compartida por el modo fácil y el avanzado).
 * Si el servicio manda why/breaks/missing, se usan tal cual. Si no, se arman con los
 * componentes de esa misma respuesta: el componente con dato más alto («por qué se parece»),
 * el más bajo («en qué no») y los que no tienen dato («dato a completar»). No se inventa nada. */
(function (root) {
  "use strict";

  const KEYS = ["G", "T", "E", "V", "O"];
  const COMPONENT_LABELS = {
    G: "geología (G)",
    T: "terreno (T)",
    E: "clima e iluminación (E)",
    V: "volátiles o hielo (V)",
    O: "operación (O)"
  };

  function formatScore(score) {
    if (score == null || Number.isNaN(Number(score))) return "sin puntaje";
    const n = Number(score);
    return n.toLocaleString(globalThis.HexastraI18n?.locale || "es-AR", {
      maximumFractionDigits: 1,
      minimumFractionDigits: n % 1 ? 1 : 0
    });
  }

  /** Puntaje 0–100 de un componente, o null si no tiene dato. */
  function componentScore(c) {
    if (c == null) return null;
    if (typeof c === "number") return c <= 1 ? c * 100 : c;
    if (c.available === false || c.score == null) return null;
    return Number(c.score);
  }

  /**
   * @param {object} m resultado de /tasi o del respaldo local
   * @param {(key: string) => string} [labelMissing] traduce claves de m.missing
   * @returns {{why: string, breaks: string, missing: string[]}}
   */
  function explainMatch(m, labelMissing) {
    const localized = globalThis.HexastraI18n?.explainMatch(m);
    if (localized) return localized;
    const comps = (m && m.components) || {};
    const scored = [];
    const missing = [];
    KEYS.forEach(function (k) {
      if (!(k in comps)) return;
      const s = componentScore(comps[k]);
      if (s == null && !comps[k]?.data_available) missing.push(COMPONENT_LABELS[k]);
      else if (s != null) scored.push({ k: k, s: s });
    });
    scored.sort(function (a, b) { return b.s - a.s; });
    const line = function (x) {
      return COMPONENT_LABELS[x.k] + ", " + formatScore(Math.round(x.s * 10) / 10) + " de 100";
    };
    let why = m && m.why;
    let breaks = m && m.breaks;
    if (!why && scored.length) why = "Lo más parecido es " + line(scored[0]) + ".";
    if (!breaks && scored.length > 1) breaks = "Lo menos parecido es " + line(scored[scored.length - 1]) + ".";
    if (!breaks && scored.length === 1) breaks = "Hay un solo componente con dato: no alcanza para decir en qué se separa.";
    const given = m && Array.isArray(m.missing) ? m.missing : null;
    const list = given ? given.map(function (k) { return labelMissing ? labelMissing(k) : k; }) : missing;
    return { why: why || "", breaks: breaks || "", missing: list };
  }

  const api = {
    COMPONENT_LABELS: COMPONENT_LABELS,
    formatScore: formatScore,
    componentScore: componentScore,
    explainMatch: explainMatch
  };
  root.HexastraExplain = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : this);
