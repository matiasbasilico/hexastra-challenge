"""NASA AppEEARS point-sample client (Earthdata login from ~/.netrc).

API docs: https://appeears.earthdatacloud.nasa.gov/api/
Only the point-sample workflow is used: submit a task, poll until done,
download the result CSV. The token is never printed or written to disk.
"""
from __future__ import annotations

import csv
import io
import netrc
import time
from typing import Dict, Iterable, List, Optional, Sequence

import httpx

API = "https://appeears.earthdatacloud.nasa.gov/api"
URS = "urs.earthdata.nasa.gov"
POLL_SECONDS = 30
MAX_WAIT_SECONDS = 3 * 3600


class AppEEARSError(RuntimeError):
    pass


def login(timeout: float = 60.0) -> str:
    auth = netrc.netrc().authenticators(URS)
    if not auth:
        raise AppEEARSError("No hay credenciales de %s en ~/.netrc" % URS)
    user, _, password = auth
    r = httpx.post("%s/login" % API, auth=(user, password), timeout=timeout)
    if r.status_code != 200:
        raise AppEEARSError("Login AppEEARS falló: HTTP %s" % r.status_code)
    return r.json()["token"]


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": "Bearer %s" % token}


def submit_point_task(
    token: str,
    name: str,
    product: str,
    layers: Sequence[str],
    points: Iterable[Dict[str, object]],
    start: str,
    end: str,
) -> str:
    """Submit a point task. Dates are MM-DD-YYYY as AppEEARS expects."""
    payload = {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start, "endDate": end}],
            "layers": [{"product": product, "layer": layer} for layer in layers],
            "coordinates": list(points),
        },
    }
    r = httpx.post("%s/task" % API, json=payload, headers=_headers(token), timeout=120.0)
    if r.status_code not in (200, 202):
        raise AppEEARSError("submit %s: HTTP %s %s" % (name, r.status_code, r.text[:300]))
    return r.json()["task_id"]


def find_task(token: str, name: str) -> Optional[str]:
    """Most recent non-failed task with this name (lets fetch resume after a network cut)."""
    r = httpx.get("%s/task" % API, headers=_headers(token), timeout=60.0)
    r.raise_for_status()
    for task in r.json():
        if task.get("task_name") == name and task.get("status") not in ("error", "expired"):
            return task["task_id"]
    return None


def _status(token: str, task_id: str) -> Optional[str]:
    try:
        r = httpx.get("%s/task/%s" % (API, task_id), headers=_headers(token), timeout=60.0)
        r.raise_for_status()
    except httpx.HTTPError:
        return None  # transient network error: poll again
    return r.json().get("status")


def wait(token: str, task_id: str) -> None:
    waited = 0
    while waited <= MAX_WAIT_SECONDS:
        status = _status(token, task_id)
        if status == "done":
            return
        if status in ("error", "expired"):
            raise AppEEARSError("tarea %s terminó con estado %s" % (task_id, status))
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    raise AppEEARSError("tarea %s no terminó en %s s" % (task_id, MAX_WAIT_SECONDS))


def download_results_csv(token: str, task_id: str) -> str:
    """Return the text of the per-product results CSV of a finished point task."""
    r = httpx.get("%s/bundle/%s" % (API, task_id), headers=_headers(token), timeout=60.0)
    r.raise_for_status()
    files = r.json().get("files") or []
    csvs = [f for f in files if f["file_name"].endswith("-results.csv")]
    if not csvs:
        raise AppEEARSError("tarea %s sin CSV de resultados" % task_id)
    f = csvs[0]
    d = httpx.get(
        "%s/bundle/%s/%s" % (API, task_id, f["file_id"]),
        headers=_headers(token), timeout=600.0, follow_redirects=True,
    )
    d.raise_for_status()
    return d.text


def parse_csv(text: str) -> List[Dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))
