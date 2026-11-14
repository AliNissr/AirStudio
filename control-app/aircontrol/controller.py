"""العقل: يربط الإيماءات بالأمان والمؤشر والقائمة الدائرية ولوحة المفاتيح، ويرسل الأوامر للإخراج.
نقي (بدون Qt ولا ويندوز)، حتى نختبر الطريق كامل.

كل أمر لازم يعبر safety.gate(): الحالة (شغال؟) ← القائمة البيضاء ← تأكيد الحساس.
"""
from collections import deque

from .actions import Command
from .gestures_ctrl import ControlGestures, CTRL_DEFAULTS
from .keyboard import KeyboardModel, Predictor
from .pointer import PointerController
from .radial import RadialMenu, LABELS
from .safety.state import SafetyState, OFF

HOTKEY_GRACE = 1.0  # بعد اختصار، ضغطات الاختصار نفسه مو "لمس حقيقي"
NAMES_AR = {"click": "نقر", "double_click": "نقر مزدوج", "right_click": "نقر يمين", "drag_start": "بداية سحب",
            "drag_end": "إفلات", "scroll": "تمرير", "zoom": "تكبير/تصغير", "alt_tab": "تبديل النوافذ",
            "type_text": "كتابة", "key": "مفتاح"}


class DryRunOutput:
    """Dry-run: يسجّل ويعرض بس. ما يرسل أي شي لويندوز."""

    def __init__(self):
        self.log = deque(maxlen=50)      # (الأمر، مكان المؤشر)
        self.blocked = deque(maxlen=50)  # أوامر انرفضت وليش

    def execute(self, cmd, pos):
        self.log.append((cmd, pos))

    def describe(self, cmd, pos):
        name = NAMES_AR.get(cmd.name) or LABELS.get(cmd.name, cmd.name)
        if cmd.name == "type_text":
            return f"راح يكتب: «{cmd.args['text']}»"
        if cmd.name == "key":
            return f"مفتاح: {cmd.args['name']}"
        return f"{name} عند {pos}"


