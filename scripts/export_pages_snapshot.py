#!/usr/bin/env python3
"""Export a verified, read-only API snapshot for the standalone Cloudflare demo.

No database connections, loads, or exports are performed. Numeric component
values come from the running reference APIs. Weights and terrain gamma remain
adjustable in the edge implementation; original source records are retained.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

def request(base, path, payload=None):
    raw = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    req = Request(base.rstrip('/') + path, data=raw, headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=60) as response:
        return json.load(response)

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
    path.write_bytes(raw)
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--planetary-url', default='http://127.0.0.1:8766')
    parser.add_argument('--earth-url', default='http://127.0.0.1:8767')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/cloudflare')
    args = parser.parse_args()
    output = args.output
    planetary, earth = args.planetary_url, args.earth_url
    generated = datetime.now(timezone.utc).isoformat()
    health = {name: request(base, '/health') for name,base in [('planetary',planetary),('earth',earth)]}
    if not all(item.get('ok') for item in health.values()):
        raise SystemExit('Reference APIs must both report healthy before export.')
    catalog = request(earth, '/candidates')
    targets = request(planetary, '/sites')
    if isinstance(targets,dict): targets = targets['sites']
    assert len(catalog['sites']) == health['earth']['n_sites']
    assert len(targets) == health['planetary']['n_sites']
    with ThreadPoolExecutor(max_workers=6) as pool:
        details = list(pool.map(lambda s: request(earth, '/candidates/' + s['id']), catalog['sites']))
        vectors = list(pool.map(lambda s: request(planetary, '/sites/' + s['id'] + '/vector'), targets))
        target_details = list(pool.map(lambda s: request(planetary, '/sites/' + s['id']), targets))
    method = request(earth,'/method')
    method['catalog']['origin'] = 'cloudflare_snapshot'
    method['catalog']['snapshot_generated_at'] = generated
    meta = {'version':1, 'generated_at':generated, 'n_earth':len(details), 'n_targets':len(vectors),
            'catalog_origin':'cloudflare_snapshot',
            'reference_catalog_origins':{k:v.get('catalog_origin') for k,v in health.items()},
            'reference_formula':'Unchanged TASI; shared components, weight renormalization, exp(-gamma * D_M).',
            'source_policy':'API measurements and citations are exported unchanged; no values are invented.'}
    files = {}
    scale_keys = ['temp_mean','temp_diurnal_range','illumination_pct','precip_mm','water_ice_indicator']
    scale_inputs = {s['id']:{k:(s.get('features',{}).get(k) or {}).get('value') for k in scale_keys} for s in details}
    files['earth/scale-inputs.json'] = write(output/'earth/scale-inputs.json',scale_inputs)
    files['earth/candidates.json'] = write(output/'earth/candidates.json',catalog)
    for d in details:
        files['earth/sites/'+d['id']+'.json'] = write(output/'earth/sites'/ (d['id']+'.json'),d)
    for name in ['regions','featured','examples','openapi.json']:
        files['earth/'+name+'.json'] = write(output/'earth'/ (name+'.json'),request(earth,'/'+name))
    files['earth/method.json'] = write(output/'earth/method.json',method)
    files['planetary/sites.json'] = write(output/'planetary/sites.json',targets)
    for d in target_details:
        files['planetary/sites/'+d['id']+'.json'] = write(output/'planetary/sites'/ (d['id']+'.json'),d)
    for v in vectors:
        files['planetary/vectors/'+v['id']+'.json'] = write(output/'planetary/vectors'/ (v['id']+'.json'),v)
    for name in ['bodies','features','sources','openapi.json']:
        files['planetary/'+name+'.json'] = write(output/'planetary'/ (name+'.json'),request(planetary,'/'+name))
    # Stable candidate order matters for identical tie-breaking and metadata.
    ordered_ids = [s['id'] for s in catalog['sites']]
    def export_pairs(vector):
        result = request(earth,'/tasi', {'target':vector,'gamma':1,'top':len(details),'apply_mask':False})
        assert len(result['matches']) == len(details)
        by_id = {m['site']['id']:m for m in result['matches']}
        result['matches'] = [by_id[sid] for sid in ordered_ids]
        for match in result['matches']:
            # Verbose source dictionaries remain available through the site and
            # vector endpoints; avoid repeating them in all 840 pair records.
            for key in ['G','O']:
                detail = match['components'][key]['detail']
                for redundant in ['target_metrics','candidate_metrics','metrics']:
                    detail.pop(redundant,None)
        return vector['id'],result
    with ThreadPoolExecutor(max_workers=4) as pool:
        for target_id,result in pool.map(export_pairs,vectors):
            name='pairs/'+target_id+'.json';files[name]=write(output/name,result)
    meta['files']=files
    write(output/'manifest.json',meta)
    total=sum(item['bytes'] for item in files.values())
    print(json.dumps({'n_earth':len(details),'n_targets':len(vectors),'pairs':len(details)*len(vectors),'files':len(files)+1,'bytes':total,'output':str(output)},indent=2))

if __name__ == '__main__':
    main()
