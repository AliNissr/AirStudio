// المشهد 3D: الجدران من المخطط، الأرضية، الأثاث، والكاميرا.
// يرسم بس لما شي يتغير (مو 60 مرة بالثانية) حتى ما ياكل المعالج.
import {
  WebGLRenderer, Scene, PerspectiveCamera, Color, HemisphereLight, DirectionalLight, Mesh, PlaneGeometry,
  BoxGeometry, MeshStandardMaterial, GridHelper, Raycaster, Vector2, Vector3, Plane, BoxHelper, PCFSoftShadowMap,
} from '../vendor/three/three.module.js';
import { buildFurniture } from './furniture.js';

const WALL_H = 2.6, WALL_T = 0.15;

// نحرر ذاكرة كارت الشاشة. materials=false للأثاث لأن خاماته مشتركة بين كل القطع
function dispose(obj, materials = true) {
  obj.traverse((o) => {
    o.geometry?.dispose();
    if (materials) [o.material].flat().forEach((m) => m?.dispose());
  });
}
const PRESETS = {
  persp: { yaw: Math.PI / 4, pitch: 0.62 },
  top: { yaw: 0, pitch: 1.55 },
  front: { yaw: 0, pitch: 0.18 },
  side: { yaw: Math.PI / 2, pitch: 0.18 },
};

