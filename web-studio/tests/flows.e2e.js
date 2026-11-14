// اختبار الاستوديو كامل بـ Chrome الحقيقي: أيادي من fixtures المحرك تنحقن بدل الكاميرا (?test).
// التشغيل: npm run test:visual
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { setup, openStudio, installHands, pixel } from './e2e_setup.js';

let env;
before(async () => { env = await setup(); });
after(() => env?.close());

// نقطة على الورقة بنسبة من حجمها (بكسل الصفحة)
const at = (page, fx, fy) => page.evaluate(([fx, fy]) => {
  const r = document.getElementById('sheet').getBoundingClientRect();
  return { x: r.x + r.width * fx, y: r.y + r.height * fy };
}, [fx, fy]);

async function studio(opts = {}) {
  const page = await openStudio(env, { query: 'index.html?test', ...opts });
  await page.waitForFunction(() => window.__air && window.__airInject);
  await installHands(page);
  return page;
}

test('pinch draws a wall, moving palm erases it', async () => {
  const page = await studio();
  await page.evaluate(async ([a, b]) => window.__drag('pinch', a, b), [await at(page, 0.3, 0.4), await at(page, 0.7, 0.4)]);
  assert.equal(await page.evaluate(() => __air.plan.walls.length), 1);
  assert.equal(await page.isHidden('#empty'), true);

  // الكف تبدي فوك الجدار وتتحرك لتحت (ممحاة)
  const from = await at(page, 0.5, 0.3), to = await at(page, 0.5, 0.6);
  await page.evaluate(async ([from, to]) => {
    for (let k = 0; k <= 10; k++) await window.__hold([{ fixture: 'open_palm', x: from.x, y: from.y + ((to.y - from.y) * k) / 10 }], 2);
  }, [from, to]);
  assert.equal(await page.evaluate(() => __air.plan.walls.length), 0);
  await page.keyboard.press('Control+z');
  assert.equal(await page.evaluate(() => __air.plan.walls.length), 1);
  assert.deepEqual(page.errors, []);
  await page.context().close();
});

test('place a sofa from the palette, then two hands zoom the camera', async () => {
  const page = await studio();
  await page.click('[data-mode="room"]');
  await page.waitForFunction(() => __air.roomMode.view);
  const btn = await page.locator('[data-type="sofa"]').boundingBox();
  await page.evaluate(async ([from, to]) => window.__drag('pinch', from, to),
    [{ x: btn.x + btn.width / 2, y: btn.y + btn.height / 2 }, await at(page, 0.5, 0.6)]);
  assert.deepEqual(await page.evaluate(() => __air.roomMode.room.items.map((i) => i.type)), ['sofa']);

  // نلغي الاختيار (قبضة على أرض فاضية) حتى اليدين يحركن الكاميرا مو الكنبة
  await page.evaluate(async (p) => { await window.__hold([{ fixture: 'fist', ...p }], 6); await window.__hold([{ fixture: 'none', ...p }], 4); }, await at(page, 0.9, 0.9));
  const before = await page.evaluate(() => __air.roomMode.view.orbit.dist);
  const [l1, r1, l2, r2] = [await at(page, 0.45, 0.5), await at(page, 0.55, 0.5), await at(page, 0.25, 0.5), await at(page, 0.75, 0.5)];
  await page.evaluate(async ([l1, r1, l2, r2]) => {
    await window.__hold([{ fixture: 'fist', ...l1 }, { fixture: 'fist', ...r1 }], 6);
    for (let k = 1; k <= 8; k++) {
      const lerp = (a, b) => ({ x: a.x + ((b.x - a.x) * k) / 8, y: a.y });
      await window.__hold([{ fixture: 'fist', ...lerp(l1, l2) }, { fixture: 'fist', ...lerp(r1, r2) }], 2);
    }
  }, [l1, r1, l2, r2]);
  const afterDist = await page.evaluate(() => __air.roomMode.view.orbit.dist);
  assert.ok(afterDist < before * 0.6, `الكاميرا ما قرّبت: ${before} ← ${afterDist}`); // تبعّد اليدين = تقرّب
  assert.deepEqual(page.errors, []);
  await page.context().close();
});

