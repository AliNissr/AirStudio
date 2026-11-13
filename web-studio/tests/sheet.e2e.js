// اختبار بصري: يفتح الصفحة بـ Chrome الحقيقي ويتأكد إن ورقة الرسم ظاهرة وبيضاء فعلاً (مو بس إلها حجم).
// التشغيل: npm run test:visual   (يحتاج Chrome أو Edge منصّب، وما يحتاج سيرفر: يشغّل سيرفره بنفسه)
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { setup, openStudio, pixel } from './e2e_setup.js';

let env;
before(async () => { env = await setup(); });
after(() => env?.close());

test('3D room renders the floor at 2556x1277', async () => {
  const page = await openStudio(env, { width: 2556, height: 1277 });
  await page.click('[data-mode="room"]');
  await page.waitForTimeout(1500);
  const box = await page.evaluate(() => {
    const r = document.getElementById('room').getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  });
  // نص المشهد = أرضية الغرفة (بيج فاتح)، مو خلفية داكنة ولا canvas فاضي
  const rgb = await pixel(page, Math.round(box.x + box.w / 2), Math.round(box.y + box.h * 0.6));
  assert.ok(rgb[0] > 150 && rgb[0] > rgb[2], `ما بانت الأرضية: rgb(${rgb})`);
  assert.deepEqual(page.errors, []);
  await page.context().close();
});

for (const [w, h] of [[2556, 1277], [930, 1340], [1280, 720]]) {
  test(`sheet is visible and white at ${w}x${h}`, async () => {
    const page = await openStudio(env, { width: w, height: h });
    await page.waitForTimeout(1500); // المشكلة المبلّغ عنها تصير بعد التحميل، فننتظر

    const box = await page.evaluate(() => {
      const r = document.getElementById('sheet').getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height, bar: document.querySelector('.bar').getBoundingClientRect().height };
    });
    assert.ok(box.h > (h - box.bar) * 0.8, `الورقة انكمشت: ارتفاعها ${box.h}`);

    // 5 نقاط على الورقة، بعيد عن شريط الأدوات وعن نص التلميح بالنص (لونه #8b8678): لازم كلها فاتحة
    for (const [fx, fy] of [[0.5, 0.65], [0.2, 0.8], [0.8, 0.8], [0.2, 0.3], [0.5, 0.95]]) {
      const rgb = await pixel(page, Math.round(box.x + box.w * fx), Math.round(box.y + box.h * fy));
      assert.ok(Math.min(...rgb) > 200, `بكسل غامق على الورقة عند (${fx}, ${fy}): rgb(${rgb})`);
    }
    assert.deepEqual(page.errors, []);
    await page.context().close();
  });
}