export class RoomView {
  constructor(container) {
    this.container = container;
    // preserveDrawingBuffer: حتى نكدر نصدّر صورة PNG من آخر رسمة
    this.renderer = new WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = PCFSoftShadowMap;
    container.prepend(this.renderer.domElement);

    this.scene = new Scene();
    this.scene.background = new Color('#18212c');
    this.camera = new PerspectiveCamera(45, 1, 0.1, 200);
    this.scene.add(new HemisphereLight('#ffffff', '#3a4250', 1.6));
    const sun = new DirectionalLight('#fff4e0', 2.2);
    sun.position.set(6, 10, 4);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12 });
    this.sun = sun;
    this.scene.add(sun, sun.target);

    this.walls = [];
    this.meshes = new Map(); // id القطعة ← مجموعة 3D
    this.ghost = null;
    this.highlight = new BoxHelper(undefined, '#e8b341');
    this.highlight.visible = false;
    this.scene.add(this.highlight);
    this.orbit = { ...PRESETS.persp, dist: 9, target: new Vector3() };
    this.raycaster = new Raycaster();
    this.floorPlane = new Plane(new Vector3(0, 1, 0), 0);
    this.resize();
  }

  resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.render();
  }

  // الجدران والأرضية من المخطط. walls فاضية = غرفة افتراضية من bounds
  setRoom(walls, b) {
    for (const m of this.walls) { this.scene.remove(m); dispose(m); }
    this.walls = [];
    const cx = (b.minX + b.maxX) / 2, cz = (b.minY + b.maxY) / 2, w = b.maxX - b.minX, d = b.maxY - b.minY;
    const floor = new Mesh(new PlaneGeometry(w + 0.6, d + 0.6), new MeshStandardMaterial({ color: '#d9cbb3', roughness: 0.9 }));
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(cx, 0, cz);
    floor.receiveShadow = true;
    const grid = new GridHelper(Math.ceil(Math.max(w, d)) + 2, Math.ceil(Math.max(w, d)) + 2, '#b9a98e', '#c9b99e');
    grid.position.set(cx, 0.002, cz);
    this.walls.push(floor, grid);

    const list = walls.length ? walls : [ // ماكو جدران بالمخطط: نرسم مستطيل
      { a: { x: b.minX, y: b.minY }, b: { x: b.maxX, y: b.minY } }, { a: { x: b.maxX, y: b.minY }, b: { x: b.maxX, y: b.maxY } },
      { a: { x: b.maxX, y: b.maxY }, b: { x: b.minX, y: b.maxY } }, { a: { x: b.minX, y: b.maxY }, b: { x: b.minX, y: b.minY } },
    ];
    for (const wall of list) {
      const len = Math.hypot(wall.b.x - wall.a.x, wall.b.y - wall.a.y);
      const m = new Mesh(new BoxGeometry(len + WALL_T, WALL_H, WALL_T),
        new MeshStandardMaterial({ color: '#f1ede4', roughness: 0.95, transparent: true }));
      m.position.set((wall.a.x + wall.b.x) / 2, WALL_H / 2, (wall.a.y + wall.b.y) / 2);
      m.rotation.y = -Math.atan2(wall.b.y - wall.a.y, wall.b.x - wall.a.x);
      m.castShadow = m.receiveShadow = true;
      // اتجاه "برة الغرفة" لهذا الجدار، حتى نعرف إذا الكاميرا وراه
      m.userData.out = new Vector3(m.position.x - cx, 0, m.position.z - cz).normalize();
      this.walls.push(m);
    }
    this.scene.add(...this.walls);
    this.orbit.target.set(cx, 0.4, cz);
    this.orbit.dist = Math.max(w, d) * 1.6 + 2;
    this.baseDist = this.orbit.dist;
    this.sun.target.position.set(cx, 0, cz);
    this.render();
  }

  setPreset(name) {
    Object.assign(this.orbit, PRESETS[name], { dist: this.baseDist ?? this.orbit.dist });
    this.render();
  }

  // تكبير ودوران باليدين أو الماوس، نسبة لبداية الحركة
  beginGesture() { this.gestureBase = { yaw: this.orbit.yaw, dist: this.orbit.dist }; }
  applyGesture({ zoom, rotate }) {
    if (!this.gestureBase) this.beginGesture();
    const b = this.gestureBase;
    this.orbit.dist = Math.min(40, Math.max(2, b.dist / zoom)); // تبعّد اليدين = تقرّب
    this.orbit.yaw = b.yaw + rotate;
    this.render();
  }
  endGesture() { this.gestureBase = null; }

  orbitBy(dyaw, dpitch) {
    this.orbit.yaw += dyaw;
    this.orbit.pitch = Math.min(1.55, Math.max(0.08, this.orbit.pitch + dpitch));
    this.render();
  }
  zoomBy(factor) {
    this.orbit.dist = Math.min(40, Math.max(2, this.orbit.dist * factor));
    this.render();
  }

  // نقطة الشاشة (بكسل داخل الحاوية) ← نقطة على الأرض بالمتر {x, y}، أو null إذا تباوع للسما
  floorAt(px, py) {
    const ndc = new Vector2((px / this.container.clientWidth) * 2 - 1, -(py / this.container.clientHeight) * 2 + 1);
    this.raycaster.setFromCamera(ndc, this.camera);
    const hit = this.raycaster.ray.intersectPlane(this.floorPlane, new Vector3());
    return hit ? { x: hit.x, y: hit.z } : null;
  }

  // نزامن الأثاث ويه الـ Room (نضيف الجديد، نشيل الممسوح، ونحرّك الباقي)
  sync(items, { ghost = null, selected = null, removing = false } = {}) {
    const live = new Set(items.map((i) => i.id));
    for (const [id, g] of this.meshes) if (!live.has(id)) { this.scene.remove(g); dispose(g, false); this.meshes.delete(id); }
    for (const it of items) {
      let g = this.meshes.get(it.id);
      if (!g) { g = buildFurniture(it.type); this.meshes.set(it.id, g); this.scene.add(g); }
      g.position.set(it.x, 0, it.y);
      g.rotation.y = -it.rot; // y بالمخطط ينزل لتحت = z بالـ 3D، فالدوران معكوس
    }
    if (this.ghost && this.ghost.userData.type !== ghost?.type) { this.scene.remove(this.ghost); dispose(this.ghost); this.ghost = null; } // الشبح خاماته منسوخة، فنحررها
    if (ghost) {
      if (!this.ghost) {
        this.ghost = buildFurniture(ghost.type);
        this.ghost.traverse((o) => { if (o.material) { o.material = o.material.clone(); o.material.transparent = true; o.material.opacity = 0.5; } });
        this.scene.add(this.ghost);
      }
      this.ghost.position.set(ghost.x, 0, ghost.y);
    }
    const sel = selected && this.meshes.get(selected);
    this.highlight.visible = Boolean(sel);
    if (sel) {
      this.highlight.setFromObject(sel);
      this.highlight.material.color.set(removing ? '#e5484d' : '#e8b341');
    }
    this.render();
  }

  render() {
    const { yaw, pitch, dist, target } = this.orbit;
    this.camera.position.set(
      target.x + dist * Math.cos(pitch) * Math.sin(yaw),
      target.y + dist * Math.sin(pitch),
      target.z + dist * Math.cos(pitch) * Math.cos(yaw),
    );
    this.camera.lookAt(target);
    // الجدار اللي بين الكاميرا والغرفة يصير شفاف (مثل بيت الدمى)
    for (const m of this.walls) {
      if (!m.userData.out) continue;
      const toCam = this.camera.position.clone().sub(m.position).setY(0);
      m.material.opacity = toCam.dot(m.userData.out) > 0 && pitch < 1.4 ? 0.15 : 1;
      m.material.depthWrite = m.material.opacity === 1;
    }
    if (this.highlight.visible) this.highlight.update();
    this.renderer.render(this.scene, this.camera);
  }

  // صورة PNG من المنظر الحالي
  toBlob() {
    this.render();
    return new Promise((r) => this.renderer.domElement.toBlob(r, 'image/png'));
  }
}
