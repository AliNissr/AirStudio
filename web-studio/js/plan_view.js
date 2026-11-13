// يرسم المخطط على الورقة، ويشغّل الماوس كبديل للإيماءات.
import { PlanInteraction } from './interaction.js';

const VIEW_METERS = 12;   // عرض الورقة = 12 متر
const WALL_T = 0.15;      // سمك الجدار بالرسم (متر)
const INK = '#2a3340', PENCIL = '#e8b341', LEAD = '#6b7484';

export class PlanView {
  constructor(canvas, plan) {
    this.canvas = canvas;
    this.plan = plan;
    this.state = {};
    this.mouse = new PlanInteraction(plan); // الماوس إله تفاعل منفصل حتى ما يتلخبط ويه الكاميرا
    this.bindMouse();
  }

  get ppm() { return Math.max(40, this.canvas.clientWidth / VIEW_METERS); } // بكسل لكل متر
  toMeters(p) { return { x: p.x / this.ppm, y: p.y / this.ppm }; }
  toPx(p) { return { x: p.x * this.ppm, y: p.y * this.ppm }; }

  setTool(tool) {
    this.tool = tool;
    if (tool !== 'erase') this.mouse.tool = tool;
  }

  bindMouse() {
    const c = this.canvas;
    let erasing = false;
    const at = (e) => this.toMeters({ x: e.offsetX, y: e.offsetY });
    const feed = (gesture, e, t = e.timeStamp / 1000) =>
      (this.state = this.mouse.update({ hands: [{ id: 'mouse', gesture, point: at(e) }], two: null }, t));
    c.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      c.setPointerCapture(e.pointerId);
      if (this.tool === 'erase') {
        erasing = true;
        this.plan.checkpoint();
        this.plan.eraseAt(at(e), 0.35, false);
      } else feed('PINCH', e);
      this.render();
    });
    c.addEventListener('pointermove', (e) => {
      if (erasing) this.plan.eraseAt(at(e), 0.35, false);
      else if (this.mouse.draw) feed('PINCH', e);
      else return;
      this.render();
    });
    c.addEventListener('pointerup', (e) => {
      if (erasing) erasing = false;
      else if (this.mouse.draw) feed('NONE', e);
      this.state = {};
      this.render();
      this.onChange?.();
    });
  }

  // state من PlanInteraction.update (للكاميرا)
  render(state = this.state) {
    this.state = state;
    const c = this.canvas, dpr = devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
    c.parentElement.style.setProperty('--m', `${this.ppm}px`); // شبكة الورقة = متر حقيقي
    const g = c.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    g.lineCap = 'round';
    g.lineJoin = 'round';

    // الرسم الحر: قلم رصاص رفيع
    const strokes = state.stroke ? [...this.plan.strokes, state.stroke] : this.plan.strokes;
    g.strokeStyle = LEAD;
    g.lineWidth = 2;
    for (const s of strokes) {
      g.beginPath();
      s.forEach((p, i) => { const q = this.toPx(p); i ? g.lineTo(q.x, q.y) : g.moveTo(q.x, q.y); });
      g.stroke();
    }

    // الجدران: حبر غامق بسمك حقيقي + طول كل جدار
    for (const wall of this.plan.walls) this.drawWall(g, wall, INK);
    if (state.preview) this.drawWall(g, state.preview, PENCIL, true);

    if (state.eraser) {
      const q = this.toPx(state.eraser.center);
      g.strokeStyle = '#c0392b';
      g.lineWidth = 2;
      g.setLineDash([6, 5]);
      g.beginPath();
      g.arc(q.x, q.y, state.eraser.radius * this.ppm, 0, Math.PI * 2);
      g.stroke();
      g.setLineDash([]);
    }
    if (state.pauseProgress > 0 && state.palm) {
      const q = this.toPx(state.palm);
      g.strokeStyle = PENCIL;
      g.lineWidth = 4;
      g.beginPath();
      g.arc(q.x, q.y, 34, -Math.PI / 2, -Math.PI / 2 + state.pauseProgress * Math.PI * 2);
      g.stroke();
    }
  }

  drawWall(g, wall, color, preview = false) {
    const a = this.toPx(wall.a), b = this.toPx(wall.b);
    g.strokeStyle = color;
    g.lineWidth = WALL_T * this.ppm;
    if (preview) g.globalAlpha = 0.8;
    g.beginPath();
    g.moveTo(a.x, a.y);
    g.lineTo(b.x, b.y);
    g.stroke();
    g.globalAlpha = 1;
    // الطول بالمتر فوك نص الجدار
    const len = Math.hypot(wall.b.x - wall.a.x, wall.b.y - wall.a.y);
    if (len < 0.2) return;
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const nx = -(b.y - a.y) / (len * this.ppm), ny = (b.x - a.x) / (len * this.ppm); // اتجاه عمودي على الجدار
    g.font = '600 12px "Segoe UI", Tahoma, sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillStyle = preview ? '#9a7417' : '#5a6372';
    g.fillText(`${len.toFixed(1)} م`, mx + nx * 16, my + ny * 16);
  }
}
