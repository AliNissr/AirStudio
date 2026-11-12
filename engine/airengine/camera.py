"""التقاط الصور من الكاميرا، مع أخطاء واضحة. الصور تبقى بالذاكرة بس، ما تنحفظ أبداً."""
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


def frame_quality(frame: np.ndarray, dark_threshold: int = 40) -> str | None:
    """يرجع "DARK" إذا الصورة معتمة، وإلا None. نصغّر الصورة أول حتى يكون الحساب سريع."""
    small = cv2.resize(frame, (80, 60))
    return "DARK" if cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean() < dark_threshold else None
