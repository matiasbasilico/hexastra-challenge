/* Geografía y presentación del par: sin renderer ni dependencia de WebGL. */
export function latLonToXYZ(lat, lon, radius = 1) {
  const phi = Number(lat) * Math.PI / 180;
  const theta = Number(lon) * Math.PI / 180;
  return [radius * Math.cos(phi) * Math.cos(theta), radius * Math.sin(phi), -radius * Math.cos(phi) * Math.sin(theta)];
}

const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function matchDialogHTML({ match, site, target }, explain) {
  const detail = explain.explainMatch(match || {});
  const hasScore = match?.score != null && Number.isFinite(Number(match.score));
  const score = hasScore ? explain.formatScore(match.score) : '—';
  const ratio = hasScore ? Math.max(0, Math.min(1, Number(match.score) / 100)) : 0;
  return `<form method="dialog" class="match-dialog-close"><button type="submit" aria-label="Cerrar ficha del sitio">Cerrar</button></form>
    <article class="match-card" style="--s:${ratio}">
      <div class="match-card-score"><span class="score-color">${escape(score)}</span><span>${hasScore ? 'de 100, TASI' : 'Sin puntaje'}</span><span class="score-bar" aria-hidden="true"><span></span></span></div>
      <div class="match-card-body"><p class="match-card-context">${escape(target?.short_name || target?.name || 'Análogo terrestre')}</p>
        <h2 id="match-dialog-title">${escape(site?.name || 'Sitio terrestre')}</h2>
        ${hasScore ? `<p><strong>Por qué se parece.</strong> ${escape(detail.why || 'Sin componentes comparables.')}</p>
        <p><strong class="match-breaks">En qué no.</strong> ${escape(detail.breaks || 'La API no detalla esta diferencia.')}</p>` : `<p>${escape(site?.summary || '')}</p><p>Elegí un destino y buscá análogos para calcular el índice TASI de este sitio.</p>`}
        ${detail.missing.length ? `<div class="easy-missing">${detail.missing.map(k => `<span class="easy-chip easy-chip-warn">Dato a completar: ${escape(k)}</span>`).join('')}</div>` : ''}
        ${site?.coord_source ? `<details class="match-source"><summary>Fuente del sitio</summary><p>${escape(site.coord_source)}</p></details>` : ''}
      </div>
    </article>`;
}

