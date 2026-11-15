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
  assert.equal(M.targetContext({id:'destino-sin-historia',body:'mars'}).history,null);
  assert.match(M.targetHTML({id:'destino-sin-historia',body:'mars'},null),/A completar en el catálogo/);
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


test('los 14 destinos actuales tienen una fecha con fuente oficial y tipo de hito explícito',()=>{
  const mars=['jezero','gale','meridiani','utopia-planitia','medusae-fossae','pavonis-mons','arsia-mons'];
  const moon=['shackleton-rim','haworth','malapert','de-gerlache','amundsen','nobile','marius-hills'];
  for(const body of ['mars','moon'])for(const id of body==='mars'?mars:moon){
    const c=M.targetContext({id,body,tags:id==='marius-hills'?[]:['artemis-iii']});
    assert.ok(c.history,id);assert.match(c.history.date,/^\d{4}-\d{2}-\d{2}$/);
    assert.ok(['nasa.gov','esa.int','jaxa.jp'].some(host=>new URL(c.history.source).hostname.endsWith('.'+host)),id);
    assert.ok(c.history.agency);
  }
  const arsia=M.targetContext({id:'arsia-mons',body:'mars'});
  assert.equal(arsia.history.date,'2007-09-21');assert.doesNotMatch(arsia.history.title,/Aterrizaje/);
  assert.equal(M.targetContext({id:'pavonis-mons',body:'mars'}).history.date,'2004-01-18');
  assert.equal(M.targetContext({id:'medusae-fossae',body:'mars'}).history.date,'2024-01-18');
  assert.equal(M.targetContext({id:'marius-hills',body:'moon'}).history.date,'2009-11-05');
});

test('las tarjetas conservan los enfoques publicados por la API, incluidos futuros enfoques',()=>{
  const cards=M.presetCardsHTML([{id:'nuevo',title_es:'Ensayo <nuevo>',lead_es:'Explicación <verificada>'}],'nuevo');
  assert.match(cards,/value="nuevo" checked/);assert.match(cards,/Ensayo &lt;nuevo&gt;/);
  assert.match(cards,/Explicación &lt;verificada&gt;/);assert.doesNotMatch(cards,/<nuevo>|<verificada>/);
  assert.equal(M.presetCardsHTML([],null),'');
});

test('la misión elige el mayor resultado válido de la API sin confundir cero con ausencia',()=>{
  const rows=[{site:{id:'sin'},score:null},{site:{id:'cero'},score:0},{site:{id:'mejor'},score:92},{site:{id:'otro'},score:60}];
  assert.equal(M.bestMatch({matches:rows}).site.id,'mejor');
  assert.equal(M.bestMatch({matches:rows.slice(0,2)}).site.id,'cero');
  assert.equal(M.bestMatch({matches:[{site:{id:'sin'},score:null}]}),null);
  assert.equal(rows[0].site.id,'sin');
});
