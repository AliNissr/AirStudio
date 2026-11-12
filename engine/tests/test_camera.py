import numpy as np
import pytest

from airengine.camera import Camera, CameraError, frame_quality
from airengine.messages import AR


class FakeCapture:
    """كاميرا وهمية: نقرر إحنا شنو ترجع، حتى نختبر بدون كاميرا حقيقية."""

    def __init__(self, opened=True, frames=()):
        self.opened, self.frames = opened, list(frames)

    def isOpened(self):
        return self.opened

    def set(self, *_):
        return True

    def read(self):
        return (True, self.frames.pop(0)) if self.frames else (False, None)

    def release(self):
        self.opened = False


def black(v=0):
    return np.full((480, 640, 3), v, np.uint8)


def test_camera_not_found_message():
    with pytest.raises(CameraError) as e:
        Camera(opener=lambda *_: FakeCapture(opened=False))
    assert e.value.code == "NOT_FOUND"
    assert "كاميرا" in AR["NOT_FOUND"]


def test_camera_busy_message():
    # تنفتح بس ما ترجع ولا صورة = برنامج ثاني ماسكها
    with pytest.raises(CameraError) as e:
        Camera(opener=lambda *_: FakeCapture(frames=[]))
    assert e.value.code == "BUSY"
    assert "برنامج" in AR["BUSY"]


def test_camera_lost_midway():
    cam = Camera(opener=lambda *_: FakeCapture(frames=[black(100)] * 2))
    assert cam.read() is not None
    with pytest.raises(CameraError) as e:
        for _ in range(Camera.MAX_FAILS + 1):
            cam.read()
    assert e.value.code == "LOST"


def test_read_mirrors_frame():
    f = black(100)
    f[:, 0] = 255  # العمود اليسار أبيض
    cam = Camera(opener=lambda *_: FakeCapture(frames=[f, f]))
    out = cam.read()
    assert out[0, -1, 0] == 255  # صار يمين (مثل المراية)


def test_dark_frame_detected():
    assert frame_quality(black(10)) == "DARK"
    assert frame_quality(black(120)) is None


def test_every_code_has_arabic_message():
    for code in ("NOT_FOUND", "BUSY", "LOST", "DARK", "UNCLEAR", "NO_MODEL"):
        assert AR[code]
