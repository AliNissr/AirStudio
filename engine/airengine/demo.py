"""العرض المباشر: يفتح الكاميرا ويرسم نقاط اليد والإيماءة والأداء.

التشغيل (من مجلد engine):
    ..\\.venv\\Scripts\\python -m airengine.demo            نافذة مباشرة، Q أو Esc للخروج
    ..\\.venv\\Scripts\\python -m airengine.demo --bench 60 قياس 60 ثانية بدون نافذة
    ..\\.venv\\Scripts\\python -m airengine.demo --hands 2  يتتبع يدين (أبطأ)
"""
import argparse
import sys
import time

import cv2

from . import load_config
from .camera import Camera, CameraError, LatestFrameReader, frame_quality
from .gestures import GestureClassifier
from .messages import AR
from .one_euro import OneEuroFilter
from .perf import AdaptiveRate, CpuMeter, set_below_normal_priority
from .tracker import HandTracker, hand_unclear, vision

BONES = [(c.start, c.end) for c in vision.HandLandmarksConnections.HAND_CONNECTIONS]
# OpenCV ما يكتب عربي، فبالنافذة نكتب إنجليزي والرسالة العربية تطلع بالطرفية
STATUS_EN = {"DARK": "Low light", "UNCLEAR": "Hand not clear"}
WINDOW = "AirStudio Engine"


def draw(frame, hands, gestures, tip, fps, cpu, status):
    for hand, g in zip(hands, gestures):
        pts = [(int(x), int(y)) for x, y, _ in hand.landmarks]
        for a, b in BONES:
            cv2.line(frame, pts[a], pts[b], (200, 200, 200), 2)
        for p in pts:
            cv2.circle(frame, p, 4, (0, 200, 255), -1)
        cv2.putText(frame, f"{hand.handedness}: {g.value}", (pts[0][0] - 40, pts[0][1] + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    if tip:  # طرف السبابة بعد التنعيم (هذا اللي راح يصير المؤشر)
        cv2.circle(frame, tip, 10, (255, 0, 255), 2)
    # مؤشر الكاميرا شغالة: نقطة حمرة واضحة دايماً
    cv2.circle(frame, (20, 20), 8, (0, 0, 255), -1)
    cv2.putText(frame, f"CAMERA ON  {fps:4.1f} fps  CPU {cpu:4.1f}%", (36, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    if status:
        cv2.putText(frame, STATUS_EN[status], (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)


def run(bench_seconds: float = 0, num_hands: int = 1) -> int:
    cfg = load_config()
    set_below_normal_priority()
    try:
        # يد وحدة أسرع بمرتين تقريباً (30 مقابل ~20 fps)، لأن يدين = يدوّر على الثانية كل إطار
        cam, tracker = LatestFrameReader(Camera()), HandTracker(num_hands=num_hands)
    except CameraError as e:
        print(AR[e.code])
        return 1

    classifiers = {}  # مصنّف لكل يد (يسار/يمين) لأن كل وحدة إلها ذاكرة
    fx, fy = OneEuroFilter(**cfg["one_euro"]), OneEuroFilter(**cfg["one_euro"])
    rate = AdaptiveRate(**{k: cfg["perf"][k] for k in ("active_fps", "idle_fps", "cpu_limit")})
    meter = CpuMeter()
    start = last_print = time.perf_counter()
    frames, hand_frames, fps, cpu, last_status, last_msg = 0, 0, 0.0, 0.0, None, 0.0
    stats = []  # (عدد الإطارات، cpu، هل في يد) كل ثانية، للقياس

    try:
        while True:
            t0 = time.perf_counter()
            frame = cam.read()
            if frame is None:
                continue
            hands = tracker.process(frame, int((t0 - start) * 1000))
            status = frame_quality(frame, cfg["quality"]["dark_threshold"])
            h, w = frame.shape[:2]
            if hands and hand_unclear(hands[0].landmarks, w, h, cfg["quality"]["min_hand_px"]):
                status = status or "UNCLEAR"
            # نطبع الرسالة مرة وحدة كل 5 ثواني بالأكثر، مو كل إطار
            if status and (status != last_status or t0 - last_msg > 5):
                print(AR[status])
                last_msg = t0
            last_status = status

            gestures = []
            for h in hands:
                c = classifiers.setdefault(h.handedness, GestureClassifier(cfg))
                gestures.append(c.update(h.landmarks))
            for side in set(classifiers) - {h.handedness for h in hands}:
                classifiers[side].reset()  # اليد طلعت: ننسى حالتها

            tip = None
            if hands:
                x, y, _ = hands[0].landmarks[8]
                tip = (int(fx.filter(x, t0)), int(fy.filter(y, t0)))
            else:
                fx.reset(), fy.reset()

            frames += 1
            hand_frames += bool(hands)
            if t0 - last_print >= 1.0:
                fps, cpu = frames / (t0 - last_print), meter.percent()
                stats.append((fps, cpu, hand_frames > frames / 2))  # "بيها يد" إذا أغلب الثانية بيها يد
                if bench_seconds:
                    print(f"  {fps:5.1f} fps  CPU {cpu:4.1f}%  hand frames {hand_frames}/{frames}")
                frames, hand_frames, last_print = 0, 0, t0

            wait = rate.next_interval(bool(hands), cpu, t0) - (time.perf_counter() - t0)
            if bench_seconds:
                if t0 - start > bench_seconds:
                    break
                time.sleep(max(wait, 0))
                continue
            draw(frame, hands, gestures, tip, fps, cpu, status)
            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(max(int(wait * 1000), 1)) & 0xFF
            if key in (ord("q"), 27) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    except CameraError as e:
        print(AR[e.code])
        return 1
    finally:
        cam.release()
        tracker.close()
        cv2.destroyAllWindows()

    if bench_seconds and stats:
        for label, rows in (("with hand", [s for s in stats if s[2]]), ("no hand", [s for s in stats if not s[2]])):
            if rows:
                print(f"{label}: {len(rows)}s  avg {sum(r[0] for r in rows)/len(rows):.1f} fps"
                      f"  avg CPU {sum(r[1] for r in rows)/len(rows):.1f}%")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", type=float, default=0, help="قياس لعدد ثواني بدون نافذة")
    ap.add_argument("--hands", type=int, default=1, choices=(1, 2), help="عدد الأيادي")
    args = ap.parse_args()
    sys.exit(run(args.bench, args.hands))
