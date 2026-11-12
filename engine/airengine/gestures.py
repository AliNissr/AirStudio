"""مصنّف الإيماءات: ياخذ 21 نقطة لليد ويكول شنو الإيماءة.

نفس القواعد مكتوبة بـ JavaScript بـ engine/js/gestures.js، والاثنين يمرون على نفس ملفات fixtures.
لازم الإحداثيات x و y تكون بنفس المقياس (مثلاً بكسل)، مو x مقسومة على العرض و y على الطول.
"""
import math
from enum import Enum

WRIST, THUMB_TIP, MIDDLE_MCP = 0, 4, 9
# (المفصل الوسطي PIP، الطرف TIP) لكل إصبع عدا الإبهام
FINGERS = {"index": (6, 8), "middle": (10, 12), "ring": (14, 16), "pinky": (18, 20)}


class Gesture(Enum):
    NONE = "NONE"
    PINCH = "PINCH"                # إبهام + سبابة
    MIDDLE_PINCH = "MIDDLE_PINCH"  # إبهام + وسطى
    OPEN_PALM = "OPEN_PALM"        # كف مفتوحة
    FIST = "FIST"                  # قبضة
    TWO_FINGERS = "TWO_FINGERS"    # سبابة + وسطى ممدودة (للتمرير)


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def hand_size(pts) -> float:
    """طول الكف (الرسغ ← قاعدة الوسطى). نقسم عليه حتى ما يفرق قرب اليد أو بعدها."""
    return _dist(pts[WRIST], pts[MIDDLE_MCP]) or 1e-6


def pinch_ratio(pts, tip: int = 8) -> float:
    """مسافة طرف الإبهام عن طرف إصبع ÷ حجم اليد."""
    return _dist(pts[THUMB_TIP], pts[tip]) / hand_size(pts)


def is_extended(pts, finger: str, extend_ratio: float) -> bool:
    """الإصبع ممدود إذا طرفه أبعد عن الرسغ من مفصله الوسطي بنسبة extend_ratio."""
    pip, tip = FINGERS[finger]
    return _dist(pts[WRIST], pts[tip]) > extend_ratio * _dist(pts[WRIST], pts[pip])


class GestureClassifier:
    def __init__(self, config: dict):
        self.enter = config["pinch_enter"]
        self.exit = config["pinch_exit"]
        self.debounce = config["debounce_frames"]
        self.extend_ratio = config["extend_ratio"]
        self.curl_ratio = config["curl_ratio"]
        self.reset()

    def reset(self) -> None:
        """نمسح الذاكرة (لما اليد تختفي)."""
        self._pinch = {8: False, 12: False}  # هل القرص "مسكّر" حالياً
        self._stable = Gesture.NONE  # الإيماءة المثبّتة
        self._candidate = Gesture.NONE  # الإيماءة اللي نشوفها هسه
        self._count = 0

    def _pinched(self, pts, tip: int) -> bool:
        # Hysteresis: نسكّر تحت 0.25، بس ما نفتح إلا فوك 0.35، حتى ما يرمش على الحد
        r = pinch_ratio(pts, tip)
        # إصبع ملفوف داخل الكف مو قرص، حتى لو الإبهام لازك بيه بالصدفة
        finger = "index" if tip == 8 else "middle"
        curled = not is_extended(pts, finger, self.curl_ratio)
        self._pinch[tip] = not curled and r < (self.exit if self._pinch[tip] else self.enter)
        return self._pinch[tip]

    def classify(self, pts) -> Gesture:
        """الإيماءة بهذا الإطار بس، بدون debounce."""
        ext = {f: is_extended(pts, f, self.extend_ratio) for f in FINGERS}
        pinch, mpinch = self._pinched(pts, 8), self._pinched(pts, 12)
        if not any(ext.values()):
            return Gesture.FIST  # قبل القرص: بالقبضة الإبهام قريب من السبابة بالصدفة
        if pinch:
            return Gesture.PINCH
        if mpinch:
            return Gesture.MIDDLE_PINCH
        if all(ext.values()):
            return Gesture.OPEN_PALM
        if ext["index"] and ext["middle"] and not ext["ring"] and not ext["pinky"]:
            return Gesture.TWO_FINGERS
        return Gesture.NONE

    def update(self, pts) -> Gesture:
        """ندخل إطار جديد. الإيماءة تتغير بس إذا تكررت debounce_frames إطارات ورا بعض."""
        if len(pts) != 21:
            raise ValueError(f"لازم 21 نقطة، وصلت {len(pts)}")
        g = self.classify(pts)
        if g == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = g, 1
        if self._count >= self.debounce:
            self._stable = g
        return self._stable
