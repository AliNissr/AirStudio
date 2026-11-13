// طبقة اليدين "النقية": بدون كاميرا ولا صفحة، حتى نختبرها بـ node على نفس fixtures المحرك.
import { GestureClassifier } from '../../engine/js/gestures.js';
import { OneEuroFilter } from '../../engine/js/one_euro.js';

const ANCHOR = 9; // قاعدة الوسطى: أثبت نقطة باليد (ما تتحرك لما تقرص أو تسكّر)
const GRAB = new Set(['FIST', 'PINCH']); // إيماءات "الإمساك" اللي تبدي التكبير والدوران

const center = (pts) => ({ x: pts[ANCHOR][0], y: pts[ANCHOR][1] });
const wrapAngle = (a) => Math.atan2(Math.sin(a), Math.cos(a)); // أي زاوية ← بين -π و π

// المسافة والزاوية والمركز بين يدين
export function twoHandMetrics(a, b) {
  const p = center(a), q = center(b);
  return {
    distance: Math.hypot(q.x - p.x, q.y - p.y),
    angle: Math.atan2(q.y - p.y, q.x - p.x),
    center: { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 },
  };
}

// MediaPipe ما يضمن نفس الترتيب كل إطار، فنعطي كل يد رقم (id) ثابت حسب أقرب مكان للإطار السابق
export function matchHands(prev, current) {
  if (!prev.length) {
    // أول مرة: اليد الأيسر بالشاشة = 0
    return [...current]
      .sort((a, b) => center(a.landmarks).x - center(b.landmarks).x)
      .map((h, id) => ({ ...h, id }));
  }
  const pairs = [];
  current.forEach((h, i) => prev.forEach((p) => {
    const c = center(h.landmarks), d = center(p.landmarks);
    pairs.push({ i, id: p.id, dist: Math.hypot(c.x - d.x, c.y - d.y) });
  }));
  pairs.sort((a, b) => a.dist - b.dist); // الأقرب أول (طريقة "جشعة": تكفي ليدين)
  const ids = new Map(), used = new Set();
  for (const { i, id } of pairs) {
    if (!ids.has(i) && !used.has(id)) { ids.set(i, id); used.add(id); }
  }
  let next = Math.max(...prev.map((p) => p.id)) + 1;
  return current.map((h, i) => ({ ...h, id: ids.has(i) ? ids.get(i) : next++ }));
}

// تكبير ودوران باليدين: يبدي لما اليدين بنفس إيماءة الإمساك، ويرجع نسبة مقارنة ببداية الإيماءة
export class TwoHandGesture {
  constructor() { this.base = null; }

  update(hands) {
    const [a, b] = [...hands].sort((x, y) => x.id - y.id);
    const active = hands.length === 2 && GRAB.has(a.gesture) && a.gesture === b.gesture;
    if (!active) {
      this.base = null; // انتهت: المرة الجاية تبدي من جديد بدون قفزة
      return null;
    }
    const m = twoHandMetrics(a.landmarks, b.landmarks);
    this.base ??= m;
    return { zoom: m.distance / (this.base.distance || 1e-6), rotate: wrapAngle(m.angle - this.base.angle), center: m.center };
  }
}

// يجمع كلشي: أرقام ثابتة لليدين، مصنّف وفلتر لكل يد، وإيماءة اليدين
export class HandPipeline {
  constructor(config) {
    this.config = config;
    this.prev = [];
    this.state = new Map(); // id ← { classifier, fx, fy }
    this.two = new TwoHandGesture();
  }

  // raw: [{landmarks بالبكسل, side}]، t بالثواني، w و h أبعاد الصورة
  process(raw, t, w, h) {
    const matched = matchHands(this.prev, raw);
    const live = new Set(matched.map((m) => m.id));
    for (const id of this.state.keys()) if (!live.has(id)) this.state.delete(id); // اليد طلعت: ننساها
    const hands = matched.map((m) => {
      let s = this.state.get(m.id);
      if (!s) {
        s = { classifier: new GestureClassifier(this.config), fx: new OneEuroFilter(this.config.one_euro), fy: new OneEuroFilter(this.config.one_euro) };
        this.state.set(m.id, s);
      }
      const p = m.landmarks;
      // المؤشر بين طرف الإبهام والسبابة: ما يتحرك لما تقرص (طرف السبابة وحده ينزل شوية وقت القرص)
      const x = (p[4][0] + p[8][0]) / 2, y = (p[4][1] + p[8][1]) / 2;
      return {
        id: m.id,
        side: m.side,
        gesture: s.classifier.update(p),
        pointer: { x: s.fx.filter(x, t) / w, y: s.fy.filter(y, t) / h },
        landmarks: p,
      };
    });
    this.prev = matched;
    return { hands, two: this.two.update(hands) };
  }
}
