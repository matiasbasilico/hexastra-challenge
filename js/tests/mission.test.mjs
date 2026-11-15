import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const M=require('../mission.js');

test('las fechas históricas citan NASA y se vinculan al sitio y cuerpo correctos',()=>{
  for(const [id,date] of Object.entries({jezero:'2021-02-18',gale:'2012-08-06',meridiani:'2004-01-25','utopia-planitia':'1976-09-03'})) {
    const c=M.targetContext({id,body:'mars'});
    assert.equal(c.history.date,date);
    assert.equal(new URL(c.history.source).hostname,'www.giss.nasa.gov');
    assert.equal(M.targetContext({id,body:'moon'}).history,null);
  }
  assert.equal(M.targetContext({id:'arsia-mons',body:'mars'}).history,null);
  assert.match(M.targetHTML({id:'arsia-mons',body:'mars'},null),/A completar en el catálogo/);
});

test('una región candidata histórica no se presenta como un aterrizaje',()=>{
  const target={id:'haworth',body:'moon',tags:['artemis-iii']};
  assert.equal(M.targetContext(target).history.date,'2022-08-19');
  const html=M.targetHTML(target,'86,9° S · 4° O');
  assert.match(html,/Anuncio de regiones · NASA/);
  assert.match(html,/no un punto de aterrizaje confirmado/);
  assert.doesNotMatch(html,/Aterrizaje ·/);
});

test('la ficha usa el catálogo, escapa texto y no acepta fuentes ejecutables',()=>{
  const target={name:'<script>nombre</script>',summary:'<img src=x onerror=alert(1)>',coord_source:'javascript:alert(1)',body:'mars'};
  const html=M.targetHTML(target,'<svg onload=alert(1)>');
  assert.doesNotMatch(html,/<script>|<img|<svg|href="javascript:/);
  assert.match(html,/&lt;script&gt;/);
  assert.equal(M.targetContext(target).source,null);
});
