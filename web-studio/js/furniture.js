// قطع الأثاث 3D من أشكال بسيطة (صناديق واسطوانات)، بدون ملفات نماذج.
// المقاسات من FURNITURE بـ layout.js. نقطة الأصل = نص القطعة على الأرض.
import { Group, Mesh, BoxGeometry, CylinderGeometry, MeshStandardMaterial } from '../vendor/three/three.module.js';
import { FURNITURE } from './layout.js';

const mat = (color, roughness = 0.8) => new MeshStandardMaterial({ color, roughness });
const M = {
  fabric: mat('#6b7f99'), cushion: mat('#7f93ad'), wood: mat('#a87b51', 0.6), darkWood: mat('#6e4c32', 0.6),
  metal: mat('#8a8f98', 0.4), linen: mat('#e9e4da'), blanket: mat('#5f8f86'), white: mat('#f1efea', 0.5),
};

// صندوق: w عرض (x)، h ارتفاع، d عمق (z)، ومكانه (x, y = ارتفاع القاعدة، z)
function box(g, w, h, d, material, x = 0, y = 0, z = 0) {
  const m = new Mesh(new BoxGeometry(w, h, d), material);
  m.position.set(x, y + h / 2, z);
  m.castShadow = m.receiveShadow = true;
  g.add(m);
  return m;
}

function leg(g, x, z, h, r = 0.025, material = M.metal) {
  const m = new Mesh(new CylinderGeometry(r, r, h, 10), material);
  m.position.set(x, h / 2, z);
  m.castShadow = true;
  g.add(m);
}

const BUILDERS = {
  sofa(g, { w, d, h }) {
    box(g, w, 0.42, d, M.fabric);                                   // القاعدة
    box(g, w, h - 0.42, 0.2, M.fabric, 0, 0.42, -d / 2 + 0.1);     // الظهر
    box(g, 0.18, 0.2, d, M.fabric, -w / 2 + 0.09, 0.42);            // المساند
    box(g, 0.18, 0.2, d, M.fabric, w / 2 - 0.09, 0.42);
    for (const x of [-w / 4 + 0.05, w / 4 - 0.05]) box(g, w / 2 - 0.24, 0.12, d - 0.26, M.cushion, x, 0.42, 0.08); // المخدات
  },
  table(g, { w, d, h }) {
    box(g, w, 0.04, d, M.wood, 0, h - 0.04);
    for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) leg(g, x * (w / 2 - 0.07), z * (d / 2 - 0.07), h - 0.04, 0.025, M.darkWood);
  },
  chair(g, { w, d, h }) {
    box(g, w, 0.04, d, M.wood, 0, 0.45);
    box(g, w, h - 0.49, 0.04, M.wood, 0, 0.49, -d / 2 + 0.02);
    for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) leg(g, x * (w / 2 - 0.04), z * (d / 2 - 0.04), 0.45, 0.018, M.darkWood);
  },
  bed(g, { w, d, h }) {
    box(g, w, 0.25, d, M.darkWood);                                  // الإطار
    box(g, w - 0.06, h - 0.25, d - 0.06, M.linen, 0, 0.25);          // الدوشك
    box(g, w, 0.9, 0.08, M.darkWood, 0, 0, -d / 2 + 0.04);           // ظهر السرير
    box(g, w - 0.04, 0.04, d * 0.62, M.blanket, 0, h, d * 0.17);    // البطانية
    for (const x of [-w / 4, w / 4]) box(g, w / 2 - 0.15, 0.1, 0.35, M.white, x, h, -d / 2 + 0.3); // المخدات
  },
  wardrobe(g, { w, d, h }) {
    box(g, w, h, d, M.wood);
    box(g, 0.01, h - 0.1, 0.01, M.darkWood, 0, 0.05, d / 2 + 0.005); // خط بين البابين
    for (const x of [-0.06, 0.06]) box(g, 0.02, 0.25, 0.03, M.metal, x, h / 2 - 0.12, d / 2 + 0.015); // المقابض
  },
};

export function buildFurniture(type) {
  const g = new Group();
  BUILDERS[type](g, FURNITURE[type]);
  g.userData.type = type;
  return g;
}
