// حفظ التصميم وقراءته. أي ملف JSON جاي من برة (أو من localStorage) نعتبره غير موثوق:
// نفحص كل حقل، ونبني نسخة جديدة بالحقول اللي نعرفها بس.
import { FURNITURE } from './layout.js';

export const MAX_BYTES = 5_000_000;
const LIMITS = { walls: 500, strokes: 500, points: 5000, items: 200, coord: 1000 };

export function serialize(plan, room) {
  return {
    app: 'airstudio',
    version: 1,
    walls: plan.walls,
    strokes: plan.strokes,
    items: room.items.map(({ id, type, x, y, rot }) => ({ id, type, x, y, rot })),
  };
}

class Bad extends Error {}
const num = (v) => {
  if (typeof v !== 'number' || !Number.isFinite(v) || Math.abs(v) > LIMITS.coord) throw new Bad();
  return v;
};
const point = (p) => ({ x: num(p?.x), y: num(p?.y) });
const list = (v, max) => {
  if (!Array.isArray(v) || v.length > max) throw new Bad();
  return v;
};

// يرجع {ok: true, design} أو {ok: false, error: كود} (الكود مفتاح رسالة بـ messages.js)
export function parseDesign(text) {
  if (typeof text !== 'string' || text.length > MAX_BYTES) return { ok: false, error: 'TOO_BIG' };
  let raw;
  try { raw = JSON.parse(text); } catch { return { ok: false, error: 'BAD_JSON' }; }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || raw.app !== 'airstudio') return { ok: false, error: 'NOT_DESIGN' };
  if (raw.version !== 1) return { ok: false, error: 'BAD_VERSION' };
  try {
    const ids = new Set();
    const design = {
      walls: list(raw.walls, LIMITS.walls).map((w) => ({ a: point(w?.a), b: point(w?.b) })),
      strokes: list(raw.strokes, LIMITS.strokes).map((s) => list(s, LIMITS.points).map(point)),
      items: list(raw.items, LIMITS.items).map((it) => {
        if (!Object.hasOwn(FURNITURE, it?.type) || !Number.isInteger(it.id) || it.id < 1 || ids.has(it.id)) throw new Bad();
        ids.add(it.id);
        return { id: it.id, type: it.type, x: num(it.x), y: num(it.y), rot: num(it.rot) };
      }),
    };
    return { ok: true, design };
  } catch (e) {
    if (e instanceof Bad) return { ok: false, error: 'BAD_DATA' };
    throw e;
  }
}

// يحط التصميم بالمخطط والغرفة، وتكدر تتراجع عنه
export function applyDesign(design, plan, room) {
  plan.checkpoint();
  plan.walls = design.walls;
  plan.strokes = design.strokes;
  room.checkpoint();
  room.items = design.items.map((i) => ({ ...i }));
  room.nextId = Math.max(0, ...room.items.map((i) => i.id)) + 1;
}
