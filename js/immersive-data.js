/* Presentación y selección de respuestas de la API. No calcula ni rellena TASI. */
(function (root) {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rows = [
    ['Relieve relativo','relative_relief','T','relative_relief_m'],
    ['Pendiente','slope','T','slope_deg'], ['Rugosidad','roughness','T','roughness_m'],
    ['Temperatura media','temp_mean','E','temp_mean'], ['Amplitud diaria','temp_diurnal_range','E','temp_diurnal_range'],
    ['Iluminación','illumination_pct','E','illumination_pct'], ['Precipitación anual','precip_mm','Vo','precip_mm'],
    ['Indicador de hielo','water_ice_indicator','Vo','water_ice_indicator']
  ];
  const units = {degC:'°C',deg:'°',percent:'%', 'mm/year':'mm/año',m:'m',mm:'mm',index_0_1:'',unitless:''};
  const qualities = {measured:'medido',derived:'derivado',modeled:'modelado',convention:'convención',derived_from_published_range:'de rango publicado'};
  function coordinates(site) {
    if (site?.lat == null || site?.lon == null) return 'Coordenadas a completar';
    return `${Math.abs(site.lat).toLocaleString('es-AR',{maximumFractionDigits:4})}° ${site.lat<0?'S':'N'} · ${Math.abs(site.lon).toLocaleString('es-AR',{maximumFractionDigits:4})}° ${site.lon<0?'O':'E'}`;
  }
  function rankingKey(target, preset, region, mask) { return JSON.stringify([target?.id,preset?.id,region,!!mask]); }
  function rankingRequest(vector, method, preset, count, region, mask) {
    const [kind,...parts] = (region || '').split(':');
    const name = parts.join(':');
    return {targetVector:vector,weights:preset?.weights || method?.default_weights,gamma:method?.default_gamma,top:count,applyMask:!!mask,continent:kind==='continent'?name:null,country:kind==='country'?name:null};
  }
  function pairFromRanking(data, siteId) {
    return {match:(data?.matches || []).find(m=>m.site?.id===siteId) || null,discarded:(data?.discarded || []).find(s=>s.id===siteId) || null};
  }
  function outsideRegion(site, region) {
    if (!region) return false;
    const [kind,...parts]=region.split(':');
    const value=parts.join(':');
    return kind==='country' ? (site.country_iso || site.country)!==value : kind==='continent' ? site.continent!==value : false;
  }
  function sourceHTML(source) {
    const text = typeof source==='string' ? source : JSON.stringify(source || 'Fuente a completar');
    return text.split(/(https?:\/\/[^\s)]+)/g).map((part,i)=>i%2 ? `<a href="${escape(part)}" target="_blank" rel="noopener">${escape(part.replace(/^https?:\/\//,'').split('/')[0])}</a>`:escape(part)).join('');
  }
  function valueCell(item) {
    if (item?.value == null) return '<td>A completar</td>';
    const value = typeof item.value==='number' ? item.value.toLocaleString('es-AR',{maximumFractionDigits:2}) : String(item.value);
    return `<td>${escape(value)} ${escape(units[item.unit] ?? item.unit ?? '')}<br><small>${escape(qualities[item.quality] || item.quality || '')}</small></td>`;
  }
  function dataTable(detail, vector) {
    return `<table class="cmp-table"><thead><tr><th>Métrica</th><th>Tierra</th><th>Destino</th></tr></thead><tbody>${rows.map(([label,key,comp,metric])=>`<tr><th scope="row">${escape(label)}</th>${valueCell(detail?.features?.[key])}${valueCell(vector?.components?.[comp]?.metrics?.[metric])}</tr>`).join('')}</tbody></table>`;
  }
  function comparisonHTML({site,target,match,discarded,detail,vector,error,loading,outside}, explain) {
    let summary;
    if (loading) summary='<p class="coverage-note" role="status">Cargando la comparación con datos del servicio…</p>';
    else if (error) summary=`<p class="compare-warning">${escape(error)}</p>`;
    else if (match?.score != null) {
      const ex=explain.explainMatch(match);
      const coverage=Object.values(match.components || {}).filter(c=>c?.available && c.score!=null).length;
      summary=`<div class="compare-score" style="--s:${Math.max(0,Math.min(1,Number(match.score)/100))}"><strong class="score-color">${escape(explain.formatScore(match.score))}</strong><span>de 100 · índice TASI</span><span class="score-bar" aria-hidden="true"><span></span></span></div>
        <p class="coverage-note">${coverage} dimensiones con datos comparables. Propuesta del equipo; no es un índice oficial de NASA.</p>
        <section class="compare-explanation"><h3>Por qué se parece</h3><p>${escape(ex.why || 'Sin explicación disponible.')}</p></section>
        <section class="compare-explanation"><h3>En qué no</h3><p>${escape(ex.breaks || 'La API no detalla esta diferencia.')}</p></section>
        ${ex.missing.length?`<div class="easy-missing">${ex.missing.map(k=>`<span class="easy-chip easy-chip-warn">Dato a completar: ${escape(k)}</span>`).join('')}</div>`:''}`;
    } else summary=`<p class="compare-warning">Sin puntaje para este par. ${outside?'El sitio está fuera de la región elegida para esta misión.':discarded?'El sitio fue descartado por la máscara de esta misión.':'No hay datos comparables con este destino y estos filtros.'}</p>`;
    const metricSources=rows.flatMap(([,key,comp,metric])=>[
      {label:`Tierra · ${key}`,item:detail?.features?.[key]},
      {label:`Destino · ${metric}`,item:vector?.components?.[comp]?.metrics?.[metric]}
    ]).filter(x=>x.item?.source);
    return summary + `<details class="compare-more"><summary>Datos lado a lado</summary><p class="coverage-note">Tierra: ${escape(coordinates(site))}<br>Destino: ${escape(coordinates(target))}</p>${dataTable(detail,vector)}</details>
      <details class="compare-more"><summary>Fuentes y contexto</summary><div class="compare-source"><p><strong>Tierra.</strong> ${sourceHTML(site?.coord_source)}</p><p><strong>Destino.</strong> ${sourceHTML(target?.coord_source)}</p>${metricSources.map(({label,item})=>`<p><strong>${escape(label)}.</strong> ${sourceHTML(item.source)}${item.note?' '+escape(item.note):''}</p>`).join('')}</div></details>
      ${target?.body==='moon'?'<p class="coverage-note">Mapa lunar en Mercator: los sitios polares se dibujan en el borde de 85°; las coordenadas de la ficha son las reales.</p>':''}`;
  }
  const api={escape,coordinates,rankingKey,rankingRequest,pairFromRanking,outsideRegion,comparisonHTML,sourceHTML};
  root.HexastraImmersiveData=api;
  if(typeof module!=='undefined' && module.exports) module.exports=api;
})(typeof window!=='undefined'?window:this);
