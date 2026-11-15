import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const N=createRequire(import.meta.url)('../navigation.js');
test('el acceso avanzado conserva la misión y los servicios explícitos sin arrastrar otros parámetros',()=>{
 const url=new URL(N.modeURL('http://localhost:19511/?earth=http://localhost:19543&planetary=http://localhost:19542&extra=1','advanced',{target:'arsia-mons',preset:'terreno',site:'laguna-antofagasta',region:'country:AR',mask:false}));
 assert.equal(url.pathname,'/classic.html');assert.equal(url.searchParams.get('mode'),'advanced');assert.equal(url.searchParams.get('region'),'country:AR');assert.equal(url.searchParams.get('mask'),'false');assert.equal(url.searchParams.get('site'),'laguna-antofagasta');assert.equal(url.searchParams.get('earth'),'http://localhost:19543');assert.equal(url.searchParams.has('extra'),false);
});
test('un acceso sin misión abre el avanzado directamente y el regreso vuelve al globo',()=>{
 const advanced=new URL(N.modeURL('https://hexastra-globo-inmersivo.pages.dev/','advanced'));
 assert.equal(advanced.search,'?mode=advanced');
 const globe=new URL(N.modeURL(advanced.href,'globe'));
 assert.equal(globe.pathname,'/');assert.equal(globe.search,'');
});
