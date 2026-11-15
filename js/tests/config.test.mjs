import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../config.js',import.meta.url),'utf8');
function load(url,saved){const location=new URL(url),data=new Map(Object.entries(saved));const root={location,localStorage:{getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)}};vm.runInNewContext(source,{window:root,URL,URLSearchParams});return {root,data};}
test('el enlace público usa el proxy aunque el navegador conserve túneles anteriores',()=>{
 const {root,data}=load('https://hexastra-globo-inmersivo.pages.dev/',{HEXASTRA_EARTH_URL:'https://viejo.trycloudflare.com',HEXASTRA_PLANETARY_URL:'http://127.0.0.1:8766'});
 assert.equal(data.size,0);assert.equal(root.HEXASTRA_CONFIG.earthUrl,'https://hexastra-globo-inmersivo.pages.dev/api/earth');
});
test('solo un túnel explícito y válido de la visita actual puede reemplazar el proxy',()=>{
 const {data}=load('https://hexastra-globo-inmersivo.pages.dev/?earth=https://nuevo.trycloudflare.com',{});assert.equal(data.get('HEXASTRA_EARTH_URL'),'https://nuevo.trycloudflare.com');
 const bad=load('https://hexastra-globo-inmersivo.pages.dev/?earth=http://127.0.0.1:8767',{HEXASTRA_EARTH_URL:'https://viejo.trycloudflare.com'});assert.equal(bad.data.size,0);
});
