"""Rock abundance (areal % covered by rocks, from thermal unmixing) for component O.

Moon  LRO Diviner GDR L3 rock abundance, 128 px/deg, ±80° (Bandfield et al. 2011,
      JGR 116, E00H02, doi:10.1029/2011JE003866), PDS Geosciences. Mean of the
      pixels under the 49 points of the T grid (7x7 at 120 m, ~237 m pixels).
      Poleward of 80° there is no Diviner rock product: null.
Mars  TES rock abundance 8 px/deg (Nowicki & Christensen 2007, JGR 112, E05007) and
      Viking IRTM 1° (Christensen 1986, Icarus 68, 217) served as numbers by the ASU
      Mars Space Flight Facility WMS (JMARS). No gridded rock product exists in PDS.
      TES uses 0 as "no data", so a 0 is stored as null.
Earth No product measures the same quantity (two-component thermal unmixing). Apparent
      thermal inertia from ASTER/MODIS is a different quantity driven by moisture and
      vegetation, so Earth stays null.

Pure helpers (pixel indices, VICAR parsing) are unit-tested; readers use HTTP ranges.
"""
from __future__ import annotations

import math
import re
import struct
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import httpx

UA = {"User-Agent": "Mozilla/5.0 (HexastraAnalogos/0.1; NASA Space Apps 2026 prototype)"}
WHEN = "14 de noviembre de 2026 (America/Buenos_Aires)"

DIVINER_BASE = ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
                "data_derived_gdr_l3/cylindrical/img/")
DIVINER_128 = DIVINER_BASE + "dgdr_ra_avg_cyl_128_img.img"
DIVINER_032 = DIVINER_BASE + "dgdr_ra_avg_cyl_032_img.img"
DIVINER = {  # name: (url, px/deg, max |lat|, samples per line)
    "128": (DIVINER_128, 128, 80.0, 46080),
    "032": (DIVINER_032, 32, 60.0, 11520),
}
DIVINER_NODATA = -32768
DIVINER_SCALE = 0.001  # DN * 0.001 = rock fraction

ASU_WMS = "http://ms-mars.mars.asu.edu/"
MARS_LAYERS = {
    "tes": ("tes_rock_abundance_numeric", 8,
            "TES rock abundance (Nowicki & Christensen 2007, JGR 112, E05007, doi:10.1029/2006JE002798), "
            "8 px/deg, % entero; roca = material con inercia térmica ≥ 1250 J m⁻² K⁻¹ s⁻½"),
    "irtm": ("VI_blocks_numeric", 8,
             "Viking IRTM rock abundance (Christensen 1986, Icarus 68, 217–238, doi:10.1016/0019-1035(86)90020-5), "
             "grilla de 1° remuestreada a 8 px/deg; rocas de más de ~0,1–0,15 m"),
}


# ------------------------------------------------------------------ pure helpers

def diviner_pixel(lat: float, lon: float, ppd: int, max_lat: float) -> Optional[Tuple[int, int]]:
    """(line, sample) of the Diviner GDR pixel containing (lat, lon east, any range); None outside."""
    if abs(lat) > max_lat:
        return None
    line = int(math.floor((max_lat - lat) * ppd))
    sample = int(math.floor((lon % 360.0) * ppd))
    return line, sample


def diviner_value(dn: int) -> Optional[float]:
    return None if dn == DIVINER_NODATA else dn * DIVINER_SCALE


def parse_vicar(blob: bytes) -> List[List[float]]:
    head = blob[:4000].decode("latin1")
    lbl = int(re.search(r"LBLSIZE=(\d+)", head).group(1))
    nl = int(re.search(r"\bNL=(\d+)", head).group(1))
    ns = int(re.search(r"\bNS=(\d+)", head).group(1))
    fmt = re.search(r"FORMAT='(\w+)'", head).group(1)
    code = {"FULL": "i", "REAL": "f", "HALF": "h", "BYTE": "B", "DOUB": "d"}[fmt]
    size = struct.calcsize(code)
    vals = struct.unpack("<%d%s" % (nl * ns, code), blob[lbl:lbl + nl * ns * size])
    return [list(vals[i * ns:(i + 1) * ns]) for i in range(nl)]


