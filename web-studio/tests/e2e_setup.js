// أدوات مشتركة لاختبارات المتصفح (*.e2e.js): سيرفر ملفات صغير + Chrome الحقيقي + أيادي محقونة.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wasm': 'application/wasm', '.svg': 'image/svg+xml' };

export async function setup() {
  // سيرفر ملفات صغير: يرفض أي مسار يطلع برة مجلد المشروع
  const server = createServer(async (req, res) => {
    let path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname)));
    if (!path.startsWith(ROOT)) { res.writeHead(403).end(); return; }
    if (path.endsWith('\\') || path.endsWith('/')) path = join(path, 'index.html'); // قبل ما نحدد النوع من الامتداد
    try {
      const body = await readFile(path);
      res.writeHead(200, { 'content-type': TYPES[extname(path)] ?? 'application/octet-stream' }).end(body);
    } catch { res.writeHead(404).end(); }
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  // AIR_CHROME_ARGS: إعدادات Chrome إضافية للتجربة، مثلاً --enable-features=WebContentsForceDark
  const args = ['--use-fake-device-for-media-stream', ...(process.env.AIR_CHROME_ARGS?.split(' ').filter(Boolean) ?? [])];
  const browser = await chromium.launch({ channel: 'chrome', args }).catch(() => chromium.launch({ channel: 'msedge', args }));
  return {
    base: `http://127.0.0.1:${server.address().port}/web-studio/`,
    browser,
    async close() { await browser.close(); server.close(); },
  };
}

// صفحة الاستوديو، بدون الشاشة التعليمية، وتجمع أخطاء JS بـ page.errors
export async function openStudio(env, { width = 1280, height = 720, query = '', camera = false } = {}) {
  const ctx = await env.browser.newContext({ viewport: { width, height }, permissions: camera ? ['camera'] : [] });
  await ctx.addInitScript(() => localStorage.setItem('airstudio.onboarded', '1'));
  const page = await ctx.newPage();
  page.errors = [];
  page.on('pageerror', (e) => page.errors.push(e.message));
  await page.goto(env.base + query);
  return page;
}

// لون بكسل وحد من صورة الشاشة الحقيقية
export async function pixel(page, x, y) {
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

// يركّب window.__hold(أيادي, n): كل يد {fixture, x, y} بإحداثيات الصفحة (بكسل)،
// نحرّك يد الـ fixture بحيث مؤشرها (نص الإبهام والسبابة) يجي على النقطة، ونحقنها n إطارات
export async function installHands(page) {
  await page.evaluate(async () => {
    const cache = {};
    const fixture = async (n) => (cache[n] ??= (await (await fetch(`/engine/fixtures/${n}.json`)).json()).landmarks);
    const sheet = () => document.getElementById('sheet').getBoundingClientRect();
    const place = (pts, x, y) => {
      const s = sheet(), nx = 0.15 + ((x - s.x) / s.width) * 0.7, ny = 0.15 + ((y - s.y) / s.height) * 0.65; // عكس REACH بـ app.js
      const k = 300, mx = ((pts[4][0] + pts[8][0]) / 2) * k, my = ((pts[4][1] + pts[8][1]) / 2) * k;
      return pts.map(([a, b, c]) => [a * k - mx + nx * 640, b * k - my + ny * 480, c]);
    };
    window.__hold = async (hands, n = 6) => {
      const raw = await Promise.all(hands.map(async (h) => ({ landmarks: place(await fixture(h.fixture), h.x, h.y) })));
      for (let i = 0; i < n; i++) { window.__airInject(raw); await new Promise((r) => setTimeout(r, 33)); }
    };
    // سحبة: من نقطة لنقطة بخطوات
    window.__drag = async (fixture, from, to, steps = 10) => {
      await window.__hold([{ fixture, ...from }], 6);
      for (let k = 1; k <= steps; k++) await window.__hold([{ fixture, x: from.x + ((to.x - from.x) * k) / steps, y: from.y + ((to.y - from.y) * k) / steps }], 2);
      await window.__hold([{ fixture, ...to }], 6);
      await window.__hold([{ fixture: 'none', ...to }], 6); // إفلات
    };
  });
}
