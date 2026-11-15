import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const H=createRequire(import.meta.url)('../tasi-help.js');
test('el popup explica cinco dimensiones e identifica las disponibles sin tratar cero como ausente',()=>{
  const html=H.explanationHTML({components:{G:{available:false,score:null},T:{available:true,score:0},E:{available:true,score:32.4},V:{available:false,score:null},O:{available:false,score:null}}});
  assert.match(html,/2 de 5 dimensiones/);assert.equal((html.match(/class="has-data"/g)||[]).length,2);
  assert.match(html,/Con dato · 0\/100/);assert.match(html,/32,4\/100/);assert.match(html,/Geología/);assert.match(html,/Operaciones/);
  assert.equal((html.match(/Sin dato comparable/g)||[]).length,3);
});
test('el popup de un par sin datos no hereda números ni agrega componentes a TASI',()=>{
  const html=H.explanationHTML(null);assert.match(html,/0 de 5 dimensiones/);assert.doesNotMatch(html,/Con dato ·/);
  const aliased=H.explanationHTML({components:{Vo:{available:true,score:80}}});assert.match(aliased,/1 de 5 dimensiones/);
});

test('el acceso terrestre y la geología parcial tienen información pero no simulan similitud',()=>{
 const html=H.explanationHTML({components:{G:{available:false,data_available:true,score:null},O:{available:false,data_available:true,score:null}}});
 assert.match(html,/0 de 5 dimensiones/);assert.match(html,/Acceso terrestre · fuera del puntaje/);assert.match(html,/Datos parciales · fuera del puntaje/);assert.doesNotMatch(html,/Con dato ·/);
});
