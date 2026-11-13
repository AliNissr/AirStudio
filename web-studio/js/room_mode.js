// وضع الغرفة 3D: يربط Room (المنطق) و RoomInteraction (الإيماءات) و RoomView (الرسم) والماوس والأزرار.
import { Room, FURNITURE } from './layout.js';
import { RoomInteraction } from './room_interaction.js';

const DEFAULT_BOUNDS = { minX: 0, minY: 0, maxX: 5, maxY: 4 }; // غرفة 5×4 م إذا ماكو جدران

export function createRoomMode({ stage, plan, blip }) {
  const $ = (id) => document.getElementById(id);
  const room = new Room(DEFAULT_BOUNDS);
  const ui = new RoomInteraction(room);
  let view = null; // ننشئ WebGL بس لما تفتح الغرفة أول مرة
  let last = {};

  const pieces = [...stage.querySelectorAll('[data-type]')];

  function refresh(extra = {}) {
    last = { ...last, ...extra };
    view?.sync(room.items, { ghost: last.ghost, selected: ui.selected, removing: last.removeProgress > 0 });
    $('rotate').disabled = $('remove').disabled = !ui.selected;
    $('room-undo').disabled = !room.history.length;
  }

  // ===== الماوس =====
  function bindMouse(canvas) {
    let drag = null;
    const at = (e) => view.floorAt(e.offsetX, e.offsetY);
    canvas.addEventListener('pointerdown', (e) => {
      canvas.setPointerCapture(e.pointerId);
      const p = at(e), item = p && room.hitTest(p);
      ui.selected = item?.id ?? null;
      // checkpoint بأول حركة فعلية، مو بالضغطة: ضغطة للاختيار بس ما لازم تصير خطوة تراجع فاضية
      if (item) drag = { item: item.id, off: { x: item.x - p.x, y: item.y - p.y }, moved: false };
      else drag = { orbit: true, x: e.clientX, y: e.clientY };
      refresh();
    });
    canvas.addEventListener('pointermove', (e) => {
      if (!drag) return;
      if (drag.orbit) {
        view.orbitBy(-(e.clientX - drag.x) * 0.008, (e.clientY - drag.y) * 0.006);
        drag.x = e.clientX;
        drag.y = e.clientY;
      } else {
        const p = at(e);
        if (!p) return;
        if (!drag.moved) { room.checkpoint(); drag.moved = true; }
        room.move(drag.item, { x: p.x + drag.off.x, y: p.y + drag.off.y }, false);
        refresh();
      }
    });
    canvas.addEventListener('pointerup', () => { drag = null; });
    canvas.addEventListener('wheel', (e) => { e.preventDefault(); view.zoomBy(e.deltaY > 0 ? 1.1 : 0.9); }, { passive: false });
  }

  // ===== الأزرار =====
  for (const b of pieces) {
    b.onclick = () => { // ضغطة بالماوس: القطعة تنحط بنص الغرفة
      const bd = room.bounds;
      ui.selected = room.add(b.dataset.type, { x: (bd.minX + bd.maxX) / 2, y: (bd.minY + bd.maxY) / 2 }).id;
      blip(1040, 90);
      refresh();
    };
  }
  const rotateSelected = () => { if (ui.selected) { room.rotate(ui.selected, room.get(ui.selected).rot + Math.PI / 2); refresh(); } };
  const removeSelected = () => { if (ui.selected) { room.remove(ui.selected); ui.selected = null; blip(240, 60); refresh(); } };
  $('rotate').onclick = rotateSelected;
  $('remove').onclick = removeSelected;
  $('room-undo').onclick = () => { room.undo(); if (!room.get(ui.selected)) ui.selected = null; refresh(); };
  stage.querySelectorAll('[data-view]').forEach((b) => {
    b.onclick = () => {
      view.setPreset(b.dataset.view);
      stage.querySelectorAll('[data-view]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    };
  });

  return {
    room,
    get view() { return view; },
    async enter() {
      if (!view) {
        const { RoomView } = await import('./room3d.js'); // three.js (2 MB) ينحمّل بس إذا احتجناه
        view = new RoomView($('room'));
        bindMouse(view.renderer.domElement);
        addEventListener('resize', () => view.resize());
      }
      // الحدود من المخطط؛ مخطط أصغر من متر مربع (جدار واحد مثلاً) = الغرفة الافتراضية
      const b = plan.bounds();
      room.bounds = b && (b.maxX - b.minX) * (b.maxY - b.minY) >= 1 ? b : DEFAULT_BOUNDS;
      for (const it of room.items) Object.assign(it, room.clamp(it, it)); // الجدران تغيّرت؟ نرجّع الأثاث داخلها
      view.resize();
      view.setRoom(room.bounds === DEFAULT_BOUNDS ? [] : plan.walls, room.bounds);
      refresh();
    },

    // frame من HandPipeline + toPx: يحوّل مؤشر اليد لبكسل داخل الحاوية
    feed(frame, toPx) {
      if (!view) return;
      const rects = pieces.map((b) => [b, b.getBoundingClientRect()]), origin = $('room').getBoundingClientRect();
      pieces.forEach((b) => b.removeAttribute('data-hover'));
      const hands = frame.hands.map((h) => {
        const p = toPx(h.pointer), cx = origin.x + p.x, cy = origin.y + p.y;
        const over = rects.find(([, r]) => cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom)?.[0];
        over?.setAttribute('data-hover', '');
        return { id: h.id, gesture: h.gesture, palette: over?.dataset.type, floor: over ? null : view.floorAt(p.x, p.y) };
      });
      const count = room.items.length;
      const out = ui.update({ hands, two: frame.two }, performance.now() / 1000);
      if (out.camera) view.applyGesture(out.camera); else view.endGesture();
      if (room.items.length > count) blip(1040, 90);
      if (out.removed) blip(240, 60);
      refresh(out);
    },

    undo() { room.undo(); if (!room.get(ui.selected)) ui.selected = null; refresh(); },
    onKey(e) {
      if (e.key === 'Delete' || e.key === 'Backspace') { removeSelected(); return true; }
      if (e.key.toLowerCase() === 'r' && !e.ctrlKey) { rotateSelected(); return true; }
      return false;
    },
    snapshot: () => view?.toBlob(),
    types: Object.keys(FURNITURE),
  };
}
