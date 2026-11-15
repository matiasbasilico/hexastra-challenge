/* Asistente de misión. El borrador solo se aplica al terminar el tercer paso. */
(function (root) {
  'use strict';
  const NASA_LANDERS='https://www.giss.nasa.gov/tools/mars24/help/landers.html';
  const NASA_REGIONS='https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/';
  // Contexto histórico editorial; no son mediciones ni entran en TASI.
  // NASA GISS Mars24, Mars Lander Missions (actualizado 2023-12-09).
  // NASA, comunicado 22-089 (2022-08-19). Consultados 2026-11-14, America/Argentina/Buenos_Aires.
  const landings={
    jezero:{mission:'Perseverance',date:'2021-02-18'},
    gale:{mission:'Curiosity',date:'2012-08-06'},
    meridiani:{mission:'Opportunity',date:'2004-01-25'},
    'utopia-planitia':{mission:'Viking 2',date:'1976-09-03'},
  };
  // Hitos de exploración orbital: la fecha es la observación o publicación indicada,
  // nunca un aterrizaje. Fuentes consultadas 2026-11-14 (America/Argentina/Buenos_Aires).
  const orbitalHistory={
    'pavonis-mons':{body:'mars',title:'Imagen publicada · Mars Global Surveyor',date:'2004-01-18',agency:'NASA',source:'https://science.nasa.gov/photojournal/pavonis-mons/'},
    'medusae-fossae':{body:'mars',title:'Publicación de radar · Mars Express',date:'2024-01-18',agency:'ESA',source:'https://www.esa.int/ESA_Multimedia/Images/2024/01/Mars_Express_radar_data_indicating_heaps_of_water_ice_at_Mars_s_equator'},
    'arsia-mons':{body:'mars',title:'Publicación de pozos · Mars Odyssey',date:'2007-09-21',agency:'NASA',source:'https://science.nasa.gov/resource/seven-possible-cave-skylights-on-mars/'},
    'marius-hills':{body:'moon',title:'Publicación del hallazgo · Kaguya',date:'2009-11-05',agency:'JAXA',source:'https://www.isas.jaxa.jp/j/topics/topics/2009/1105.shtml'},
  };
  const geology={
    impact_crater_lacustrine:'Cráter y depósitos de lago',volcaniclastic_aeolian:'Depósitos erosionados por viento',
    volcanic_shield:'Volcán en escudo',sedimentary_sulfate:'Depósitos de sulfatos',lowland_plain_ground_ice:'Planicie del norte',
    impact_crater_rim:'Borde de cráter',impact_crater:'Cráter de impacto',impact_crater_massif:'Cráter y macizo',
    volcanic_lava_tube_pit:'Pozo volcánico',
  };
  const escape=value=>String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function targetContext(target={}) {
    const landing=target.body==='mars'?landings[target.id]:null;
    const lunarRegion=target.body==='moon' && (target.tags || []).some(t=>t==='artemis-iii' || t==='artemis-cercano');
    const url=(target.coord_source || '').match(/https:\/\/[^\s<>"']+/)?.[0]?.replace(/[.,;)]+$/,'');
    return {
      name:target.short_name || target.name || 'Destino',
      body:target.body==='moon'?'Luna':'Marte',
      summary:(target.summary || '').match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim() || target.summary || 'Descripción a completar.',
      geology:geology[target.geology_class] || 'Tipo de terreno a completar',
      history:landing?{title:`Aterrizaje · ${landing.mission}`,date:landing.date,agency:'NASA',source:NASA_LANDERS}:
        lunarRegion?{title:'Anuncio de regiones · NASA',date:'2022-08-19',agency:'NASA',source:NASA_REGIONS}:
        orbitalHistory[target.id]?.body===target.body?orbitalHistory[target.id]:null,
      clarification:lunarRegion?'Referencia geográfica de la región, no un punto de aterrizaje confirmado.':'',
      source:url || (landing?NASA_LANDERS:null),
    };
  }
  function targetHTML(target,coordinates) {
    const c=targetContext(target);
    const date=c.history?new Intl.DateTimeFormat('es-AR',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(`${c.history.date}T12:00:00Z`)):'';
    return `<header><span class="mission-target-dot" aria-hidden="true"></span><h3>${escape(c.name)}</h3><span>${escape(c.body)}</span></header>
      <p class="mission-target-intro">${escape(c.summary)}</p>
      <dl class="mission-target-facts"><div><dt>Terreno</dt><dd>${escape(c.geology)}</dd></div><div><dt>Coordenadas</dt><dd>${escape(coordinates || 'A completar')}</dd></div></dl>
      <div class="mission-target-history">${c.history?`<p>${escape(c.history.title)}</p><time datetime="${c.history.date}">${escape(date)}</time>`:'<p>Fecha de exploración</p><span>A completar en el catálogo</span>'}</div>
      ${c.clarification?`<p class="mission-target-note">${escape(c.clarification)}</p>`:''}
      <p class="mission-target-sources">${c.source?`<a href="${escape(c.source)}" target="_blank" rel="noopener">Fuente del sitio ↗</a>`:''}${c.history && c.history.source!==c.source?`<a href="${escape(c.history.source)}" target="_blank" rel="noopener">Historia · ${escape(c.history.agency)} ↗</a>`:''}</p>`;
  }
  const presetVisuals={
    equilibrado:{title:'Equilibrado',intro:'Compará todas las dimensiones.',art:'<circle cx="20" cy="20" r="13"/><path d="M20 3v34M3 20h34"/><circle cx="20" cy="20" r="4"/>'},
    terreno:{title:'Terreno',intro:'Relieve, pendientes y geología.',art:'<path d="m3 31 11-20 7 11 6-15 10 24H3Z"/><path d="m10 18 4 4 4-4M24 14l3 4 3-4M8 35h24"/>'},
    clima:{title:'Clima extremo',intro:'Temperatura, luz y hielo.',art:'<circle cx="14" cy="14" r="6"/><path d="M14 3v3M14 22v3M3 14h3M22 14h3M6 6l2 2M20 20l2 2M6 22l2-2M20 8l2-2M29 16v20M22 23l14 8M22 31l14-8"/>'},
    robots:{title:'Robots',intro:'Movilidad y condiciones de operación.',art:'<rect x="8" y="12" width="24" height="18" rx="4"/><path d="M20 5v7M16 5h8M3 20h5M32 20h5M14 30v5M26 30v5M15 24h10"/><circle cx="14" cy="18" r="1"/><circle cx="26" cy="18" r="1"/>'},
  };
  function presetCardsHTML(presets,selected) {
    return (presets || []).map(p=>{
      const v=presetVisuals[p.id] || {title:p.title_es || p.id,intro:p.lead_es || '',art:'<circle cx="20" cy="20" r="13"/><path d="M12 20h16M20 12v16"/>'};
      return `<label class="preset-card"><input type="radio" name="mission-preset" value="${escape(p.id)}"${p.id===selected?' checked':''}>
        <span class="preset-card-check" aria-hidden="true">✓</span>
        <svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${v.art}</svg>
        <strong>${escape(v.title)}</strong><span class="preset-card-full">${escape(p.lead_es || v.intro)}</span><span class="preset-card-brief">${escape(v.intro)}</span></label>`;
    }).join('');
  }
  function bestMatch(ranking){return (ranking?.matches || []).reduce((best,m)=>m.site?.id && Number.isFinite(m.score) && (!best || m.score>best.score)?m:best,null);}
  function create({getState,coordinates,onStep}) {
    const $=id=>document.getElementById(id),dialog=$('mission-dialog');
    let step=0,furthest=0;
    const titles=['¿Marte o la Luna?','Conocé tu destino','Definí el enfoque'];
    const actions=['Elegir destino','Elegir enfoque','Explorar esta misión'];
    function describeTarget() {
      const target=getState().targets.find(t=>t.id===$('world-target').value);
      if(!target)return;
      $('mission-target-info').dataset.body=target.body;
      $('mission-target-info').innerHTML=targetHTML(target,coordinates(target));
    }
    function focusTab(value,focus=false) {
      dialog.querySelectorAll('[data-focus-tab]').forEach(button=>{
        const selected=button.dataset.focusTab===value;
        button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;
        $(button.getAttribute('aria-controls')).hidden=!selected;
        if(selected && focus)button.focus();
      });
    }
    function syncPreset() {
      const id=$('world-preset').value,preset=getState().method?.presets.find(p=>p.id===id);
      dialog.querySelectorAll('input[name="mission-preset"]').forEach(r=>r.checked=r.value===id);
      $('mission-current-preset').textContent=`Prueba elegida · ${presetVisuals[id]?.title || preset?.title_es || ''}`;
    }
    dialog.querySelectorAll('[data-focus-tab]').forEach(button=>{
      button.addEventListener('click',()=>focusTab(button.dataset.focusTab));
      button.addEventListener('keydown',e=>{
        if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
        e.preventDefault();focusTab(e.key==='Home'?'test':e.key==='End'?'filters':button.dataset.focusTab==='test'?'filters':'test',true);
      });
    });
    $('mission-presets').addEventListener('change',e=>{
      if(e.target.name!=='mission-preset')return;
      $('world-preset').value=e.target.value;$('world-preset').dispatchEvent(new Event('change',{bubbles:true}));
    });
    $('world-preset').addEventListener('change',syncPreset);
    function show(next,focus=true) {
      step=Math.max(0,Math.min(2,next));furthest=Math.max(furthest,step);
      dialog.dataset.missionStep=step;
      dialog.querySelectorAll('[data-mission-page]').forEach(page=>page.hidden=Number(page.dataset.missionPage)!==step);
      dialog.querySelectorAll('[data-mission-go]').forEach(button=>{
        const i=Number(button.dataset.missionGo);
        const target=getState().targets.find(t=>t.id===$('world-target').value);
        const name=i===0 && step>0?(target?.body==='moon'?'Luna':'Marte'):i===1 && step>1?(target?.short_name || target?.name || 'Destino'):['Cuerpo','Destino','Enfoque'][i];
        button.innerHTML=`<span aria-hidden="true">${i<step?'✓':`0${i+1}`}</span><span class="mission-progress-name">${escape(name)}</span>`;
        button.setAttribute('aria-label',`Paso ${i+1}: ${name}${i<step?', completado':''}`);
        button.disabled=i>furthest;
        if(i===step)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');
        button.classList.toggle('is-complete',i<step);
      });
      $('mission-title').textContent=titles[step];
      $('mission-step-label').textContent=`Tu exploración · Paso ${step+1} de 3`;
      $('mission-next-label').textContent=actions[step];
      $('mission-back').hidden=step===0;
      describeTarget();onStep?.(step);
      if(focus)$('mission-title').focus({preventScroll:true});
    }
    dialog.querySelectorAll('[data-mission-go]').forEach(button=>button.addEventListener('click',()=>show(Number(button.dataset.missionGo))));
    $('mission-back').addEventListener('click',()=>show(step-1));
    $('world-target').addEventListener('change',describeTarget);
    return {
      reset(){furthest=0;$('mission-presets').innerHTML=presetCardsHTML(getState().method?.presets,$('world-preset').value);syncPreset();focusTab('test');show(0,false);},
      next(){show(step+1);},
      isLastStep(){return step===2;},
      describeTarget,
    };
  }
  const api={create,targetContext,targetHTML,presetCardsHTML,bestMatch};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.HexastraMission=api;
})(typeof window!=='undefined'?window:globalThis);
