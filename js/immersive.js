/* HexAstra — el planeta como interfaz. Catálogo, destinos, pesos y TASI vienen de las APIs. */
(function () {
  'use strict';
  const $=id=>document.getElementById(id);
  const H=window.HexastraImmersiveData;
  const state={missionActive:false,api:null,sites:[],targets:[],method:null,regions:null,target:null,preset:null,region:'',mask:true,onlyComparable:true,selected:null,ranking:null,rankings:new Map(),vectors:new Map(),details:new Map(),markers:new Map(),revision:0,pairRevision:0};
  let earth,globe,destination,destinationLayer,destinationMarker,destinationTargetId,planetCards,missionFlow,missionHintTimer,missionHintExpiry;
  const reduced=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function status(text,error=false){$('world-status').textContent=text;$('world-status').classList.toggle('is-error',error);}
  function openDialog(id){const d=$(id);if(!d.open)d.showModal();}
  function clearMissionHint(){clearTimeout(missionHintTimer);clearTimeout(missionHintExpiry);const hint=$('mission-map-hint');if(hint)hint.hidden=true;}
  function guideToOtherSite(id,revision){
    clearMissionHint();
    missionHintTimer=setTimeout(()=>{
      if(revision!==state.revision || state.selected?.id!==id || !$('world-map').classList.contains('earth-globe-mode') || document.querySelector('dialog[open]'))return;
      const host=$('world-map'),rect=host.getBoundingClientRect();
      const other=Array.from(host.querySelectorAll('.globe-pin[data-site-id]')).find(b=>b.dataset.siteId!==id && !b.hidden && b.getBoundingClientRect().width>0);
      let hint=$('mission-map-hint');if(!hint){hint=document.createElement('p');hint.id='mission-map-hint';hint.className='mission-map-hint';hint.setAttribute('role','status');host.append(hint);}
      hint.textContent=other?'Seleccionamos el mayor TASI. Tocá otro punto para cambiar de sitio.':'Seleccionamos el mayor TASI. Girá la Tierra y tocá otro punto para cambiar.';
      hint.hidden=false;
      const point=other?.getBoundingClientRect();
      const x=point?point.left-rect.left:12,y=point?point.top-rect.top-hint.offsetHeight-12:rect.height-hint.offsetHeight-12;
      hint.style.left=`${Math.max(12,Math.min(x,rect.width-hint.offsetWidth-12))}px`;
      hint.style.top=`${Math.max(12,Math.min(y,rect.height-hint.offsetHeight-12))}px`;
      missionHintExpiry=setTimeout(clearMissionHint,6500);
    },reduced()?200:950);
  }
  function setSitesOpen(open){$('sites-panel').hidden=!open;$('open-sites').setAttribute('aria-expanded',String(open));document.body.classList.toggle('sites-open',open);if(open)$('site-query').focus();}
  // En 2D el mapa sigue debajo de la ficha (sin franja negra): el punto se centra en la parte visible.
  function panelCovers2DMap(){
    return document.body.classList.contains('comparison-open') && !$('world-map').classList.contains('earth-globe-mode') && window.matchMedia('(min-width: 761px)').matches;
  }
  function centerEarth(center,zoom=earth.getZoom()){
    const ll=L.latLng(center);
    if(!panelCovers2DMap()){earth.setView(ll,zoom,{animate:false});return;}
    const panel=$('compare-panel').getBoundingClientRect(),map=$('world-map').getBoundingClientRect();
    const shift=Math.max(0,(map.right-panel.left)/2);
    earth.setView(earth.unproject(earth.project(ll,zoom).add([shift,0]),zoom),zoom,{animate:false});
  }
  function setComparisonOpen(open){
    const center=state.selected?[state.selected.lat,state.selected.lon]:earth.getCenter();
    $('compare-panel').hidden=!open;document.body.classList.toggle('comparison-open',open);
    if(open)setSitesOpen(false);
    requestAnimationFrame(()=>{earth.invalidateSize({pan:false});centerEarth(center);globe?.resize();destination?.invalidateSize({pan:false});});
    if(!open){clearMissionHint();state.pairRevision++;state.selected=null;updateIcons();}
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
    const leading=rank>0 && rank<=5 && Number.isFinite(match?.score) && match.score>0;
    const uncompared=state.missionActive && !Number.isFinite(match?.score);
    const active=state.selected?.id===site.id;
    const kind=site.highlight_less_studied || site.known_level==='lesser-known'?'menos':'earth';
    return L.divIcon({className:'',html:`<span class="pin ${rank && active?'rank':kind}${active?' active':''}${leading?' is-leading':''}${uncompared?' is-uncompared':''}" style="--pulse-delay:${-180*Math.max(0,rank-1)}ms">${active?rank || '':''}</span>`,iconSize:[28,28],iconAnchor:[14,14]});
  }
  function isComparable(site){return Number.isFinite(H.pairFromRanking(state.ranking,site.id).match?.score);}
  function rankingStatus(){
    if(!state.ranking)return;
    const n=(state.ranking.matches || []).filter(m=>Number.isFinite(m.score)).length;
    const leaders=(state.ranking.matches || []).slice(0,5).filter(m=>Number.isFinite(m.score) && m.score>0).length;
    status(`${state.onlyComparable?n:state.sites.length} de ${state.sites.length} sitios visibles · ${n} ${n===1?'comparable':'comparables'}${leaders?` · ${leaders} ${leaders===1?'mejor TASI':'mejores TASI'} con pulso`:''}`);
  }
  function setComparableFilter(enabled,validateSelection=true){
    state.onlyComparable=enabled;document.body.dataset.comparableOnly=String(state.missionActive && enabled);
    $('toggle-comparable').setAttribute('aria-pressed',String(enabled));
    $('toggle-comparable-list').setAttribute('aria-pressed',String(enabled));
    $('toggle-comparable-list').title=enabled?'Mostrar el catálogo completo':'Mostrar solo sitios comparables';
    $('comparable-label').textContent=enabled?'Solo comparables':'Todos los sitios';
    $('toggle-comparable').firstElementChild.textContent=enabled?'✓':'◉';
    $('toggle-comparable').title=enabled?'Mostrar también los sitios sin puntaje en esta misión':'Ocultar los sitios sin puntaje en esta misión';
    $('world-comparable-only').checked=enabled;
    if(validateSelection && enabled && state.ranking && state.selected && !isComparable(state.selected))setComparisonOpen(false);
    updateIcons();renderSites();rankingStatus();
  }
  function updateIcons(){state.markers.forEach((marker,id)=>marker.setIcon(siteIcon(state.sites.find(s=>s.id===id))));}
  function renderSites(){
    $('open-advanced').href=window.HexastraNavigation.modeURL(location.href,'advanced',state.missionActive?{target:state.target?.id,preset:state.preset?.id,region:state.region,mask:state.mask,site:state.selected?.id}:{});
    const query=$('site-query').value.trim().toLocaleLowerCase('es');
    const ranking=state.ranking?.matches || [];
    const scores=new Map(ranking.map(m=>[m.site.id,m.score]));
    const visible=state.sites.filter(s=>!state.missionActive || !state.onlyComparable || isComparable(s));
    $('site-count').textContent=state.missionActive && state.onlyComparable?`${visible.length}/${state.sites.length}`:state.sites.length;
    const sites=visible.filter(s=>`${s.name} ${s.country_name || s.country || ''} ${window.HexastraI18n?.t(s.name) || ''} ${window.HexastraI18n?.t(s.country_name || s.country || '') || ''}`.toLocaleLowerCase('es').includes(query)).slice().sort((a,b)=>(scores.get(b.id)??-1)-(scores.get(a.id)??-1));
    $('world-sites').innerHTML=sites.length?sites.map(site=>`<button type="button" class="world-site" data-id="${H.escape(site.id)}" aria-pressed="${state.selected?.id===site.id}"><strong>${H.escape(site.short_name || site.name)}</strong><small>${H.escape(site.country_name || site.country || site.continent || '')}${site.highlight_less_studied || site.known_level==='lesser-known'?' · Menos estudiado':''}</small><span class="site-score">${scores.get(site.id)!=null?H.escape(window.HexastraExplain.formatScore(scores.get(site.id))):'—'}</span></button>`).join(''):'<p class="empty-note">No hay sitios con ese nombre o país.</p>';
  }
  function targetOptions(body){
    const targets=state.targets.filter(t=>t.body===body);
    $('world-target').innerHTML=targets.map(t=>`<option value="${H.escape(t.id)}">${H.escape(t.short_name || t.name)}</option>`).join('');
    $('world-target').disabled=!targets.length;
  }
  function openMission(){
    window.HexastraTasiHelp?.hide();clearMissionHint();
    const target=state.target || state.targets.find(t=>t.body==='mars') || state.targets[0];
    if(target){document.querySelector(`input[name="body"][value="${target.body}"]`).checked=true;targetOptions(target.body);$('world-target').value=target.id;}
    const preset=state.preset || state.method?.presets?.[0];if(preset)$('world-preset').value=preset.id;
    $('world-region').value=state.region;$('world-mask').checked=state.mask;$('world-comparable-only').checked=state.onlyComparable;describePreset();missionFlow?.reset();openDialog('mission-dialog');
    if(!planetCards)planetCards=window.HexastraGlobe?.createPlanetCards?.($('mission-dialog'));
    planetCards?.render();
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
  async function refreshRanking(selectBest=false){
    const revision=++state.revision;
    state.ranking=null;updateIcons();renderSites();
    status('Comparando los sitios para esta misión…');
    try{
      const ranking=await rankingFor(state.target,state.preset,state.region,state.mask);
      if(revision!==state.revision)return;
      state.ranking=ranking;
      if(state.onlyComparable && state.selected && !isComparable(state.selected))setComparisonOpen(false);
      updateIcons();renderSites();rankingStatus();
      if(selectBest){
        const best=window.HexastraMission.bestMatch(ranking);
        if(best){await selectSite(best.site.id);if(revision===state.revision && state.selected?.id===best.site.id)guideToOtherSite(best.site.id,revision);}
      }
    }catch(e){if(revision===state.revision)status(`No se pudo calcular TASI. ${e.message}`,true);}
  }
  function focusEarth(site){
    centerEarth([site.lat,site.lon],3);globe?.focus();
  }
  function showDestination(target){
    // Otro punto terrestre conserva el mismo mapa, sus teselas y el zoom del usuario.
    if(destination && destinationTargetId===target.id){
      requestAnimationFrame(()=>destination.invalidateSize({pan:false}));
      return;
    }
    if(!destination){
      destination=L.map('destination-map',{zoomControl:true,minZoom:1,maxZoom:8,attributionControl:true}).setView([0,0],1);
      // La altura del mapa cede espacio al texto de la ficha: recentrar el destino cuando cambia.
      if(typeof ResizeObserver==='function')new ResizeObserver(()=>{destination.invalidateSize({pan:false});if(destinationMarker)destination.panTo(destinationMarker.getLatLng(),{animate:false});}).observe($('destination-map'));
    }
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
    destinationTargetId=target.id;
    requestAnimationFrame(()=>destination.invalidateSize({pan:false}));
  }
  async function selectSite(id){
    const site=state.sites.find(s=>s.id===id);
    if(!site)return;
    if(!state.missionActive){openMission();return;}
    clearMissionHint();
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
    window.HexastraTasiHelp?.decorate($('compare-content'),pair.match);
    if(H.outsideRegion(site,region))$('compare-content').querySelector('.compare-warning')?.insertAdjacentHTML('afterend','<button type="button" class="compare-reset-filter" data-reset-region>Comparar sin filtro de región ↗</button>');
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
      earth.invalidateSize({pan:false});centerEarth(center);destination?.invalidateSize({pan:false});
    });
    $('world-map').addEventListener('pointerdown',clearMissionHint);
    $('open-sites').addEventListener('click',()=>setSitesOpen($('sites-panel').hidden));
    $('close-sites').addEventListener('click',()=>{setSitesOpen(false);$('open-sites').focus();});
    $('site-query').addEventListener('input',renderSites);
    $('world-sites').addEventListener('click',e=>{const button=e.target.closest('[data-id]');if(button)selectSite(button.dataset.id);});
    $('close-comparison').addEventListener('click',closeComparison);
    $('toggle-comparable').addEventListener('click',()=>setComparableFilter(!state.onlyComparable));
    $('toggle-comparable-list').addEventListener('click',()=>setComparableFilter(!state.onlyComparable));
    $('compare-content').addEventListener('click',e=>{
      if(!e.target.closest('[data-reset-region]') || !state.selected)return;
      const id=state.selected.id;state.region='';$('world-region').value='';refreshRanking();selectSite(id);
    });
    $('open-mission').addEventListener('click',openMission);
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
      if(state.selected)requestAnimationFrame(()=>{earth.invalidateSize({pan:false});centerEarth([state.selected.lat,state.selected.lon]);globe?.focus();});
      $('toggle-earth-view').textContent=active?'Volver al globo 3D':'Cambiar a mapa 2D';
    });
    document.querySelectorAll('[data-close-dialog]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
    document.querySelectorAll('input[name="body"]').forEach(r=>r.addEventListener('change',()=>targetOptions(r.value)));
    $('world-preset').addEventListener('change',describePreset);
    $('mission-form').addEventListener('submit',e=>{
      e.preventDefault();if(missionFlow && !missionFlow.isLastStep()){missionFlow.next();return;}
      const target=state.targets.find(t=>t.id===$('world-target').value);if(!target)return;
      state.missionActive=true;document.body.classList.add('has-mission');$('toggle-comparable').hidden=false;$('toggle-comparable-list').hidden=false;$('mission-control-label').textContent='Misión · cambiar';
      state.target=target;state.preset=state.method.presets.find(p=>p.id===$('world-preset').value);state.region=$('world-region').value;state.mask=$('world-mask').checked;
      setComparableFilter($('world-comparable-only').checked,false);
      document.body.dataset.body=target.body;
      $('mission-label').textContent=`${target.body==='moon'?'Luna':'Marte'} · ${target.short_name || target.name}`;
      $('mission-dialog').close();setComparisonOpen(false);refreshRanking(true);
    });
    document.addEventListener('keydown',e=>{if(e.key!=='Escape' || document.querySelector('dialog[open]'))return;if(!$('sites-panel').hidden){setSitesOpen(false);$('open-sites').focus();}else if(!$('compare-panel').hidden)closeComparison();});
    const onboardingKey='hexastra.onboarding.v1';
    $('help-dialog').addEventListener('close',()=>{
      if(!$('help-dialog').classList.contains('is-onboarding'))return;
      try{localStorage.setItem(onboardingKey,'seen');}catch(e){/* El recorrido sigue disponible sin almacenamiento. */}
      $('help-dialog').classList.remove('is-onboarding');$('help-dialog').querySelector('.onboarding-intro').hidden=true;
    });
    $('onboarding-start').addEventListener('click',()=>{$('help-dialog').close();openMission();});
    let sawOnboarding=false;
    try{sawOnboarding=localStorage.getItem(onboardingKey)==='seen';}catch(e){/* Primera visita también en modo privado. */}
    if(!sawOnboarding){$('help-dialog').classList.add('is-onboarding');$('help-dialog').querySelector('.onboarding-intro').hidden=false;$('open-help').click();}

    try{
      state.api=await(window.HEXASTRA_API_READY || Promise.resolve(window.HexastraAPI));
      const [candidates,moon,mars,method,regions]=await Promise.all([state.api.getCandidates(),state.api.getTargets('moon'),state.api.getTargets('mars'),state.api.getMethod(),state.api.getRegions()]);
      state.sites=(candidates.sites || []).filter(s=>s.lat!=null && s.lon!=null);state.targets=[...moon,...mars];state.method=method;state.regions=regions;
      const initialBody=document.querySelector('input[name="body"]:checked')?.value || 'mars';
      const initialTarget=state.targets.find(t=>t.body===initialBody) || state.targets[0];
      state.sites.forEach(site=>{
        const marker=L.marker([site.lat,site.lon],{icon:siteIcon(site),title:site.name}).addTo(earth);
        marker.hexastraSite=site;
        marker.on('click',()=>selectSite(site.id));marker.bindTooltip(site.name);state.markers.set(site.id,marker);
      });
      $('site-count').textContent=state.sites.length;
      $('world-preset').innerHTML=(method.presets || []).map(p=>`<option value="${H.escape(p.id)}">${H.escape(p.title_es || p.id)}</option>`).join('');$('world-preset').disabled=!method.presets?.length;
      $('world-region').innerHTML='<option value="">Todo el mundo</option>'+(regions.continents || []).map(c=>`<optgroup label="${H.escape(c.name)}"><option value="continent:${H.escape(c.name)}">${H.escape(c.name)} · continente</option>${(c.countries || []).map(p=>`<option value="country:${H.escape(p.iso)}">${H.escape(p.name)}</option>`).join('')}</optgroup>`).join('');
      if(!initialTarget){status('El catálogo no tiene destinos disponibles.',true);renderSites();return;}
      targetOptions(initialTarget.body);$('world-target').value=initialTarget.id;
      missionFlow=window.HexastraMission.create({getState:()=>state,coordinates:H.coordinates,onStep:()=>planetCards?.render()});
      $('apply-mission').disabled=false;$('onboarding-start').disabled=false;renderMethod();
      $('mission-label').textContent='Elegir misión';
      renderSites();status(`${state.sites.length} sitios · Elegí una misión para compararlos.`);
    }catch(e){status(`Servicio no disponible. ${e.message || 'No se pudieron cargar los sitios.'}`,true);$('site-count').textContent='0';$('world-sites').innerHTML='<p class="empty-note">Los catálogos no están disponibles. No mostramos sitios ni puntajes sin verificar.</p>';$('mission-label').textContent='Servicio no disponible';}
  }
  window.addEventListener('hexastra:languagechange',()=>{
    if(!state.api)return;
    renderSites();renderMethod();describePreset();missionFlow?.refresh();
    if(state.selected)selectSite(state.selected.id);
    if(state.ranking)rankingStatus();
  });
  boot();
})();