def wms_cell_bbox(lat: float, lon: float, ppd: int) -> Tuple[float, float, float, float]:
    """Bounding box (lonW, latS, lonE, latN) of the ppd cell that contains the point, lon in -180..180."""
    lon = ((lon + 180.0) % 360.0) - 180.0
    x0 = math.floor(lon * ppd) / ppd
    y0 = math.floor(lat * ppd) / ppd
    return x0, y0, x0 + 1.0 / ppd, y0 + 1.0 / ppd


# ------------------------------------------------------------------ readers

def _range(client: httpx.Client, url: str, start: int, n: int) -> bytes:
    last: Optional[Exception] = None
    for _ in range(4):
        try:
            r = client.get(url, headers={"Range": "bytes=%d-%d" % (start, start + n - 1)}, follow_redirects=True)
            r.raise_for_status()
            if len(r.content) != n:
                raise RuntimeError("range returned %d bytes, expected %d" % (len(r.content), n))
            return r.content
        except Exception as exc:
            last = exc
    raise RuntimeError("%s: %s" % (url, last))


def diviner_mean(points: Sequence[Tuple[float, float]], product: str = "128",
                 client: Optional[httpx.Client] = None) -> Tuple[Optional[float], int]:
    """Mean rock fraction of the distinct pixels under the points, and how many were valid."""
    url, ppd, max_lat, ns = DIVINER[product]
    pix = {diviner_pixel(la, lo, ppd, max_lat) for la, lo in points}
    if None in pix:
        return None, 0
    own = client is None
    client = client or httpx.Client(timeout=60.0, headers=UA)
    try:
        vals = []
        for line, sample in sorted(pix):
            dn = struct.unpack("<h", _range(client, url, (line * ns + sample) * 2, 2))[0]
            v = diviner_value(dn)
            if v is not None:
                vals.append(v)
    finally:
        if own:
            client.close()
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


def mars_cell(lat: float, lon: float, layer_key: str, client: Optional[httpx.Client] = None) -> Optional[float]:
    """Rock abundance (%) of the 8 px/deg cell containing the point; None where the layer has 0 (no data)."""
    own = client is None
    client = client or httpx.Client(timeout=90.0, headers=UA)
    try:
        # the server rejects percent-encoded commas in BBOX, so the URL is built verbatim
        r = client.get(mars_url(layer_key, lat, lon), follow_redirects=True)
        r.raise_for_status()
        v = parse_vicar(r.content)[0][0]
    finally:
        if own:
            client.close()
    return None if v == 0 else float(v)


def mars_url(layer_key: str, lat: float, lon: float) -> str:
    layer, ppd, _ = MARS_LAYERS[layer_key]
    bbox = wms_cell_bbox(lat, lon, ppd)
    return ("%s?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&FORMAT=image/vicar&SRS=EPSG:4326&STYLES=&LAYERS=%s"
            "&WIDTH=1&HEIGHT=1&BBOX=%s" % (ASU_WMS, layer, ",".join("%.6f" % v for v in bbox)))


def diviner_global_mean_60(client: Optional[httpx.Client] = None) -> Tuple[float, float]:
    """Area-weighted mean rock fraction within ±60° from the 32 px/deg map (validation, ~88 MB)."""
    url, ppd, max_lat, ns = DIVINER["032"]
    nl = int(2 * max_lat * ppd)
    own = client is None
    client = client or httpx.Client(timeout=300.0, headers=UA)
    try:
        blob = client.get(url, follow_redirects=True).content
    finally:
        if own:
            client.close()
    import numpy as np

    arr = np.frombuffer(blob[: nl * ns * 2], dtype="<i2").reshape(nl, ns)
    lat = max_lat - (np.arange(nl) + 0.5) / ppd
    w = np.cos(np.radians(lat))[:, None] * np.ones((1, ns))
    ok = arr != DIVINER_NODATA
    mean = float((arr * DIVINER_SCALE * w)[ok].sum() / w[ok].sum())
    coverage = float(ok.mean())
    return mean, coverage


