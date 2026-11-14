/* HexAstra — el planeta como interfaz. Catálogo, destinos, pesos y TASI vienen de las APIs. */
(function () {
  'use strict';
  const $=id=>document.getElementById(id);
  const H=window.HexastraImmersiveData;
  const state={api:null,sites:[],targets:[],method:null,regions:null,target:null,preset:null,region:'',mask:true,selected:null,ranking:null,rankings:new Map(),vectors:new Map(),details:new Map(),markers:new Map(),revision:0,pairRevision:0};
  let earth,globe,destination,destinationLayer,destinationMarker;
  const reduced=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function status(text,error=false){$('world-status').textContent=text;$('world-status').classList.toggle('is-error',error);}
  function openDialog(id){const d=$(id);if(!d.open)d.showModal();}
  function setSitesOpen(open){$('sites-panel').hidden=!open;$('open-sites').setAttribute('aria-expanded',String(open));document.body.classList.toggle('sites-open',open);if(open)$('site-query').focus();}
  function setComparisonOpen(open){
    const center=state.selected?[state.selected.lat,state.selected.lon]:earth.getCenter();
    $('compare-panel').hidden=!open;document.body.classList.toggle('comparison-open',open);
    if(open)setSitesOpen(false);
    requestAnimationFrame(()=>{earth.invalidateSize({pan:false});earth.setView(center,earth.getZoom(),{animate:false});globe?.resize();destination?.invalidateSize({pan:false});});
    if(!open){state.pairRevision++;state.selected=null;updateIcons();}
  }
  function closeComparison(){
    const id=state.selected?.id;
    setComparisonOpen(false);
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      const point=Array.from(document.querySelectorAll('.globe-pin[data-site-id]')).find(b=>b.dataset.siteId===id && !b.hidden);
      (point || $('open-sites')).focus({preventScroll:true});
    }));
  }
  function siteIcon(site){
    const match=H.pairFromRanking(state.ranking,site.id).match;
    const rank=match?.score!=null?(state.ranking.matches || []).indexOf(match)+1:0;
    const active=state.selected?.id===site.id;
    const kind=site.highlight_less_studied || site.known_level==='lesser-known'?'menos':'earth';
    return L.divIcon({className:'',html:`<span class="pin ${rank && active?'rank':kind}${active?' active':''}">${active?rank || '':''}</span>`,iconSize:[28,28],iconAnchor:[14,14]});
  }
  function updateIcons(){state.markers.forEach((marker,id)=>marker.setIcon(siteIcon(state.sites.find(s=>s.id===id))));}
  function renderSites(){
    const query=$('site-query').value.trim().toLocaleLowerCase('es');
    const ranking=state.ranking?.matches || [];
    const scores=new Map(ranking.map(m=>[m.site.id,m.score]));
    const sites=state.sites.filter(s=>`${s.name} ${s.country_name || s.country || ''}`.toLocaleLowerCase('es').includes(query)).slice().sort((a,b)=>(scores.get(b.id)??-1)-(scores.get(a.id)??-1));
    $('world-sites').innerHTML=sites.length?sites.map(site=>`<button type="button" class="world-site" data-id="${H.escape(site.id)}" aria-pressed="${state.selected?.id===site.id}"><strong>${H.escape(site.short_name || site.name)}</strong><small>${H.escape(site.country_name || site.country || site.continent || '')}${site.highlight_less_studied || site.known_level==='lesser-known'?' · Menos estudiado':''}</small><span class="site-score">${scores.get(site.id)!=null?H.escape(window.HexastraExplain.formatScore(scores.get(site.id))):'—'}</span></button>`).join(''):'<p class="empty-note">No hay sitios con ese nombre o país.</p>';
  }
  function targetOptions(body){
    const targets=state.targets.filter(t=>t.body===body);
    $('world-target').innerHTML=targets.map(t=>`<option value="${H.escape(t.id)}">${H.escape(t.short_name || t.name)}</option>`).join('');
    $('world-target').disabled=!targets.length;
  }
  function openMission(){
    if(state.target){document.querySelector(`input[name="body"][value="${state.target.body}"]`).checked=true;targetOptions(state.target.body);$('world-target').value=state.target.id;}
    if(state.preset)$('world-preset').value=state.preset.id;
    $('world-region').value=state.region;$('world-mask').checked=state.mask;describePreset();openDialog('mission-dialog');
  }
  function describePreset(){const p=(state.method?.presets || []).find(p=>p.id===$('world-preset').value);$('preset-description').textContent=p?.lead_es || '';}
  async function vectorFor(target){
    if(!state.vectors.has(target.id))state.vectors.set(target.id,state.api.getTargetVector(target.id).catch(e=>{state.vectors.delete(target.id);throw e;}));
    return state.vectors.get(target.id);
  }
  async function rankingFor(target,preset,region,mask){
    const key=H.rankingKey(target,preset,region,mask);
    if(!state.rankings.has(key))state.rankings.set(key,(async()=>state.api.rankAnalogs(H.rankingRequest(await vectorFor(target),state.method,preset,state.sites.length,region,mask)))().catch(e=>{state.rankings.delete(key);throw e;}));
    return state.rankings.get(key);
  }
  async function detailFor(site){
    if(!state.details.has(site.id))state.details.set(site.id,state.api.getCandidate(site.id).catch(e=>{state.details.delete(site.id);throw e;}));
    return state.details.get(site.id);
  }
  async function refreshRanking(){
    const revision=++state.revision;
    state.ranking=null;updateIcons();renderSites();
    status('Comparando los sitios para esta misión…');
    try{
      const ranking=await rankingFor(state.target,state.preset,state.region,state.mask);
      if(revision!==state.revision)return;
      state.ranking=ranking;updateIcons();renderSites();
      const n=(ranking.matches || []).filter(m=>m.score!=null).length;
      status(`${state.sites.length} sitios · ${n} comparables en esta misión`);
    }catch(e){if(revision===state.revision)status(`No se pudo calcular TASI. ${e.message}`,true);}
  }
  function focusEarth(site){
    earth.setView([site.lat,site.lon],3,{animate:false});globe?.focus();
  }
  function showDestination(target){
    if(!destination)destination=L.map('destination-map',{zoomControl:true,minZoom:1,maxZoom:8,attributionControl:true}).setView([0,0],1);
    if(destinationLayer)destination.removeLayer(destinationLayer);
    if(destinationMarker)destination.removeLayer(destinationMarker);
    const moon=target.body==='moon';
    const url=moon?'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png':'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png';
    destinationLayer=L.tileLayer(url,{attribution:moon?'OpenPlanetaryMap · Moon Basemap v0.1':'OpenPlanetaryMap · Mars Basemap v0.2',maxNativeZoom:moon?9:7}).addTo(destination);
    const ll=[Math.max(-85.05,Math.min(85.05,target.lat)),target.lon];
    destinationMarker=L.marker(ll,{icon:L.divIcon({className:'',html:`<span class="pin target ${moon?'moon':'mars'} active"></span>`,iconSize:[24,24],iconAnchor:[12,12]}),title:target.name}).addTo(destination);
    destinationMarker.bindTooltip(target.short_name || target.name,{permanent:true,direction:'top',offset:[0,-14]});
    destination.setView(ll,moon?3:4,{animate:false});
    $('destination-label').textContent=`${moon?'Luna':'Marte'} · ${target.short_name || target.name}`;
    $('compare-body').textContent=moon?'Luna':'Marte';
    requestAnimationFrame(()=>destination.invalidateSize({pan:false}));
  }
  async function selectSite(id){
    const site=state.sites.find(s=>s.id===id);
    if(!site || !state.target)return;
    const request=++state.pairRevision;
    const target=state.target,preset=state.preset,region=state.region,mask=state.mask;
    state.selected=site;setComparisonOpen(true);updateIcons();renderSites();focusEarth(site);
    $('compare-title').textContent=site.name;
    $('compare-place').textContent=[site.country_name || site.country,H.coordinates(site)].filter(Boolean).join(' · ');
    $('compare-content').scrollTop=0;
    $('compare-content').innerHTML=H.comparisonHTML({site,target,loading:true},window.HexastraExplain);
    showDestination(target);
    $('compare-title').focus({preventScroll:true});
    const results=await Promise.allSettled([rankingFor(target,preset,region,mask),detailFor(site),vectorFor(target)]);
    if(request!==state.pairRevision || state.selected?.id!==id || state.target?.id!==target.id)return;
    const [ranking,detail,vector]=results.map(r=>r.status==='fulfilled'?r.value:null);
    const errors=results.filter(r=>r.status==='rejected').map(r=>r.reason.message);
    const pair=H.pairFromRanking(ranking,id);
    $('compare-content').innerHTML=H.comparisonHTML({site,target,...pair,detail,vector,outside:H.outsideRegion(site,region),error:ranking?null:errors.join(' ') || 'No se pudo obtener la comparación.'},window.HexastraExplain);
    if(errors.length && ranking)$('compare-content').insertAdjacentHTML('beforeend',`<p class="compare-warning">Algunos detalles no están disponibles: ${H.escape(errors.join(' '))}</p>`);
  }
  function renderMethod(){
    const m=state.method;
    $('world-method').innerHTML=m?`<p>${H.escape(m.status_es || '')}</p><ol>${(m.steps_es || []).map(s=>`<li>${H.escape(s)}</li>`).join('')}</ol>`:'<p>El método no está disponible. Revisá la conexión con el servicio.</p>';
  }
  async function boot(){
    earth=L.map('world-map',{zoomControl:false,minZoom:1,maxZoom:12,worldCopyJump:true}).setView([-15,-55],2);
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'Esri · Maxar · Earthstar Geographics',maxZoom:18}).addTo(earth);
    globe=window.HexastraGlobe?.attach(earth,{immersive:true});
    window.addEventListener('resize',()=>{
      const center=state.selected?[state.selected.lat,state.selected.lon]:earth.getCenter();
      earth.invalidateSize({pan:false});earth.setView(center,earth.getZoom(),{animate:false});destination?.invalidateSize({pan:false});
    });
    $('open-sites').addEventListener('click',()=>setSitesOpen($('sites-panel').hidden));
    $('close-sites').addEventListener('click',()=>{setSitesOpen(false);$('open-sites').focus();});
    $('site-query').addEventListener('input',renderSites);
    $('world-sites').addEventListener('click',e=>{const button=e.target.closest('[data-id]');if(button)selectSite(button.dataset.id);});
    $('close-comparison').addEventListener('click',closeComparison);
    $('open-mission').addEventListener('click',openMission);$('open-settings').addEventListener('click',openMission);
    $('open-help').addEventListener('click',()=>{
      renderMethod();
      const unavailable=$('world-map').querySelector('[data-view="globe"]')?.disabled;
      $('toggle-earth-view').disabled=!!unavailable;
      $('toggle-earth-view').textContent=unavailable?'Mapa 2D · 3D no disponible':$('world-map').classList.contains('earth-globe-mode')?'Cambiar a mapa 2D':'Volver al globo 3D';
      openDialog('help-dialog');
    });
    $('toggle-earth-view').addEventListener('click',()=>{
      const active=$('world-map').classList.contains('earth-globe-mode');
      globe?.setMode(!active);$('help-dialog').close();
      $('toggle-earth-view').textContent=active?'Volver al globo 3D':'Cambiar a mapa 2D';
    });
    document.querySelectorAll('[data-close-dialog]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
    document.querySelectorAll('input[name="body"]').forEach(r=>r.addEventListener('change',()=>targetOptions(r.value)));
    $('world-preset').addEventListener('change',describePreset);
    $('mission-form').addEventListener('submit',e=>{
      e.preventDefault();const target=state.targets.find(t=>t.id===$('world-target').value);if(!target)return;
      state.target=target;state.preset=state.method.presets.find(p=>p.id===$('world-preset').value);state.region=$('world-region').value;state.mask=$('world-mask').checked;
      document.body.dataset.body=target.body;
      $('mission-label').textContent=`${target.body==='moon'?'Luna':'Marte'} · ${target.short_name || target.name}`;
      $('mission-dialog').close();refreshRanking();if(state.selected)selectSite(state.selected.id);
    });
    document.addEventListener('keydown',e=>{if(e.key!=='Escape' || document.querySelector('dialog[open]'))return;if(!$('sites-panel').hidden){setSitesOpen(false);$('open-sites').focus();}else if(!$('compare-panel').hidden)closeComparison();});
    try{
      state.api=await(window.HEXASTRA_API_READY || Promise.resolve(window.HexastraAPI));
      const [candidates,moon,mars,method,regions]=await Promise.all([state.api.getCandidates(),state.api.getTargets('moon'),state.api.getTargets('mars'),state.api.getMethod(),state.api.getRegions()]);
      state.sites=(candidates.sites || []).filter(s=>s.lat!=null && s.lon!=null);state.targets=[...moon,...mars];state.method=method;state.regions=regions;
      state.target=state.targets.find(t=>t.body==='mars') || state.targets[0];state.preset=method.presets?.[0] || null;
      state.sites.forEach(site=>{
        const marker=L.marker([site.lat,site.lon],{icon:siteIcon(site),title:site.name}).addTo(earth);
        marker.hexastraSite=site;
        marker.on('click',()=>selectSite(site.id));marker.bindTooltip(site.name);state.markers.set(site.id,marker);
      });
      $('site-count').textContent=state.sites.length;
      $('world-preset').innerHTML=(method.presets || []).map(p=>`<option value="${H.escape(p.id)}">${H.escape(p.title_es || p.id)}</option>`).join('');$('world-preset').disabled=!method.presets?.length;
      $('world-region').innerHTML='<option value="">Todo el mundo</option>'+(regions.continents || []).map(c=>`<optgroup label="${H.escape(c.name)}"><option value="continent:${H.escape(c.name)}">${H.escape(c.name)} · continente</option>${(c.countries || []).map(p=>`<option value="country:${H.escape(p.iso)}">${H.escape(p.name)}</option>`).join('')}</optgroup>`).join('');
      if(!state.target){status('El catálogo no tiene destinos disponibles.',true);renderSites();return;}
      targetOptions(state.target.body);$('world-target').value=state.target.id;$('apply-mission').disabled=false;
      document.body.dataset.body=state.target.body;
      $('mission-label').textContent=`${state.target.body==='moon'?'Luna':'Marte'} · ${state.target.short_name || state.target.name}`;
      renderSites();refreshRanking();
    }catch(e){status(`Servicio no disponible. ${e.message || 'No se pudieron cargar los sitios.'}`,true);$('site-count').textContent='0';$('world-sites').innerHTML='<p class="empty-note">Los catálogos no están disponibles. No mostramos sitios ni puntajes sin verificar.</p>';$('mission-label').textContent='Servicio no disponible';}
  }
  boot();
})();
