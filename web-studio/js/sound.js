// أصوات تأكيد خفيفة، مصنوعة بالكود (Web Audio) بدون ملفات صوت.
const KEY = 'airstudio.sound';
let ctx = null;
let on = (() => { try { return localStorage.getItem(KEY) !== '0'; } catch { return true; } })();

export const soundOn = () => on;
export function setSound(value) {
  on = value;
  try { localStorage.setItem(KEY, value ? '1' : '0'); } catch { /* نتجاهل */ }
}

// المتصفح ما يسمح بالصوت إلا بعد ضغطة من المستخدم، فنصنع الـ AudioContext وقتها
export function unlockSound() {
  ctx ??= new AudioContext();
  if (ctx.state === 'suspended') ctx.resume();
}

// نغمة قصيرة: freq بالهيرتز، ms مدتها
export function blip(freq = 660, ms = 70) {
  if (!on || !ctx) return;
  const t = ctx.currentTime, osc = ctx.createOscillator(), gain = ctx.createGain();
  osc.frequency.value = freq;
  osc.type = 'sine';
  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(0.05, t + 0.01); // يبدي بنعومة حتى ما يطك
  gain.gain.exponentialRampToValueAtTime(0.0001, t + ms / 1000);
  osc.connect(gain).connect(ctx.destination);
  osc.start(t);
  osc.stop(t + ms / 1000 + 0.02);
}

// كل إيماءة إلها نغمة، حتى تعرفها بأذنك بدون ما تباوع
export const GESTURE_TONE = { PINCH: 880, MIDDLE_PINCH: 740, FIST: 330, OPEN_PALM: 520, TWO_FINGERS: 620 };