test('pointer is visible above the 3D room', async () => {
  const page = await studio();
  await page.click('[data-mode="room"]');
  await page.waitForFunction(() => __air.roomMode.view);
  const p = await at(page, 0.5, 0.75); // على أرض الغرفة
  await page.evaluate(async (p) => window.__hold([{ fixture: 'fist', ...p }], 8), p);
  // قبضة = دائرة مملوءة باللون الأصفر بنص المؤشر. نقرا بكسل الشاشة الحقيقي
  const rgb = await pixel(page, Math.round(p.x), Math.round(p.y));
  assert.ok(rgb[0] > 200 && rgb[1] > 140 && rgb[2] < 120, `المؤشر مو ظاهر فوك الغرفة: rgb(${rgb})`);
  await page.context().close();
});

test('button under the pointer lights up, in plan and room', async () => {
  const page = await studio();
  const center = async (sel) => { const b = await page.locator(sel).boundingBox(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; };
  await page.evaluate(async (p) => window.__hold([{ fixture: 'open_palm', ...p }], 4), await center('[data-tool="pen"]'));
  assert.equal(await page.getAttribute('[data-tool="pen"]', 'data-hover'), '');
  await page.click('[data-mode="room"]');
  await page.waitForFunction(() => __air.roomMode.view);
  await page.evaluate(async (p) => window.__hold([{ fixture: 'open_palm', ...p }], 4), await center('[data-view="top"]'));
  assert.equal(await page.getAttribute('[data-view="top"]', 'data-hover'), '');
  assert.equal(await page.getAttribute('[data-tool="pen"]', 'data-hover'), null); // القديم انطفى
  await page.context().close();
});

test('camera denied shows message and mouse still draws', async () => {
  const page = await studio({ camera: false });
  await page.click('#camera');
  await page.waitForSelector('#toast:not([hidden])');
  assert.match(await page.textContent('#toast'), /ما سمح بالكاميرا/);
  const a = await at(page, 0.3, 0.5), b = await at(page, 0.6, 0.5);
  await page.mouse.move(a.x, a.y);
  await page.mouse.down();
  await page.mouse.move(b.x, b.y, { steps: 8 });
  await page.mouse.up();
  assert.equal(await page.evaluate(() => __air.plan.walls.length), 1);
  await page.context().close();
});

test('fake camera starts tracking without errors and shows the recording indicator', async () => {
  const page = await studio({ camera: true });
  await page.click('#camera');
  await page.waitForSelector('#mirror:not([hidden])', { timeout: 15000 });
  assert.equal(await page.textContent('#camera'), 'طفّي الكاميرا');
  await page.click('#camera'); // نطفيها
  assert.equal(await page.isHidden('#mirror'), true);
  assert.deepEqual(page.errors, []);
  await page.context().close();
});

test('export then import restores the design; a bad file changes nothing', async () => {
  const page = await studio();
  await page.evaluate(() => {
    __air.plan.addWall({ x: 1, y: 1 }, { x: 5, y: 1 });
    __air.roomMode.room.add('bed', { x: 3, y: 3 });
  });
  const [download] = await Promise.all([page.waitForEvent('download'), page.click('#export')]);
  const saved = await readFile(await download.path(), 'utf8');

  await page.evaluate(() => { __air.plan.clear(); __air.roomMode.room.items = []; });
  await page.setInputFiles('#file', { name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{"app":"airstudio","version":1,"walls":[{"a":{"x":1e99}}]}') });
  await page.waitForSelector('#toast:not([hidden])');
  assert.match(await page.textContent('#toast'), /ما فتحناه/);
  assert.equal(await page.evaluate(() => __air.plan.walls.length), 0);

  await page.setInputFiles('#file', { name: 'design.json', mimeType: 'application/json', buffer: Buffer.from(saved) });
  await page.waitForFunction(() => __air.plan.walls.length === 1);
  assert.deepEqual(await page.evaluate(() => __air.roomMode.room.items.map((i) => i.type)), ['bed']);
  assert.deepEqual(page.errors, []);
  await page.context().close();
});
