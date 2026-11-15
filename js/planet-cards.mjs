/* Previsualizaciones 3D ilustrativas. Un solo contexto WebGL para las dos cards. */
import * as THREE from 'three';

export function createPlanetCards(dialog) {
  const field = dialog.querySelector('.body-options');
  if (!field) return null;
  const canvas = document.createElement('canvas');
  canvas.className = 'planet-card-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  field.append(canvas);
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'low-power' });
  } catch (e) {
    canvas.remove();
    return { render() {} };
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.autoClear = false;
  const loader = new THREE.TextureLoader();
  const geometry = new THREE.SphereGeometry(1, 48, 32);
  let loaded = 0, failed = false, frame = 0;
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const planets = Array.from(field.querySelectorAll('.planet-card')).map(card => {
    const body = card.querySelector('input').value;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 20);
    camera.position.set(0, 0, 3.8);
    scene.add(new THREE.AmbientLight(0xffffff, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 2.5);
    sun.position.set(-3, 2, 4);
    scene.add(sun);
    const material = new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0 });
    const texture = loader.load(`assets/globe/${body}.jpg`, () => {
      loaded++;
      if (loaded === 2 && !failed) field.classList.add('has-planet-previews');
      schedule();
    }, undefined, () => { failed = true; field.classList.remove('has-planet-previews'); });
    texture.colorSpace = THREE.SRGBColorSpace;
    material.map = texture;
    const planet = new THREE.Mesh(geometry, material);
    const base = body === 'mars' ? 0.35 : -0.5;
    planet.rotation.y = base;
    planet.rotation.x = 0.12;
    scene.add(planet);
    card.addEventListener('pointermove', event => {
      if (reduced()) return;
      const r = card.getBoundingClientRect();
      planet.rotation.y = base + ((event.clientX - r.left) / r.width - 0.5) * 0.35;
      planet.rotation.x = 0.12 + ((event.clientY - r.top) / r.height - 0.5) * 0.15;
      schedule();
    });
    card.addEventListener('pointerleave', () => { planet.rotation.set(0.12, base, 0); schedule(); });
    return { card, scene, camera, visual: card.querySelector('.planet-visual') };
  });

  function schedule() { if (!frame) frame = requestAnimationFrame(render); }
  function render() {
    frame = 0;
    if (!dialog.open || !field.clientWidth || !field.clientHeight || failed) return;
    // El canvas de un fieldset se posiciona después del legend: usar su rect real evita deformar las esferas.
    const root = canvas.getBoundingClientRect();
    if (!root.width || !root.height) return;
    renderer.setSize(root.width, root.height, false);
    renderer.setScissorTest(false);
    renderer.clear();
    renderer.setScissorTest(true);
    planets.forEach(({ visual, scene, camera }) => {
      const r = visual.getBoundingClientRect();
      if (!r.width || !r.height) return;
      const x = r.left - root.left, y = root.bottom - r.bottom;
      camera.aspect = r.width / r.height;
      camera.updateProjectionMatrix();
      renderer.setViewport(x, y, r.width, r.height);
      renderer.setScissor(x, y, r.width, r.height);
      renderer.render(scene, camera);
    });
    renderer.setScissorTest(false);
  }
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(schedule).observe(field);
  document.fonts?.ready.then(schedule);
  field.addEventListener('change', schedule);
  render();
  return { render: schedule };
}
