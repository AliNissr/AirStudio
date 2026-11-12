import numpy as np
import pytest

from airengine.camera import CameraError
from airengine.tracker import HandTracker


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
