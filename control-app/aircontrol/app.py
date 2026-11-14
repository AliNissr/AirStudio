"""AirControl: نقطة البداية. يربط الكاميرا (خيط) ← المتحكم ← الطبقات فوق الشاشات + الـ tray + اختصارات ويندوز.

التشغيل (من مجلد المشروع):
    .venv\\Scripts\\python control-app\\run.py              Dry-run (الوحيد المتوفر بهاي المرحلة)
    .venv\\Scripts\\python control-app\\run.py --selftest 8  يشتغل 8 ثواني ويطبع أرقام ويطلع
"""
import argparse
import sys
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from airengine.camera import Camera, CameraError, LatestFrameReader
from airengine.messages import AR
from airengine.perf import AdaptiveRate, CpuMeter, set_below_normal_priority
from airengine.tracker import HandTracker

from . import settings as S
from .bindings import load_bindings
from .controller import Controller
from .keyboard import Predictor
from .safety.state import OFF, ACTIVE, PAUSED
from .screens import Desktop
from .ui.overlay import Overlay, MODE_AR
from .ui.sound import Sound
from .winapi import InputWatcher, foreground_elevated, monitors, set_dpi_awareness


class Bridge(QObject):
    """إشارات Qt: الطريقة الآمنة حتى الخيوط الثانية تكلّم الواجهة."""
    frame = Signal(list, float, int, int)
    hotkey = Signal(str)
    real = Signal()
    error = Signal(str)


class TrackerWorker(threading.Thread):
    """يقرا الكاميرا ويتتبع اليد بخيط منفصل حتى الواجهة ما تتجمد."""

    def __init__(self, bridge, want_hands):
        super().__init__(daemon=True)
        self.bridge, self.want_hands = bridge, want_hands  # want_hands: دالة ترجع 1 أو 2
        self.running, self.fps, self.frames = True, 0.0, 0

    def run(self):
        try:
            cam = LatestFrameReader(Camera())
        except CameraError as e:
            self.bridge.error.emit(e.code)
            return
        n = self.want_hands()
        tracker = HandTracker(num_hands=n)
        rate, start, count, window = AdaptiveRate(), time.perf_counter(), 0, time.perf_counter()
        last_hand = 0.0
        try:
            while self.running:
                t0 = time.perf_counter()
                if self.want_hands() != n:  # يدين وقت الانتظار، يد وحدة وقت التحكم (~33 ms للتبديل)
                    tracker.close()
                    n = self.want_hands()
                    tracker = HandTracker(num_hands=n)
                frame = cam.read()
                h, w = frame.shape[:2]
                hands = [hd.landmarks for hd in tracker.process(frame, int((t0 - start) * 1000))]
                if hands:
                    last_hand = t0
                self.bridge.frame.emit(hands, t0, w, h)
                self.frames += 1
                count += 1
                if t0 - window >= 1:
                    self.fps, count, window = count / (t0 - window), 0, t0
                time.sleep(max(0.0, rate.next_interval(t0 - last_hand < 1, 0, t0) - (time.perf_counter() - t0)))
        except CameraError as e:
            self.bridge.error.emit(e.code)
        finally:
            cam.release()
            tracker.close()


