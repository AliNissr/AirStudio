// الأثاث داخل الغرفة، بالمتر. نقي بدون three.js حتى نختبره بسرعة.
// الإحداثيات نفس المخطط: x لليمين، y لتحت (بالـ 3D تصير z). (x, y) = نص القطعة، rot بالراديان.

// المقاسات بالمتر: w عرض، d عمق، h ارتفاع. أرقام شائعة لأثاث البيت
export const FURNITURE = {
  sofa: { w: 2.0, d: 0.9, h: 0.85, label: 'كنبة' },
  table: { w: 1.4, d: 0.8, h: 0.75, label: 'طاولة' },
  chair: { w: 0.5, d: 0.5, h: 0.9, label: 'كرسي' },
  bed: { w: 1.6, d: 2.0, h: 0.5, label: 'سرير' },
  wardrobe: { w: 1.2, d: 0.6, h: 2.0, label: 'خزانة' },
};

const TAU = Math.PI * 2;
export const wrapRot = (r) => ((r % TAU) + TAU) % TAU;

// المساحة اللي تاخذها القطعة على الأرض بعد الدوران (مستطيل محيط بيها)
export function footprint({ type, rot = 0 }) {
  const { w, d } = FURNITURE[type], c = Math.abs(Math.cos(rot)), s = Math.abs(Math.sin(rot));
  return { w: w * c + d * s, d: w * s + d * c };
}

// shortcut: الحدود = مستطيل يحيط بالجدران، مو شكل الغرفة بالضبط؛ غرفة على شكل L تسمح بأثاث بالزاوية الفاضية
const clampAxis = (v, min, max, half) => (max - min < 2 * half ? (min + max) / 2 : Math.min(Math.max(v, min + half), max - half));

export class Room {
  constructor(bounds) {
    this.bounds = bounds; // {minX, minY, maxX, maxY}
    this.items = [];      // [{id, type, x, y, rot}]
    this.history = [];
    this.nextId = 1;
  }

  checkpoint() {
    this.history.push(JSON.stringify({ items: this.items, nextId: this.nextId }));
    if (this.history.length > 50) this.history.shift();
  }

  undo() {
    const last = this.history.pop();
    if (last) Object.assign(this, JSON.parse(last));
  }

  get(id) { return this.items.find((i) => i.id === id); }

  // يرجع مكان مسموح: القطعة كلها داخل الجدران
  clamp(item, pos) {
    const fp = footprint(item), b = this.bounds;
    return { x: clampAxis(pos.x, b.minX, b.maxX, fp.w / 2), y: clampAxis(pos.y, b.minY, b.maxY, fp.d / 2) };
  }

  add(type, pos, rot = 0) {
    if (!FURNITURE[type]) throw new Error(`نوع أثاث غير معروف: ${type}`);
    this.checkpoint();
    const item = { id: this.nextId++, type, rot: wrapRot(rot) };
    Object.assign(item, this.clamp(item, pos));
    this.items.push(item);
    return item;
  }

  // record=false: المتصل سوّى checkpoint بأول الحركة (سحبة وحدة = تراجع واحد)
  move(id, pos, record = true) {
    const item = this.get(id);
    if (!item) return;
    if (record) this.checkpoint();
    Object.assign(item, this.clamp(item, pos));
  }

  rotate(id, rot, record = true) {
    const item = this.get(id);
    if (!item) return;
    if (record) this.checkpoint();
    item.rot = wrapRot(rot);
    Object.assign(item, this.clamp(item, item)); // الدوران يغيّر المساحة، فنرجّعها داخل الجدران
  }

  remove(id) {
    if (!this.get(id)) return;
    this.checkpoint();
    this.items = this.items.filter((i) => i.id !== id);
  }

  // القطعة تحت النقطة (آخر وحدة انضافت فوك)، مع احتساب الدوران
  hitTest(p) {
    for (let i = this.items.length - 1; i >= 0; i--) {
      const it = this.items[i], { w, d } = FURNITURE[it.type];
      const dx = p.x - it.x, dy = p.y - it.y, c = Math.cos(-it.rot), s = Math.sin(-it.rot);
      if (Math.abs(dx * c - dy * s) <= w / 2 && Math.abs(dx * s + dy * c) <= d / 2) return it;
    }
    return null;
  }
}
