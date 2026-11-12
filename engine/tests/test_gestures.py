import json
from pathlib import Path

import pytest

from airengine import load_config
from airengine.gestures import Gesture, GestureClassifier, pinch_ratio

FIXTURES = sorted((Path(__file__).parents[1] / "fixtures").glob("*.json"))


def load(name: str) -> list:
    return json.loads((FIXTURES[0].parent / f"{name}.json").read_text(encoding="utf-8"))["landmarks"]


def classifier(**override) -> GestureClassifier:
    return GestureClassifier({**load_config(), **override})


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_gesture(path):
    # كل ملف fixture يكول شنو الإيماءة الصحيحة، والمصنّف لازم يطابقه
    data = json.loads(path.read_text(encoding="utf-8"))
    c = classifier()
    for _ in range(3):  # نكرر الإطار حتى يعبر الـ debounce
        g = c.update(data["landmarks"])
    assert g == Gesture[data["gesture"]]


def test_pinch_ratio_is_scale_free():
    # يد قريبة من الكاميرا (أكبر ×3) لازم تعطي نفس النسبة
    pts = load("pinch")
    big = [[x * 3, y * 3, z] for x, y, z in pts]
    assert pinch_ratio(pts) == pytest.approx(pinch_ratio(big))


def _with_ratio(ratio: float) -> list:
    """قرص بنسبة محددة: نحرّك طرف الإبهام بعيد عن طرف السبابة."""
    pts = [p[:] for p in load("pinch")]
    size = 0.2  # الرسغ ← قاعدة الوسطى بالـ fixture
    tip = pts[8]
    pts[4] = [tip[0] - ratio * size, tip[1], 0.0]
    return pts


def test_pinch_hysteresis_no_flicker():
    # النسبة ترجف حول 0.27 (بين الدخول 0.25 والخروج 0.35): لازم يبقى قرص وما يرمش
    c = classifier(debounce_frames=1)
    seq = [c.update(_with_ratio(r)) for r in (0.20, 0.30, 0.24, 0.30, 0.33)]
    assert seq == [Gesture.PINCH] * 5
    assert c.update(_with_ratio(0.40)) != Gesture.PINCH


def test_pinch_needs_enter_threshold():
    # 0.30 أكبر من عتبة الدخول، فمن البداية ما يعتبره قرص
    c = classifier(debounce_frames=1)
    assert c.update(_with_ratio(0.30)) != Gesture.PINCH


def test_debounce_requires_3_frames():
    c = classifier()
    palm, fist = load("open_palm"), load("fist")
    for _ in range(3):
        c.update(palm)
    assert c.update(fist) == Gesture.OPEN_PALM  # إطار واحد ما يكفي
    assert c.update(fist) == Gesture.OPEN_PALM
    assert c.update(fist) == Gesture.FIST  # الثالث يثبّتها


def test_reset_clears_state():
    c = classifier(debounce_frames=1)
    c.update(load("pinch"))
    c.reset()
    assert c.update(_with_ratio(0.30)) != Gesture.PINCH


def test_wrong_point_count_rejected():
    with pytest.raises(ValueError):
        classifier().update([[0, 0, 0]] * 5)