def tray_icon(color):
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#18212c"))
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.setPen(QColor(color))
    p.setBrush(QColor(color))
    p.drawEllipse(20, 20, 24, 24)
    p.end()
    return QIcon(pm)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", type=float, default=0, help="يشتغل ثواني ويطبع أرقام ويطلع")
    args = ap.parse_args(argv)

    set_dpi_awareness()
    set_below_normal_priority()
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)

    cfg = S.load()
    bindings, radial, cfg_error = load_bindings(S.CONFIG)
    desktop = Desktop(monitors())
    predictor = Predictor(S.load_words())
    ctrl = Controller(desktop, bindings, radial, {**S.POINTER, "region": cfg["region"]}, predictor=predictor)
    ctrl.pointer.mode = cfg["mode"]
    sound = Sound(cfg["sound"])
    if cfg_error:
        ctrl.message = "ملف الإعدادات بيه أمر مو مسموح أو غلط، فاستخدمنا الإعدادات الافتراضية"

    # طبقة لكل شاشة: نطابق شاشة Qt بشاشة ويندوز حسب مكانها (Qt يحط الزاوية بالبكسل الحقيقي)
    overlays = []
    for screen in app.screens():
        tl = screen.geometry().topLeft()
        mon = next((m for m in desktop.monitors if (m.left, m.top) == (tl.x(), tl.y())), None)
        if mon:
            overlays.append(Overlay(screen, mon, primary=screen == app.primaryScreen()))
    for o in overlays:
        o.show()

    bridge = Bridge()
    worker = TrackerWorker(bridge, lambda: ctrl.want_hands)
    watcher = InputWatcher(lambda name: bridge.real.emit() if name == "real_input" else bridge.hotkey.emit(name)).start()
    meter = CpuMeter()
    stats = {"cpu": 0.0, "elevated": False, "last_mode": OFF, "calib": None}

    # ===== tray =====
    tray = QSystemTrayIcon(tray_icon("#93a0b1"))
    menu = QMenu()
    status = menu.addAction("AirControl")
    status.setEnabled(False)
    menu.addSeparator()
    menu.addAction("تفعيل  (Ctrl+Alt+Shift+A)", lambda: bridge.hotkey.emit("activate"))
    menu.addAction("إيقاف  (Ctrl+Alt+Shift+Q)", lambda: bridge.hotkey.emit("stop"))
    menu.addSeparator()
    modes = QActionGroup(menu)
    for key, label in (("relative", "لوحة لمس بالهوا (نسبي)"), ("absolute", "مطلق (الكاميرا = كل الشاشات)")):
        a = QAction(label, menu, checkable=True, checked=cfg["mode"] == key)
        a.triggered.connect(lambda _=False, k=key: (setattr(ctrl.pointer, "mode", k), cfg.update(mode=k), S.save(cfg)))
        modes.addAction(a)
        menu.addAction(a)
    precision = menu.addAction("وضع الدقة  (Ctrl+Alt+Shift+P)", lambda: bridge.hotkey.emit("precision"))
    precision.setCheckable(True)
    sound_action = menu.addAction("الأصوات", lambda: (setattr(sound, "enabled", not sound.enabled),
                                                      cfg.update(sound=sound.enabled), S.save(cfg)))
    sound_action.setCheckable(True)
    sound_action.setChecked(sound.enabled)
    menu.addAction("معايرة الوضع المطلق (5 ثواني)", lambda: stats.update(calib={"until": time.perf_counter() + 5, "pts": []}))
    menu.addAction("سجل الأوامر", lambda: QMessageBox.information(None, "AirControl: سجل Dry-run", "\n".join(
        [ctrl.output.describe(c, p) for c, p in list(ctrl.output.log)[-25:]] or ["ماكو أوامر بعد"])
        + ("\n\nانرفض:\n" + "\n".join(list(ctrl.output.blocked)[-10:]) if ctrl.output.blocked else "")))
    menu.addSeparator()
    menu.addAction("خروج", app.quit)
    tray.setContextMenu(menu)
    tray.show()
    if cfg["first_run"]:
        tray.showMessage("AirControl (تجريبي)", "افتح كفينك قدام الكاميرا ثانيتين حتى تفعّل.\nقبضة ثابتة ثانية، أو Ctrl+Alt+Shift+Q، توقف كلشي.")
        S.save(cfg)
    if watcher.failed:
        ctrl.message = "اختصار محجوز من برنامج ثاني: " + "، ".join(watcher.failed)

    # ===== الإشارات =====
    def on_frame(hands, t, w, h):
        before = ctrl.safety.mode
        n_log, n_blocked = len(ctrl.output.log), len(ctrl.output.blocked)
        view = ctrl.step(hands, t, w, h)
        calib = stats["calib"]
        if calib and view.get("anchor"):
            calib["pts"].append(view["anchor"])
        if ctrl.safety.mode != before:
            sound.play({ACTIVE: "activate", OFF: "stop", PAUSED: "pause"}[ctrl.safety.mode])
        elif len(ctrl.output.log) > n_log:
            sound.play("tap")
        elif len(ctrl.output.blocked) > n_blocked and ctrl.safety.mode != OFF:
            sound.play("blocked")
        extra = {}
        if stats["elevated"] and ctrl.safety.mode == ACTIVE:
            extra["message"] = "النافذة الأمامية مرفوعة الصلاحية (كمسؤول): ويندوز يمنع التحكم بيها. استخدم الماوس"
        if calib:
            left = calib["until"] - time.perf_counter()
            extra["message"] = f"معايرة: حرّك إيدك لأبعد مكان مريح بكل الاتجاهات ({max(0, left):.0f})"
        for o in overlays:
            o.refresh(ctrl, extra)

    def on_hotkey(name):
        ctrl.on_hotkey(name, time.perf_counter())
        precision.setChecked(ctrl.pointer.precision)
        for o in overlays:
            o.update()

    def on_error(code):
        ctrl.message = AR.get(code, code)
        tray.showMessage("AirControl", AR.get(code, code), QSystemTrayIcon.Warning)
        for o in overlays:
            o.refresh(ctrl, {})

    bridge.frame.connect(on_frame)
    bridge.hotkey.connect(on_hotkey)
    bridge.real.connect(lambda: ctrl.on_real_input(time.perf_counter()))
    bridge.error.connect(on_error)

    def every_second():
        stats["cpu"] = meter.percent()
        stats["elevated"] = ctrl.safety.mode == ACTIVE and foreground_elevated() is True
        mode = ctrl.safety.mode
        tray.setIcon(tray_icon({OFF: "#93a0b1", ACTIVE: "#e8b341", PAUSED: "#ff9d4d"}[mode]))
        text = f"AirControl (تجريبي): {MODE_AR[mode]}  |  {worker.fps:.0f} fps  |  CPU {stats['cpu']:.1f}%"
        tray.setToolTip(text)
        status.setText(text)
        calib = stats["calib"]
        if calib and time.perf_counter() > calib["until"]:
            pts = calib["pts"]
            if len(pts) > 30:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                cfg["region"] = [min(xs), min(ys), max(xs), max(ys)]
                ctrl.pointer.cfg["region"] = cfg["region"]
                S.save(cfg)
                ctrl.message = "انحفظت المعايرة"
            else:
                ctrl.message = "المعايرة ما نجحت: ما شفنا اليد كفاية"
            stats["calib"] = None

    timer = QTimer()
    timer.timeout.connect(every_second)
    timer.start(1000)
    words_timer = QTimer()
    words_timer.timeout.connect(lambda: S.save_words(predictor.learned))
    words_timer.start(60_000)

    def cleanup():
        worker.running = False
        watcher.stop()
        S.save_words(predictor.learned)

    app.aboutToQuit.connect(cleanup)
    worker.start()

    if args.selftest:
        def report():
            print(f"monitors={len(desktop.monitors)} overlays={len(overlays)} hotkeys_failed={watcher.failed} "
                  f"frames={worker.frames} fps={worker.fps:.1f} cpu={stats['cpu']:.1f}% mode={ctrl.safety.mode} "
                  f"want_hands={ctrl.want_hands} log={len(ctrl.output.log)} message={ctrl.message!r}")
            app.quit()
        QTimer.singleShot(int(args.selftest * 1000), report)
    return app.exec()
