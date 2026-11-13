import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Plan } from '../js/plan.js';
import { PlanInteraction } from '../js/interaction.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

// ===== المخطط =====

test('wall snaps start to 10 cm grid and angle to 15 degrees', () => {
  const p = new Plan();
  const w = p.addWall({ x: 1.04, y: 2.96 }, { x: 4.03, y: 3.1 }); // تقريباً أفقي (2.7°)
  assert.deepEqual(w.a, { x: 1, y: 3 });
  near(w.b.y, 3); // صار أفقي تماماً
  near(w.b.x, 4); // الطول تقرّب لـ 3.0 م
});

test('diagonal wall keeps 45 degrees', () => {
  const p = new Plan();
  const w = p.addWall({ x: 0, y: 0 }, { x: 2.1, y: 1.9 });
  near(Math.atan2(w.b.y - w.a.y, w.b.x - w.a.x), Math.PI / 4);
});

test('wall end sticks to an existing corner (closing a room)', () => {
  const p = new Plan();
  p.addWall({ x: 0, y: 0 }, { x: 4, y: 0 });
  const w = p.addWall({ x: 4, y: 3 }, { x: 0.15, y: 0.1 }); // قريب من الزاوية (0,0)
  assert.deepEqual(w.b, { x: 0, y: 0 });
});

test('tiny wall ignored (accidental pinch)', () => {
  const p = new Plan();
  assert.equal(p.addWall({ x: 1, y: 1 }, { x: 1.1, y: 1.05 }), null);
  assert.equal(p.walls.length, 0);
});

test('erase removes touched walls only', () => {
  const p = new Plan();
  p.addWall({ x: 0, y: 0 }, { x: 4, y: 0 });
  p.addWall({ x: 0, y: 3 }, { x: 4, y: 3 });
  assert.equal(p.eraseAt({ x: 2, y: 0.2 }, 0.3), 1);
  assert.equal(p.walls.length, 1);
  assert.equal(p.walls[0].a.y, 3);
});

test('strokes: added and erased', () => {
  const p = new Plan();
  assert.equal(p.addStroke([{ x: 1, y: 1 }]), null); // نقطة وحدة مو خط
  p.addStroke([{ x: 1, y: 1 }, { x: 2, y: 1 }, { x: 3, y: 1.5 }]);
  assert.equal(p.strokes.length, 1);
  p.eraseAt({ x: 3, y: 1.4 }, 0.3);
  assert.equal(p.strokes.length, 0);
});

test('undo restores the previous state, one step at a time', () => {
  const p = new Plan();
  p.addWall({ x: 0, y: 0 }, { x: 4, y: 0 });
  p.addWall({ x: 0, y: 0 }, { x: 0, y: 3 });
  p.eraseAt({ x: 2, y: 0 }, 0.3);
  p.undo();
  assert.equal(p.walls.length, 2);
  p.undo();
  assert.equal(p.walls.length, 1);
  p.undo();
  p.undo(); // تراجع زيادة ما يخرّب
  assert.equal(p.walls.length, 0);
});

test('clear is undoable', () => {
  const p = new Plan();
  p.addWall({ x: 0, y: 0 }, { x: 4, y: 0 });
  p.clear();
  assert.equal(p.walls.length, 0);
  p.undo();
  assert.equal(p.walls.length, 1);
});

test('bounds of walls', () => {
  const p = new Plan();
  assert.equal(p.bounds(), null);
  p.addWall({ x: 1, y: 1 }, { x: 5, y: 1 });
  p.addWall({ x: 5, y: 1 }, { x: 5, y: 4 });
  assert.deepEqual(p.bounds(), { minX: 1, minY: 1, maxX: 5, maxY: 4 });
});

// ===== التفاعل بالإيماءات =====

const hand = (gesture, x, y, id = 0) => ({ id, gesture, point: { x, y } });
const frame = (...hands) => ({ hands, two: null });

