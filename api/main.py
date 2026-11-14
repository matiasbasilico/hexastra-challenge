"""API Hexastra: normalización y similitud de análogos Tierra–Luna–Marte."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from catalog import all_sites, feature_schema, load_catalog, site_by_id, sites_by_body
from similarity import resolve_features, resolve_weights, similar as compute_similar

ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="Hexastra Analogos API",
    version="0.2.0",
    description=(
        "Catálogo unificado de sitios en la Tierra, la Luna y Marte, con normalización "
        "por rasgo (z-score o min-max, y log1p cuando el rango cubre órdenes de magnitud) "
        "y búsqueda de análogos por similitud coseno o euclidiana ponderada. "
        "Si falta un valor, ese rasgo se omite y se renormalizan los pesos. "
        "Los números no verificados van como null con quality=placeholder."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "sites": len(all_sites())}


@app.get("/features", tags=["catalogo"])
def get_features():
    cat = load_catalog()
    return {
        "features": feature_schema(),
        "normalization_rationale": cat["meta"]["normalization_rationale"],
        "disclaimer": cat["meta"]["disclaimer"],
        "artemis_iii_regions_nasa_2022": cat["meta"]["artemis_iii_regions_nasa_2022"],
        "artemis_source": cat["meta"]["artemis_source"],
    }


@app.get("/sites", tags=["catalogo"])
def get_sites(
    body: str | None = Query(None, description="Filtro opcional: earth, moon o mars"),
):
    if body is not None:
        body = body.lower()
        if body not in {"earth", "moon", "mars"}:
            raise HTTPException(400, "body debe ser earth, moon o mars")
    return {"body": body, "count": len(sites_by_body(body)), "sites": sites_by_body(body)}


@app.get("/sites/{site_id}", tags=["catalogo"])
def get_site(site_id: str):
    site = site_by_id(site_id)
    if not site:
        raise HTTPException(404, f"No está el sitio '{site_id}'")
    return site


@app.get("/similar", tags=["similitud"])
def get_similar(
    target: str = Query(..., description="id del sitio objetivo (p. ej. jezero, shackleton-rim)"),
    body: str = Query("earth", description="Cuerpo en el que buscar análogos: earth, moon o mars"),
    features: str | None = Query(
        None,
        description="Rasgos separados por coma (elevation,slope,temp_mean,temp_diurnal_range,precip_mm,...)",
    ),
    weights: str | None = Query(None, description="Pesos separados por coma, en el mismo orden que features"),
    method: str = Query("cosine", description="cosine o euclidean"),
    norm: str = Query("zscore", description="zscore o minmax"),
    top: int = Query(5, ge=1, le=50),
    log: bool = Query(True, description="Aplicar log1p a rasgos con use_log (precip_mm, roughness) antes de normalizar"),
):
    body = body.lower()
    if body not in {"earth", "moon", "mars"}:
        raise HTTPException(400, "body debe ser earth, moon o mars")
    site = site_by_id(target)
    if not site:
        raise HTTPException(404, f"No está el sitio objetivo '{target}'")
    try:
        feat_ids = resolve_features(features)
        w = resolve_weights(feat_ids, weights)
        result = compute_similar(site, body, feat_ids, w, method, norm, top, apply_log=log)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


# Front estático (un solo proceso sirve la app y la API)
@app.get("/", include_in_schema=False)
def frontend_index():
    return FileResponse(ROOT / "index.html")


app.mount("/css", StaticFiles(directory=ROOT / "css"), name="css")
app.mount("/js", StaticFiles(directory=ROOT / "js"), name="js")
app.mount("/data", StaticFiles(directory=ROOT / "data"), name="data")
