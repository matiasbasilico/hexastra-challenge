-- HexAstra: catálogo de sitios y mediciones con procedencia por valor.
-- La base se reconstruye entera desde archivos versionados (db/load.py):
-- los catálogos base de cada servicio + data/measurements/*.jsonl.

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS measurements;
DROP TABLE IF EXISTS feature_defs;
DROP TABLE IF EXISTS sites;
DROP TABLE IF EXISTS catalog_meta;

CREATE TABLE sites (
    id          text PRIMARY KEY,
    body        text NOT NULL CHECK (body IN ('earth', 'moon', 'mars')),
    name        text NOT NULL,
    short_name  text,
    lat         double precision NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lon         double precision NOT NULL CHECK (lon BETWEEN -180 AND 180),
    -- Solo para la Tierra: SRID 4326 es un datum terrestre.
    geom        geography(Point, 4326),
    attrs       jsonb NOT NULL DEFAULT '{}'::jsonb,   -- resto del registro (coord_source, summary, país, featured…)
    position    integer NOT NULL,                     -- orden original del catálogo
    CHECK ((body = 'earth') = (geom IS NOT NULL))
);

CREATE TABLE feature_defs (
    service  text NOT NULL CHECK (service IN ('earth', 'planetary')),
    id       text NOT NULL,
    payload  jsonb NOT NULL,
    PRIMARY KEY (service, id)
);

CREATE TABLE measurements (
    site_id       text NOT NULL REFERENCES sites (id) ON DELETE CASCADE,
    feature       text NOT NULL,
    value         double precision,
    unit          text,
    quality       text NOT NULL,
    is_real       boolean NOT NULL,
    source        text,
    note          text,
    comparable    boolean,
    method        text,
    retrieved_at  date,
    dataset       text NOT NULL,   -- 'base:earth', 'base:planetary' o el .jsonl de origen
    PRIMARY KEY (site_id, feature),
    CHECK (value IS NOT NULL OR quality IN ('placeholder', 'unavailable')),
    CHECK (NOT is_real OR value IS NOT NULL)
);

CREATE INDEX measurements_feature_idx ON measurements (feature);
CREATE INDEX sites_body_idx ON sites (body);
CREATE INDEX sites_geom_idx ON sites USING gist (geom);

CREATE TABLE catalog_meta (
    service  text PRIMARY KEY CHECK (service IN ('earth', 'planetary')),
    meta     jsonb NOT NULL,
    extra    jsonb NOT NULL DEFAULT '{}'::jsonb      -- p. ej. la covarianza de earth
);
