"""نرسم كل أجزاء الطبقة على صورة بالذاكرة (بدون شاشة)، حتى أي خطأ رسم يطلع بالاختبار مو بإيدك."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from aircontrol.bindings import DEFAULT_BINDINGS, DEFAULT_RADIAL  # noqa: E402
from aircontrol.controller import Controller  # noqa: E402
from aircontrol.radial import RadialMenu  # noqa: E402
from aircontrol.screens import Desktop, Monitor  # noqa: E402
from aircontrol.safety.state import OFF, ACTIVE, PAUSED  # noqa: E402
from aircontrol.ui.overlay import Overlay  # noqa: E402

PCFG = {"gain_min": 600, "gain_max": 3000, "speed_low": 0.05, "speed_high": 1.0, "precision": 1 / 3,
        "one_euro": {"min_cutoff": 1.0, "beta": 0.0, "d_cutoff": 1.0}, "region": [0.2, 0.2, 0.8, 0.8]}


@pytest.fixture(scope="module")
def overlay():
    app = QApplication.instance() or QApplication([])
    screen = app.primaryScreen()
    g = screen.geometry()
    mon = Monitor(g.x(), g.y(), g.x() + int(g.width() * screen.devicePixelRatio()), g.y() + int(g.height() * screen.devicePixelRatio()))
    ctrl = Controller(Desktop([mon]), dict(DEFAULT_BINDINGS), list(DEFAULT_RADIAL), PCFG)
    return Overlay(screen, mon, primary=True), ctrl, mon


@pytest.mark.parametrize("pose,lock,mode", [("point", 0.0, ACTIVE), ("point", 0.7, ACTIVE), ("fist", 0.0, OFF), ("open", 0.0, PAUSED)])
def test_every_part_paints_without_errors(overlay, pose, lock, mode):
    o, ctrl, mon = overlay
    cx, cy = mon.center
    ctrl.view = {"pos": (cx, cy), "mode": mode, "pose": pose, "click_lock": lock, "anchor": (0.5, 0.5),
                 "fist_progress": 0.5, "palms_progress": 0.3, "precision": True, "clutch": pose == "open"}
    ctrl.radial = RadialMenu(DEFAULT_RADIAL, (cx, cy))
    ctrl.open_keyboard()
    ctrl.keyboard.model.word = "he"  # حتى تبين اقتراحات
    o.ctrl, o.extra = ctrl, {"message": "رسالة تجربة"}
    img = QImage(o.width(), o.height(), QImage.Format_ARGB32)
    g = QPainter(img)
    o.badge(g, ctrl, ctrl.view)
    o.radial(g, ctrl)
    o.keyboard(g, ctrl)
    o.pointer(g, ctrl.view, mode)
    g.end()
