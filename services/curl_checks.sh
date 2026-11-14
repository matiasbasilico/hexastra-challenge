#!/usr/bin/env bash
set -euo pipefail
echo "== planetary /health =="
curl -sS http://127.0.0.1:8766/health | python3 -m json.tool | head
echo "== planetary /sites?body=moon =="
curl -sS "http://127.0.0.1:8766/sites?body=moon" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['n'], [s['id'] for s in d['sites']])"
echo "== planetary vector shackleton-rim =="
curl -sS http://127.0.0.1:8766/sites/shackleton-rim/vector | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['id'], d['body'], {k:v['available'] for k,v in d['components'].items()})"
echo "== earth /health =="
curl -sS http://127.0.0.1:8767/health | python3 -m json.tool | head
echo "== earth /featured =="
curl -sS http://127.0.0.1:8767/featured | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['n'], [s['id'] for s in d['sites']])"
echo "== earth /regions =="
curl -sS http://127.0.0.1:8767/regions | python3 -c "import sys,json;d=json.load(sys.stdin);print([(c['name'], [x['iso'] for x in c['countries']]) for c in d['continents']])"
echo "== earth /candidates country=AR =="
curl -sS "http://127.0.0.1:8767/candidates?continent=South%20America&country=AR" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['n'], [s['id'] for s in d['sites']])"
echo "== POST /tasi jezero top=5 =="
python3 - << 'PY'
import json, urllib.request
vec = json.load(urllib.request.urlopen("http://127.0.0.1:8766/sites/jezero/vector"))
req = urllib.request.Request(
    "http://127.0.0.1:8767/tasi",
    data=json.dumps({"target": vec, "gamma": 1, "top": 5}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
out = json.load(urllib.request.urlopen(req))
print("discarded", out.get("n_discarded_by_mask"), "scored", out.get("n_scored"))
for m in out.get("matches") or []:
    print(m["score"], m["site"]["id"], m["site"].get("country_iso"), m["coverage"]["available_components"])
PY
echo OK
