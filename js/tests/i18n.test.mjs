import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const en=fs.readFileSync(new URL('../locales/en.js',import.meta.url),'utf8');
const source=fs.readFileSync(new URL('../i18n.js',import.meta.url),'utf8');
function load({query='',saved=null,languages=['en-US']}={}){
  const context={URL,URLSearchParams,Intl,Map,Set,WeakMap,navigator:{languages},location:{search:query},localStorage:{getItem(){return saved;}}};
  vm.createContext(context);vm.runInContext(en,context);vm.runInContext(source,context);return context.HexastraI18n;
}
test('Explicit language, saved preference and supported browser languages have clear precedence',()=>{
  assert.equal(load({query:'?lang=es',saved:'en'}).language,'es');
  assert.equal(load({saved:'es',languages:['en-GB']}).language,'es');
  assert.equal(load({languages:['fr-FR','es-MX','en']}).language,'es');
  assert.equal(load({query:'?lang=invalid',saved:'invalid',languages:['de-DE']}).language,'en');
});
test('English wizard, messages, dynamic counts, regions and formatting are localized',()=>{
  const i=load();assert.equal(i.t('¿Marte o la Luna?'),'Mars or the Moon?');
  assert.equal(i.t('Paso 2: Arsia Mons, completado'),'Step 2: Arsia Mons, completed');
  assert.equal(i.t('1 de 5 dimensiones con dato en este par'),'1 of 5 dimensions have data for this pair');
  assert.equal(i.t('8 sitios en el ranking TASI frente a '),'8 sites ranked against ');
  assert.equal(i.t(', ordenados en la lista de la izquierda.'),', ordered in the list on the left.');
  assert.equal(i.t('Sitio'),'Site');
  assert.equal(i.number(72.7),'72.7');assert.equal(i.t('América del Sur'),'South America');
});
test('Spanish preserves native UI messages and uses localized region names and decimals',()=>{
  const i=load({languages:['es-AR']});assert.equal(i.t('¿Marte o la Luna?'),'¿Marte o la Luna?');
  assert.equal(i.t('South America'),'América del Sur');assert.equal(i.number(72.7),'72,7');
});
test('English explanations preserve zero, absent evidence, and do not mutate the response',()=>{
  const match={components:{G:{available:true,score:0,detail:{blocks:{composition:0}}},O:{available:false,score:null,data_available:true}},missing:[]};
  const before=JSON.stringify(match),out=load().explainMatch(match);
  assert.match(out.why,/geology \(G\), 0 out of 100/);assert.equal(out.missing.length,0);assert.equal(JSON.stringify(match),before);
});
