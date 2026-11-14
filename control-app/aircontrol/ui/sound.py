"""نغمات تأكيد قصيرة بخيط بالخلفية (winsound.Beep يوقف الخيط اللي يناديه، فما نناديه من الواجهة)."""
import queue
import threading
import winsound

TONES = {"activate": (880, 120), "stop": (300, 260), "pause": (440, 90), "tap": (1250, 18),
         "confirm": (990, 140), "blocked": (220, 80), "menu": (700, 40)}


class Sound:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._q = queue.Queue(maxsize=4)  # إذا تراكمت نغمات، نتجاهل الزايد (ما نتأخر)
        threading.Thread(target=self._run, daemon=True).start()

    def play(self, name):
        if self.enabled and name in TONES:
            try:
                self._q.put_nowait(TONES[name])
            except queue.Full:
                pass

    def _run(self):
        while True:
            freq, ms = self._q.get()
            winsound.Beep(freq, ms)