# ------------------------------------------------------------------ rows

EARTH_WHY = ("sin equivalente terrestre: ningún producto de NASA/ESA mide la fracción de área cubierta por rocas por "
             "separación térmica de dos componentes, como Diviner o TES; la inercia térmica aparente de ASTER/MODIS es "
             "otra magnitud (depende de humedad y vegetación) y no se usa como sustituto")

DIVINER_SRC = ("LRO Diviner GDR nivel 3, rock abundance promedio 2009–2016, 128 px/grado (~237 m), cilíndrico ±80° "
               "(Bandfield et al. 2011, JGR 116, E00H02, doi:10.1029/2011JE003866), PDS Geosciences, leído por rangos "
               "HTTP el %s. Valor = media de los píxeles bajo los 49 puntos de la grilla 7×7 a 120 m de T, DN × 0,001 × 100. %s"
               % (WHEN, DIVINER_128))
DIVINER_NOTE = ("Diviner detecta rocas de ~1 m o más; TES/IRTM en Marte usan otro tamaño de corte, así que Luna y Marte "
                "no son estrictamente la misma magnitud.")


def rock_rows(site: Dict[str, Any], row: Callable[..., Dict[str, Any]], points: Sequence[Tuple[float, float]]) -> List[Dict[str, Any]]:
    sid, body = site["id"], site["body"]
    if body == "earth":
        return [row(sid, "rock_abundance_pct", None, "percent", "unavailable", "sin fuente equivalente",
                    EARTH_WHY + " (a completar si aparece un producto comparable)", False)]
    if body == "moon":
        if abs(float(site["lat"])) > DIVINER[("128")][2]:
            return [row(sid, "rock_abundance_pct", None, "percent", "unavailable", DIVINER_128,
                        "Diviner no publica abundancia de rocas al sur de 80° (GDR ±80°, GHRM ±70°; los productos polares "
                        "son solo de temperatura): sin dato (a completar)")]
        try:
            mean, n = diviner_mean(points)
        except Exception as exc:
            return [row(sid, "rock_abundance_pct", None, "percent", "placeholder", DIVINER_128,
                        "lectura fallida: %s (a completar)" % exc)]
        if mean is None:
            return [row(sid, "rock_abundance_pct", None, "percent", "placeholder", DIVINER_128,
                        "píxeles sin dato en Diviner (a completar)")]
        return [row(sid, "rock_abundance_pct", round(mean * 100.0, 3), "percent", "derived",
                    DIVINER_SRC, DIVINER_NOTE + " Píxeles válidos: %d." % n)]
    out = []
    for key, feature in (("tes", "rock_abundance_pct"), ("irtm", "rock_abundance_irtm_pct")):
        layer, _ppd, desc = MARS_LAYERS[key]
        url = mars_url(key, float(site["lat"]), float(site["lon"]))
        try:
            v = mars_cell(float(site["lat"]), float(site["lon"]), key)
        except Exception as exc:
            out.append(row(sid, feature, None, "percent", "placeholder", url, "lectura fallida: %s (a completar)" % exc))
            continue
        src = ("%s. Celda de 8 px/grado (~7,4 km) que contiene el punto, leída como número del servidor WMS del ASU "
               "Mars Space Flight Facility (JMARS, capa %s) el %s; PDS no tiene una grilla de abundancia de rocas. %s"
               % (desc, layer, WHEN, url))
        scale = ("Escala: la celda es mucho mayor que la grilla de 720 m de T; describe la región, no el punto. "
                 "TES (roca = inercia ≥ 1250) e IRTM (rocas > ~0,1–0,15 m) y Diviner (~1 m) usan definiciones distintas.")
        if v is None:
            out.append(row(sid, feature, None, "percent", "unavailable", src,
                           "la capa vale 0 en esta celda, que en este producto significa sin dato (a completar)"))
        else:
            out.append(row(sid, feature, round(v, 2), "percent", "derived", src, scale))
    return out
