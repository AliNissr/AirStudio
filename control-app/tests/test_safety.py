"""اختبارات الأمان: القائمة البيضاء، ملف الإعدادات، وحالة التحكم. هذي أهم اختبارات بالمشروع."""
import json

import pytest

from aircontrol.actions import Command, Forbidden, validate, combo_for, SENSITIVE
from aircontrol.bindings import load_bindings, DEFAULT_BINDINGS, DEFAULT_RADIAL
from aircontrol.safety.state import SafetyState, OFF, ACTIVE, PAUSED

# ===== القائمة البيضاء =====


@pytest.mark.parametrize("name", ["click", "double_click", "right_click", "drag_start", "drag_end", "copy", "paste",
                                  "undo", "select_all", "media_play_pause", "volume_up", "show_desktop", "dictation"])
def test_allowed_actions_pass(name):
    assert validate(Command(name)) == Command(name)


@pytest.mark.parametrize("name", ["alt_f4", "run", "delete", "shutdown", "lock", "task_manager", "cut", "powershell", "", "CLICK"])
def test_unknown_or_dangerous_action_names_rejected(name):
    with pytest.raises(Forbidden):
        validate(Command(name))


@pytest.mark.parametrize("key", ["delete", "f4", "r", "x", "l", "escape_all", "win", "ctrl+alt+delete", "shift+delete", "f12"])
def test_forbidden_keys_rejected(key):
    with pytest.raises(Forbidden):
        validate(Command("key", {"name": key}))


@pytest.mark.parametrize("key", ["enter", "backspace", "tab", "esc", "left", "right", "up", "down", "home", "end", "pageup", "pagedown", "space"])
def test_typing_keys_allowed(key):
    validate(Command("key", {"name": key}))


def test_no_allowed_action_maps_to_a_forbidden_combo():
    # فحص شامل: كل أمر مسموح، شنو المفاتيح اللي راح يضغطها فعلاً؟ ولا واحد منها خطر
    danger = [{"alt", "f4"}, {"win", "r"}, {"win", "x"}, {"win", "l"}, {"ctrl", "shift", "esc"}, {"delete"}, {"ctrl", "x"}, {"ctrl", "alt", "delete"}]
    from aircontrol.actions import ALLOWED
    for name in ALLOWED:
        keys = set(combo_for(name))
        assert not any(d <= keys for d in danger), (name, keys)


def test_type_text_limits():
    validate(Command("type_text", {"text": "مرحبا hello {}"}))
    with pytest.raises(Forbidden):
        validate(Command("type_text", {"text": "x" * 201}))
    with pytest.raises(Forbidden):  # حروف تحكم مخفية (مثل Ctrl+...) ممنوعة
        validate(Command("type_text", {"text": "abc\x1b[2J"}))


def test_scroll_and_zoom_bounded():
    validate(Command("scroll", {"dx": 0, "dy": -3}))
    with pytest.raises(Forbidden):
        validate(Command("scroll", {"dx": 0, "dy": 10_000}))
    with pytest.raises(Forbidden):
        validate(Command("move", {"x": "1", "y": 2}))


def test_close_window_is_sensitive():
    assert "close_window" in SENSITIVE

# ===== ملف الإعدادات (غير موثوق) =====


def write(tmp_path, data):
    p = tmp_path / "aircontrol.json"
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return p


def test_missing_file_gives_defaults(tmp_path):
    b, radial, err = load_bindings(tmp_path / "nope.json")
    assert (b, radial, err) == (DEFAULT_BINDINGS, DEFAULT_RADIAL, None)


def test_custom_binding_accepted(tmp_path):
    b, _, err = load_bindings(write(tmp_path, {"bindings": {"tap_middle": "copy"}}))
    assert err is None and b["tap_middle"] == "copy" and b["tap_index"] == "click"


@pytest.mark.parametrize("bad", [
    {"bindings": {"tap_index": "alt_f4"}},                 # أمر ممنوع
    {"bindings": {"tap_index": "key:delete"}},             # محاولة تمرير مفتاح
    {"bindings": {"fist_hold": "click"}},                  # الإيقاف الطارئ ما يتغير
    {"bindings": {"both_palms": "click"}},                 # التفعيل ما يتغير
    {"bindings": {"unknown_gesture": "click"}},
    {"bindings": {"two_finger_move": "volume_up"}},        # حركة مستمرة لأمر مفرد = يتكرر 10 مرات
    {"bindings": {"three_finger_vertical": "paste"}},
    {"radial": ["copy", "shutdown"]},
    {"radial": ["copy"] * 13},
    "{not json",
    [1, 2],
])
def test_bad_config_rejected_whole_and_defaults_used(tmp_path, bad):
    b, radial, err = load_bindings(write(tmp_path, bad))
    assert err == "BAD_CONFIG"
    assert b == DEFAULT_BINDINGS and radial == DEFAULT_RADIAL


def test_huge_config_rejected(tmp_path):
    assert load_bindings(write(tmp_path, " " * 70_000))[2] == "BAD_CONFIG"

# ===== حالة التحكم =====


def test_starts_off_and_blocks_everything():
    s = SafetyState()
    assert s.mode == OFF
    assert s.gate(Command("click"), 0) == "blocked:off"


def test_activate_then_allowed():
    s = SafetyState()
    s.activate(0)
    assert s.mode == ACTIVE
    assert s.gate(Command("click"), 0.1) == "ok"


def test_emergency_stop_from_any_state():
    for prep in (lambda s: None, lambda s: s.activate(0), lambda s: (s.activate(0), s.real_input(0.5))):
        s = SafetyState()
        prep(s)
        s.emergency_stop()
        assert s.mode == OFF
        assert s.gate(Command("click"), 1) == "blocked:off"


def test_real_input_pauses_for_3_seconds():
    s = SafetyState()
    s.activate(0)
    s.real_input(1.0)
    assert s.mode == PAUSED
    assert s.gate(Command("click"), 2.0) == "blocked:paused"
    s.real_input(3.5)  # لمسة ثانية تمدد التوقف
    s.tick(6.0)
    assert s.mode == PAUSED
    s.tick(6.6)
    assert s.mode == ACTIVE


def test_real_input_while_off_stays_off():
    s = SafetyState()
    s.real_input(1)
    s.tick(10)
    assert s.mode == OFF


def test_forbidden_command_blocked_even_when_active():
    s = SafetyState()
    s.activate(0)
    assert s.gate(Command("key", {"name": "delete"}), 1).startswith("blocked:forbidden")


def test_sensitive_needs_confirmation_within_5_seconds():
    s = SafetyState()
    s.activate(0)
    close = Command("close_window")
    assert s.gate(close, 1) == "needs_confirm"
    assert s.confirm(1.5) == close              # أكّد بالوقت
    assert s.gate(close, 2) == "needs_confirm"
    assert s.confirm(8) is None                 # تأخر: انلغى
    assert s.gate(close, 9) == "needs_confirm"
    s.emergency_stop()
    assert s.confirm(9.1) is None               # الإيقاف يلغي أي تأكيد معلّق


def test_backspace_flood_limited():
    s = SafetyState()
    s.activate(0)
    bs = Command("key", {"name": "backspace"})
    assert all(s.gate(bs, i * 0.01) == "ok" for i in range(20))
    assert s.gate(bs, 1) == "blocked:backspace_limit"
    s.gate(Command("type_text", {"text": "a"}), 1.1)  # كتابة ترجّع العداد
    assert s.gate(bs, 1.2) == "ok"
