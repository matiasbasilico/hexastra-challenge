import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const H=require('../immersive-data.js');
const explain=require('../explain.js');

test('la misión usa pesos y gamma del servicio sin defaults ni otra fórmula en el front',()=>{
 const vector={id:'destino',components:{}},method={default_weights:{T:1},default_gamma:0.37},preset={id:'personal',weights:{E:0.9,V:0.1}};
 const request=H.rankingRequest(vector,method,preset,61,'country:AR',true);
 assert.equal(request.targetVector,vector);assert.equal(request.weights,preset.weights);assert.equal(request.gamma,0.37);assert.equal(request.top,61);assert.equal(request.country,'AR');assert.equal(request.continent,null);
 const fallback=H.rankingRequest(vector,method,null,61,'continent:South America',false);
 assert.equal(fallback.weights,method.default_weights);assert.equal(fallback.continent,'South America');assert.equal(fallback.applyMask,false);
});

test('cada misión tiene su propia caché y un sitio no hereda el puntaje de otro',()=>{
 const a={id:'a'},b={id:'b'},preset={id:'terreno'};
 const key=H.rankingKey(a,preset,'',true);
 assert.notEqual(key,H.rankingKey(b,preset,'',true));assert.notEqual(key,H.rankingKey(a,preset,'country:AR',true));assert.notEqual(key,H.rankingKey(a,preset,'',false));
 const ranking={matches:[{site:{id:'otro'},score:92}],discarded:[{id:'sin-dato'}]};
 assert.deepEqual(H.pairFromRanking(ranking,'sin-dato'),{match:null,discarded:{id:'sin-dato'}});
 assert.equal(H.pairFromRanking(ranking,'ausente').match,null);
});

test('distingue una región excluida de un componente sin mediciones',()=>{
 const site={id:'sitio',country_iso:'AR',continent:'South America'};
 assert.equal(H.outsideRegion(site,'country:AR'),false);assert.equal(H.outsideRegion(site,'country:CL'),true);assert.equal(H.outsideRegion(site,'continent:South America'),false);
 const html=H.comparisonHTML({site,target:{},outside:true},explain);
 assert.match(html,/fuera de la región/);assert.doesNotMatch(html,/de 100/);
});

test('la comparativa conserva las coordenadas reales polares, el puntaje y los nulos',()=>{
 const html=H.comparisonHTML({site:{name:'<sitio>',lat:-26,lon:-67},target:{name:'destino',body:'moon',lat:-89.9,lon:120},match:{score:32.4,why:'Razón fuente',breaks:'Brecha fuente',components:{T:{available:true,score:32.4},G:{available:false,score:null}}}},explain);
 assert.match(html,/32,4/);assert.match(html,/89,9/);assert.match(html,/Razón fuente/);assert.match(html,/Brecha fuente/);assert.match(html,/Dato a completar/);assert.match(html,/A completar/);assert.match(html,/85°/);
});

test('las fuentes y errores de la API no pueden inyectar contenido HTML',()=>{
 const html=H.comparisonHTML({site:{coord_source:'<img src=x onerror=alert(1)>'},target:{},error:'<script>bad</script>'},explain);
 assert.doesNotMatch(html,/<script>|<img/);assert.match(html,/&lt;script&gt;/);assert.match(html,/&lt;img/);
});

test('geología y acceso documentados sustituyen el pendiente sin inventar un puntaje operacional',()=>{
 const metric={value:0,unit:'km',quality:'derived',source:'https://nasa.gov/data',is_real:true,comparable:false};
 const match={score:65,missing:[],components:{G:{available:true,data_available:true,score:100,detail:{representation:'geology_categories_v0',coverage:{n_available:1,n_possible:2}}},O:{available:false,data_available:true,score:null,detail:{metrics:{dist_road_km:metric}}}}};
 const html=H.comparisonHTML({site:{},target:{},match},explain);
 assert.doesNotMatch(html,/Dato a completar/);assert.match(html,/1 de 2 bloques/);assert.match(html,/Operación \(O\) · acceso terrestre/);assert.match(html,/0 km/);assert.match(html,/fuera del TASI/);assert.match(html,/Detalle de los datos y fuentes/);
});

test('los datos de geología incluyen valores y fuentes de ambos cuerpos',()=>{
 const metric={value:1,unit:'fraction',quality:'derived',source:'https://usgs.gov/map',is_real:true};
 const html=H.comparisonHTML({site:{},target:{},detail:{features:{g_lito_basaltico:metric}},vector:{components:{G:{metrics:{g_lito_basaltico:metric}}}}},explain);
 assert.match(html,/Basáltico/);assert.match(html,/fracción 0–1/);assert.match(html,/usgs.gov/);
});
