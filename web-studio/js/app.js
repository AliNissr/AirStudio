// يربط كلشي: الكاميرا، الشاشة التعليمية، المؤشرات، الأصوات، والرسائل.
import { startHands, loadConfig } from './hands.js';
import { HandPipeline } from './two_hand.js';
import { TrackerError } from './tracker.js';
import { message } from './messages.js';
import { mountOnboarding, seenOnboarding } from './onboarding.js';
import { blip, unlockSound, setSound, soundOn, GESTURE_TONE } from './sound.js';
import { Plan } from './plan.js';
import { PlanInteraction } from './interaction.js';
import { PlanView } from './plan_view.js';
import { createRoomMode } from './room_mode.js';
import { serialize, parseDesign, applyDesign, MAX_BYTES } from './storage.js';

const $ = (id) => document.getElementById(id);
const HAND_COLORS = ['#e8b341', '#4fc1cf'];
const NAMES = { PINCH: 'قرص', MIDDLE_PINCH: 'قرص الوسطى', OPEN_PALM: 'كف مفتوحة', FIST: 'قبضة', TWO_FINGERS: 'إصبعين', NONE: 'يد' };
const BONES = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [0, 17], [17, 18], [18, 19], [19, 20]];
// منطقة وسط الكاميرا اللي تغطي الورقة كاملة: ما تحتاج تمد إيدك لحافة الصورة حتى توصل حافة الورقة
const REACH = { x0: 0.15, x1: 0.85, y0: 0.15, y1: 0.8 };

const state = { session: null, onboarding: null, lastGesture: new Map(), toastTimer: 0, mode: 'plan' };
const plan = new Plan();
const gestures = new PlanInteraction(plan); // الإيماءات من الكاميرا
const view = new PlanView($('plan'), plan);  // الرسم + الماوس
const roomMode = createRoomMode({ stage: $('sheet'), plan, blip });

// ===== الرسائل =====
function toast(code, data) {
  const el = $('toast');
  el.textContent = message(code, data);
  el.hidden = false;
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => { el.hidden = true; }, 7000);
}
function onStatus(code, data) {
  if (code === 'OK') { if ($('toast').textContent === message('DARK')) $('toast').hidden = true; return; }
  if (code === 'DARK' && !$('toast').hidden && $('toast').textContent === message('DARK')) return; // لا نكرر نفس الرسالة
  toast(code, data);
}

// ===== الرسم =====
function sheetPoint(p, w, h) {
  const nx = (p.x - REACH.x0) / (REACH.x1 - REACH.x0), ny = (p.y - REACH.y0) / (REACH.y1 - REACH.y0);
  return { x: Math.min(Math.max(nx, 0), 1) * w, y: Math.min(Math.max(ny, 0), 1) * h };
}

function drawPointers(frame) {
  const c = $('pointers'), dpr = devicePixelRatio || 1;
  const w = c.clientWidth, h = c.clientHeight;
  if (c.width !== w * dpr) { c.width = w * dpr; c.height = h * dpr; }
  const g = c.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  for (const hand of frame.hands) {
    const { x, y } = sheetPoint(hand.pointer, w, h);
    const color = HAND_COLORS[hand.id % 2], grab = hand.gesture === 'PINCH' || hand.gesture === 'FIST';
    // علامة تصويب مثل أدوات الرسم: دائرة + 4 خطوط. تصغر وتمتلي لما تمسك
    const r = grab ? 9 : 16;
    g.strokeStyle = color;
    g.lineWidth = 2;
    g.beginPath();
    g.arc(x, y, r, 0, Math.PI * 2);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      g.moveTo(x + dx * (r + 4), y + dy * (r + 4));
      g.lineTo(x + dx * (r + 12), y + dy * (r + 12));
    }
    g.stroke();
    if (grab) { g.fillStyle = color + '55'; g.fill(); }
    g.font = '600 13px "Segoe UI", Tahoma, sans-serif';
    g.fillStyle = state.mode === 'room' ? '#e4e8ee' : '#18212c'; // الغرفة خلفيتها داكنة
    g.textAlign = 'center';
    g.fillText(NAMES[hand.gesture], x, y + r + 30);
  }
}

function drawSkeleton(frame, w, h) {
  const c = $('skeleton');
  if (c.width !== w) { c.width = w; c.height = h; }
  const g = c.getContext('2d');
  g.clearRect(0, 0, w, h);
  for (const hand of frame.hands) {
    g.strokeStyle = HAND_COLORS[hand.id % 2];
    g.lineWidth = 3;
    g.beginPath();
    for (const [a, b] of BONES) {
      g.moveTo(hand.landmarks[a][0], hand.landmarks[a][1]);
      g.lineTo(hand.landmarks[b][0], hand.landmarks[b][1]);
    }
    g.stroke();
  }
  $('chips').innerHTML = frame.hands
    .map((hd) => `<li style="--c:${HAND_COLORS[hd.id % 2]}">${NAMES[hd.gesture]}</li>`).join('');
}

