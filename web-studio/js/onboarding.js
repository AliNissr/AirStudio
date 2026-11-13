// الشاشة التعليمية: 5 خطوات بالترتيب، كل خطوة تنتظرك تسوي الإيماءة (ثابتة 0.6 ثانية) حتى تتقدم.
// OnboardingFlow نقي (بدون صفحة) حتى نختبره، و mountOnboarding يرسمه.

const HOLD_S = 0.6;
const has = (g) => (f) => f.hands.some((h) => h.gesture === g);

export const STEPS = [
  { id: 'camera', title: 'نشغّل الكاميرا', body: 'الاستوديو يشوف يدك من الكاميرا. الصورة تبقى بجهازك، ما تنحفظ وما تنرسل لأي مكان.', check: null },
  { id: 'palm', title: 'افتح كفّك', body: 'ثبّت كفك مفتوحة قدام الكاميرا. بالاستوديو، الكف المفتوحة تمسح، وإذا ثبّتها ثانية ونص توقف الشغل.', check: has('OPEN_PALM') },
  { id: 'pinch', title: 'اقرص', body: 'لزّك طرف الإبهام بطرف السبابة. القرص يرسم الجدران ويمسك قطع الأثاث.', check: has('PINCH') },
  { id: 'fist', title: 'سكّر قبضتك', body: 'القبضة تسحب الأشياء الموجودة وتحركها لمكان جديد.', check: has('FIST') },
  { id: 'two', title: 'اليدين سوية', body: 'سكّر القبضتين بنفس الوقت. بعّدهم عن بعض تكبّر، قرّبهم تصغّر، ودوّرهم حتى يدور المنظر.', check: (f) => Boolean(f.two) },
];

export class OnboardingFlow {
  constructor(start = 0) {
    this.index = start;
    this.holdStart = null;
    this.progress = 0; // 0..1 شكد ثبّتت الإيماءة (للحلقة)
  }

  get current() { return STEPS[this.index]; }
  get done() { return this.index >= STEPS.length; }

  next() {
    this.index++;
    this.holdStart = null;
    this.progress = 0;
  }

  skip() { this.index = STEPS.length; }

  // frame من HandPipeline، t بالثواني. يرجع true إذا تقدمت خطوة
  update(frame, t) {
    if (this.done || !this.current.check) return false;
    if (!this.current.check(frame)) {
      this.holdStart = null; // انكسرت الإيماءة: نبدي العد من جديد
      this.progress = 0;
      return false;
    }
    this.holdStart ??= t;
    this.progress = Math.min(1, (t - this.holdStart) / HOLD_S);
    if (t - this.holdStart >= HOLD_S) {
      this.next();
      return true;
    }
    return false;
  }
}

const SEEN_KEY = 'airstudio.onboarded';
export const seenOnboarding = () => { try { return localStorage.getItem(SEEN_KEY) === '1'; } catch { return false; } };
const markSeen = () => { try { localStorage.setItem(SEEN_KEY, '1'); } catch { /* وضع التصفح الخاص: نتجاهل */ } };

/**
 * يرسم الشاشة التعليمية داخل root (عنصر <dialog>).
 * onStartCamera: دالة async تشغّل الكاميرا وترجع true إذا اشتغلت.
 * يرجع {feed(frame, t)} حتى app.js يمرر إطارات اليد.
 */
export function mountOnboarding(root, { onStartCamera, onAdvance = () => {}, onDone = () => {} }) {
  const flow = new OnboardingFlow();
  const $ = (sel) => root.querySelector(sel);

  const render = () => {
    if (flow.done) {
      markSeen();
      root.close();
      onDone();
      return;
    }
    const s = flow.current;
    $('[data-step]').textContent = `${flow.index + 1} من ${STEPS.length}`;
    $('[data-title]').textContent = s.title;
    $('[data-body]').textContent = s.body;
    $('[data-art]').dataset.art = s.id;
    root.querySelectorAll('[data-dot]').forEach((d, i) => d.toggleAttribute('data-on', i <= flow.index));
    $('[data-camera]').hidden = s.id !== 'camera';
    $('[data-next]').textContent = s.id === 'camera' ? 'أكمل بالماوس' : 'التالي';
    $('[data-ring]').style.setProperty('--p', flow.progress);
  };

  $('[data-camera]').onclick = async () => {
    $('[data-camera]').disabled = true;
    if (await onStartCamera()) flow.next();
    $('[data-camera]').disabled = false;
    render();
  };
  $('[data-next]').onclick = () => { flow.next(); render(); };
  $('[data-skip]').onclick = () => { flow.skip(); render(); };

  root.showModal();
  render();
  return {
    feed(frame, t) {
      if (flow.done) return;
      if (flow.update(frame, t)) onAdvance();
      render();
    },
  };
}