test('pinch drag draws a wall on release', () => {
  const p = new Plan(), ui = new PlanInteraction(p);
  ui.update(frame(hand('PINCH', 1, 1)), 0);
  const mid = ui.update(frame(hand('PINCH', 3, 1)), 0.1);
  assert.deepEqual(mid.preview.a, { x: 1, y: 1 }); // معاينة أثناء السحب
  assert.equal(p.walls.length, 0);
  ui.update(frame(hand('NONE', 4, 1)), 0.2); // فتح الأصابع = إفلات
  assert.equal(p.walls.length, 1);
  near(p.walls[0].b.x, 3); // آخر مكان وانت قارص: لما تفتح أصابعك المؤشر يزحف، فما ناخذ نقطة الإفلات
});

test('pen tool draws a free stroke', () => {
  const p = new Plan(), ui = new PlanInteraction(p);
  ui.tool = 'pen';
  [[1, 1], [1.5, 1.2], [2, 1.1]].forEach(([x, y], i) => ui.update(frame(hand('PINCH', x, y)), i / 30));
  ui.update(frame(hand('NONE', 2, 1.1)), 0.2);
  assert.equal(p.strokes.length, 1);
  assert.equal(p.strokes[0].length, 3);
});

test('hand lost mid-pinch cancels the wall', () => {
  const p = new Plan(), ui = new PlanInteraction(p);
  ui.update(frame(hand('PINCH', 1, 1)), 0);
  ui.update(frame(hand('PINCH', 3, 1)), 0.1);
  ui.update(frame(), 0.2);
  assert.equal(p.walls.length, 0);
});

test('two-hand gesture cancels drawing', () => {
  const p = new Plan(), ui = new PlanInteraction(p);
  ui.update(frame(hand('PINCH', 1, 1)), 0);
  ui.update({ hands: [hand('PINCH', 3, 1), hand('PINCH', 5, 1, 1)], two: { zoom: 1, rotate: 0 } }, 0.1);
  ui.update(frame(hand('NONE', 3, 1)), 0.2);
  assert.equal(p.walls.length, 0);
});

test('moving open palm erases, as one undo step', () => {
  const p = new Plan(), ui = new PlanInteraction(p);
  p.addWall({ x: 0, y: 0 }, { x: 4, y: 0 });
  p.addWall({ x: 0, y: 2 }, { x: 4, y: 2 });
  [[1, 0], [1.5, 0.5], [2, 1.5], [2, 2]].forEach(([x, y], i) => ui.update(frame(hand('OPEN_PALM', x, y)), i * 0.1));
  assert.equal(p.walls.length, 0);
  p.undo();
  assert.equal(p.walls.length, 2); // تراجع واحد يرجّع كل اللي انمسح بنفس الحركة
});

test('still open palm does not erase, and pauses after 1.5 s', () => {
  const p = new Plan(), ui = new PlanInteraction(p);
  p.addWall({ x: 0, y: 0 }, { x: 4, y: 0 });
  let s;
  for (let t = 0; t <= 1.6; t += 0.1) s = ui.update(frame(hand('OPEN_PALM', 2, 0.05)), t);
  assert.equal(p.walls.length, 1); // كف ثابتة فوق جدار ما تمسحه
  assert.equal(s.paused, true);
  // وهو موقف: القرص ما يرسم
  ui.update(frame(hand('PINCH', 1, 1)), 2);
  ui.update(frame(hand('PINCH', 3, 1)), 2.1);
  ui.update(frame(hand('NONE', 3, 1)), 2.2);
  assert.equal(p.walls.length, 1);
});

test('pause toggles once per palm hold', () => {
  const ui = new PlanInteraction(new Plan());
  let s;
  for (let t = 0; t <= 4; t += 0.1) s = ui.update(frame(hand('OPEN_PALM', 2, 2)), t);
  assert.equal(s.paused, true); // ثبّتها 4 ثواني: يتوقف مرة وحدة، ما يرمش
  ui.update(frame(), 4.1);
  for (let t = 4.2; t <= 5.8; t += 0.1) s = ui.update(frame(hand('OPEN_PALM', 2, 2)), t);
  assert.equal(s.paused, false); // المرة الثانية تكمّل
});
