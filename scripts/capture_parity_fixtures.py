#!/usr/bin/env python3
"""Read-only capture of numerical API parity fixtures after reviewed data updates."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
import json
import argparse
parser=argparse.ArgumentParser(description='Capture independent ranking expectations from the verified Python reference API.')
parser.add_argument('--earth-url',default='http://127.0.0.1:8767')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
method=json.loads((root/'data/cloudflare/earth/method.json').read_text())
targets=json.loads((root/'data/cloudflare/planetary/sites.json').read_text())
cases=[]
for i,target in enumerate(targets):
 vector=json.loads((root/'data/cloudflare/planetary/vectors'/ (target['id']+'.json')).read_text())
 for j,preset in enumerate(method['presets']):
  region=[{}, {'country':'AR'}, {'continent':'Africa'}, {'country':'US'}][(i+j)%4]
  cases.append({'name':target['id']+'/'+preset['id'],'request':{'target':vector,'weights':preset['weights'],'gamma':[1,.75,3,.1][j],'top':60,'apply_mask':(i+j)%2==0,**region}})
vector=json.loads((root/'data/cloudflare/planetary/vectors/arsia-mons.json').read_text())
for name,changes in [('zero-weights',{'weights':dict.fromkeys(['G','T','E','V','O'],0)}),('empty-country',{'country':'ZZ'}),('vo-alias',{'weights':{'Vo':2,'G':0,'T':.3,'E':0,'O':0}}),('unscored-geology',{'target':json.loads((root/'data/cloudflare/planetary/vectors/jezero.json').read_text()),'weights':{'G':1,'T':0,'E':0,'V':0,'O':0}})]:
 cases.append({'name':name,'request':{'target':vector,'gamma':.75,'top':60,'apply_mask':True,**changes}})
def fetch(case):
 req=Request(args.earth_url.rstrip('/')+'/tasi',data=json.dumps(case['request']).encode(),headers={'Content-Type':'application/json'})
 with urlopen(req,timeout=60) as r:result=json.load(r)
 def signature(d):
  return {k:d[k] for k in ['n_candidates','n_discarded_by_mask','n_scored','scales','filter']} | {'discarded':[x['id'] for x in d['discarded']], 'matches':[{k:m[k] for k in ['site','score','score_0_1','weights','coverage','mask']} | {'components':{k:{kk:v[kk] for kk in ['score','score_0_1','available','data_available']} for k,v in m['components'].items()}} for m in d['matches']]}
 return {'name':case['name'],'request':{k:v for k,v in case['request'].items() if k!='target'} | {'target_id':case['request']['target']['id']},'expected':signature(result)}
with ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(fetch,cases))
path=root/'pages/tests/fixtures/reference-parity.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n')
print('Reference cases:',len(out),'bytes',path.stat().st_size)
