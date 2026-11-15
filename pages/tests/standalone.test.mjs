import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {rankSnapshot,standalone,round2} from '../lib/standalone.mjs';
const root=new URL('../../',import.meta.url);
const json=async path=>JSON.parse(await fs.readFile(new URL(path,root),'utf8'));
const candidates=await json('data/cloudflare/earth/candidates.json');
const inputs=await json('data/cloudflare/earth/scale-inputs.json');
const cases=await json('pages/tests/fixtures/reference-parity.json');
function close(actual,expected,path=''){
  if(typeof expected==='number'){assert.equal(typeof actual,'number',path);assert.ok(Math.abs(actual-expected)<=1e-11,`${path}: ${actual} versus ${expected}`);return;}
  if(expected===null || typeof expected!=='object'){assert.equal(actual,expected,path);return;}
  if(Array.isArray(expected)){assert.equal(actual.length,expected.length,path+'.length');expected.forEach((v,i)=>close(actual[i],v,path+'['+i+']'));return;}
  for(const [k,v] of Object.entries(expected))close(actual[k],v,path+'.'+k);
}
for(const fixture of cases){
  test('Python API parity: '+fixture.name,async()=>{
    const pair=await json('data/cloudflare/pairs/'+fixture.request.target_id+'.json');
    const before=JSON.stringify(pair);
    const result=rankSnapshot(pair,candidates.sites,inputs,fixture.request);
    close({...result,discarded:result.discarded.map(s=>s.id)},fixture.expected,fixture.name);
    assert.equal(JSON.stringify(pair),before,'Cached reference evidence must stay immutable.');
  });
}
const env={ASSETS:{async fetch(request){
  const path=new URL(request.url).pathname.slice(1);
  try{return new Response(await fs.readFile(new URL(path,root)));}catch(_){return new Response('Not found',{status:404});}
}}};
const call=async(service,path,body)=>standalone({request:new Request('https://hexastra.pages.dev/api/'+service+'/'+path,body?{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}:{}),params:{service,path:path.split('?')[0].split('/')},env});
test('Health is independent of local services and tunnels',async()=>{
  for(const service of ['earth','planetary']){
    const res=await call(service,'health');assert.equal(res.status,200);const h=await res.json();
    assert.equal(h.catalog_origin,'cloudflare_snapshot');assert.equal(h.requires_local_services,false);
  }
});
test('Unknown resources, invalid vectors and filters are rejected honestly',async()=>{
  assert.equal((await call('earth','candidates/not-a-site')).status,404);
  assert.equal((await call('earth','candidates?country=Argentina')).status,400);
  assert.equal((await call('earth','tasi',{target_id:'not-a-target'})).status,400);
  const vector=await json('data/cloudflare/planetary/vectors/arsia-mons.json');
  vector.components.T.metrics.slope_deg.value+=1;
  assert.equal((await call('earth','tasi',{target:vector})).status,422);
});
test('Live endpoint shape supports browser POST, GET, and original detail records',async()=>{
  const vector=await json('data/cloudflare/planetary/vectors/arsia-mons.json');
  const post=await call('earth','tasi',{target:vector,top:60,country:'AR',gamma:.75});
  assert.equal(post.status,200);assert.equal((await post.json()).target.id,'arsia-mons');
  const get=await call('earth','tasi?target_id=arsia-mons&gamma=0.75&country=AR&top=60');
  assert.equal(get.status,200);
  const detail=await call('earth','candidates/laguna-antofagasta');
  assert.deepEqual(await detail.json(),await json('data/cloudflare/earth/sites/laguna-antofagasta.json'));
});
test('Region scaling uses the entire region before masking, and empty regions remain valid',async()=>{
  const pair=await json('data/cloudflare/pairs/arsia-mons.json');
  const a=rankSnapshot(pair,candidates.sites,inputs,{country:'AR'}),b=rankSnapshot(pair,candidates.sites,inputs,{country:'AR',apply_mask:false});
  assert.deepEqual(a.scales,b.scales);
  assert.notEqual(a.scales.temp_mean,pair.scales.temp_mean);
  assert.equal(rankSnapshot(pair,candidates.sites,inputs,{country:'ZZ'}).matches.length,0);
});
test('Python rounding at exact half cases is retained',()=>{
  assert.equal(round2(.125),.12);assert.equal(round2(.375),.38);assert.equal(round2(2.675),2.67);
});
test('Planetary list retains the object envelope consumed by getTargets()',async()=>{
  for(const body of ['moon','mars']){
    const res=await call('planetary','sites?body='+body),data=await res.json();
    assert.equal(data.n,7);assert.equal(data.body,body);assert.equal(data.sites.length,7);
    assert.ok(data.sites.every(s=>s.body===body));
  }
});
