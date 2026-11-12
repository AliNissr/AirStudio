"""يصنع أيادي "رسم هندسي" للاختبارات (مو صور حقيقية).

ترتيب نقاط MediaPipe الـ 21:
0 الرسغ | 1-4 الإبهام | 5-8 السبابة | 9-12 الوسطى | 13-16 البنصر | 17-20 الخنصر
بكل إصبع: قاعدة (MCP) ← مفصل وسطي (PIP) ← مفصل أخير (DIP) ← الطرف (TIP)
المحور y ينزل لتحت (مثل الصور)، فالأصابع الممدودة لفوك يعني y أصغر.

شغّله: python engine/fixtures/make_synthetic.py
"""
import json
from pathlib import Path

WRIST = (0.5, 0.8)
BASES_X = {"index": 0.44, "middle": 0.5, "ring": 0.56, "pinky": 0.62}


def finger(x: float, extended: bool) -> list:
    if extended:  # خط مستقيم لفوك
        ys = [0.6, 0.5, 0.44, 0.38]
        xs = [x] * 4
    else:  # ملفوف: يصعد للمفصل ويرجع للكف
        ys = [0.6, 0.52, 0.58, 0.62]
        xs = [x] * 4
    return [[a, b, 0.0] for a, b in zip(xs, ys)]


THUMB_OPEN = [[0.42, 0.75, 0], [0.37, 0.7, 0], [0.33, 0.65, 0], [0.30, 0.60, 0]]
# الإبهام مطوي فوك الأصابع الملفوفة (مثل القبضة)
THUMB_TUCKED = [[0.43, 0.76, 0], [0.42, 0.7, 0], [0.45, 0.66, 0], [0.49, 0.65, 0]]


def hand(thumb, ext: dict, overrides: dict | None = None) -> list:
    pts = [[*WRIST, 0.0]] + thumb
    for name in ("index", "middle", "ring", "pinky"):
        pts += finger(BASES_X[name], ext[name])
    for i, p in (overrides or {}).items():
        pts[i] = p
    return pts


ALL = dict(index=True, middle=True, ring=True, pinky=True)
NONE = dict(index=False, middle=False, ring=False, pinky=False)

FIXTURES = {
    "open_palm": ("OPEN_PALM", hand(THUMB_OPEN, ALL)),
    "fist": ("FIST", hand(THUMB_TUCKED, NONE)),
    "two_fingers": ("TWO_FINGERS", hand(THUMB_TUCKED, dict(NONE, index=True, middle=True))),
    # قرص: طرف الإبهام (4) لازك بطرف السبابة (8)، وباقي الأصابع ممدودة (شكل "OK")
    "pinch": ("PINCH", hand(THUMB_OPEN, ALL, {8: [0.42, 0.46, 0], 7: [0.43, 0.48, 0], 4: [0.40, 0.47, 0]})),
    # قرص الوسطى: الإبهام لازك بطرف الوسطى (12)
    "middle_pinch": ("MIDDLE_PINCH", hand(THUMB_OPEN, ALL, {12: [0.48, 0.46, 0], 11: [0.49, 0.48, 0], 4: [0.46, 0.47, 0]})),
    # إصبعين ممدودة بس مو السبابة+الوسطى (السبابة والخنصر) = ولا إيماءة
    "none": ("NONE", hand(THUMB_TUCKED, dict(NONE, index=True, pinky=True))),
}

if __name__ == "__main__":
    out = Path(__file__).parent
    for name, (gesture, pts) in FIXTURES.items():
        assert len(pts) == 21, name
        data = {"gesture": gesture, "source": "synthetic", "landmarks": pts}
        (out / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
        print("wrote", name)
