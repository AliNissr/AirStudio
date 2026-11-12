"""فلتر One Euro: ينعّم الرجفة لما اليد واكفة، ويخلي الحركة السريعة بدون تأخير.

الفكرة: نعدّل "قوة التنعيم" حسب السرعة.
- يد بطيئة/ثابتة → تنعيم قوي (نشيل الرجفة).
- يد سريعة → تنعيم خفيف (ما نتأخر وراها).
المرجع: Casiez et al., CHI 2012.
"""
import math


def _alpha(cutoff: float, dt: float) -> float:
    # نحوّل "تردد القطع" لنسبة خلط بين 0 و 1 (كلما أكبر، نصدّق القيمة الجديدة أكثر)
    tau = 1.0 / (2 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff  # أقل تنعيم: كلما أصغر، رجفة أقل وتأخير أكثر
        self.beta = beta              # شكد السرعة تقلل التنعيم
        self.d_cutoff = d_cutoff      # تنعيم حساب السرعة نفسه
        self.reset()

    def reset(self) -> None:
        """ننسى كل شي (مثلاً لما اليد تطلع من الصورة)."""
        self._x = None
        self._dx = 0.0
        self._t = None

    def filter(self, x: float, t: float) -> float:
        """x = القيمة الجديدة، t = الوقت بالثواني. يرجع القيمة المنعّمة."""
        if self._x is None:
            self._x, self._t = x, t
            return x
        dt = t - self._t
        if dt <= 0:  # نفس الإطار مكرر، ماكو جديد
            return self._x
        # 1) السرعة الحالية، منعّمة
        dx = (x - self._x) / dt
        self._dx += _alpha(self.d_cutoff, dt) * (dx - self._dx)
        # 2) كلما أسرع، cutoff أعلى، يعني تنعيم أقل
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        self._x += _alpha(cutoff, dt) * (x - self._x)
        self._t = t
        return self._x
