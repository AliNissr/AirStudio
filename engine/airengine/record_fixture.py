"""يسجّل نقاط يدك الحقيقية (21 نقطة بس، بدون أي صورة) كملف اختبار.

الاستخدام (من مجلد engine):
    ..\\.venv\\Scripts\\python -m airengine.record_fixture real_pinch PINCH
يعدّ 3 ثواني، سوّي الإيماءة قدام الكاميرا، ويحفظ engine/fixtures/real_pinch.json.
بعدها pytest يختبره تلقائياً ويه باقي الملفات.
"""
import json
import sys
import time

from . import ENGINE_DIR, load_config
from .camera import Camera, CameraError, LatestFrameReader
from .gestures import Gesture, GestureClassifier, pinch_ratio
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
        # نسجل ثانيتين ونحفظ آخر إطار بيه يد. أول إطار غلط: غالباً بعدك ما سويت الإيماءة
        print("سجّل! ثبّت الإيماءة...")
        start, last = time.perf_counter(), None
        while time.perf_counter() - start < 2:
            hands = tracker.process(cam.read(), int((time.perf_counter() - start) * 1000))
            if hands:
                last = hands[0].landmarks
        if last is None:
            print("ما شفت يد، جرب مرة ثانية.")
            return 1
        got = GestureClassifier(load_config()).classify(last)
        print(f"قياس القرص: {pinch_ratio(last):.2f} (القرص أقل من 0.25)، المصنّف شاف: {got.value}")
        if got.value != gesture:
            print(f"ما حفظت: طلبت {gesture} بس اليد كانت {got.value}. إذا متأكد إنك سويتها صح، "
                  "معناها العتبات تحتاج تعديل بـ gestures.json لإيدك.")
            return 1
        path = ENGINE_DIR / "fixtures" / f"{name}.json"
        path.write_text(json.dumps({"gesture": gesture, "source": "recorded", "landmarks": last}), encoding="utf-8")
        print(f"انحفظ: {path}")
        return 0
    finally:
        cam.release()
        tracker.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
