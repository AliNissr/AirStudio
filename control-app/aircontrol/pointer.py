"""حركة المؤشر من نقطة اليد. نقي.

الأوضاع:
  relative (الافتراضي): "لوحة لمس بالهوا": حركة إيدك = حركة المؤشر، مع تسارع.
  absolute: منطقة المعايرة بالكاميرا = سطح المكتب كله.
  precision: السرعة ÷ 3 (يشتغل ويه الوضعين).
anchor = نقطة ثابتة بالسبابة (قاعدة الإصبع)، مقسومة على حجم الصورة (0..1).
"""
import math

from airengine.one_euro import OneEuroFilter


def smoothstep(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * (3 - 2 * k)


class PointerController:
    def __init__(self, desktop, cfg, mode="relative", start=None):
        self.desktop, self.cfg, self.mode = desktop, cfg, mode
        self.precision = False
        self.fpos = list(start or desktop.monitors[0].center)  # بالكسور، حتى الحركات الصغيرة ما تضيع بالتقريب
        self.prev = None  # (anchor, t) للإطار السابق
        self.fx, self.fy = OneEuroFilter(**cfg["one_euro"]), OneEuroFilter(**cfg["one_euro"])

    @property
    def pos(self):
        return (round(self.fpos[0]), round(self.fpos[1]))

    def _set(self, x, y):
        self.fpos = list(self.desktop.clamp(round(x), round(y)))

    def jump(self, direction):
        """ينقل المؤشر لنص الشاشة الثانية."""
        self._set(*self.desktop.next_center(*self.pos, direction))

    def update(self, anchor, t, clutch=False, click_lock=0.0):
        """clutch: كف مفتوحة (المؤشر واكف). click_lock: 0..1 شكد الإبهام قريب من النقر (يبطّئ الحركة)."""
        a = (self.fx.filter(anchor[0], t), self.fy.filter(anchor[1], t))
        slow = (self.cfg["precision"] if self.precision else 1.0) * (1.0 - click_lock)

        if self.mode == "absolute":
            r = self.cfg["region"]
            l, top, right, bottom = self.desktop.bounds
            nx = min(max((a[0] - r[0]) / (r[2] - r[0]), 0), 1)
            ny = min(max((a[1] - r[1]) / (r[3] - r[1]), 0), 1)
            tx, ty = l + nx * (right - l - 1), top + ny * (bottom - top - 1)
            if not clutch:  # بالدقة أو قفل النقر نقرّب للهدف بالتدريج بدل ما نقفز
                self._set(self.fpos[0] + (tx - self.fpos[0]) * slow, self.fpos[1] + (ty - self.fpos[1]) * slow)
            return self.pos

        if clutch or self.prev is None:
            self.prev = (a, t)  # رفعت إيدك: نحفظ مكانها الجديد بدون ما نحرك المؤشر
            return self.pos
        (px, py), pt = self.prev
        dt = max(t - pt, 1e-3)
        dx, dy = a[0] - px, a[1] - py
        speed = math.hypot(dx, dy) / dt
        c = self.cfg
        gain = c["gain_min"] + (c["gain_max"] - c["gain_min"]) * smoothstep((speed - c["speed_low"]) / (c["speed_high"] - c["speed_low"]))
        self.prev = (a, t)
        x = self.fpos[0] + dx * gain * slow
        y = self.fpos[1] + dy * gain * slow
        cx, cy = self.desktop.clamp(round(x), round(y))
        # نخلي الكسور إذا ما انقصّ، حتى الحركة البطيئة جداً تتجمع وما تضيع
        self.fpos = [x if cx == round(x) else cx, y if cy == round(y) else cy]
        return self.pos
