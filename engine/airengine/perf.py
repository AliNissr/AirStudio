"""أداء: نخفف الشغل لما ماكو يد أو لما المعالج مضغوط، حتى ما نأثر على شغلك."""
import psutil


class AdaptiveRate:
    def __init__(self, active_fps: int = 30, idle_fps: int = 5, cpu_limit: float = 25, idle_after: float = 1.0):
        self.active_fps, self.idle_fps = active_fps, idle_fps
        self.cpu_limit = cpu_limit    # نسبة من المعالج كله (كل الأنوية)
        self.idle_after = idle_after  # كم ثانية بدون يد قبل ما نبطّئ
        self._last_hand = None

    def next_interval(self, hand_present: bool, cpu: float, now: float) -> float:
        """يرجع كم ثانية ننتظر قبل الإطار الجاي."""
        if hand_present or self._last_hand is None:
            self._last_hand = now
        if now - self._last_hand > self.idle_after:
            return 1 / self.idle_fps
        if cpu > self.cpu_limit:
            return 1 / max(self.idle_fps, self.active_fps // 2)
        return 1 / self.active_fps


class CpuMeter:
    """يقيس استهلاك برنامجنا بس، كنسبة من المعالج كله (مثل مدير المهام)."""

    def __init__(self):
        self._p = psutil.Process()
        self._cores = psutil.cpu_count() or 1
        self._p.cpu_percent()  # أول قراءة دايماً صفر، نسويها هسه

    def percent(self) -> float:
        return self._p.cpu_percent() / self._cores


def set_below_normal_priority() -> None:
    """نكول للويندوز: برامجك الثانية أهم منا. ما يحتاج Administrator."""
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
