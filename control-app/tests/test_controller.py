"""الطريق كامل: إيماءة ← أمان ← أمر ← سجل Dry-run. بدون كاميرا ولا نوافذ."""
from aircontrol.controller import Controller, DryRunOutput
from aircontrol.screens import Desktop, Monitor
from aircontrol.bindings import DEFAULT_BINDINGS, DEFAULT_RADIAL
from aircontrol.safety.state import OFF, ACTIVE, PAUSED

DESK = Desktop([Monitor(0, 0, 1920, 1080, "A"), Monitor(1920, 0, 4480, 1440, "B")])
PCFG = {"gain_min": 600, "gain_max": 3000, "speed_low": 0.05, "speed_high": 1.0, "precision": 1 / 3,
        "one_euro": {"min_cutoff": 1e6, "beta": 0.0, "d_cutoff": 1.0}, "region": [0.2, 0.2, 0.8, 0.8]}


class FakeGestures:
    """بدل كاشف الإيماءات: نحدد إحنا شنو "يشوف" بكل إطار."""

    def __init__(self):
        self.next = ([], {})

    def update(self, hands, t, w, h):
        ev, st = self.next
        self.next = ([], {})
        base = {"clutch": False, "click_lock": 0.0, "anchor": (0.5, 0.5), "pose": "point", "fist_progress": 0.0, "palms_progress": 0.0}
        return ev, {**base, **st}


def make():
    out = DryRunOutput()
    c = Controller(DESK, dict(DEFAULT_BINDINGS), list(DEFAULT_RADIAL), PCFG, gestures=FakeGestures(), output=out)
    return c, out


def step(c, t, *events, **state):
    c.gestures.next = (list(events), state)
    return c.step([[0]], t, 640, 480)


def names(out):
    return [cmd.name for cmd, _ in out.log]


def test_nothing_happens_while_off():
    c, out = make()
    step(c, 0, ("tap_index", {}))
    assert c.safety.mode == OFF and names(out) == []
    assert c.want_hands == 2  # وقت الانتظار نتتبع يدين (للتفعيل)


def test_activate_then_tap_clicks():
    c, out = make()
    step(c, 0, ("both_palms", {}))
    assert c.safety.mode == ACTIVE and c.want_hands == 1
    step(c, 0.1, ("tap_index", {}))
    assert names(out) == ["click"]
    assert out.log[-1][1] == c.pointer.pos


def test_fist_stops_everything():
    c, out = make()
    step(c, 0, ("both_palms", {}))
    step(c, 0.1, ("fist_hold", {}))
    step(c, 0.2, ("tap_index", {}))
    assert c.safety.mode == OFF and names(out) == []


def test_hotkeys_activate_stop_and_ignore_their_own_keypresses():
    c, out = make()
    c.on_hotkey("activate", 0)
    c.on_real_input(0.3)  # فكّة زر A من الاختصار نفسه: مو "لمس حقيقي"
    assert c.safety.mode == ACTIVE
    c.on_real_input(2.0)
    assert c.safety.mode == PAUSED
    c.on_hotkey("stop", 2.1)
    assert c.safety.mode == OFF


def test_real_input_blocks_commands():
    c, out = make()
    c.on_hotkey("activate", 0)
    c.on_real_input(2)
    step(c, 2.5, ("tap_index", {}))
    assert names(out) == []
    assert "blocked:paused" in out.blocked[-1]


def test_drag_maps_to_start_and_end():
    c, out = make()
    c.on_hotkey("activate", 0)
    step(c, 2, ("hold_index", {"phase": "start"}))
    step(c, 3, ("hold_index", {"phase": "end"}))
    assert names(out) == ["drag_start", "drag_end"]


def test_scroll_and_zoom_carry_amounts():
    c, out = make()
    c.on_hotkey("activate", 0)
    step(c, 2, ("two_finger_move", {"dx": 0, "dy": 1}), ("three_finger_vertical", {"steps": -1}))
    assert [(cmd.name, cmd.args) for cmd, _ in out.log] == [("scroll", {"dx": 0, "dy": 1}), ("zoom", {"steps": -1})]


def test_radial_menu_opens_and_selects_an_item():
    c, out = make()
    c.on_hotkey("activate", 0)
    step(c, 2, ("hold_middle", {"phase": "start"}))
    assert c.radial is not None
    cx, cy = c.radial.item_center(1)  # "copy" بالقائمة الافتراضية
    c.pointer.fpos = [cx, cy]
    step(c, 3, ("tap_index", {}), clutch=True)  # clutch حتى المؤشر ما يتحرك بالاختبار
    assert names(out) == ["copy"] and c.radial is None


def test_radial_tap_in_center_cancels():
    c, out = make()
    c.on_hotkey("activate", 0)
    step(c, 2, ("hold_middle", {"phase": "start"}))
    step(c, 3, ("tap_index", {}), clutch=True)
    assert names(out) == [] and c.radial is None


def test_keyboard_from_radial_then_typing():
    c, out = make()
    c.on_hotkey("activate", 0)
    c.open_keyboard()
    k = c.keyboard
    key = k.model.key_by_label("h")
    x, y, w, h = key.rect
    c.pointer.fpos = [k.origin[0] + x + w / 2, k.origin[1] + y + h / 2]
    step(c, 3, ("tap_index", {}), clutch=True)
    assert [(cmd.name, cmd.args) for cmd, _ in out.log] == [("type_text", {"text": "h"})]
    close = k.model.key_by_label("✕")
    x, y, w, h = close.rect
    c.pointer.fpos = [k.origin[0] + x + w / 2, k.origin[1] + y + h / 2]
    step(c, 4, ("tap_index", {}), clutch=True)
    assert c.keyboard is None


def test_close_window_needs_hold_to_confirm():
    c, out = make()
    c.on_hotkey("activate", 0)
    c.run_action("close_window", 2)
    assert names(out) == [] and c.confirm_until
    step(c, 3, ("hold_index", {"phase": "start"}))   # التأكيد = ثبّت الإبهام على السبابة
    assert names(out) == ["close_window"]
    assert "drag_start" not in names(out)              # التأكيد ما صار سحب


def test_close_window_unconfirmed_expires():
    c, out = make()
    c.on_hotkey("activate", 0)
    c.run_action("close_window", 2)
    step(c, 9, ("hold_index", {"phase": "start"}))
    assert names(out) == ["drag_start"]


def test_monitor_jump_by_hotkey_and_palm_swipe():
    c, out = make()
    c.on_hotkey("activate", 0)
    c.on_hotkey("monitor_right", 1)
    assert DESK.monitor_at(*c.pointer.pos) == 1
    step(c, 2, ("palm_swipe", {"dir": -1}), clutch=True)
    assert DESK.monitor_at(*c.pointer.pos) == 0


def test_precision_hotkey_toggles():
    c, _ = make()
    c.on_hotkey("precision", 0)
    assert c.pointer.precision is True
