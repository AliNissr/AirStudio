// يحوّل إيماءات اليد لأوامر على المخطط. نقي: ياخذ أيادي بالمتر ويرجع شنو نرسم.
//   قرص + سحب  = جدار (أو رسم حر بأداة القلم)، الإفلات ينهيه
//   كف تتحرك   = ممحاة
//   كف ثابتة 1.5 ث = إيقاف / استئناف
// المؤشر ينطي نقاط {x, y} بالمتر؛ الصفحة هي اللي تحوّل من الكاميرا للمتر.

const ERASE_RADIUS = 0.35; // متر
const STILL_RADIUS = 0.15; // الكف تعتبر "ثابتة" إذا ما طلعت من دائرة 15 سم
const PAUSE_HOLD = 1.5;    // ثانية

const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

export class PlanInteraction {
  constructor(plan) {
    this.plan = plan;
    this.tool = 'wall'; // 'wall' أو 'pen'
    this.paused = false;
    this.draw = null;   // { id, start, last, points }
    this.palm = null;   // { id, anchor, since, erasing, toggled }
  }

  cancel() { this.draw = null; }

  // frame: {hands: [{id, gesture, point}], two}، t بالثواني
  update(frame, t) {
    const out = { preview: null, stroke: null, eraser: null, paused: this.paused, pauseProgress: 0 };

    // اليدين بإيماءة مسك = تكبير/دوران، مو رسم
    if (frame.two) { this.cancel(); this.palm = null; return out; }

    this.updatePalm(frame, t, out);
    out.paused = this.paused;
    if (this.paused) { this.cancel(); return out; }

    const d = this.draw;
    const h = d ? frame.hands.find((x) => x.id === d.id) : frame.hands.find((x) => x.gesture === 'PINCH');
    if (!d && h) {
      this.draw = { id: h.id, start: h.point, last: h.point, points: [h.point] };
    } else if (d && !h) {
      this.cancel(); // اليد اختفت بنص الرسم: نلغي، ما نكمّل جدار ما قصدته
    } else if (d && h.gesture === 'PINCH') {
      d.last = h.point;
      if (this.tool === 'pen' && dist(h.point, d.points.at(-1)) > 0.02) d.points.push(h.point);
    } else if (d) {
      // فتحت أصابعك: نثبّت بآخر نقطة وانت قارص
      if (this.tool === 'pen') this.plan.addStroke(d.points);
      else this.plan.addWall(d.start, d.last);
      this.cancel();
    }

    if (this.draw) {
      if (this.tool === 'pen') out.stroke = this.draw.points;
      else out.preview = this.plan.snapWall(this.draw.start, this.draw.last);
    }
    return out;
  }

  updatePalm(frame, t, out) {
    const h = frame.hands.find((x) => x.gesture === 'OPEN_PALM' && (!this.palm || x.id === this.palm.id));
    if (!h) { this.palm = null; return; }
    let p = this.palm;
    if (!p) p = this.palm = { id: h.id, anchor: h.point, since: t, erasing: false, toggled: false };

    if (!p.erasing && dist(h.point, p.anchor) > STILL_RADIUS) {
      // تحركت: صارت ممحاة. نحفظ نسخة وحدة حتى تراجع واحد يرجّع كل المسح
      if (this.paused) return;
      p.erasing = true;
      this.plan.checkpoint();
    }
    if (p.erasing) {
      // نمسح على طول الطريق من آخر نقطة، مو بس بالنقطة الحالية: الحركة السريعة تقفز فوك الجدران بين إطارين
      const from = p.last ?? p.anchor, steps = Math.ceil(dist(from, h.point) / (ERASE_RADIUS / 2));
      for (let i = 0; i <= steps; i++) {
        const k = steps ? i / steps : 1;
        this.plan.eraseAt({ x: from.x + (h.point.x - from.x) * k, y: from.y + (h.point.y - from.y) * k }, ERASE_RADIUS, false);
      }
      p.last = h.point;
      out.eraser = { center: h.point, radius: ERASE_RADIUS };
      return;
    }
    if (p.toggled) return; // نفس المسكة: ما نبدّل مرة ثانية
    out.palm = p.anchor; // وين نرسم حلقة العد
    out.pauseProgress = Math.min(1, (t - p.since) / PAUSE_HOLD);
    if (t - p.since >= PAUSE_HOLD) {
      this.paused = !this.paused;
      p.toggled = true;
      out.pauseProgress = 0;
    }
  }
}