// ===== المخطط =====
function updateChrome() {
  $('empty').hidden = !plan.empty || Boolean(view.state.preview || view.state.stroke);
  $('paused').hidden = !gestures.paused;
  $('undo').disabled = !plan.history.length;
  $('clear').disabled = plan.empty;
}

function feedPlan(frame) {
  if (state.onboarding) return; // وقت الشرح، الإيماءات للشرح بس
  const c = $('pointers');
  const hands = frame.hands.map((hd) => ({
    id: hd.id, gesture: hd.gesture, point: view.toMeters(sheetPoint(hd.pointer, c.clientWidth, c.clientHeight)),
  }));
  const before = plan.walls.length + plan.strokes.length, wasPaused = gestures.paused;
  view.render(gestures.update({ hands, two: frame.two }, performance.now() / 1000));
  const after = plan.walls.length + plan.strokes.length;
  if (after > before) blip(1040, 90);          // انضاف جدار
  else if (after < before) blip(240, 60);      // انمسح شي
  if (wasPaused !== gestures.paused) blip(gestures.paused ? 300 : 900, 160);
  updateChrome();
}

function setTool(tool) {
  view.setTool(tool);
  gestures.tool = tool === 'pen' ? 'pen' : 'wall'; // الممحاة باليد هي الكف، فالأداة تأثر على الماوس بس
  document.querySelectorAll('[data-tool]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.tool === tool)));
}

function undo() {
  if (state.mode === 'room') { roomMode.undo(); return; }
  plan.undo();
  view.render({});
  updateChrome();
}

// ===== التبديل بين المخطط والغرفة =====
async function setMode(mode) {
  state.mode = mode;
  const inRoom = mode === 'room';
  for (const id of ['plan', 'empty', 'paused']) $(id).hidden = inRoom;
  document.querySelector('.tools').hidden = inRoom;
  $('room').hidden = !inRoom;
  document.querySelectorAll('[data-mode]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
  gestures.cancel();
  if (inRoom) await roomMode.enter();
  else { view.render({}); updateChrome(); }
}
document.querySelectorAll('[data-mode]').forEach((b) => { b.onclick = () => setMode(b.dataset.mode); });

document.querySelectorAll('[data-tool]').forEach((b) => { b.onclick = () => setTool(b.dataset.tool); });
$('undo').onclick = undo;
$('clear').onclick = () => { plan.clear(); view.render({}); updateChrome(); toast('CLEARED'); };
view.onChange = updateChrome;
addEventListener('keydown', (e) => {
  if (e.target.closest('input, textarea, dialog')) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); undo(); return; }
  if (state.mode === 'room') { if (roomMode.onKey(e)) e.preventDefault(); return; }
  const tool = { w: 'wall', p: 'pen', e: 'erase' }[e.key.toLowerCase()];
  if (tool && !e.ctrlKey && !e.altKey) setTool(tool);
});
addEventListener('resize', () => view.render());

// ===== الحفظ والتصدير =====
const SAVE_KEY = 'airstudio.design';
let lastSaved = null, saveWarned = false;

function download(blob, name) {
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: name });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// حفظ تلقائي: كل ثانية نقارن، ونكتب بس إذا تغيّر شي (التصميم صغير، فالمقارنة رخيصة)
function autosave() {
  const text = JSON.stringify(serialize(plan, roomMode.room));
  if (text === lastSaved) return;
  try {
    localStorage.setItem(SAVE_KEY, text);
    lastSaved = text;
  } catch {
    if (!saveWarned) toast('SAVE_FAILED');
    saveWarned = true;
  }
}

async function afterLoad() {
  if (state.mode === 'room') await roomMode.enter();
  else view.render({});
  updateChrome();
}

// أول ما تنفتح الصفحة: نرجّع آخر تصميم. حتى المحفوظ بالمتصفح نفحصه، ممكن يكون معطوب
try {
  const saved = localStorage.getItem(SAVE_KEY);
  const r = saved && parseDesign(saved);
  if (r?.ok) {
    applyDesign(r.design, plan, roomMode.room);
    plan.history = [];
    roomMode.room.history = []; // فتح الصفحة مو خطوة تتراجع عنها
    lastSaved = saved;
  } else if (saved) console.warn('AirStudio: التصميم المحفوظ معطوب، بدينا من جديد', r?.error);
} catch { /* localStorage مقفول: نبدي فاضي */ }
setInterval(autosave, 1000);
addEventListener('pagehide', autosave);

