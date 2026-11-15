/* Default service URLs for the Hexastra prototype.
   Override at runtime with localStorage:
     HEXASTRA_PLANETARY_URL, HEXASTRA_EARTH_URL
   or with the share link produced by scripts/share.sh:
     https://<pages-url>/?planetary=https://<a>.trycloudflare.com&earth=https://<b>.trycloudflare.com
   Only Cloudflare quick-tunnel hosts and the local machine are accepted from
   the URL, so a crafted link cannot point the page at an arbitrary server.
*/
(function (root) {
  "use strict";

  const LOCAL_HOST = /^(?:127\.0\.0\.1|localhost)$/;
  const servedLocally = LOCAL_HOST.test(root.location.hostname) || root.location.protocol === "file:";

  // On the published site (Cloudflare Pages) the services are reached through the
  // same-origin proxy /api/<service> (pages/functions), so a shared link works for anyone.
  root.HEXASTRA_CONFIG = root.HEXASTRA_CONFIG || (servedLocally
    ? { planetaryUrl: "http://127.0.0.1:8766", earthUrl: "http://127.0.0.1:8767" }
    : { planetaryUrl: root.location.origin + "/api/planetary", earthUrl: root.location.origin + "/api/earth" });

  // Cada visita publicada empieza por el proxy de este dominio. Un túnel viejo
  // guardado en el navegador no debe sobrevivir al reinicio de los servicios.
  // applyShareLink vuelve a aplicar solo los overrides explícitos de esta URL.
  if (!servedLocally) {
    ["HEXASTRA_PLANETARY_URL", "HEXASTRA_EARTH_URL"].forEach(function (key) {
      try { root.localStorage.removeItem(key); } catch (e) { /* modo privado */ }
    });
  }

  const ALLOWED_HOST = /^(?:[a-z0-9-]+\.trycloudflare\.com|127\.0\.0\.1|localhost)$/;

  function safeServiceUrl(raw) {
    try {
      const url = new URL(raw);
      const local = url.hostname === "127.0.0.1" || url.hostname === "localhost";
      if (!ALLOWED_HOST.test(url.hostname)) return null;
      if (local && !servedLocally) return null;
      if (url.protocol !== "https:" && !(local && url.protocol === "http:")) return null;
      return url.origin;
    } catch (e) {
      return null;
    }
  }

  function applyShareLink() {
    let params;
    try {
      params = new URLSearchParams(root.location.search);
    } catch (e) {
      return;
    }
    const pairs = [["planetary", "HEXASTRA_PLANETARY_URL"], ["earth", "HEXASTRA_EARTH_URL"]];
    pairs.forEach(function (pair) {
      const value = params.get(pair[0]);
      if (!value) return;
      const safe = safeServiceUrl(value);
      if (!safe) return;
      try {
        root.localStorage.setItem(pair[1], safe);
      } catch (e) {
        // Private mode: fall back to this page load only.
        root.HEXASTRA_CONFIG[pair[0] + "Url"] = safe;
      }
    });
  }

  applyShareLink();
})(window);
