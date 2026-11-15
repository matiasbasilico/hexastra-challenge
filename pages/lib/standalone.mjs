/** Standalone TASI runtime for the verified catalog. No tunnels or database.
 * Geological/terrain evidence is exported by the unchanged Python reference.
 * Recompute exp(-gamma * D_M), regional E/V scales, and normalized weights.
 * Full measurements and citations remain at candidate/vector detail endpoints.
 */
const KEYS=['G','T','E','V','O'];
const FALLBACK={temp_mean:20,temp_diurnal_range:10,illumination_pct:20,precip_mm:200,water_ice_indicator:.5};
const cache=new Map();
function response(value,status=200){return new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','access-control-allow-origin':'*','x-hexastra-runtime':'cloudflare-standalone'}});}
function failure(message,status=400){return response({detail:message},status);}
async function asset(env,url,path){
  const key=url.origin+path;
  if(!cache.has(key)){
    if(cache.size>24)cache.delete(cache.keys().next().value);
    cache.set(key,env.ASSETS.fetch(new Request(new URL('/data/cloudflare/'+path,url))).then(async r=>{if(!r.ok)throw new Error('Verified snapshot asset unavailable: '+path);return r.json();}).catch(e=>{cache.delete(key);throw e;}));
  }
  return cache.get(key);
}
// Python round(...,2) uses ties-to-even for exact binary half cases.
export function round2(n){
  const scaled=n*100,lo=Math.floor(scaled);
  if(Number.isInteger(n*8) && scaled-lo===.5)return (lo%2===0?lo:lo+1)/100;
  return Number(n.toFixed(2));
}
export function normalizeWeights(weights,available){
  const requested=Object.fromEntries(KEYS.map(k=>[k,.2]));
  for(const [raw,v] of Object.entries(weights || {})){
    const k=['Vo','VO'].includes(raw)?'V':raw;
    if(KEYS.includes(k) && v!=null){if(!Number.isFinite(Number(v)))throw new Error('Weights must be finite numbers.');requested[k]=Math.max(0,Number(v));}
  }
  const used=Object.fromEntries(KEYS.filter(k=>available[k] && requested[k]>0).map(k=>[k,requested[k]]));
  const sum=Object.values(used).reduce((a,b)=>a+b,0);
  if(sum<=0)return {requested,used:{},renormalized:{},note:'No available components with positive weight.'};
  const renormalized=Object.fromEntries(Object.entries(used).map(([k,v])=>[k,v/sum]));
  const skipped=KEYS.filter(k=>!(k in renormalized));
  return {requested,used,renormalized,skipped,note:skipped.length?'Weights renormalized over components that returned a score.':'All requested components available.'};
}
export function earthScales(sites,inputs){
  return Object.fromEntries(Object.entries(FALLBACK).map(([k,fallback])=>{
    const values=sites.map(s=>inputs[s.id]?.[k]).filter(v=>typeof v==='number' && Number.isFinite(v));
    if(values.length<2)return [k,fallback];
    const mean=values.reduce((a,b)=>a+b,0)/values.length;
    const std=Math.sqrt(values.reduce((sum,v)=>sum+(v-mean)**2,0)/(values.length-1));
    return [k,std>1e-6?std:fallback];
  }));
}
function filterSites(sites,continent,country){
  return sites.filter(s=>(!continent || (s.continent || '').toLowerCase()===continent.trim().toLowerCase()) && (!country || (s.country_iso || '').toUpperCase()===country.trim().toUpperCase()));
}
const numberFormats=new Map();
function numberES(n,digits=1){if(!numberFormats.has(digits))numberFormats.set(digits,new Intl.NumberFormat('es-AR',{maximumFractionDigits:digits}));return numberFormats.get(digits).format(Number(n)).replace(/-/g,'−');}
function explanation(match){
  const labels={G:'geología (G)',T:'terreno (T)',E:'clima e iluminación (E)',V:'volátiles o hielo (V)',O:'operación (O)'};
  const scored=KEYS.filter(k=>match.components[k].available && match.components[k].score!=null).sort((a,b)=>match.components[b].score-match.components[a].score);
  const missing=KEYS.filter(k=>!scored.includes(k) && !match.components[k].data_available).map(k=>labels[k][0].toUpperCase()+labels[k].slice(1));
  function line(k,best){
    const c=match.components[k],d=c.detail || {},head=labels[k]+', '+numberES(c.score)+' de 100';
    if(k==='G'){
      const names=Object.keys(d.blocks || {}).map(k=>({composition:'tipo de roca',impact:'origen por impacto'}[k]));
      return head+': se comparan '+names.join(' y ')+` (${names.length} de 2 bloques geológicos).`;
    }
    if(k==='T'){
      const names=(d.used || []).map(k=>({relative_relief_m:'relieve relativo',slope_deg:'pendiente',roughness_m:'rugosidad'}[k] || k));
      const joined=names.length>1?names.slice(0,-1).join(', ')+' y '+names.at(-1):(names[0] || 'relieve');
      return head+': '+joined+(best?' parecidos':' se alejan')+(d.D_M==null?'':` (distancia de Mahalanobis ${numberES(d.D_M,2)})`)+'.';
    }
    const parts=(d.parts || []).filter(p=>p.s!=null).slice().sort((a,b)=>best?b.s-a.s:a.s-b.s),p=parts[0];
    if(!p)return head+'.';
    const [name,unit]=({temp_mean:['temperatura media','°C'],temp_diurnal_range:['amplitud térmica diaria','°C'],illumination_pct:['iluminación','%'],precip_mm:['precipitación anual','mm'],water_ice_indicator:['indicador de hielo','']}[p.metric] || [p.metric,'']);
    const suffix=unit?(unit==='%'?'%':' '+unit):'';
    return `${head}: ${name} ${numberES(p.y)}${suffix} en la Tierra frente a ${numberES(p.x)}${suffix} en el destino${p.metric==='precip_mm' && p.x===0?' (convención para un cuerpo sin lluvia)':''}.`;
  }
  return {why:scored.length?'Lo más parecido es '+line(scored[0],true):null,breaks:scored.length>1?'Lo menos parecido es '+line(scored.at(-1),false):scored.length?'Hay un solo componente con dato: no alcanza para decir en qué se separa.':'Ningún componente tiene dato en los dos lados: no se puede decir en qué se parece.',missing,explain_source:'cloudflare-standalone, a partir de components'};
}
export function rankSnapshot(pair,candidates,inputs,{weights,gamma=1,top=5,apply_mask=true,continent=null,country=null}={}){
  const filtered=filterSites(candidates,continent,country),ids=new Set(filtered.map(s=>s.id)),scales=earthScales(filtered,inputs),discarded=[],matches=[];
  for(const reference of pair.matches){
    if(!ids.has(reference.site.id))continue;
    if(apply_mask && !reference.mask.viable){const s=reference.site;discarded.push({id:s.id,name:s.name,continent:s.continent,country_iso:s.country_iso,mask:reference.mask});continue;}
    const components={};
    for(const k of KEYS){
      const source=reference.components[k],detail={...source.detail};let value=source.score_0_1;
      if(k==='T' && source.available && detail.D_M!=null){value=Math.exp(-gamma*detail.D_M);detail.score=value;detail.gamma=gamma;}
      if((k==='E' || k==='V') && detail.parts?.length){
        detail.parts=detail.parts.map(p=>({...p,scale:scales[p.metric] || 1,s:Math.exp(-Math.abs(p.x-p.y)/(scales[p.metric] || 1))}));
        value=detail.parts.reduce((sum,p)=>sum+p.s,0)/detail.parts.length;detail.score=value;
      }
      components[k]={...source,score:value==null?null:round2(value*100),score_0_1:value,detail};
    }
    const available=Object.fromEntries(KEYS.map(k=>[k,!!components[k].available && components[k].score_0_1!=null]));
    const normalized=normalizeWeights(weights,available);
    const used=Object.keys(normalized.renormalized);
    const value=used.length?used.reduce((sum,k)=>sum+normalized.renormalized[k]*components[k].score_0_1,0):null;
    const m={site:reference.site,score:value==null?null:round2(value*100),score_0_1:value,components,weights:normalized,coverage:reference.coverage,mask:reference.mask};
    matches.push({...m,...explanation(m)});
  }
  // Match the reference engine's numeric and codepoint tie-breaking exactly.
  matches.sort((a,b)=>((a.score==null?-1:-a.score)-(b.score==null?-1:-b.score)) || (a.site.name<b.site.name?-1:a.site.name>b.site.name?1:0));
  return {index:pair.index,formula:pair.formula,gamma,apply_mask,target:pair.target,n_candidates:filtered.length,n_discarded_by_mask:discarded.length,n_scored:matches.length,matches:matches.slice(0,Math.max(1,Math.trunc(top || 5))),discarded,scales,filter:{continent,country:country?country.toUpperCase():null}};
}
function sameData(a,b){
  if(a===b)return true;
  if(a==null || b==null || typeof a!==typeof b)return false;
  if(typeof a!=='object')return false;
  const keys=Object.keys(a);
  return keys.length===Object.keys(b).length && keys.every(k=>Object.prototype.hasOwnProperty.call(b,k) && sameData(a[k],b[k]));
}
export async function standalone({request,params,env}){
  const service=params.service,url=new URL(request.url),path=Array.isArray(params.path)?params.path.join('/'):params.path || '';
  if(!['earth','planetary'].includes(service))return failure('Unknown service.',404);
  if(request.method==='OPTIONS')return new Response(null,{status:204,headers:{'access-control-allow-origin':'*','access-control-allow-methods':'GET, POST, OPTIONS','access-control-allow-headers':'content-type'}});
  if(!['GET','HEAD','POST'].includes(request.method))return failure('Method not allowed.',405);
  try{
    if(path==='health'){
      const meta=await asset(env,url,'manifest.json');
      return response({ok:true,service:service+'-service',n_sites:service==='earth'?meta.n_earth:meta.n_targets,catalog_origin:'cloudflare_snapshot',snapshot_generated_at:meta.generated_at,runtime:'cloudflare-pages-functions',requires_local_services:false});
    }
    if(path==='docs')return new Response(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>HexAstra ${service} API</title><body style="background:#070915;color:#f6f7fe;font:18px system-ui;max-width:60rem;margin:4rem auto;padding:1rem"><h1>HexAstra ${service} API</h1><p>Hosted entirely on Cloudflare. No local computer or tunnel is required.</p><p><a style="color:#65d0ea" href="openapi.json">OpenAPI contract (JSON)</a> · <a style="color:#65d0ea" href="health">Service health</a> · <a style="color:#65d0ea" href="/">Explore HexAstra</a></p><p>The hosted demonstration supports the verified catalog targets. Original measurement sources are available through site and vector endpoints. Ranking weights, region, masking, and terrain gamma remain adjustable.</p></body></html>`,{headers:{'content-type':'text/html; charset=utf-8'}});
    if(path==='openapi.json'){
      const schema=await asset(env,url,service+'/openapi.json.json');
      return response({...schema,servers:[{url:'/api/'+service}]});
    }
    if(service==='planetary'){
      if(path==='sites'){
        const sites=await asset(env,url,'planetary/sites.json'),body=url.searchParams.get('body');
        const filtered=body?sites.filter(s=>s.body===body):sites;
        return response({n:filtered.length,body,sites:filtered});
      }
      const match=/^sites\/([a-z0-9-]+)(\/vector)?$/.exec(path);
      if(match){
        const sites=await asset(env,url,'planetary/sites.json');
        if(!sites.some(s=>s.id===match[1]))return failure('Unknown target.',404);
        return response(await asset(env,url,`planetary/${match[2]?'vectors':'sites'}/${match[1]}.json`));
      }
      if(['bodies','features','sources'].includes(path))return response(await asset(env,url,'planetary/'+path+'.json'));
    }else{
      if(['regions','method','examples','featured'].includes(path))return response(await asset(env,url,'earth/'+path+'.json'));
      if(path==='candidates'){
        const data=await asset(env,url,'earth/candidates.json'),continent=url.searchParams.get('continent'),country=url.searchParams.get('country');
        if(country && country.trim().length!==2)return failure('country must be an ISO-3166 alpha-2 code.',400);
        const sites=filterSites(data.sites,continent,country);
        return response({n:sites.length,continent,country:country?country.toUpperCase():null,sites});
      }
      const match=/^candidates\/([a-z0-9-]+)$/.exec(path);
      if(match){
        const data=await asset(env,url,'earth/candidates.json');
        if(!data.sites.some(s=>s.id===match[1]))return failure('Unknown Earth candidate.',404);
        return response(await asset(env,url,'earth/sites/'+match[1]+'.json'));
      }
      if(path==='tasi'){
        let body;
        if(request.method==='POST'){
          const raw=await request.text();if(raw.length>1024*1024)return failure('Request body is too large.',413);
          try{body=JSON.parse(raw);}catch(_){return failure('Invalid JSON.',400);}
        }else body={target_id:url.searchParams.get('target_id'),gamma:Number(url.searchParams.get('gamma') || 1),top:Number(url.searchParams.get('top') || 5),continent:url.searchParams.get('continent'),country:url.searchParams.get('country'),apply_mask:url.searchParams.get('apply_mask')!=='false',weights:Object.fromEntries(KEYS.map(k=>[k,Number(url.searchParams.get('w'+k) ?? .2)]))};
        if(body.apply_mask!=null && typeof body.apply_mask!=='boolean')return failure('apply_mask must be a boolean.',422);
        if(body.weights!=null && (typeof body.weights!=='object' || Array.isArray(body.weights)))return failure('weights must be an object.',422);
        if(['country','continent'].some(k=>body[k]!=null && typeof body[k]!=='string'))return failure('Region filters must be strings.',422);
        if(Object.values(body.weights || {}).some(v=>v!=null && !Number.isFinite(Number(v))))return failure('Weights must be finite numbers.',422);
        const id=body.target?.id || body.target_id;
        const sites=await asset(env,url,'planetary/sites.json');
        if(!id || !sites.some(s=>s.id===id))return failure('A verified catalog target or target_id is required.',400);
        const vector=await asset(env,url,'planetary/vectors/'+id+'.json');
        if(body.target && !sameData(body.target,vector))return failure('This hosted demo accepts the verified catalog vectors unchanged. Fetch the current target vector before ranking.',422);
        const gamma=Number(body.gamma ?? 1),top=Number(body.top ?? 5);
        if(!Number.isFinite(gamma) || gamma<0 || gamma>100 || !Number.isFinite(top))return failure('Invalid gamma or top.',422);
        if(body.country && String(body.country).trim().length!==2)return failure('country must be an ISO-3166 alpha-2 code.',400);
        const [pair,candidates,inputs]=await Promise.all([asset(env,url,'pairs/'+id+'.json'),asset(env,url,'earth/candidates.json'),asset(env,url,'earth/scale-inputs.json')]);
        return response(rankSnapshot(pair,candidates.sites,inputs,{...body,gamma,top}));
      }
    }
    return failure('Endpoint not found.',404);
  }catch(error){return failure('Service unavailable: '+String(error.message || error),503);}
}
