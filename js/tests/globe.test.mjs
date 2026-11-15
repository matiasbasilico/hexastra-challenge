import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { latLonToXYZ, matchDialogHTML } from '../globe-data.mjs';
const require = createRequire(import.meta.url);
const explain = require('../explain.js');

const near = (a,b) => a.forEach((v,i) => assert.ok(Math.abs(v-b[i]) < 1e-10));
test('la longitud de los pines coincide con la textura equirectangular de Three.js', () => {
  near(latLonToXYZ(0,0), [1,0,0]);
  near(latLonToXYZ(0,90), [0,0,-1]);
  near(latLonToXYZ(0,-90), [0,0,1]);
  near(latLonToXYZ(90,0), [0,1,0]);
  near(latLonToXYZ(-90,0), [0,-1,0]);
  near(latLonToXYZ(0,180), [-1,0,0]);
  const point = latLonToXYZ(-32.4,-69.1,1.008);
  assert.ok(Math.abs(Math.hypot(...point)-1.008) < 1e-10);
});

test('el modal usa el puntaje y las razones del par, con componentes ausentes explícitos', () => {
  const html = matchDialogHTML({
    site: {name:'Sitio <script>no ejecutar</script>'}, target:{name:'Destino'},
    match: {score:32.4, why:'Analogía verificada', breaks:'Brecha verificada', components:{G:{available:false,score:null}, E:{available:true,score:32.4}}},
  }, explain);
  assert.match(html,/32,4/);
  assert.match(html,/Analogía verificada/);
  assert.match(html,/Brecha verificada/);
  assert.match(html,/Dato a completar:/);
  assert.match(html,/&lt;script&gt;/);
  assert.doesNotMatch(html,/<script>/);
});

test('un sitio sin comparación nunca hereda ni inventa un puntaje', () => {
  const html = matchDialogHTML({site:{name:'Sitio sin comparar'},match:null},explain);
  assert.match(html,/Sin puntaje/);
  assert.match(html,/buscá análogos/);
  assert.doesNotMatch(html,/de 100, TASI/);
});

test('la rotación sideral usa tiempo real, conserva su velocidad entre frames y pausa sin retroceder', async () => {
  const {earthRotationAngle,EARTH_SIDEREAL_SECONDS}=await import('../globe-data.mjs');
  assert.equal(EARTH_SIDEREAL_SECONDS,23.9345*3600);
  assert.ok(Math.abs(earthRotationAngle(EARTH_SIDEREAL_SECONDS*1000)-2*Math.PI)<1e-12);
  assert.ok(Math.abs(earthRotationAngle(1000)+earthRotationAngle(9000)-earthRotationAngle(10000))<1e-12);
  assert.ok(earthRotationAngle(1000)<0.00008);
  assert.equal(earthRotationAngle(-1),0);
  assert.equal(earthRotationAngle(NaN),0);
});
