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
      history:landing?{title:`Aterrizaje · ${landing.mission}`,date:landing.date,source:NASA_LANDERS}:
        lunarRegion?{title:'Anuncio de regiones · NASA',date:'2022-08-19',source:NASA_REGIONS}:null,
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
      <p class="mission-target-sources">${c.source?`<a href="${escape(c.source)}" target="_blank" rel="noopener">Fuente del sitio ↗</a>`:''}${c.history && c.history.source!==c.source?`<a href="${escape(c.history.source)}" target="_blank" rel="noopener">Historia · NASA ↗</a>`:''}</p>`;
  }
  function create({getState,coordinates,onStep}) {
    const $=id=>document.getElementById(id),dialog=$('mission-dialog');
    let step=0,furthest=0;
    const titles=['¿Marte o la Luna?','Conocé tu destino','Definí el enfoque'];
    const actions=['Elegir destino','Elegir enfoque','Explorar esta misión'];
    function describeTarget() {
      const target=getState().targets.find(t=>t.id===$('world-target').value);
      if(!target)return;
      const body=target.body==='moon'?'Luna':'Marte';
      $('mission-world-label').textContent=`Cuerpo celeste · ${body}`;
      $('mission-selection-label').textContent=`${body} · ${target.short_name || target.name}`;
      $('mission-target-info').dataset.body=target.body;
      $('mission-target-info').innerHTML=targetHTML(target,coordinates(target));
    }
    function show(next,focus=true) {
      step=Math.max(0,Math.min(2,next));furthest=Math.max(furthest,step);
      dialog.dataset.missionStep=step;
      dialog.querySelectorAll('[data-mission-page]').forEach(page=>page.hidden=Number(page.dataset.missionPage)!==step);
      dialog.querySelectorAll('[data-mission-go]').forEach(button=>{
        const i=Number(button.dataset.missionGo);
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
      reset(){furthest=0;dialog.querySelector('.mission-refine').open=false;show(0,false);},
      next(){show(step+1);},
      isLastStep(){return step===2;},
      describeTarget,
    };
  }
  const api={create,targetContext,targetHTML};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.HexastraMission=api;
})(typeof window!=='undefined'?window:globalThis);
