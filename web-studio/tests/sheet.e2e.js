// اختبار بصري: يفتح الصفحة بـ Chrome الحقيقي ويتأكد إن ورقة الرسم ظاهرة وبيضاء فعلاً (مو بس إلها حجم).
// التشغيل: npm run test:visual   (يحتاج Chrome أو Edge منصّب، وما يحتاج سيرفر: يشغّل سيرفره بنفسه)
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wasm': 'application/wasm', '.svg': 'image/svg+xml' };
let server, browser, base;

before(async () => {
  // سيرفر ملفات صغير: يرفض أي مسار يطلع برة مجلد المشروع
  server = createServer(async (req, res) => {
    let path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname)));
    if (!path.startsWith(ROOT)) { res.writeHead(403).end(); return; }
    if (path.endsWith('\\') || path.endsWith('/')) path = join(path, 'index.html'); // قبل ما نحدد النوع من الامتداد
    try {
      const body = await readFile(path);
      res.writeHead(200, { 'content-type': TYPES[extname(path)] ?? 'application/octet-stream' }).end(body);
    } catch { res.writeHead(404).end(); }
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}/web-studio/`;
  // AIR_CHROME_ARGS: إعدادات Chrome إضافية للتجربة، مثلاً --enable-features=WebContentsForceDark
  const args = process.env.AIR_CHROME_ARGS?.split(' ').filter(Boolean) ?? [];
  browser = await chromium.launch({ channel: 'chrome', args }).catch(() => chromium.launch({ channel: 'msedge', args }));
});

after(async () => {
  await browser?.close();
  server?.close();
});

// لون بكسل وحد من صورة الشاشة الحقيقية
async function pixel(page, x, y) {
  const png = await page.screenshot({ clip: { x, y, width: 1, height: 1 } });
  return page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const g = new OffscreenCanvas(1, 1).getContext('2d');
    g.drawImage(img, 0, 0);
    return [...g.getImageData(0, 0, 1, 1).data.slice(0, 3)];
  }, png.toString('base64'));
}

for (const [w, h] of [[2556, 1277], [930, 1340], [1280, 720]]) {
  test(`sheet is visible and white at ${w}x${h}`, async () => {
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    await page.addInitScript(() => localStorage.setItem('airstudio.onboarded', '1'));
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(base);
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
    assert.deepEqual(errors, []);
    await page.close();
  });
}
