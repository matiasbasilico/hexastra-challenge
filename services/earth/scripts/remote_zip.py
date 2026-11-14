"""Extract single members of a remote ZIP using HTTP Range requests.

The USGS geologic-map packages are large (Moon 224 MB, Mars 809 MB) and the
hosts reset long connections. We only need a few shapefile members, so we read
the ZIP central directory and download just those byte ranges, in chunks, with
retries. Results are cached on disk.
"""
from __future__ import annotations

import io
import struct
import time
import zipfile
import zlib
from pathlib import Path
from typing import Dict, Iterable

import httpx

CHUNK = 4 * 1024 * 1024
RETRIES = 8


def _get_range(client: httpx.Client, url: str, start: int, end: int) -> bytes:
    """Bytes [start, end] inclusive, retrying on connection resets."""
    last_exc = None
    for attempt in range(RETRIES):
        try:
            resp = client.get(url, headers={"Range": "bytes=%d-%d" % (start, end)}, timeout=120)
            if resp.status_code != 206:
                raise RuntimeError("HTTP %s pidiendo un rango de %s" % (resp.status_code, url))
            data = resp.content
            if len(data) != end - start + 1:
                raise RuntimeError("rango incompleto (%d de %d bytes)" % (len(data), end - start + 1))
            return data
        except (httpx.TransportError, RuntimeError) as exc:
            last_exc = exc
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError("no se pudo bajar %s [%d-%d]: %s" % (url, start, end, last_exc))


def _fetch(client: httpx.Client, url: str, start: int, length: int) -> bytes:
    parts = []
    pos = start
    stop = start + length
    while pos < stop:
        end = min(stop, pos + CHUNK) - 1
        parts.append(_get_range(client, url, pos, end))
        pos = end + 1
    return b"".join(parts)


class _RangeFile(io.RawIOBase):
    """Seekable file over HTTP ranges; used only to parse the central directory."""

    def __init__(self, client: httpx.Client, url: str):
        self.client, self.url, self.pos = client, url, 0
        self.size = int(client.head(url, follow_redirects=True).headers["content-length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (self.pos + offset if whence == 1 else self.size + offset)
        return self.pos

    def readinto(self, buf):
        if self.pos >= self.size:
            return 0
        end = min(self.size, self.pos + len(buf)) - 1
        data = _get_range(self.client, self.url, self.pos, end)
        buf[: len(data)] = data
        self.pos += len(data)
        return len(data)


def extract_members(url: str, members: Iterable[str], cache_dir: Path) -> Dict[str, Path]:
    """Download and inflate the given ZIP members into cache_dir (kept between runs)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    wanted = list(members)
    out = {m: cache_dir / Path(m).name for m in wanted}
    missing = [m for m in wanted if not out[m].exists()]
    if not missing:
        return out
    with httpx.Client(follow_redirects=True) as client:
        directory = zipfile.ZipFile(io.BufferedReader(_RangeFile(client, url), buffer_size=1 << 16))
        infos = {i.filename: i for i in directory.infolist()}
        for name in missing:
            if name not in infos:
                raise KeyError("%s no está en %s" % (name, url))
            info = infos[name]
            header = _get_range(client, url, info.header_offset, info.header_offset + 29)
            name_len, extra_len = struct.unpack("<HH", header[26:30])
            data_start = info.header_offset + 30 + name_len + extra_len
            raw = _fetch(client, url, data_start, info.compress_size)
            if info.compress_type == zipfile.ZIP_DEFLATED:
                raw = zlib.decompress(raw, -15)
            elif info.compress_type != zipfile.ZIP_STORED:
                raise RuntimeError("compresión %s no soportada" % info.compress_type)
            if zlib.crc32(raw) & 0xFFFFFFFF != info.CRC:
                raise RuntimeError("CRC distinto para %s" % name)
            tmp = out[name].with_suffix(out[name].suffix + ".part")
            tmp.write_bytes(raw)
            tmp.replace(out[name])
    return out
