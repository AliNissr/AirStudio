"""يسجّل حركة يدك عبر الزمن (نقاط + وقت فقط، بدون أي صورة) حتى نختبر الإيماءات الزمنية (نقر، سحب...).

الاستخدام (من مجلد engine):
    ..\\.venv\\Scripts\\python -m airengine.record_sequence click 3
    ..\\.venv\\Scripts\\python -m airengine.record_sequence activate 4 --hands 2
يعدّ 3، يسجّل الثواني المطلوبة، ويحفظ engine/fixtures/seq/click_01.json (والرقم يزيد كل مرة).
هذا المجلد بـ .gitignore: تسجيلاتك تبقى بجهازك وما تنرفع.
"""
import argparse
import json
import sys
import time

from . import ENGINE_DIR
from .camera import Camera, CameraError, LatestFrameReader
from .messages import AR
from .tracker import HandTracker

SEQ_DIR = ENGINE_DIR / "fixtures" / "seq"


def next_path(name: str):
    SEQ_DIR.mkdir(parents=True, exist_ok=True)
    n = 1
    while (SEQ_DIR / f"{name}_{n:02d}.json").exists():
        n += 1
    return SEQ_DIR / f"{name}_{n:02d}.json"


def main(name: str, seconds: float, hands: int) -> int:
    if not name.replace("_", "").isalnum():
        print("الاسم لازم حروف إنجليزية وأرقام بس، مثل click أو idle")
        return 2
    try:
        cam, tracker = LatestFrameReader(Camera()), HandTracker(num_hands=hands)
    except CameraError as e:
        print(AR[e.code])
        return 1
    frames = []
    try:
        for i in (3, 2, 1):
            print(f"{name}: نبدي بعد {i}...")
            time.sleep(1)
        print(f"سجّل! ({seconds:g} ثواني)")
        start = time.perf_counter()
        while (t := time.perf_counter() - start) < seconds:
            frame = cam.read()
            h, w = frame.shape[:2]
            found = tracker.process(frame, int(t * 1000))
            frames.append({"t": round(t, 4), "hands": [hd.landmarks for hd in found]})
    finally:
        cam.release()
        tracker.close()
    seen = sum(bool(f["hands"]) for f in frames)
    path = next_path(name)
    path.write_text(json.dumps({"gesture": name, "source": "recorded", "size": [w, h], "frames": frames}), encoding="utf-8")
    print(f"انحفظ: {path}  ({len(frames)} إطار، اليد ظهرت بـ {seen})")
    if seen < len(frames) * 0.8:
        print("تنبيه: اليد ما ظهرت بأغلب الإطارات. خليها كلها داخل الصورة وعيد التسجيل.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="اسم الإيماءة، مثل click أو double أو idle")
    ap.add_argument("seconds", type=float, nargs="?", default=3)
    ap.add_argument("--hands", type=int, default=1, choices=(1, 2))
    a = ap.parse_args()
    sys.exit(main(a.name, a.seconds, a.hands))
