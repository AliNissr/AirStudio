"""يسجّل نقاط يدك الحقيقية (21 نقطة بس، بدون أي صورة) كملف اختبار.

الاستخدام (من مجلد engine):
    ..\\.venv\\Scripts\\python -m airengine.record_fixture real_pinch PINCH
يعدّ 3 ثواني، سوّي الإيماءة قدام الكاميرا، ويحفظ engine/fixtures/real_pinch.json.
بعدها pytest يختبره تلقائياً ويه باقي الملفات.
"""
import json
import sys
import time

from . import ENGINE_DIR
from .camera import Camera, CameraError, LatestFrameReader
from .gestures import Gesture
from .messages import AR
from .tracker import HandTracker


def main(name: str, gesture: str) -> int:
    Gesture[gesture]  # يتأكد إن اسم الإيماءة صحيح قبل ما نبدي (KeyError إذا غلط)
    try:
        cam, tracker = LatestFrameReader(Camera()), HandTracker(num_hands=1)
    except CameraError as e:
        print(AR[e.code])
        return 1
    try:
        for i in (3, 2, 1):
            print(f"سوّي إيماءة {gesture}... {i}")
            time.sleep(1)
        start = time.perf_counter()
        while time.perf_counter() - start < 3:
            hands = tracker.process(cam.read(), int((time.perf_counter() - start) * 1000))
            if hands:
                data = {"gesture": gesture, "source": "recorded", "landmarks": hands[0].landmarks}
                path = ENGINE_DIR / "fixtures" / f"{name}.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                print(f"انحفظ: {path}")
                return 0
        print("ما شفت يد خلال 3 ثواني، جرب مرة ثانية.")
        return 1
    finally:
        cam.release()
        tracker.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
