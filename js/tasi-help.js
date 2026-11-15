/* Explica los componentes de la misma respuesta TASI, sin calcular el índice. */
(function(root){
  'use strict';
  const dimensions=[
    ['G','Geología','Tipo de roca y origen por impacto. Cobertura por bloques.'],
    ['T','Terreno','Relieve, pendientes y rugosidad.'],
    ['E','Clima e iluminación','Temperatura, extremos e iluminación.'],
    ['V','Volátiles e hielo','Agua, hielo y otros recursos volátiles.'],
    ['O','Operaciones','Condiciones para aterrizar, moverse y operar.'],
  ];
  const escape=v=>String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function explanationHTML(match){
    const rows=dimensions.map(([key,name,description])=>{
      const c=match?.components?.[key] || (key==='V'?match?.components?.Vo:null);
      const available=!!c?.available && Number.isFinite(c.score);
      const score=available?c.score.toLocaleString('es-AR',{maximumFractionDigits:1}):null;
      const context=c?.data_available && !available;
      const status=available?`Con dato · ${score}/100`:context?(key==='O'?'Acceso terrestre · fuera del puntaje':'Datos parciales · fuera del puntaje'):'Sin dato comparable';
      return {key,name,description:context && key==='O'?'Acceso terrestre: rutas, aeródromos y población. No se suma al TASI.':description,available,score,status};
    });
    const count=rows.filter(r=>r.available).length;
    return `<h3>¿Qué compara TASI?</h3><p class="tasi-popover-coverage">${count} de 5 dimensiones con dato en este par</p><ul>${rows.map(r=>`<li class="${r.available?'has-data':'no-data'}"><span class="tasi-dimension" aria-hidden="true">${r.key==='V'?'V<sub>o</sub>':r.key}</span><div><strong>${r.name}</strong><span class="tasi-dimension-status">${escape(r.status)}</span><p>${r.description}</p></div></li>`).join('')}</ul><p class="tasi-popover-note">Los pesos se ajustan a los componentes comparables. Un dato faltante no se considera cero.</p>`;
  }
  let panel,active,pinned=false,timer,observer;
  const isOpen=()=>panel && !panel.hidden;
  function hide(){
    clearTimeout(timer);
    if(panel)panel.hidden=true;
    active?.setAttribute('aria-expanded','false');active=null;pinned=false;
  }
  function position(){
    if(!active?.isConnected || !isOpen())return;
    const rect=active.getBoundingClientRect();
    const view=window.visualViewport,zoomed=view?.scale>1.01;
    const w=zoomed?Math.min(view.width,innerWidth):innerWidth,h=zoomed?Math.min(view.height,innerHeight):innerHeight;
    const left=zoomed?Math.max(0,Math.min(view.offsetLeft,innerWidth-w)):0,top=zoomed?Math.max(0,Math.min(view.offsetTop,innerHeight-h)):0;
    panel.dataset.compact=String(innerHeight<=500 && innerWidth>=480);
    panel.style.width=`${Math.min(panel.dataset.compact==='true'?640:380,w-24)}px`;
    panel.style.maxWidth=`${w-24}px`;panel.style.maxHeight=`${h-24}px`;
    const r=panel.getBoundingClientRect();
    panel.style.left=`${Math.max(left+12,Math.min(rect.left,left+w-r.width-12))}px`;
    const preferred=rect.top-r.height-8>=top+12?rect.top-r.height-8:rect.bottom+8;
    panel.style.top=`${Math.max(top+12,Math.min(preferred,top+h-r.height-12))}px`;
  }
  function initialize(container){
    if(panel)return;
    panel=document.createElement('div');panel.id='tasi-explainer';panel.className='tasi-popover';panel.setAttribute('role','tooltip');panel.hidden=true;
    document.body.append(panel);
    panel.addEventListener('pointerenter',()=>clearTimeout(timer));
    panel.addEventListener('pointerleave',()=>{if(!pinned && document.activeElement!==active)hide();});
    document.addEventListener('pointerdown',e=>{if(isOpen() && !panel.contains(e.target) && !active?.contains(e.target))hide();});
    document.addEventListener('keydown',e=>{if(e.key==='Escape' && isOpen()){e.preventDefault();e.stopImmediatePropagation();hide();}},true);
    document.addEventListener('beforetoggle',e=>{if(e.target.tagName==='DIALOG' && e.newState==='open')hide();},true);
    document.addEventListener('scroll',hide,true);window.addEventListener('resize',()=>requestAnimationFrame(position));
    window.visualViewport?.addEventListener('resize',()=>requestAnimationFrame(position));
    if(typeof ResizeObserver!=='undefined')new ResizeObserver(()=>{if(isOpen())position();}).observe(panel);
    observer=new MutationObserver(()=>{if(active && !active.isConnected)hide();});observer.observe(container,{childList:true,subtree:true});
  }
  function decorate(container,match){
    const label=container.querySelector('.compare-score > span:not(.score-bar)');
    if(!label || !label.textContent.includes('índice TASI'))return;
    initialize(container);
    const [before,...after]=label.textContent.split('índice TASI');
    const button=document.createElement('button');button.type='button';button.className='tasi-help-trigger';button.innerHTML='índice TASI <span aria-hidden="true">ⓘ</span>';
    button.setAttribute('aria-label','Qué dimensiones compara este índice TASI');button.setAttribute('aria-describedby','tasi-explainer');button.setAttribute('aria-controls','tasi-explainer');button.setAttribute('aria-expanded','false');
    label.replaceChildren(document.createTextNode(before),button,document.createTextNode(after.join('índice TASI')));
    function show(){
      clearTimeout(timer);
      if(active!==button){hide();active=button;panel.innerHTML=explanationHTML(match);}
      if(!isOpen()){panel.style.left='12px';panel.style.top='12px';panel.hidden=false;}
      button.setAttribute('aria-expanded','true');position();requestAnimationFrame(position);
    }
    button.addEventListener('pointermove',e=>{if(e.pointerType!=='touch')show();});
    button.addEventListener('pointerleave',()=>{timer=setTimeout(()=>{if(!pinned && !panel.matches(':hover') && document.activeElement!==button)hide();},150);});
    button.addEventListener('focus',()=>{if(button.matches(':focus-visible'))show();});
    button.addEventListener('blur',()=>{if(!pinned)hide();});
    button.addEventListener('click',()=>{if(pinned && active===button){hide();return;}show();pinned=true;});
  }
  const api={explanationHTML,decorate,hide};
  if(typeof module!=='undefined' && module.exports)module.exports=api;else root.HexastraTasiHelp=api;
})(typeof window!=='undefined'?window:globalThis);
