// نفس اختبارات Python، على نفس ملفات fixtures. التشغيل: node --test engine/js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { GestureClassifier, Gesture, pinchRatio } from './gestures.js';
import { OneEuroFilter } from './one_euro.js';

const dir = new URL('../fixtures/', import.meta.url);
const config = JSON.parse(readFileSync(new URL('../gestures.json', import.meta.url), 'utf8'));
const load = (name) => JSON.parse(readFileSync(new URL(`${name}.json`, dir), 'utf8'));
const fixtures = readdirSync(dir).filter((f) => f.endsWith('.json'));

for (const file of fixtures) {
  test(`fixture ${file}`, () => {
    const data = load(file.replace('.json', ''));
    const c = new GestureClassifier(config);
    let g;
    for (let i = 0; i < 3; i++) g = c.update(data.landmarks);
    assert.equal(g, Gesture[data.gesture]);
  });
}

const withRatio = (ratio) => {
  const pts = load('pinch').landmarks.map((p) => [...p]);
  const tip = pts[8];
  pts[4] = [tip[0] - ratio * 0.2, tip[1], 0];
  return pts;
};

test('pinch hysteresis no flicker', () => {
  const c = new GestureClassifier({ ...config, debounce_frames: 1 });
  const seq = [0.2, 0.3, 0.24, 0.3, 0.33].map((r) => c.update(withRatio(r)));
  assert.deepEqual(seq, Array(5).fill(Gesture.PINCH));
  assert.notEqual(c.update(withRatio(0.4)), Gesture.PINCH);
});

test('debounce requires 3 frames', () => {
  const c = new GestureClassifier(config);
  const palm = load('open_palm').landmarks, fist = load('fist').landmarks;
  for (let i = 0; i < 3; i++) c.update(palm);
  assert.equal(c.update(fist), Gesture.OPEN_PALM);
  assert.equal(c.update(fist), Gesture.OPEN_PALM);
  assert.equal(c.update(fist), Gesture.FIST);
});

test('pinch ratio is scale free', () => {
  const pts = load('pinch').landmarks;
  const big = pts.map(([x, y, z]) => [x * 3, y * 3, z]);
  assert.ok(Math.abs(pinchRatio(pts) - pinchRatio(big)) < 1e-9);
});

test('wrong point count rejected', () => {
  assert.throws(() => new GestureClassifier(config).update([[0, 0, 0]]));
});

test('one euro: passthrough, smoothing, follows motion', () => {
  const f = new OneEuroFilter(config.one_euro);
  assert.equal(f.filter(42, 0), 42);
  f.reset();
  for (let i = 0; i < 10; i++) f.filter(0, i / 30);
  let y;
  for (let i = 10; i < 20; i++) y = f.filter(100, i / 30);
  assert.ok(y > 90);
});
