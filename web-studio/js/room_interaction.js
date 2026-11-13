// إيماءات الغرفة 3D. نقي: ياخذ أيادي بنقطة على الأرض (بالمتر) أو فوك قائمة الأثاث، ويرجع شنو نرسم.
//   قرص على قطعة بالقائمة + سحب + إفلات = تنضاف للغرفة
//   قبضة (أو قرص) على قطعة موجودة + سحب = تتحرك
//   يدين بإيماءة مسك = تدور القطعة المختارة، أو الكاميرا إذا ماكو قطعة مختارة
//   كف مفتوحة ثابتة ثانية فوك قطعة = تنمسح
// كل يد: {id, gesture, floor: {x,y} | null, palette: نوع | undefined}

const GRAB = new Set(['PINCH', 'FIST']);
const REMOVE_HOLD = 1.0; // ثانية

export class RoomInteraction {
  constructor(room) {
    this.room = room;
    this.hold = null;      // شنو ماسكين: {hand, mode: 'new'|'move', type|itemId, ...}
    this.selected = null;  // آخر قطعة لمستها
    this.twoBase = null;   // دوران القطعة ببداية إيماءة اليدين
    this.palm = null;      // {itemId, since}
    this.lastGesture = new Map();
  }

  update(frame, t = 0) {
    const out = { ghost: null, camera: null, removeProgress: 0, removeAt: null };
    const started = (h) => GRAB.has(h.gesture) && !GRAB.has(this.lastGesture.get(h.id));
    try {
      if (frame.two) return this.updateTwo(frame.two, out);
      this.twoBase = null;
      this.updatePalm(frame, t, out);
      this.updateHold(frame, started, out);
      return out;
    } finally {
      this.lastGesture = new Map(frame.hands.map((h) => [h.id, h.gesture]));
      out.selected = this.selected;
    }
  }

  updateTwo(two, out) {
    if (this.hold) this.cancel();
    const item = this.selected && this.room.get(this.selected);
    if (!item) { out.camera = { zoom: two.zoom, rotate: two.rotate }; return out; }
    if (this.twoBase === null) { this.twoBase = item.rot; this.room.checkpoint(); }
    this.room.rotate(item.id, this.twoBase + two.rotate, false);
    return out;
  }

  updatePalm(frame, t, out) {
    if (this.hold) { this.palm = null; return; } // يد وحدة ماسكة شي: ما نمسح بالثانية، حتى التراجع يبقى صحيح
    const h = frame.hands.find((x) => x.gesture === 'OPEN_PALM' && x.floor);
    const item = h && this.room.hitTest(h.floor);
    if (!item) { this.palm = null; return; }
    if (this.palm?.itemId !== item.id) this.palm = { itemId: item.id, since: t };
    out.removeProgress = Math.min(1, (t - this.palm.since) / REMOVE_HOLD);
    out.removeAt = { x: item.x, y: item.y };
    if (t - this.palm.since >= REMOVE_HOLD) {
      this.room.remove(item.id);
      if (this.selected === item.id) this.selected = null;
      this.palm = null;
      out.removeProgress = 0;
      out.removed = true;
    }
  }

  updateHold(frame, started, out) {
    if (!this.hold) {
      const h = frame.hands.find(started);
      if (!h) return;
      if (h.palette && h.gesture === 'PINCH') {
        this.hold = { hand: h.id, mode: 'new', type: h.palette, pos: null };
      } else if (h.floor) {
        const item = this.room.hitTest(h.floor);
        this.selected = item?.id ?? null; // مسك على أرض فاضية = نلغي الاختيار
        if (item) {
          this.room.checkpoint();
          // نحفظ الفرق بين المؤشر ونص القطعة، حتى ما تقفز لما تمسكها من طرفها
          this.hold = { hand: h.id, mode: 'move', itemId: item.id, off: { x: item.x - h.floor.x, y: item.y - h.floor.y } };
        }
      }
      return;
    }
    const hold = this.hold, h = frame.hands.find((x) => x.id === hold.hand);
    if (!h) { this.cancel(); return; } // اليد اختفت: نرجّع كلشي مثل ما كان
    if (GRAB.has(h.gesture)) {
      if (!h.floor) return;
      if (hold.mode === 'new') {
        hold.pos = h.floor;
        const ghost = { type: hold.type, rot: 0 };
        out.ghost = { ...ghost, ...this.room.clamp(ghost, h.floor) };
      } else {
        this.room.move(hold.itemId, { x: h.floor.x + hold.off.x, y: h.floor.y + hold.off.y }, false);
      }
      return;
    }
    // فتحت إيدك: نثبّت
    if (hold.mode === 'new' && hold.pos) this.selected = this.room.add(hold.type, hold.pos).id;
    this.hold = null;
  }

  cancel() {
    if (this.hold?.mode === 'move') this.room.undo(); // نرجع للنسخة اللي حفظناها ببداية السحب
    this.hold = null;
  }
}
