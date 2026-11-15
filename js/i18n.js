/* UI localization only: never modify API payloads, identifiers, sources, or TASI inputs. */
(function (root) {
  'use strict';
  const STORAGE_KEY = 'hexastra.language';
  const supported = value => /^(en|es)(?:-|$)/i.exec(String(value || ''))?.[1]?.toLowerCase() || null;
  function resolveLanguage({query, saved, languages = []} = {}) {
    return supported(query) || supported(saved) || languages.map(supported).find(Boolean) || 'en';
  }
  let saved;
  try { saved = root.localStorage?.getItem(STORAGE_KEY); } catch (_) { /* Private browsing. */ }
  const query = root.location ? new URLSearchParams(root.location.search).get('lang') : null;
  let language = resolveLanguage({query, saved, languages: root.navigator?.languages || [root.navigator?.language]});
  const messages = root.HexastraEnglish || {};
  const lowerMessages=new Map(Object.entries(messages).map(([key,value])=>[key.toLowerCase(),value]));
  const regions = new Map();
  const continents = [['South America','América del Sur'],['North America','América del Norte'],['Europe','Europa'],['Africa','África'],['Asia','Asia'],['Oceania','Oceanía'],['Antarctica','Antártida']];
  continents.forEach(([en,es]) => { regions.set(en,{en,es}); regions.set(es,{en,es}); });
  try {
    const en = new Intl.DisplayNames(['en'], {type:'region'}), es = new Intl.DisplayNames(['es'], {type:'region'});
    'AR CL BO US CA MX BR PE EC CO VE UY PY GB ES FR DE IT IS NO RU TN ET TZ CV ZA NA IR IN JO AU AQ NZ CN'.split(' ').forEach(iso => {
      const names = {en:en.of(iso),es:es.of(iso)};
      regions.set(names.en,names); regions.set(names.es,names); regions.set(iso,names);
      if(iso==='US') regions.set('United States of America',names);
    });
  } catch (_) { /* Names remain readable in browsers without DisplayNames. */ }
  const templates = [
    ['{rank}. {name}','{rank}. {name}'],
    ['Resultados para {target} en {scope}','Results for {target} in {scope}'],
    ['Dato a completar: {label}','Missing evidence: {label}'],
    ['En {site}','At {site}'],
    ['{score} de 100','{score} out of 100'],
    ['{name} (Marte)','{name} (Mars)'],['{name} (Luna)','{name} (Moon)'],
    ['con {target}','with {target}'],
    ['Ranking TASI y resto del catálogo ({n} sitios)','TASI ranking and remaining sites ({n} sites)'],
    ['{n} sitios en el ranking TASI frente a','{n} sites ranked against'],
    [', ordenados en la lista de la izquierda. La máscara descartó {n}.',', ordered in the list on the left. The mask excluded {n}.'],
    ['{n} sitios en el ranking TASI frente a {target}, ordenados en la lista de la izquierda.','{n} sites ranked against {target}, ordered in the list on the left.'],
    ['de 100, índice TASI frente a {target}, con los pesos de tu búsqueda.','out of 100, TASI index against {target}, using your search weights.'],
    ['de 100, índice TASI frente a {target}, con los pesos y γ por defecto del servicio.','out of 100, TASI index against {target}, using the service’s default weights and γ.'],
    ['{value} mm/año','{value} mm/year'],
    ['{n} dimensiones comparables','{n} comparable dimensions'],
    ['{n} sitios · Elegí una misión para compararlos.','{n} sites · Choose a mission to compare them.'],
    ['{visible} de {total} sitios visibles','{visible} of {total} sites visible'],
    ['{n} comparables','{n} comparable sites'], ['{n} comparable','{n} comparable site'],
    ['{n} mejores TASI con pulso','{n} top TASI matches pulse'],['{n} mejor TASI con pulso','{n} top TASI match pulses'],
    ['No se pudo calcular TASI. {error}','TASI could not be calculated. {error}'],
    ['Servicio no disponible. {error}','Service unavailable. {error}'],
    ['Algunos detalles no están disponibles: {error}','Some details are unavailable: {error}'],
    ['Paso {n}: {name}, completado','Step {n}: {name}, completed'],['Paso {n}: {name}','Step {n}: {name}'],
    ['Prueba elegida · {preset}','Selected test · {preset}'],
    ['{n} de 100 · índice TASI · {coverage} dimensiones comparables','out of 100 · TASI index · {coverage} comparable dimensions'],
    ['de 100 · índice TASI · {coverage} dimensiones comparables','out of 100 · TASI index · {coverage} comparable dimensions'],
    ['{n} de 5 dimensiones con dato en este par','{n} of 5 dimensions have data for this pair'],
    ['Con dato · {score}/100','Available · {score}/100'],
    ['{n} de 2 bloques comparables: tipo de roca y origen por impacto. Mapas regionales; no son espectros.','{n} of 2 comparable blocks: rock type and impact origin. Regional maps, not spectra.'],
    ['Sin puntaje para este par. {reason}','No score for this pair. {reason}'],
    ['Historia · {agency} ↗','History · {agency} ↗'],['Aterrizaje · {mission}','Landing · {mission}'],
    ['{continent} · continente','{continent} · continent'],['Todo {continent}','All of {continent}'],
    ['Comparado con {target}','Compared with {target}'], ['Destino elegido: {target}','Selected destination: {target}'],
    ['Destino: {target}','Destination: {target}'], ['Análogo {rank}','Analog {rank}'],
    ['Desglose por componente ({n} de 5 con dato)','Component breakdown ({n} of 5 with data)'],
    ['No pudimos cargar los datos del par: {error}','Pair data could not be loaded: {error}'],
    ['Falló la consulta a los servicios: {error}','The service request failed: {error}'],
    ['No se pudo iniciar el modo avanzado: {error}','Advanced mode could not start: {error}'],
    ['Los servicios respondieron /health pero falló una consulta del catálogo: {error}','Service health checks passed, but a catalog request failed: {error}'],
    ['No pudimos completar la búsqueda. {error}','The search could not be completed. {error}'],
    ['No pudimos completar la comparación. {error}','The comparison could not be completed. {error}'],
    ['No pude cargar los datos de ese destino. {error}','Destination data could not be loaded. {error}'],
    ['No pudimos cargar el método del servicio. {error}','The service method could not be loaded. {error}'],
    ['No pudimos cargar los destinos. Recargá la página. {error}','Destinations could not be loaded. Reload the page. {error}'],
    ['Máscara incompleta ({flags}): el sitio no se descartó.','Incomplete mask ({flags}): the site was retained.'],
    ['Consultado el {date}.','Retrieved on {date}.'],
    ['{n} análogos encontrados','{n} analogs found'],['{n} sitios','{n} sites'],['{n} resultados','{n} results'],
    ['{name} · Menos estudiado','{name} · Less studied'],
  ];
  const escapeRegex = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const compiled = templates.map(([source,target]) => {
    const keys = [];
    const pattern = source.split(/(\{\w+\})/).map(part => /^\{/.test(part) ? (keys.push(part.slice(1,-1)), ['rank','n','visible','total','coverage'].includes(part.slice(1,-1))?'(\\d+)':'(.+?)') : escapeRegex(part)).join('');
    return {regex:new RegExp('^'+pattern+'$'),target,keys};
  });
  const spanishReasons = {
    'Zoom in':'Acercar', 'Zoom out':'Alejar', 'Layers':'Capas',
    'No shared metrics.':'No hay métricas compartidas.',
    'No usable pairs.':'No hay pares utilizables.',
    'No shared topographic dimensions (relative relief, slope, roughness) with a sourced value on both sides, or Sigma is missing.':'No hay dimensiones de terreno con fuente en ambos sitios, o falta la covarianza.',
    'No shared thermal/illumination metrics with sourced values on both sides.':'No hay métricas de temperatura o iluminación con fuente en ambos sitios.',
    'No shared volatile metrics with sourced values on both sides.':'No hay métricas de volátiles con fuente en ambos sitios.',
    'Spectral vectors missing or of different length.':'Faltan vectores espectrales comparables.',
    'Zero spectral vector.':'El vector espectral es cero.',
  };
  function translate(value, depth=0) {
    const input = String(value ?? '');
    if(!input.trim() || depth>4) return input;
    const text = input.trim();
    let result;
    if(regions.has(text)) result=regions.get(text)[language];
    else if(language==='es') result=spanishReasons[text] || text;
    else if(Object.prototype.hasOwnProperty.call(messages,text)) result=messages[text];
    else if(lowerMessages.has(text.toLowerCase()))result=lowerMessages.get(text.toLowerCase());
    else if(/[.:]$/.test(text) && Object.prototype.hasOwnProperty.call(messages,text.slice(0,-1)))result=messages[text.slice(0,-1)]+text.slice(-1);
    else {
      for(const entry of compiled) {
        const match=entry.regex.exec(text);
        if(!match) continue;
        result=entry.target;
        entry.keys.forEach((key,i)=>{result=result.replace('{'+key+'}',translate(match[i+1],depth+1));});
        break;
      }
      if(result===undefined && text.includes(' · ')) result=text.split(' · ').map(part=>translate(part,depth+1)).join(' · ');
      if(result===undefined && /^(Tierra|Destino|Marte|Luna): /.test(text)) {
        const at=text.indexOf(': ');result=translate(text.slice(0,at),depth+1)+text.slice(at);
      }
      if(result===undefined) result=text;
    }
    return input.slice(0,input.indexOf(text))+result+input.slice(input.indexOf(text)+text.length);
  }
  const sourceText = new WeakMap(), sourceAttributes = new WeakMap();
  // Source records are quoted evidence: retain their original wording and links.
  const excluded = 'script,style,code,pre,textarea,svg,[translate="no"],.compare-source,.limits-list,.sources';
  function localizeText(node) {
    if(!node.parentElement || node.parentElement.closest(excluded)) return;
    const current=node.nodeValue;
    let record=sourceText.get(node);
    if(!record || current!==record.last) record={source:current,last:current};
    const next=translate(record.source);
    if(next!==current) node.nodeValue=next;
    record.last=next;sourceText.set(node,record);
  }
  const attributes=['aria-label','title','placeholder','alt','label','data-label'];
  function localizeElement(el) {
    if(!el || el.nodeType!==1 || el.closest(excluded))return;
    let records=sourceAttributes.get(el);
    if(!records){records={};sourceAttributes.set(el,records);}
    const names=el.matches('meta[name="description"]')?[...attributes,'content']:attributes;
    for(const name of names) {
      if(!el.hasAttribute(name))continue;
      const current=el.getAttribute(name);
      if(!records[name] || records[name].last!==current)records[name]={source:current,last:current};
      const next=translate(records[name].source);
      if(next!==current)el.setAttribute(name,next);
      records[name].last=next;
    }
    if(el.matches('[data-language-select]'))el.value=language;
    if(el.classList.contains('comp-reason'))el.lang=api.locale;
    if(el.tagName==='A' && el.hasAttribute('href') && root.location){
      try{
        const url=new URL(el.getAttribute('href'),root.location.href);
        if(url.origin===root.location.origin && (/\/(?:index|classic)\.html$/.test(url.pathname) || url.pathname.endsWith('/')) && url.searchParams.get('lang')!==language){
          url.searchParams.set('lang',language);el.setAttribute('href',url.href);
        }
      }catch(_){/* Non-URL references retain their original value. */}
    }
    if(el.hasAttribute('data-ui-language')) el.lang=api.locale;
  }
  function apply(container) {
    if(!root.document)return;
    container=container || root.document.documentElement;
    if(container.nodeType===3){localizeText(container);return;}
    localizeElement(container);
    const walker=root.document.createTreeWalker(container,5); // Elements and text only.
    let node;
    while((node=walker.nextNode())) {
      if(node.nodeType===3)localizeText(node);else localizeElement(node);
    }
  }
  function applyLanguage() {
    root.document.documentElement.lang=api.locale;
    apply();
    root.document.querySelectorAll('[data-language-select]').forEach(select=>{select.value=language;});
  }
  function setLanguage(value) {
    const next=supported(value);
    if(!next || next===language)return;
    language=next;
    try{root.localStorage.setItem(STORAGE_KEY,language);}catch(_){/* Preferences are optional. */}
    if(root.location && root.history){const url=new URL(root.location.href);url.searchParams.set('lang',language);root.history.replaceState(null,'',url);}
    applyLanguage();
    root.dispatchEvent(new CustomEvent('hexastra:languagechange',{detail:{language,locale:api.locale}}));
  }
  function number(value,options){return Number(value).toLocaleString(api.locale,options);}
  function explainMatch(match) {
    if(language!=='en')return null;
    const comps=match?.components || {};
    const labels={G:'geology (G)',T:'terrain (T)',E:'climate and illumination (E)',V:'volatiles or ice (V)',O:'operations (O)'};
    const scored=Object.entries(comps).filter(([,c])=>c?.available && Number.isFinite(c.score)).sort((a,b)=>b[1].score-a[1].score);
    const line=([key,c],best)=>{
      let head=`${labels[key] || labels.Vo || key}, ${number(c.score,{maximumFractionDigits:1})} out of 100`;
      const d=c.detail || {};
      if(key==='G'){
        const names=Object.keys(d.blocks || {}).map(k=>({composition:'rock type',impact:'impact origin'}[k] || k));
        return `${head}: comparing ${names.join(' and ')} (${names.length} of 2 geological blocks).`;
      }
      if(key==='T'){
        const names=(d.used || []).map(k=>({relative_relief_m:'relative relief',slope_deg:'slope',roughness_m:'roughness'}[k] || k));
        return `${head}: ${names.join(', ')} ${best?'are similar':'differ'}${d.D_M==null?'':` (Mahalanobis distance ${number(d.D_M,{maximumFractionDigits:2})})`}.`;
      }
      const parts=(d.parts || []).filter(p=>p.s!=null).sort((a,b)=>best?b.s-a.s:a.s-b.s),p=parts[0];
      if(!p)return head+'.';
      const metric={temp_mean:['mean temperature','°C'],temp_diurnal_range:['daily temperature range','°C'],illumination_pct:['illumination','%'],precip_mm:['annual precipitation','mm'],water_ice_indicator:['ice indicator','']}[p.metric] || [p.metric,''];
      return `${head}: ${metric[0]} ${number(p.y,{maximumFractionDigits:1})} ${metric[1]} on Earth versus ${number(p.x,{maximumFractionDigits:1})} ${metric[1]} at the destination${p.metric==='precip_mm' && p.x===0?' (documented convention for a body without liquid rain)':''}.`;
    };
    return {why:scored.length?'The closest match is '+line(scored[0],true):'',breaks:scored.length>1?'The weakest match is '+line(scored[scored.length-1],false):translate('Hay un solo componente con dato: no alcanza para decir en qué se separa.'),missing:(match?.missing || []).map(s=>translate(s))};
  }
  const api={resolveLanguage,supported,translate,t:translate,apply,setLanguage,number,explainMatch,
    get language(){return language;},get locale(){return language==='es'?'es-AR':'en-US';}};
  root.HexastraI18n=api;
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  if(!root.document)return;
  root.document.documentElement.lang=api.locale;
  function start() {
    applyLanguage();
    root.document.addEventListener('change',e=>{if(e.target.matches('[data-language-select]'))setLanguage(e.target.value);});
    const observer=new MutationObserver(records=>{
      const nodes=new Set();
      for(const record of records){
        if(record.type==='characterData')localizeText(record.target);
        else if(record.type==='attributes')localizeElement(record.target);
        else record.addedNodes.forEach(node=>{if(node.nodeType===1 || node.nodeType===3)nodes.add(node);});
      }
      nodes.forEach(apply);
    });
    observer.observe(root.document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:[...attributes,'content','href']});
  }
  start();
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',applyLanguage);
})(typeof window!=='undefined'?window:globalThis);
