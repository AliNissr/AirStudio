import { test } from 'node:test';
import assert from 'node:assert/strict';
import { serialize, parseDesign, applyDesign, MAX_BYTES } from '../js/storage.js';
import { Plan } from '../js/plan.js';
import { Room } from '../js/layout.js';

const BOUNDS = { minX: 0, minY: 0, maxX: 6, maxY: 4 };
function sample() {
  const plan = new Plan(), room = new Room(BOUNDS);
  plan.addWall({ x: 0, y: 0 }, { x: 6, y: 0 });
  plan.addStroke([{ x: 1, y: 1 }, { x: 2, y: 1.5 }]);
  room.add('sofa', { x: 2, y: 2 }, Math.PI / 2);
  room.add('chair', { x: 4, y: 3 });
  return { plan, room };
}
const design = (extra = {}) => JSON.stringify({ app: 'airstudio', version: 1, walls: [], strokes: [], items: [], ...extra });

test('roundtrip keeps design', () => {
  const { plan, room } = sample();
  const text = JSON.stringify(serialize(plan, room));
  const r = parseDesign(text);
  assert.equal(r.ok, true);
  const plan2 = new Plan(), room2 = new Room(BOUNDS);
  applyDesign(r.design, plan2, room2);
  assert.deepEqual(plan2.walls, plan.walls);
  assert.deepEqual(plan2.strokes, plan.strokes);
  assert.deepEqual(room2.items, room.items);
  assert.equal(room2.add('table', { x: 1, y: 1 }).id, 3); // الأرقام تكمل، ما تتكرر
});

test('import rejects bad json', () => {
  assert.deepEqual(parseDesign('{"app": "airstudio", '), { ok: false, error: 'BAD_JSON' });
});

test('import rejects files that are not designs', () => {
  assert.equal(parseDesign('[1, 2, 3]').error, 'NOT_DESIGN');
  assert.equal(parseDesign('{"name": "something else"}').error, 'NOT_DESIGN');
  assert.equal(parseDesign(design({ version: 99 })).error, 'BAD_VERSION');
});

test('import rejects unknown furniture', () => {
  const r = parseDesign(design({ items: [{ id: 1, type: 'piano', x: 1, y: 1, rot: 0 }] }));
  assert.equal(r.error, 'BAD_DATA');
});

test('import rejects huge, missing or non-numeric numbers', () => {
  for (const wall of [
    { a: { x: 1e9, y: 0 }, b: { x: 1, y: 1 } },
    { a: { x: 0 }, b: { x: 1, y: 1 } },
    { a: { x: '0', y: 0 }, b: { x: 1, y: 1 } },
  ]) assert.equal(parseDesign(design({ walls: [wall] })).error, 'BAD_DATA', JSON.stringify(wall));
});

test('import rejects too many things', () => {
  const walls = Array.from({ length: 501 }, () => ({ a: { x: 0, y: 0 }, b: { x: 1, y: 0 } }));
  assert.equal(parseDesign(design({ walls })).error, 'BAD_DATA');
});

test('import rejects oversized text before parsing', () => {
  assert.equal(parseDesign(' '.repeat(MAX_BYTES + 1)).error, 'TOO_BIG');
});

test('import keeps only known fields (no extra data sneaks in)', () => {
  const r = parseDesign(design({
    walls: [{ a: { x: 0, y: 0, evil: 1 }, b: { x: 1, y: 0 }, onclick: 'x' }],
    items: [{ id: 7, type: 'chair', x: 1, y: 1, rot: 0, html: '<img>' }],
  }));
  assert.deepEqual(r.design.walls, [{ a: { x: 0, y: 0 }, b: { x: 1, y: 0 } }]);
  assert.deepEqual(r.design.items, [{ id: 7, type: 'chair', x: 1, y: 1, rot: 0 }]);
});

test('applying a design is undoable', () => {
  const { plan, room } = sample();
  const r = parseDesign(design());
  applyDesign(r.design, plan, room);
  assert.equal(plan.walls.length, 0);
  assert.equal(room.items.length, 0);
  plan.undo();
  room.undo();
  assert.equal(plan.walls.length, 1);
  assert.equal(room.items.length, 2);
});
