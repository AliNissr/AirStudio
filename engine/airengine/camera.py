"""التقاط الصور من الكاميرا، مع أخطاء واضحة. الصور تبقى بالذاكرة بس، ما تنحفظ أبداً."""
import threading
import time

import cv2
import numpy as np


class CameraError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code  # واحد من مفاتيح messages.AR


def _open_dshow(index: int):
    # DirectShow يفتح الكاميرا أسرع من الافتراضي (MSMF) على أغلب لابتوبات ويندوز
    return cv2.VideoCapture(index, cv2.CAP_DSHOW)


class Camera:
    MAX_FAILS = 15  # كم مرة ورا بعض نفشل بالقراءة قبل ما نكول "انقطعت"

    def __init__(self, index: int = 0, width: int = 640, height: int = 480, opener=_open_dshow):
        # opener: الدالة اللي تفتح الكاميرا. بالاختبارات نمرر كاميرا وهمية بدالها
        self._cap = opener(index)
        if not self._cap.isOpened():
            raise CameraError("NOT_FOUND")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        # ملاحظة: جربنا CAP_PROP_FPS=30 وخلّى كاميرتك تثبت على 15، فما نحدده.
        # الكاميرا تنزل لـ 15 لحالها بالضوء الضعيف (تعريض تلقائي)، وهذا من العتاد مو من الكود.
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # نريد أحدث صورة، مو صور قديمة متراكمة
        self._fails = 0
        # أول صورة: إذا ما إجت أبداً، الكاميرا محجوزة من برنامج ثاني
        for _ in range(10):
            ok, _frame = self._cap.read()
            if ok:
                return
            time.sleep(0.05)
        self.release()
        raise CameraError("BUSY")

    def read(self) -> np.ndarray | None:
        """يرجع صورة BGR معكوسة مثل المراية، أو None إذا فشلت هالمرة."""
        ok, frame = self._cap.read()
        if not ok:
            self._fails += 1
            if self._fails > self.MAX_FAILS:
                raise CameraError("LOST")
            return None
        self._fails = 0
        return cv2.flip(frame, 1)

    def release(self) -> None:
        self._cap.release()


class LatestFrameReader:
    """يقرأ الكاميرا بخيط (Thread) بالخلفية ويحتفظ بأحدث صورة بس.

    ليش؟ قراءة الكاميرا تاخذ ~33ms والنموذج ~33ms. إذا ورا بعض = 15 fps.
    بالتوازي: النموذج يشتغل على صورة، والخيط يجيب الجاية بنفس الوقت = 30 fps.
    """

    def __init__(self, cam: Camera):
        self._cam = cam
        self._frame, self._error = None, None
        self._new = threading.Event()  # "جرس" يرن لما تجي صورة جديدة
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            try:
                f = self._cam.read()
            except CameraError as e:
                self._error = e
                self._new.set()
                return
            if f is not None:
                self._frame = f
                self._new.set()

    def read(self, timeout: float = 2.0) -> np.ndarray | None:
        """ينتظر صورة جديدة (ما يرجع نفس الصورة مرتين)."""
        if not self._new.wait(timeout):
            raise CameraError("LOST")
        self._new.clear()
        if self._error:
            raise self._error
        return self._frame

    def release(self) -> None:
        self._running = False
        self._thread.join(timeout=1)
        self._cam.release()


def frame_quality(frame: np.ndarray, dark_threshold: int = 40) -> str | None:
    """يرجع "DARK" إذا الصورة معتمة، وإلا None. نصغّر الصورة أول حتى يكون الحساب سريع."""
    small = cv2.resize(frame, (80, 60))
    return "DARK" if cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean() < dark_threshold else None
