import { test } from 'node:test';
import assert from 'node:assert/strict';
import { OnboardingFlow, STEPS } from '../js/onboarding.js';

const hand = (gesture) => ({ hands: [{ id: 0, gesture }], two: null });
const twoFists = { hands: [{ id: 0, gesture: 'FIST' }, { id: 1, gesture: 'FIST' }], two: { zoom: 1, rotate: 0 } };

test('steps are camera, palm, pinch, fist, two hands', () => {
  assert.deepEqual(STEPS.map((s) => s.id), ['camera', 'palm', 'pinch', 'fist', 'two']);
});

test('advances only after the gesture is held 600 ms', () => {
  const f = new OnboardingFlow();
  f.next(); // الكاميرا اشتغلت (زر)
  assert.equal(f.current.id, 'palm');
  f.update(hand('OPEN_PALM'), 0);
  f.update(hand('OPEN_PALM'), 0.5);
  assert.equal(f.current.id, 'palm');
  f.update(hand('OPEN_PALM'), 0.65);
  assert.equal(f.current.id, 'pinch');
});

test('breaking the gesture restarts the hold timer', () => {
  const f = new OnboardingFlow();
  f.next();
  f.update(hand('OPEN_PALM'), 0);
  f.update(hand('NONE'), 0.4);
  f.update(hand('OPEN_PALM'), 0.5);
  f.update(hand('OPEN_PALM'), 1.0);
  assert.equal(f.current.id, 'palm');
});

test('camera step is never passed by gestures', () => {
  const f = new OnboardingFlow();
  f.update(hand('OPEN_PALM'), 0);
  f.update(hand('OPEN_PALM'), 5);
  assert.equal(f.current.id, 'camera');
});

test('two-hand step needs a real two-hand frame', () => {
  const f = new OnboardingFlow(4);
  f.update(hand('FIST'), 0);
  f.update(hand('FIST'), 1);
  assert.equal(f.done, false);
  f.update(twoFists, 2);
  f.update(twoFists, 2.7);
  assert.equal(f.done, true);
});

test('progress reports hold fraction for the ring', () => {
  const f = new OnboardingFlow(1);
  f.update(hand('OPEN_PALM'), 0);
  f.update(hand('OPEN_PALM'), 0.3);
  assert.ok(Math.abs(f.progress - 0.5) < 1e-9);
});

test('skip finishes immediately', () => {
  const f = new OnboardingFlow();
  f.skip();
  assert.equal(f.done, true);
});