class KeyboardPanel:
    def __init__(self, monitor, predictor):
        w = min(1100, int((monitor.right - monitor.left) * 0.8))
        h = 330
        self.origin = (monitor.left + (monitor.right - monitor.left - w) // 2, monitor.bottom - h - 40)
        self.model = KeyboardModel(w, h, predictor)

    def contains(self, x, y):
        return 0 <= x - self.origin[0] < self.model.width and 0 <= y - self.origin[1] < self.model.height

    def hit(self, x, y):
        return self.model.hit(x - self.origin[0], y - self.origin[1])


class Controller:
    def __init__(self, desktop, bindings, radial_items, pointer_cfg, gestures=None, output=None, predictor=None):
        self.desktop, self.bindings, self.radial_items = desktop, bindings, radial_items
        self.gestures = gestures or ControlGestures(CTRL_DEFAULTS)
        self.output = output or DryRunOutput()
        self.pointer = PointerController(desktop, pointer_cfg)
        self.safety = SafetyState()
        self.predictor = predictor or Predictor()
        self.radial = None
        self.keyboard = None
        self.confirm_until = 0.0
        self.last_hotkey = -10.0
        self.message = ""  # آخر شي صار (للطبقة)
        self.view = {}

    @property
    def want_hands(self):
        return 2 if self.safety.mode == OFF else 1  # يدين بس وقت ننتظر التفعيل (أسرع بيد وحدة)

    # ===== من ويندوز =====
    def on_hotkey(self, name, t):
        self.last_hotkey = t
        if name == "stop":
            self._stop()
        elif name == "activate":
            self.safety.activate(t)
            self.message = "التحكم شغال"
        elif name == "precision":
            self.pointer.precision = not self.pointer.precision
            self.message = "وضع الدقة" if self.pointer.precision else "السرعة العادية"
        elif name in ("monitor_right", "monitor_left"):
            self.pointer.jump(1 if name == "monitor_right" else -1)

    def on_real_input(self, t):
        if t - self.last_hotkey < HOTKEY_GRACE:
            return
        if self.safety.mode != OFF:
            self.message = "لمست الماوس أو الكيبورد: موقف 3 ثواني"
        self.safety.real_input(t)

    def _stop(self):
        self.safety.emergency_stop()
        self.radial = self.keyboard = None
        self.confirm_until = 0.0
        self.message = "إيقاف طارئ: التحكم مطفي"

    # ===== الأوامر =====
    def send(self, cmd, t):
        decision = self.safety.gate(cmd, t)
        if decision == "ok":
            self.output.execute(cmd, self.pointer.pos)
            self.message = self.output.describe(cmd, self.pointer.pos)
        elif decision == "needs_confirm":
            self.confirm_until = t + 5
            self.message = f"تأكيد «{LABELS.get(cmd.name, cmd.name)}»: ثبّت الإبهام على السبابة"
        else:
            self.output.blocked.append(f"{cmd.name}: {decision}")
            if not decision.startswith("blocked:off"):
                self.message = f"انرفض: {cmd.name} ({decision.split(':', 1)[1]})"

    def run_action(self, action, t, args=None):
        if action == "keyboard":
            self.open_keyboard()
        elif action == "radial_menu":
            self.radial = RadialMenu(self.radial_items, self._menu_center())
        elif action not in ("none", "drag"):
            self.send(Command(action, args or {}), t)

    def open_keyboard(self):
        mon = self.desktop.monitors[self.desktop.monitor_at(*self.pointer.pos) or 0]
        self.keyboard = KeyboardPanel(mon, self.predictor)

    def _menu_center(self):
        x, y = self.pointer.pos
        mon = self.desktop.monitors[self.desktop.monitor_at(x, y) or 0]
        m = 220  # القائمة كلها لازم تبين داخل الشاشة
        return (min(max(x, mon.left + m), mon.right - m), min(max(y, mon.top + m), mon.bottom - m))

    def _tap(self, t):
        """نقرة السبابة: إذا فوك القائمة أو لوحة المفاتيح نتعامل وياها، وإلا الأمر المربوط."""
        x, y = self.pointer.pos
        if self.radial:
            i = self.radial.hit(x, y)
            item = self.radial.items[i] if i is not None else None
            self.radial = None
            if item:
                self.run_action(item, t)
            return
        if self.keyboard and self.keyboard.contains(x, y):
            hit = self.keyboard.hit(x, y)
            cmds = self.keyboard.model.pick(hit) if isinstance(hit, str) else self.keyboard.model.press(hit) if hit else []
            for cmd in cmds:
                if cmd.name == "_close_keyboard":
                    self.keyboard = None
                else:
                    self.send(cmd, t)
            return
        self.run_action(self.bindings["tap_index"], t)

    # ===== كل إطار =====
    def step(self, hands, t, w, h):
        events, st = self.gestures.update(hands, t, w, h)
        self.safety.tick(t)
        for name, data in events:
            if name == "fist_hold":
                self._stop()
            elif name == "both_palms":
                self.safety.activate(t)
                self.message = "التحكم شغال"
            elif self.safety.mode == OFF:
                continue  # مطفي: نتجاهل كل الباقي
            elif name == "palm_swipe":
                self.pointer.jump(data["dir"])
            elif name == "tap_index":
                self._tap(t)
            elif name == "hold_index":
                if data["phase"] == "start" and self.confirm_until:
                    cmd = self.safety.confirm(t) if t <= self.confirm_until else None
                    self.confirm_until = 0.0
                    if cmd:
                        self.output.execute(cmd, self.pointer.pos)
                        self.message = self.output.describe(cmd, self.pointer.pos)
                        continue
                if self.bindings["hold_index"] == "drag":
                    self.send(Command("drag_start" if data["phase"] == "start" else "drag_end"), t)
                elif data["phase"] == "start":  # أمر مفرد: مرة وحدة بالبداية، مو مرة ثانية بالفك
                    self.run_action(self.bindings["hold_index"], t)
            elif name in ("two_finger_move", "three_finger_vertical"):
                # حركة مستمرة: الربط مسموح بس لتمرير أو تكبير أو لا شي (bindings.CONTINUOUS)
                amount = data.get("steps", data.get("dy", 0))
                if self.bindings[name] == "scroll":
                    self.send(Command("scroll", {"dx": data.get("dx", 0), "dy": amount}), t)
                elif self.bindings[name] == "zoom" and amount:
                    self.send(Command("zoom", {"steps": amount}), t)
            elif name == "three_finger_swipe" and self.bindings[name] == "alt_tab":
                self.send(Command("alt_tab", data), t)
            elif name in self.bindings:
                self.run_action(self.bindings[name], t)
        if self.confirm_until and t > self.confirm_until:
            self.confirm_until = 0.0
            self.safety.confirm(t)  # انتهى الوقت: نمسح المعلّق
            self.message = "انلغى التأكيد"

        if st.get("anchor") is not None:
            # المؤشر يتحرك بكل الحالات حتى تشوف التتبع شغال. بالـ Dry-run ما نسجّل الحركة (تملي السجل)؛
            # بالمرحلة 4 الإخراج الحقيقي يحرك الماوس بس إذا الحالة ACTIVE (عبر gate مثل أي أمر)
            self.pointer.update(st["anchor"], t, clutch=st["clutch"], click_lock=st["click_lock"])
        self.view = {**st, "pos": self.pointer.pos, "mode": self.safety.mode, "precision": self.pointer.precision}
        return self.view
