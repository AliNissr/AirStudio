"""سطح المكتب الافتراضي: كل الشاشات بلوحة وحدة، بالبكسل الحقيقي (البرنامج Per-Monitor DPI Aware V2).
نقي: الشاشات تجي كمستطيلات (من ويندوز بـ winapi.py، أو وهمية بالاختبارات).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Monitor:
    left: int
    top: int
    right: int   # حصري: آخر بكسل = right - 1
    bottom: int
    name: str = ""

    @property
    def center(self):
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    def contains(self, x, y):
        return self.left <= x < self.right and self.top <= y < self.bottom

    def clamp(self, x, y):
        return (min(max(x, self.left), self.right - 1), min(max(y, self.top), self.bottom - 1))


class Desktop:
    def __init__(self, monitors):
        if not monitors:
            raise ValueError("ماكو شاشات")
        self.monitors = list(monitors)
        self.bounds = (min(m.left for m in monitors), min(m.top for m in monitors),
                       max(m.right for m in monitors), max(m.bottom for m in monitors))

    def monitor_at(self, x, y):
        for i, m in enumerate(self.monitors):
            if m.contains(x, y):
                return i
        return None

    def clamp(self, x, y):
        """نقطة على شاشة حقيقية. الفراغات بين شاشات بأحجام مختلفة ← أقرب نقطة على أقرب شاشة."""
        if self.monitor_at(x, y) is not None:
            return (x, y)
        return min((m.clamp(x, y) for m in self.monitors), key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)

    def next_center(self, x, y, direction):
        """نص الشاشة اللي على اليمين (+1) أو اليسار (-1)، حسب مكانها الفعلي مو ترتيب ويندوز."""
        order = sorted(self.monitors, key=lambda m: (m.left, m.top))
        cur = self.monitors[self.monitor_at(*self.clamp(x, y))]
        i = min(max(order.index(cur) + direction, 0), len(order) - 1)
        return order[i].center

    def to_absolute(self, x, y):
        """بكسل ← 0..65535 على سطح المكتب الافتراضي كله (MOUSEEVENTF_ABSOLUTE | VIRTUALDESK)."""
        l, t, r, b = self.bounds
        return (round((x - l) * 65535 / max(r - l - 1, 1)), round((y - t) * 65535 / max(b - t - 1, 1)))
