// Same-origin proxy: /api/planetary/... and /api/earth/... -> the Mac, through the
// current cloudflared quick tunnel. scripts/share.sh writes each tunnel URL to KV,
// so the public link never changes even though tunnel URLs do.
const SERVICES = new Set(["planetary", "earth"]);
const TUNNEL = /^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/;
const HOP_BY_HOP = ["host", "connection", "cf-connecting-ip", "cf-ipcountry", "cf-ray", "cf-visitor", "x-forwarded-proto", "x-real-ip"];

function unavailable(service, reason) {
  return new Response(
    JSON.stringify({ ok: false, service, error: "Servicio no disponible", reason }),
    { status: 503, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } }
  );
}

export async function onRequest({ request, params, env }) {
  const service = params.service;
  if (!SERVICES.has(service)) {
    return new Response(JSON.stringify({ ok: false, error: "Servicio desconocido" }), { status: 404 });
  }
  const base = env.HEXASTRA_TUNNELS ? await env.HEXASTRA_TUNNELS.get(service) : null;
  if (!base || !TUNNEL.test(base)) {
    return unavailable(service, "El túnel hacia los servicios está apagado. Corré scripts/share.sh en la Mac.");
  }
  const path = Array.isArray(params.path) ? params.path.join("/") : params.path || "";
  const url = new URL(request.url);
  const target = base + "/" + path + url.search;
  const headers = new Headers(request.headers);
  HOP_BY_HOP.forEach((h) => headers.delete(h));
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });
    const out = new Response(upstream.body, upstream);
    out.headers.set("cache-control", "no-store");
    return out;
  } catch (err) {
    return unavailable(service, "No se pudo conectar con el túnel: " + String(err && err.message || err));
  }
}
