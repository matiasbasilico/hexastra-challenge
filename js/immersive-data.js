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
  const geologyRows=[['Basáltico','basaltico'],['Silícico','silicico'],['Sedimentario clástico','clastico'],['Sedimentario químico','quimico'],['Cristalino','cristalino'],['Hielo','hielo'],['Volcánico sin detalle','volc_indiviso'],['Sedimentario sin detalle','sed_indiviso']].map(([label,key])=>[label,'g_lito_'+key,'G','g_lito_'+key]).concat([['Origen por impacto (0/1)','g_impacto','G','g_impacto']]);
  const operationRows=[['Ruta más cercana','dist_road_km'],['Aeródromo más cercano','dist_airport_km'],['Aeropuerto con vuelos regulares','dist_airport_scheduled_km'],['Población a 50 km','population_50km']];
  const units = {degC:'°C',deg:'°',percent:'%', 'mm/year':'mm/año',m:'m',mm:'mm',km:'km',persons:'personas',fraction:'(fracción 0–1)',boolean:'',index_0_1:'',unitless:''};
  const qualities = {measured:'medido',derived:'derivado',modeled:'modelado',convention:'convención',derived_from_published_range:'de rango publicado'};
  function coordinates(site) {
    if (site?.lat == null || site?.lon == null) return 'Coordenadas a completar';
    return `${Math.abs(site.lat).toLocaleString(globalThis.HexastraI18n?.locale || 'es-AR',{maximumFractionDigits:4})}° ${site.lat<0?'S':'N'} · ${Math.abs(site.lon).toLocaleString(globalThis.HexastraI18n?.locale || 'es-AR',{maximumFractionDigits:4})}° ${site.lon<0?(globalThis.HexastraI18n?.language==='en'?'W':'O'):'E'}`;
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
    const value = typeof item.value==='number' ? item.value.toLocaleString(globalThis.HexastraI18n?.locale || 'es-AR',{maximumFractionDigits:2}) : String(item.value);
    return `<td>${escape(value)} ${escape(units[item.unit] ?? item.unit ?? '')}<br><small>${escape(qualities[item.quality] || item.quality || '')}</small></td>`;
  }
  function dataTable(detail, vector) {
    const allRows=rows.concat(geologyRows.filter(([,key,,metric])=>detail?.features?.[key]?.value!=null || vector?.components?.G?.metrics?.[metric]?.value!=null));
    return `<table class="cmp-table"><thead><tr><th>Métrica</th><th>Tierra</th><th>Destino</th></tr></thead><tbody>${allRows.map(([label,key,comp,metric])=>`<tr><th scope="row">${escape(label)}</th>${valueCell(detail?.features?.[key])}${valueCell(vector?.components?.[comp]?.metrics?.[metric])}</tr>`).join('')}</tbody></table>`;
  }
  function operationsHTML(match, detail) {
    const comp=match?.components?.O;
    const metrics=comp?.detail?.metrics || detail?.features || {};
    const present=operationRows.filter(([,key])=>metrics[key]?.value!=null && metrics[key]?.source && metrics[key]?.is_real!==false && ['derived','measured'].includes(metrics[key]?.quality));
    if(!present.length)return '';
    return `<h3>Operación (O) · acceso terrestre</h3><p class="coverage-note">Datos para preparar una campaña. Las distancias son en línea recta; no miden el trayecto ni los permisos de acceso. Sin equivalente en Marte o la Luna, quedan fuera del TASI.</p><table class="cmp-table"><thead><tr><th>Métrica</th><th>Tierra</th></tr></thead><tbody>${present.map(([label,key])=>`<tr><th scope="row">${escape(label)}</th>${valueCell(metrics[key])}</tr>`).join('')}</tbody></table><div class="compare-source">${present.map(([label,key])=>`<p><strong>${escape(label)}.</strong> ${sourceHTML(metrics[key].source)}${metrics[key].note?' '+escape(metrics[key].note):''}</p>`).join('')}</div>`;
  }
  function coverageHTML(match) {
    const g=match?.components?.G,o=match?.components?.O;
    let text='';
    if(g?.detail?.representation==='geology_categories_v0' && g?.data_available){
      const n=g.detail.coverage?.n_available || 0;
      text+=`<strong>Geología (G).</strong> ${g.available?`${escape(n)} de 2 bloques comparables: tipo de roca y origen por impacto. Mapas regionales; no son espectros.`:'Datos parciales disponibles; sin un bloque comparable en ambos sitios, queda fuera del puntaje.'}`;
    }
    if(o?.data_available)text+=`${text?'<br>':''}<strong>Operación (O).</strong> Acceso terrestre documentado en el detalle; fuera del puntaje de similitud.`;
    return text?`<p class="coverage-note">${text}</p>`:'';
  }
  function comparisonHTML({site,target,match,discarded,detail,vector,error,loading,outside}, explain) {
    let summary;
    if (loading) summary='<p class="coverage-note" role="status">Cargando la comparación con datos del servicio…</p>';
    else if (error) summary=`<p class="compare-warning">${escape(error)}</p>`;
    else if (match?.score != null) {
      const ex=explain.explainMatch(match);
      const coverage=Object.values(match.components || {}).filter(c=>c?.available && c.score!=null).length;
      summary=`<div class="compare-score" style="--s:${Math.max(0,Math.min(1,Number(match.score)/100))}"><strong class="score-color">${escape(explain.formatScore(match.score))}</strong><span>de 100 · índice TASI · ${coverage} dimensiones comparables</span><span class="score-bar" aria-hidden="true"><span></span></span></div>
        <p class="coverage-note">Propuesta del equipo; no es un índice oficial de NASA.</p>
        <section class="compare-explanation"><h3>¿Por qué se parece?</h3><p>${escape(ex.why || 'Sin explicación disponible.')}</p></section>
        <section class="compare-explanation"><h3>¿En qué no se parece?</h3><p>${escape(ex.breaks || 'La API no detalla esta diferencia.')}</p></section>
        ${ex.missing.length?`<p class="compare-missing"><span>Dato a completar:</span> ${ex.missing.map(escape).join(' · ')}</p>`:''}`;
    } else summary=`<p class="compare-warning">Sin puntaje para este par. ${outside?'El sitio está fuera de la región elegida para esta misión.':discarded?'El sitio fue descartado por la máscara de esta misión.':'No hay datos comparables con este destino y estos filtros.'}</p>`;
    const metricSources=rows.concat(geologyRows).flatMap(([,key,comp,metric])=>[
      {label:`Tierra · ${key}`,item:detail?.features?.[key]},
      {label:`Destino · ${metric}`,item:vector?.components?.[comp]?.metrics?.[metric]}
    ]).filter(x=>x.item?.source);
    return summary + coverageHTML(match) + `<details class="compare-more"><summary>Detalle de los datos y fuentes</summary><p class="coverage-note">Tierra: ${escape(coordinates(site))}<br>Destino: ${escape(coordinates(target))}</p>${dataTable(detail,vector)}${operationsHTML(match,detail)}<h3 class="compare-source-title">Fuentes y contexto</h3><div class="compare-source"><p><strong>Tierra.</strong> ${sourceHTML(site?.coord_source)}</p><p><strong>Destino.</strong> ${sourceHTML(target?.coord_source)}</p>${metricSources.map(({label,item})=>`<p><strong>${escape(label)}.</strong> ${sourceHTML(item.source)}${item.note?' '+escape(item.note):''}</p>`).join('')}</div></details>
      ${target?.body==='moon'?'<p class="coverage-note">Mapa lunar en Mercator: los sitios polares se dibujan en el borde de 85°; las coordenadas de la ficha son las reales.</p>':''}`;
  }
  const api={escape,coordinates,rankingKey,rankingRequest,pairFromRanking,outsideRegion,comparisonHTML,sourceHTML,operationsHTML,coverageHTML};
  root.HexastraImmersiveData=api;
  if(typeof module!=='undefined' && module.exports) module.exports=api;
})(typeof window!=='undefined'?window:this);
