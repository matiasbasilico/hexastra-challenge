/* HexAstra — tabla «Lo que la Tierra no puede imitar», armada con GET {planetary}/bodies.
 * Cada valor trae su fuente desde la API; lo que llega null se muestra como «A completar» con su nota.
 * El front solo convierte unidades para leer mejor (Pa → mbar) y no agrega cifras. */
(function () {
  "use strict";

  const BODIES = [["earth", "Tierra"], ["mars", "Marte"], ["moon", "Luna"]];
  const ROWS = [
    { key: "gravity_m_s2", label: "Gravedad, m/s²", convert: (v) => v },
    { key: "surface_pressure_pa", label: "Presión en superficie, mbar", convert: (v) => v / 100 },
    { key: "surface_dose_msv_day", label: "Radiación cósmica en superficie, mSv/día", convert: (v) => v, digits: 3 },
    { key: "day_length_h", label: "Duración del día solar, h", convert: (v) => v, digits: 1 },
  ];

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /** Número en es-AR; los muy chicos en notación científica (3×10⁻¹²). */
  function formatValue(v, maximumFractionDigits) {
    if (v == null || Number.isNaN(Number(v))) return null;
    const n = Number(v);
    if (n !== 0 && Math.abs(n) < 0.01) {
      const exp = Math.floor(Math.log10(Math.abs(n)));
      const mant = Math.round((n / Math.pow(10, exp)) * 10) / 10;
      return escapeHtml(String(mant).replace(".", ",")) + "×10<sup>" + String(exp).replace("-", "−") + "</sup>";
    }
    const digits = maximumFractionDigits ?? (Math.abs(n) >= 100 ? 0 : Math.abs(n) >= 10 ? 1 : 2);
    return escapeHtml(n.toLocaleString("es-AR", { maximumFractionDigits: digits, useGrouping: Math.abs(n) >= 10000 }));
  }

  function linkify(text) {
    const parts = String(text || "").split(/(https?:\/\/[^\s)]+)/g);
    return parts.map((p, i) => i % 2
      ? '<a href="' + escapeHtml(p) + '" target="_blank" rel="noopener">' + escapeHtml(p.replace(/^https?:\/\//, "").split("/")[0]) + "</a>"
      : escapeHtml(p)).join("");
  }

  function render(data) {
    const rows = document.getElementById("limits-rows");
    const notes = document.getElementById("limits-notes");
    const bodies = (data && data.bodies) || {};
    const sources = [];
    const pending = [];
    rows.innerHTML = ROWS.map((row) => {
      const cells = BODIES.map(([id, name]) => {
        const item = (bodies[id] || {})[row.key];
        const shown = item && item.value != null && !Array.isArray(item.value) ? formatValue(row.convert(Number(item.value)), row.digits) : null;
        if (item && item.source && shown != null) sources.push({ body: name, label: row.label, source: item.source, note: item.note });
        if (shown == null) {
          pending.push({ body: name, label: row.label, note: (item && item.note) || "a completar: la API no trae este valor." });
          return '<td class="num" data-label="' + name + '"><span class="chip chip-warn">A completar</span></td>';
        }
        return '<td class="num" data-label="' + name + '">' + shown + "</td>";
      }).join("");
      return '<tr><th scope="row">' + escapeHtml(row.label) + "</th>" + cells + "</tr>";
    }).join("");
    const seen = {};
    const sourceItems = sources.filter((s) => {
      const k = s.body + "|" + s.source;
      if (seen[k]) return false;
      seen[k] = true;
      return true;
    }).map((s) => "<li><strong>" + escapeHtml(s.body) + ".</strong> " + linkify(s.source) + (s.note ? " " + escapeHtml(s.note) : "") + "</li>").join("");
    const pendingItems = pending.map((p) => "<li><strong>" + escapeHtml(p.body) + ", " + escapeHtml(p.label) + ":</strong> " + escapeHtml(p.note) + "</li>").join("");
    const retrieved = data && data.meta && data.meta.retrieved_at ? " Consultado el " + escapeHtml(data.meta.retrieved_at) + "." : "";
    notes.innerHTML =
      "<p class='limits-source'>Fuentes que devuelve el servicio planetary (/bodies)." + retrieved + "</p>" +
      "<ul class='limits-list'>" + sourceItems + "</ul>" +
      (pendingItems ? "<p class='limits-source'>A completar:</p><ul class='limits-list'>" + pendingItems + "</ul>" : "");
  }

  function renderError(message) {
    const rows = document.getElementById("limits-rows");
    rows.innerHTML = '<tr><td colspan="4" class="limits-pending"><span class="chip chip-warn">Servicio no disponible</span> ' + escapeHtml(message) + "</td></tr>";
    document.getElementById("limits-notes").innerHTML = "";
  }

  async function boot() {
    const button = document.getElementById("btn-limites");
    const dialog = document.getElementById("limits-dialog");
    if (button && dialog) button.addEventListener("click", () => dialog.showModal());
    const ready = window.HEXASTRA_API_READY;
    const api = ready && typeof ready.then === "function" ? await ready.catch(() => window.HexastraAPI) : window.HexastraAPI;
    try {
      if (!api || typeof api.getBodies !== "function") throw new Error("La API no expone /bodies.");
      render(await api.getBodies());
    } catch (e) {
      renderError((window.HexastraAPIStub && window.HexastraAPIStub.message) || e.message);
    }
  }

  window.HexastraLimits = { formatValue: formatValue, render: render };
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
  }
})();
