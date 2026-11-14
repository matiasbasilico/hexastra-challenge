/* HexAstra — respaldo cuando no hay servicios.
 *
 * No guarda ni copia datos: todo el contenido sale de la API (planetary-service y earth-service).
 * Si los servicios no responden, cada método rechaza con un error claro de «servicio no disponible»
 * y la interfaz lo muestra en lugar de cifras viejas. Mantiene el arranque: resuelve
 * window.HEXASTRA_API_READY con window.HexastraAPI (js/api.js) o con este respaldo.
 */
(function (global) {
  "use strict";

  const MESSAGE =
    "El servicio no está disponible en este momento. Levantá los servicios con ./run_all.sh " +
    "o abrí el link para compartir con ?planetary=…&earth=…; mientras tanto no mostramos datos.";

  function unavailable() {
    const err = new Error(MESSAGE);
    err.code = "SERVICE_UNAVAILABLE";
    return Promise.reject(err);
  }

  const METHODS = [
    "getTargets", "getTargetVector", "getRegions", "getFeatured", "getCandidates",
    "getCandidate", "getExamples", "rankAnalogs", "getMethod", "getBodies"
  ];

  const stub = { source: "unavailable", message: MESSAGE };
  METHODS.forEach(function (name) { stub[name] = unavailable; });

  global.HexastraAPIStub = stub;
  if (!global.HexastraAPI) global.HexastraAPI = stub;
  if (typeof global.__hexastraResolveApi === "function") {
    global.__hexastraResolveApi(global.HexastraAPI);
  }
  if (typeof module !== "undefined" && module.exports) module.exports = stub;
})(typeof window !== "undefined" ? window : this);
