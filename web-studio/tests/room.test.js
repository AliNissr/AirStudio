import { test } from 'node:test';
import assert from 'node:assert/strict';
import { FURNITURE, Room, footprint, wrapRot } from '../js/layout.js';
import { RoomInteraction } from '../js/room_interaction.js';
import { buildFurniture } from '../js/furniture.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);
const BOUNDS = { minX: 0, minY: 0, maxX: 5, maxY: 4 };

// ===== الغرفة =====

test('furniture clamped inside room', () => {
  const r = new Room(BOUNDS);
  const sofa = r.add('sofa', { x: -3, y: 10 });           // الكنبة 2.0 × 0.9
  near(sofa.x, 1.0);                                        // نص العرض من الجدار
  near(sofa.y, 4 - 0.45);
});

test('rotated furniture uses its rotated footprint', () => {
  const r = new Room(BOUNDS);
  const sofa = r.add('sofa', { x: 2, y: 2 });
  r.rotate(sofa.id, Math.PI / 2);
  r.move(sofa.id, { x: 100, y: 100 });
  near(r.get(sofa.id).x, 5 - 0.45);                         // صار عرضها 0.9
  near(r.get(sofa.id).y, 4 - 1.0);
  const fp = footprint({ type: 'sofa', rot: Math.PI / 4 });
  near(fp.w, fp.d);                                         // بزاوية 45 العرض والعمق متساويين
});

test('rotate wraps to 0..2π', () => {
  near(wrapRot(-Math.PI / 2), 1.5 * Math.PI);
  near(wrapRot(5 * Math.PI), Math.PI);
});

test('room smaller than furniture centres it instead of escaping', () => {
  const r = new Room({ minX: 0, minY: 0, maxX: 1, maxY: 1 });
  const bed = r.add('bed', { x: 9, y: 9 });
  near(bed.x, 0.5);
  near(bed.y, 0.5);
});

test('hitTest finds the item under a point, respecting rotation', () => {
  const r = new Room(BOUNDS);
  const sofa = r.add('sofa', { x: 2.5, y: 2 });
  assert.equal(r.hitTest({ x: 3.3, y: 2 })?.id, sofa.id);  // جوه (العرض 2 م)
  r.rotate(sofa.id, Math.PI / 2);
  assert.equal(r.hitTest({ x: 3.3, y: 2 }), null);          // بعد الدوران صار عرضها 0.9
  assert.equal(r.hitTest({ x: 2.5, y: 2.9 })?.id, sofa.id);
});

test('add, remove and undo', () => {
  const r = new Room(BOUNDS);
  const a = r.add('chair', { x: 1, y: 1 });
  r.add('table', { x: 3, y: 2 });
  r.remove(a.id);
  assert.equal(r.items.length, 1);
  r.undo();
  assert.equal(r.items.length, 2);
  r.undo();
  r.undo();
  r.undo(); // زيادة ما يخرّب
  assert.equal(r.items.length, 0);
});

test('unknown furniture type rejected', () => {
  assert.throws(() => new Room(BOUNDS).add('piano', { x: 1, y: 1 }));
});

test('every furniture type builds a 3D group of the right size', () => {
  for (const [type, spec] of Object.entries(FURNITURE)) {
    const g = buildFurniture(type);
    assert.ok(g.children.length > 0, type);
    assert.equal(g.userData.type, type);
    assert.ok(spec.w > 0 && spec.d > 0 && spec.h > 0 && spec.label, type);
  }
});

// ===== الإيماءات بالغرفة =====

const hand = (gesture, floor, extra = {}) => ({ id: 0, gesture, floor, ...extra });
const frame = (...hands) => ({ hands, two: null });

