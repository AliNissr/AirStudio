import numpy as np
import pytest

from airengine.camera import CameraError
from airengine.tracker import HandTracker, hand_unclear


def _box(x0, y0, x1, y1):
    return [[x0, y0, 0], [x1, y1, 0]] + [[(x0 + x1) / 2, (y0 + y1) / 2, 0]] * 19


def test_hand_unclear_rules():
    assert not hand_unclear(_box(200, 150, 350, 350), 640, 480)  # يد بالنص وبحجم زين
    assert hand_unclear(_box(0, 150, 150, 350), 640, 480)        # مكصوصة يسار
    assert hand_unclear(_box(300, 200, 320, 225), 640, 480)      # صغيرة (بعيدة هواية)


def test_missing_model_gives_clear_error(tmp_path):
    with pytest.raises(CameraError) as e:
        HandTracker(tmp_path / "missing.task")
    assert e.value.code == "NO_MODEL"


def test_empty_frame_has_no_hands():
    t = HandTracker()
    try:
        frame = np.full((480, 640, 3), 128, np.uint8)
        assert t.process(frame, 0) == []
        assert t.process(frame, 0) == []  # نفس الوقت مرتين ما يخرّب
    finally:
        t.close()
