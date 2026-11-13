// التشغيل: node --test web-studio/tests
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { twoHandMetrics, matchHands, TwoHandGesture, HandPipeline } from '../js/two_hand.js';

const engine = new URL('../../engine/', import.meta.url);
const config = JSON.parse(readFileSync(new URL('gestures.json', engine), 'utf8'));
const fixture = (name) => JSON.parse(readFileSync(new URL(`fixtures/${name}.json`, engine), 'utf8')).landmarks;

// نحرك اليد كلها (dx, dy) حتى نصنع يد ثانية بمكان ثاني
const moved = (pts, dx, dy = 0) => pts.map(([x, y, z]) => [x + dx, y + dy, z]);
// نحط نقطة 9 (قاعدة الوسطى) بمكان محدد
const at = (pts, x, y) => moved(pts, x - pts[9][0], y - pts[9][1]);
const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

test('metrics: distance, angle and center from point 9', () => {
  const m = twoHandMetrics(at(fixture('fist'), 0, 0), at(fixture('fist'), 3, 4));
  near(m.distance, 5);
  near(m.angle, Math.atan2(4, 3));
  assert.deepEqual(m.center, { x: 1.5, y: 2 });
});

const fists = (d, angle = 0) => [
  { id: 0, gesture: 'FIST', landmarks: at(fixture('fist'), 0, 0) },
  { id: 1, gesture: 'FIST', landmarks: at(fixture('fist'), d * Math.cos(angle), d * Math.sin(angle)) },
];

test('zoom ratio from distance change', () => {
  const g = new TwoHandGesture();
  assert.equal(g.update(fists(1)).zoom, 1); // بداية الإيماءة = 1
  near(g.update(fists(2)).zoom, 2);
  near(g.update(fists(0.5)).zoom, 0.5);
});

test('rotate from angle change, wrapped to -π..π', () => {
  const g = new TwoHandGesture();
  g.update(fists(1, 0));
  near(g.update(fists(1, Math.PI / 6)).rotate, Math.PI / 6);
  const g2 = new TwoHandGesture();
  g2.update(fists(1, Math.PI - 0.1));
  near(g2.update(fists(1, -Math.PI + 0.1)).rotate, 0.2); // عبر الحد، مو -6.08
});

test('two hand gesture ends cleanly when one hand lost', () => {
  const g = new TwoHandGesture();
  g.update(fists(1));
  g.update(fists(2));
  assert.equal(g.update([fists(2)[0]]), null);
  // ترجع اليد: إيماءة جديدة تبدي من 1، ما تقفز لـ 2
  assert.equal(g.update(fists(2)).zoom, 1);
});

test('needs both hands in the same grab gesture', () => {
  const g = new TwoHandGesture();
  const mixed = fists(1);
  mixed[1].gesture = 'OPEN_PALM';
  assert.equal(g.update(mixed), null);
  const pinches = fists(1).map((h) => ({ ...h, gesture: 'PINCH' }));
  assert.equal(g.update(pinches).zoom, 1);
});

test('hands matched by position across frames', () => {
  const a = at(fixture('open_palm'), 0.2, 0.5), b = at(fixture('open_palm'), 0.8, 0.5);
  const first = matchHands([], [{ landmarks: b }, { landmarks: a }]);
  const idOfLeft = first.find((h) => h.landmarks === a).id;
  // الإطار الجاي: نفس اليدين تحركن شوية، والمكتبة رجّعتهن بترتيب معكوس
  const a2 = moved(a, 0.01), b2 = moved(b, -0.01);
  const second = matchHands(first, [{ landmarks: a2 }, { landmarks: b2 }]);
  assert.equal(second.find((h) => h.landmarks === a2).id, idOfLeft);
});

test('new hand gets a fresh id, not a reused one', () => {
  const one = matchHands([], [{ landmarks: at(fixture('fist'), 0.5, 0.5) }]);
  const two = matchHands(one, [{ landmarks: at(fixture('fist'), 0.5, 0.5) }, { landmarks: at(fixture('fist'), 0.9, 0.5) }]);
  assert.deepEqual(new Set(two.map((h) => h.id)).size, 2);
});

test('pipeline: gesture after debounce, pointer normalized between thumb and index', () => {
  const p = new HandPipeline(config);
  const pts = fixture('pinch');
  let frame;
  for (let i = 0; i < 3; i++) frame = p.process([{ landmarks: pts, side: 'Right' }], i / 30, 1, 1);
  const h = frame.hands[0];
  assert.equal(h.gesture, 'PINCH');
  near(h.pointer.x, (pts[4][0] + pts[8][0]) / 2, 1e-3);
  near(h.pointer.y, (pts[4][1] + pts[8][1]) / 2, 1e-3);
});

test('pipeline: lost hand is forgotten', () => {
  const p = new HandPipeline(config);
  const raw = [{ landmarks: fixture('fist'), side: 'Right' }];
  for (let i = 0; i < 3; i++) p.process(raw, i / 30, 1, 1);
  assert.deepEqual(p.process([], 0.2, 1, 1).hands, []);
  // رجعت: لازم تعبر الـ debounce من جديد
  assert.equal(p.process(raw, 0.3, 1, 1).hands[0].gesture, 'NONE');
});

test('pipeline: two fists produce a two-hand frame', () => {
  const p = new HandPipeline(config);
  const raw = [{ landmarks: at(fixture('fist'), 0.3, 0.5) }, { landmarks: at(fixture('fist'), 0.7, 0.5) }];
  let frame;
  for (let i = 0; i < 3; i++) frame = p.process(raw, i / 30, 1, 1);
  assert.equal(frame.two.zoom, 1);
});
