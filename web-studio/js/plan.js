// مخطط الغرفة: جدران (خطوط مستقيمة) ورسم حر، بالمتر. نقي بدون صفحة حتى نختبره.

const GRID = 0.1;                 // شبكة 10 سم
const ANGLE_STEP = Math.PI / 12;  // 15 درجة
const MIN_WALL = 0.2;             // أقصر من 20 سم = قرص بالغلط
const MAGNET = 0.3;               // نهاية الجدار تلتصق بزاوية موجودة إذا قريبة 30 سم
const MAX_HISTORY = 50;

const snap = (v, step) => Math.round(v / step) * step;
const round = (v) => Math.round(v * 1000) / 1000; // نشيل كسور مثل 2.9999999
const pt = (x, y) => ({ x: round(x), y: round(y) });
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

// أقرب مسافة من نقطة p لقطعة مستقيمة a-b
export function distToSegment(p, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, len2 = dx * dx + dy * dy;
  const t = len2 ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2)) : 0;
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

export class Plan {
  constructor() {
    this.walls = [];   // [{a:{x,y}, b:{x,y}}]
    this.strokes = []; // [[{x,y}, ...]]
    this.history = [];
  }

  // نحفظ نسخة قبل أي تغيير، حتى نكدر نتراجع
  checkpoint() {
    this.history.push(JSON.stringify({ walls: this.walls, strokes: this.strokes }));
    if (this.history.length > MAX_HISTORY) this.history.shift();
  }

  undo() {
    const last = this.history.pop();
    if (last) Object.assign(this, JSON.parse(last));
  }

  corners() {
    return this.walls.flatMap((w) => [w.a, w.b]);
  }

  // أقرب زاوية موجودة لـ p إذا ضمن المغناطيس
  magnet(p) {
    let best = null;
    for (const c of this.corners()) if (dist(c, p) < MAGNET && (!best || dist(c, p) < dist(best, p))) best = c;
    return best;
  }

  // يرجع الجدار بعد التعديل (شبكة، زاوية، مغناطيس)، بدون ما يضيفه. نستخدمه للمعاينة أيضاً
  snapWall(a0, b0) {
    const a = this.magnet(a0) ?? pt(snap(a0.x, GRID), snap(a0.y, GRID));
    const stuck = this.magnet(b0);
    if (stuck) return { a, b: { ...stuck } };
    const angle = snap(Math.atan2(b0.y - a.y, b0.x - a.x), ANGLE_STEP);
    const len = snap(dist(a, b0), GRID);
    return { a, b: pt(a.x + len * Math.cos(angle), a.y + len * Math.sin(angle)) };
  }

  addWall(a0, b0) {
    const w = this.snapWall(a0, b0);
    if (dist(w.a, w.b) < MIN_WALL) return null;
    this.checkpoint();
    this.walls.push(w);
    return w;
  }

  addStroke(points) {
    if (points.length < 2) return null;
    this.checkpoint();
    const s = points.map((p) => pt(p.x, p.y));
    this.strokes.push(s);
    return s;
  }

  // يمسح كل شي تلمسه دائرة (p, radius). record=false: المتصل سوّى checkpoint بنفسه (مسح بحركة وحدة)
  eraseAt(p, radius, record = true) {
    const walls = this.walls.filter((w) => distToSegment(p, w.a, w.b) > radius);
    const strokes = this.strokes.filter((s) => s.every((q) => dist(q, p) > radius));
    const removed = this.walls.length - walls.length + this.strokes.length - strokes.length;
    if (removed) {
      if (record) this.checkpoint();
      this.walls = walls;
      this.strokes = strokes;
    }
    return removed;
  }

  clear() {
    if (!this.walls.length && !this.strokes.length) return;
    this.checkpoint();
    this.walls = [];
    this.strokes = [];
  }

  get empty() { return !this.walls.length && !this.strokes.length; }

  bounds() {
    const cs = this.corners();
    if (!cs.length) return null;
    const xs = cs.map((c) => c.x), ys = cs.map((c) => c.y);
    return { minX: Math.min(...xs), minY: Math.min(...ys), maxX: Math.max(...xs), maxY: Math.max(...ys) };
  }
}