$('export').onclick = () => {
  autosave();
  download(new Blob([JSON.stringify(serialize(plan, roomMode.room), null, 1)], { type: 'application/json' }), 'airstudio-design.json');
};
$('open').onclick = () => $('file').click();
$('file').onchange = async () => {
  const file = $('file').files[0];
  $('file').value = ''; // حتى تكدر تفتح نفس الملف مرة ثانية
  if (!file) return;
  if (file.size > MAX_BYTES) { toast('TOO_BIG'); return; }
  const r = parseDesign(await file.text());
  if (!r.ok) { toast(r.error); return; }
  applyDesign(r.design, plan, roomMode.room);
  await afterLoad();
  toast('IMPORTED');
};
$('png').onclick = async () => {
  if (state.mode === 'room') { download(await roomMode.snapshot(), 'airstudio-room.png'); return; }
  // المخطط: الـ canvas شفاف، فنرسمه فوك لون الورقة
  const src = $('plan'), out = Object.assign(document.createElement('canvas'), { width: src.width, height: src.height });
  const g = out.getContext('2d');
  g.fillStyle = '#fbfaf7';
  g.fillRect(0, 0, out.width, out.height);
  g.drawImage(src, 0, 0);
  out.toBlob((b) => download(b, 'airstudio-plan.png'), 'image/png');
};

view.setTool('wall');
view.render({});
updateChrome();

// ===== كل إطار =====
function onFrame(frame, w = 640, h = 480) {
  drawPointers(frame);
  drawSkeleton(frame, w, h);
  if (state.mode === 'room') {
    const c = $('pointers');
    if (!state.onboarding) roomMode.feed(frame, (p) => sheetPoint(p, c.clientWidth, c.clientHeight));
  } else feedPlan(frame);
  for (const hand of frame.hands) {
    if (state.lastGesture.get(hand.id) !== hand.gesture && GESTURE_TONE[hand.gesture]) blip(GESTURE_TONE[hand.gesture]);
    state.lastGesture.set(hand.id, hand.gesture);
  }
  state.onboarding?.feed(frame, performance.now() / 1000);
}

// ===== الكاميرا =====
async function startCamera() {
  unlockSound();
  try {
    const video = $('video');
    state.session = await startHands({ video, onFrame: (f) => onFrame(f, video.videoWidth, video.videoHeight), onStatus });
  } catch (e) {
    toast(e instanceof TrackerError ? e.code : 'NO_MODEL');
    console.error(e);
    return false;
  }
  $('mirror').hidden = false;
  if (new URLSearchParams(location.search).has('perf')) showPerf();
  $('camera').textContent = 'طفّي الكاميرا';
  $('camera').setAttribute('aria-pressed', 'true');
  return true;
}

// ?perf بالرابط: أرقام الأداء فوك مراية الكاميرا، حتى تقيس الاستوديو كامل (التتبع + الرسم سوية)
function showPerf() {
  // سطر منفصل بعد "الكاميرا شغالة": مؤشر الكاميرا يبقى كامل وواضح
  const el = document.querySelector('.live').appendChild(document.createElement('span'));
  const timer = setInterval(() => {
    const i = state.session?.info;
    if (!i) { clearInterval(timer); el.remove(); return; }
    el.textContent = ` | ${i.delegate}, ${i.numHands} يد، نموذج ${i.modelMs?.toFixed(1)} ms، إطار ${i.frameMs?.toFixed(1)} ms، كاميرا ${i.cameraFps?.toFixed(0) ?? '…'} fps`;
  }, 500);
}

function stopCamera() {
  state.session?.stop();
  state.session = null;
  $('mirror').hidden = true;
  $('camera').textContent = 'شغّل الكاميرا';
  $('camera').setAttribute('aria-pressed', 'false');
  drawPointers({ hands: [] });
}

function openOnboarding() {
  state.onboarding = mountOnboarding($('onboarding'), {
    onStartCamera: () => (state.session ? true : startCamera()),
    onAdvance: () => blip(990, 120),
    onDone: () => { state.onboarding = null; },
  });
}

$('camera').onclick = () => (state.session ? stopCamera() : startCamera());
$('help').onclick = openOnboarding;
$('sound').onclick = () => {
  unlockSound();
  setSound(!soundOn());
  $('sound').setAttribute('aria-pressed', String(soundOn()));
};
$('sound').setAttribute('aria-pressed', String(soundOn()));
addEventListener('pagehide', stopCamera); // نطفي الكاميرا لما تسكّر التبويب

// للاختبارات بس (?test): ندخل يدين جاهزة بدل الكاميرا
if (new URLSearchParams(location.search).has('test')) {
  const pipeline = new HandPipeline(await loadConfig());
  window.__airInject = (raw, w = 640, h = 480) => onFrame(pipeline.process(raw, performance.now() / 1000, w, h), w, h);
  window.__air = { plan, gestures, view, roomMode, setMode };
}

if (!seenOnboarding()) openOnboarding();
