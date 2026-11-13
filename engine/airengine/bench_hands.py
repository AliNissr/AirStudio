"""قياس: يد وحدة مقابل يدين، وكلفة التبديل بيناتهم.

التشغيل (من مجلد engine)، وخلي يدينك الثنتين قدام الكاميرا طول الوقت:
    ..\\.venv\\Scripts\\python -m airengine.bench_hands 10
"""
import sys
import time

from .camera import Camera, LatestFrameReader
from .perf import CpuMeter, set_below_normal_priority
from .tracker import HandTracker


def measure(cam, num_hands: int, seconds: float) -> dict:
    t_create = time.perf_counter()
    tracker = HandTracker(num_hands=num_hands)
    create_ms = (time.perf_counter() - t_create) * 1000  # هذا اللي يكلفه "التبديل"
    meter, model_ms, hands_seen = CpuMeter(), [], []
    start = time.perf_counter()
    while time.perf_counter() - start < seconds:
        frame = cam.read()
        a = time.perf_counter()
        hands = tracker.process(frame, int((a - start) * 1000))
        model_ms.append((time.perf_counter() - a) * 1000)
        hands_seen.append(len(hands))
    elapsed = time.perf_counter() - start
    tracker.close()
    n = len(model_ms)
    return {
        "num_hands": num_hands, "fps": n / elapsed, "model_ms": sum(model_ms) / n,
        "cpu": meter.percent(), "create_ms": create_ms,
        "frames_with_2": sum(h == 2 for h in hands_seen) / n, "frames_with_1": sum(h == 1 for h in hands_seen) / n,
    }


def main(seconds: float) -> None:
    set_below_normal_priority()
    cam = LatestFrameReader(Camera())
    try:
        rows = [measure(cam, n, seconds) for n in (1, 2, 1, 2)]  # مرتين حتى نتأكد إن النتيجة ثابتة
    finally:
        cam.release()
    print(f"{'hands':>5} {'fps':>6} {'model ms':>9} {'CPU %':>6} {'switch ms':>10} {'saw 1':>6} {'saw 2':>6}")
    for r in rows:
        print(f"{r['num_hands']:>5} {r['fps']:6.1f} {r['model_ms']:9.1f} {r['cpu']:6.1f} {r['create_ms']:10.0f}"
              f" {r['frames_with_1']:6.0%} {r['frames_with_2']:6.0%}")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 10)
