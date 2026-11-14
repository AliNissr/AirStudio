import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pointerStyle } from '../js/pointer.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

test('open hand far from pinching: empty ring at full size', () => {
  assert.deepEqual(pointerStyle('OPEN_PALM', 1.0), { radius: 16, fill: 0, solid: false });
});

test('ring fills and shrinks smoothly as the thumb approaches the index', () => {
  const half = pointerStyle('NONE', 0.425); // نص الطريق بين 0.6 (بعيد) و 0.25 (قرص)
  near(half.fill, 0.5);
  near(half.radius, 12.5);
  assert.equal(half.solid, false);
});

test('pinch: fully filled small ring', () => {
  assert.deepEqual(pointerStyle('PINCH', 0.1), { radius: 9, fill: 1, solid: false });
});

test('fist: solid circle, whatever the pinch distance', () => {
  assert.deepEqual(pointerStyle('FIST', 0.9), { radius: 12, fill: 1, solid: true });
});