test('pinch on palette, drag, release places the item', () => {
  const r = new Room(BOUNDS), ui = new RoomInteraction(r);
  ui.update(frame(hand('PINCH', null, { palette: 'chair' })));
  const s = ui.update(frame(hand('PINCH', { x: 2, y: 2 })));
  assert.equal(s.ghost.type, 'chair');                     // شبح أثناء السحب
  ui.update(frame(hand('PINCH', { x: 3, y: 1 })));
  ui.update(frame(hand('NONE', { x: 4, y: 3 })));          // الإفلات
  assert.equal(r.items.length, 1);
  assert.deepEqual([r.items[0].x, r.items[0].y], [3, 1]); // آخر نقطة وانت قارص
});

test('hand lost while carrying a new item drops nothing', () => {
  const r = new Room(BOUNDS), ui = new RoomInteraction(r);
  ui.update(frame(hand('PINCH', null, { palette: 'bed' })));
  ui.update(frame(hand('PINCH', { x: 2, y: 2 })));
  ui.update(frame());
  assert.equal(r.items.length, 0);
});

test('fist on an item drags it, as one undo step', () => {
  const r = new Room(BOUNDS), ui = new RoomInteraction(r);
  const t = r.add('table', { x: 1, y: 1 });
  ui.update(frame(hand('FIST', { x: 1.1, y: 1 })));
  ui.update(frame(hand('FIST', { x: 2.1, y: 2 })));
  ui.update(frame(hand('FIST', { x: 3.1, y: 2 })));
  ui.update(frame(hand('NONE', { x: 3.1, y: 2 })));
  near(r.get(t.id).x, 3);                                   // يتحرك بنفس الإزاحة، ما يقفز لنص المؤشر
  r.undo();
  near(r.get(t.id).x, 1);
});

test('hand lost while moving puts the item back', () => {
  const r = new Room(BOUNDS), ui = new RoomInteraction(r);
  const t = r.add('table', { x: 1, y: 1 });
  ui.update(frame(hand('FIST', { x: 1, y: 1 })));
  ui.update(frame(hand('FIST', { x: 3, y: 3 })));
  ui.update(frame());
  near(r.get(t.id).x, 1);
});

test('pinch on empty floor does nothing', () => {
  const r = new Room(BOUNDS), ui = new RoomInteraction(r);
  ui.update(frame(hand('PINCH', { x: 2, y: 2 })));
  ui.update(frame(hand('NONE', { x: 2, y: 2 })));
  assert.equal(r.items.length, 0);
});

const two = (rotate, zoom = 1) => ({ hands: [hand('FIST', null), { ...hand('FIST', null), id: 1 }], two: { zoom, rotate } });

test('two hands rotate the selected item', () => {
  const r = new Room(BOUNDS), ui = new RoomInteraction(r);
  const s = r.add('sofa', { x: 2.5, y: 2 });
  ui.update(frame(hand('FIST', { x: 2.5, y: 2 })));
  ui.update(frame(hand('NONE', { x: 2.5, y: 2 })));       // صارت مختارة
  ui.update(two(0));
  ui.update(two(Math.PI / 2));
  near(r.get(s.id).rot, Math.PI / 2);
  ui.update(frame());
  r.undo();
  near(r.get(s.id).rot, 0);                                 // الدوران كله = خطوة تراجع وحدة
});

test('two hands move the camera when nothing is selected', () => {
  const ui = new RoomInteraction(new Room(BOUNDS));
  ui.update(two(0, 1));
  const out = ui.update(two(0.3, 2));
  assert.deepEqual(out.camera, { zoom: 2, rotate: 0.3 });
});

test('open palm held 1 s over an item removes it', () => {
  const r = new Room(BOUNDS), ui = new RoomInteraction(r);
  r.add('chair', { x: 2, y: 2 });
  let s;
  for (let t = 0; t <= 0.9; t += 0.1) s = ui.update(frame(hand('OPEN_PALM', { x: 2, y: 2 })), t);
  assert.equal(r.items.length, 1);
  assert.ok(s.removeProgress > 0.8);
  ui.update(frame(hand('OPEN_PALM', { x: 2, y: 2 })), 1.05);
  assert.equal(r.items.length, 0);
});
