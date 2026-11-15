/* Globo geográfico HexAstra: referencia visual Earth3D (mitchcamza), integración propia.
 * La imagen es ilustrativa; los puntos y los puntajes siguen viniendo de las APIs.
 * La geometría no gira sola: la longitud del sitio debe permanecer sobre su textura. */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

import { latLonToXYZ, matchDialogHTML } from './globe-data.mjs';
import { createPlanetCards } from './planet-cards.mjs';

function openMatch(context) {
  let dialog = document.getElementById('match-dialog');
  if (!dialog) {
    dialog = document.createElement('dialog');
    dialog.id = 'match-dialog';
    dialog.className = 'match-dialog';
    dialog.setAttribute('aria-labelledby', 'match-dialog-title');
    document.body.append(dialog);
  }
  dialog.innerHTML = matchDialogHTML(context || {}, window.HexastraExplain);
  if (!dialog.open) dialog.showModal();
}

export function attach(map, options = {}) {
  const host = map.getContainer();
  const shell = document.createElement('div');
  shell.className = 'earth-globe';
  shell.innerHTML = '<canvas class="globe-canvas" aria-label="Globo terrestre 3D: arrastrá para girar y usá los botones para acercar" tabindex="0"></canvas><div class="globe-pins"></div><p class="globe-guide">Arrastrá para explorar · Tocá un punto</p><div class="globe-zoom"><button type="button" data-zoom="in" aria-label="Acercar el globo">+</button><button type="button" data-zoom="out" aria-label="Alejar el globo">−</button><button type="button" data-zoom="home" aria-label="Ver el planeta completo">↺</button></div><p class="globe-credits"><a href="https://github.com/mitchcamza/Earth3D" target="_blank" rel="noopener">Earth3D</a> · <a href="https://www.solarsystemscope.com/textures/" target="_blank" rel="noopener">Textura: Solar System Scope, CC BY 4.0</a></p>';
  host.append(shell);
  const canvas = shell.querySelector('canvas');
  const pins = shell.querySelector('.globe-pins');
  const tools = options.tools || document.createElement('div');
  if (!options.tools) {
    tools.className = 'globe-view-switch';
    host.append(tools);
    tools.innerHTML = '<button type="button" data-view="flat">Mapa 2D</button>';
  }
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = options.tools ? 'easy-map-btn' : '';
  toggle.textContent = 'Globo 3D';
  toggle.dataset.view = 'globe';
  toggle.setAttribute('aria-pressed', 'true');
  tools.prepend(toggle);

  let scene, camera, renderer, controls, observer;
  let desired = true, failed = false, frame = 0, tween = null, fitDistance = 3.5;
  const entries = new Map();
  const projected = new THREE.Vector3();
  const horizon = new THREE.Vector3();
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const visible = () => host.clientWidth > 0 && host.clientHeight > 0 && desired && !failed && !document.hidden;
  const schedule = () => { if (!frame && renderer && visible()) frame = requestAnimationFrame(draw); };

  function setMode(globe) {
    desired = globe && !failed;
    if (desired) initialize();
    const active = desired && !!renderer;
    host.classList.toggle('earth-globe-mode', active);
    shell.hidden = !active;
    ['dragging', 'scrollWheelZoom', 'keyboard'].forEach(key => {
      if (active) map[key]?.disable();
      else map[key]?.enable();
    });
    tools.querySelectorAll('button').forEach(b => {
      const selected = active ? b === toggle : b !== toggle && (b.dataset.view === 'flat' || b.id === (options.flatButton || 'easy-basemap-sat'));
      b.setAttribute('aria-pressed', String(selected));
      if (options.tools) b.classList.toggle('is-active', selected);
    });
    if (active) resize();
    else map.invalidateSize({ pan: false });
  }
  tools.addEventListener('click', e => {
    const button = e.target.closest('button');
    if (!button) return;
    if (button !== toggle && button.id) options.flatButton = button.id;
    setMode(button === toggle);
  });

  function initialize() {
    if (renderer || failed || !host.clientWidth || !host.clientHeight) return;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'low-power' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(42, 1, 0.1, 30);
      const center = map.getCenter();
      camera.position.fromArray(latLonToXYZ(center.lat, center.lng, fitDistance));
      controls = new OrbitControls(camera, canvas);
      controls.enablePan = false;
      controls.enableDamping = false;
      controls.minDistance = 1.7;
      controls.maxDistance = 5.5;
      controls.rotateSpeed = 0.6;
      controls.addEventListener('change', schedule);
      controls.addEventListener('start', () => { tween = null; });
      scene.add(new THREE.AmbientLight(0xffffff, options.immersive ? 1.6 : 2.0));
      const sun = new THREE.DirectionalLight(0xffffff, options.immersive ? 2.2 : 2.4);
      sun.position.set(-3, 4, 5);
      scene.add(sun);
      const material = new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: 8 });
      const texture = new THREE.TextureLoader().load('assets/globe/earth-day.jpg', schedule, undefined, () => {
        failed = true;
        toggle.disabled = true;
        toggle.title = 'No se pudo cargar el globo. Usá el mapa 2D.';
        setMode(false);
      });
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 4);
      material.map = texture;
      const geometry = new THREE.SphereGeometry(1, 64, 48);
      scene.add(new THREE.Mesh(geometry, material));
      if (options.immersive) {
        const clouds = new THREE.TextureLoader().load('assets/globe/earth-clouds.jpg', schedule);
        const cloudLayer = new THREE.Mesh(geometry, new THREE.MeshPhongMaterial({
          color: 0xffffff, alphaMap: clouds, transparent: true, opacity: 0.18, depthWrite: false,
        }));
        cloudLayer.scale.setScalar(1.003);
        scene.add(cloudLayer);
      }
      const accent = getComputedStyle(host).getPropertyValue('--hx-cian').trim();
      const atmosphere = new THREE.Mesh(geometry, new THREE.ShaderMaterial({
        uniforms: { glow: { value: new THREE.Color(accent) } },
        vertexShader: 'varying vec3 n; varying vec3 v; void main(){ vec4 p=modelViewMatrix*vec4(position,1.0); n=normalize(normalMatrix*normal); v=normalize(-p.xyz); gl_Position=projectionMatrix*p; }',
        fragmentShader: 'uniform vec3 glow; varying vec3 n; varying vec3 v; void main(){ float rim=pow(1.0-abs(dot(normalize(n),normalize(v))),3.0); gl_FragColor=vec4(glow,rim*0.5); }',
        side: THREE.BackSide, transparent: true, depthWrite: false,
      }));
      atmosphere.scale.setScalar(1.035);
      scene.add(atmosphere);
      canvas.addEventListener('webglcontextlost', e => {
        e.preventDefault(); failed = true; toggle.disabled = true;
        toggle.title = 'La vista 3D no está disponible. Usá el mapa 2D.';
        setMode(false);
      });
      canvas.addEventListener('keydown', e => {
        if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','Home'].includes(e.key)) return;
        e.preventDefault();
        const sph = new THREE.Spherical().setFromVector3(camera.position);
        if (e.key === 'ArrowLeft') sph.theta -= 0.1;
        if (e.key === 'ArrowRight') sph.theta += 0.1;
        if (e.key === 'ArrowUp') sph.phi -= 0.1;
        if (e.key === 'ArrowDown') sph.phi += 0.1;
        if (e.key === '+') sph.radius *= 0.85;
        if (e.key === '-') sph.radius *= 1.15;
        if (e.key === 'Home') sph.radius = 3.5;
        sph.phi = Math.max(0.05, Math.min(Math.PI - 0.05, sph.phi));
        sph.radius = Math.max(controls.minDistance, Math.min(controls.maxDistance, sph.radius));
        tween = null;
        camera.position.setFromSpherical(sph); controls.update(); schedule();
      });
    } catch (error) {
      failed = true;
      renderer?.dispose();
      renderer = null;
      toggle.disabled = true;
      toggle.title = 'Este navegador no tiene WebGL disponible. Usá el mapa 2D.';
    }
  }

  function sync() {
    const remaining = new Set(entries.keys());
    map.eachLayer(layer => {
      if (!layer.getLatLng || !layer.options.icon) return;
      const ll = layer.getLatLng();
      if (!Number.isFinite(ll.lat) || !Number.isFinite(ll.lng)) return;
      remaining.delete(layer);
      let entry = entries.get(layer);
      if (!entry) {
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'globe-pin';
        button.hidden = true;
        button.setAttribute('aria-label', layer.options.title || layer.options.alt || 'Sitio terrestre');
        button.title = layer.options.title || '';
        button.addEventListener('click', async e => {
          e.stopPropagation();
          layer.fire('click');
          const context = await options.getContext?.(layer);
          if (context) openMatch(context);
        });
        pins.append(button);
        entry = { button, html: '', position: new THREE.Vector3() };
        entries.set(layer, entry);
      }
      entry.position.fromArray(latLonToXYZ(ll.lat, ll.lng, 1.008));
      const html = layer.options.icon.options?.html || '<span class="pin earth"></span>';
      if (entry.html !== html) { entry.button.innerHTML = html; entry.html = html; }
      entry.button.classList.toggle('is-selected', /(?:is-active|\bactive\b)/.test(html));
      entry.button.dataset.lat = ll.lat;
      entry.button.dataset.lon = ll.lng;
      if (layer.hexastraSite?.id) entry.button.dataset.siteId = layer.hexastraSite.id;
    });
    remaining.forEach(layer => { entries.get(layer).button.remove(); entries.delete(layer); });
    schedule();
  }

  function focus() {
    if (!camera) return;
    const center = map.getCenter();
    const to = new THREE.Vector3().fromArray(latLonToXYZ(center.lat, center.lng, fitDistance));
    if (reduced() || !visible()) { camera.position.copy(to); controls.update(); }
    else tween = { from: camera.position.clone(), to, start: performance.now() };
    schedule();
  }

  function resize() {
    if (!renderer && desired) initialize();
    if (!renderer || !host.clientWidth || !host.clientHeight) return;
    host.classList.toggle('earth-globe-mode', desired);
    shell.hidden = !desired;
    if (desired) {
      ['dragging', 'scrollWheelZoom', 'keyboard'].forEach(key => map[key]?.disable());
      tools.querySelectorAll('button').forEach(button => {
        button.setAttribute('aria-pressed', String(button === toggle));
        if (options.tools) button.classList.toggle('is-active', button === toggle);
      });
    }
    camera.aspect = host.clientWidth / host.clientHeight;
    const nextFit = 1.08 / Math.sin(Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * Math.min(1, camera.aspect)));
    const scale = nextFit / fitDistance;
    camera.position.multiplyScalar(scale);
    if (tween) { tween.from.multiplyScalar(scale); tween.to.multiplyScalar(scale); }
    fitDistance = nextFit;
    controls.maxDistance = Math.max(5.5, fitDistance * 1.8);
    camera.updateProjectionMatrix();
    renderer.setSize(host.clientWidth, host.clientHeight, false);
    // setSize borra el canvas: dibujar en el mismo ciclo evita un planeta vacío al abrir una pieza flotante.
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    if (visible()) draw(performance.now());
  }

  function draw(now) {
    frame = 0;
    if (!visible()) return;
    if (tween) {
      const t = Math.min(1, (now - tween.start) / 700);
      camera.position.copy(tween.from).lerp(tween.to, t*t*(3-2*t));
      if (t === 1) tween = null;
    }
    controls.update();
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    renderer.render(scene, camera);
    entries.forEach(entry => {
      // Solo los puntos por delante del horizonte son visibles y alcanzables con Tab.
      const front = horizon.copy(camera.position).sub(entry.position).dot(entry.position) > 0;
      projected.copy(entry.position).project(camera);
      const onScreen = front && Math.abs(projected.x) < 0.98 && Math.abs(projected.y) < 0.95;
      entry.button.hidden = !onScreen;
      if (onScreen) {
        entry.button.style.left = `${(projected.x + 1) * host.clientWidth / 2}px`;
        entry.button.style.top = `${(1 - projected.y) * host.clientHeight / 2}px`;
      }
    });
    if (tween) schedule();
  }

  shell.querySelectorAll('[data-zoom]').forEach(button => button.addEventListener('click', () => {
    if (!camera) return;
    tween = null;
    const action = button.dataset.zoom;
    const distance = action === 'home' ? fitDistance : camera.position.length() * (action === 'in' ? 0.8 : 1.25);
    camera.position.setLength(Math.max(1.7, Math.min(controls.maxDistance, distance)));
    controls.update(); schedule();
  }));
  map.on('layeradd layerremove', sync);
  map.on('moveend', focus);
  map.on('resize', resize);
  const markerObserver = new MutationObserver(sync);
  markerObserver.observe(map.getPane('markerPane'), { childList: true, subtree: true });
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(resize);
    observer.observe(host);
  }
  document.addEventListener('visibilitychange', schedule);
  initialize(); setMode(true); sync();
  return { setMode, sync, focus, resize, openMatch };
}

if (typeof window !== 'undefined') window.HexastraGlobe = { attach, openMatch, createPlanetCards };
