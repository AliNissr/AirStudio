"""الإيماءات الزمنية على أيادي مرسومة هندسياً. التسجيلات الحقيقية من إيدك تنضاف بـ test_recordings.py."""
import random

from aircontrol.gestures_ctrl import ControlGestures, CTRL_DEFAULTS

W = H = 1  # الأيادي المرسومة بنفس المقياس بالمحورين
WRIST = (0.5, 0.8)
BASES = {"index": 0.44, "middle": 0.5, "ring": 0.56, "pinky": 0.62}
THUMB = {
    "far": [[0.42, 0.75, 0], [0.37, 0.7, 0], [0.33, 0.65, 0], [0.30, 0.60, 0]],
    "index": [[0.42, 0.75, 0], [0.40, 0.68, 0], [0.41, 0.61, 0], [0.425, 0.56, 0]],   # على جانب السبابة
    "middle": [[0.42, 0.75, 0], [0.43, 0.65, 0], [0.46, 0.52, 0], [0.485, 0.45, 0]],  # على الوسطى
    "tucked": [[0.43, 0.76, 0], [0.42, 0.7, 0], [0.45, 0.66, 0], [0.49, 0.65, 0]],
}
POSES = {
    "open": ("far", {"index", "middle", "ring", "pinky"}),
    "point": ("far", {"index", "middle"} - {"middle"}),
    "two": ("far", {"index", "middle"}),
    "three": ("far", {"index", "middle", "ring"}),
    "fist": ("tucked", set()),
}


def hand(pose="point", thumb=None, dx=0.0, dy=0.0):
    default_thumb, ext = POSES[pose]
    pts = [[*WRIST, 0]] + [p[:] for p in THUMB[thumb or default_thumb]]
    for name, x in BASES.items():
        ys = [0.6, 0.5, 0.44, 0.38] if name in ext else [0.6, 0.52, 0.58, 0.62]
        pts += [[x, y, 0] for y in ys]
    return [[x + dx, y + dy, z] for x, y, z in pts]


def play(seq, g=None, dt=1 / 30):
    """seq: قائمة (أيادي، عدد الإطارات). يرجع كل الأحداث وآخر حالة."""
    g = g or ControlGestures(CTRL_DEFAULTS)
    events, t, state = [], 0.0, None
    for hands, n in seq:
        for _ in range(n):
            ev, state = g.update(hands, t, W, H)
            events += ev
            t += dt
    return [e[0] for e in events], events, state


def names(seq):
    return play(seq)[0]


def test_quick_tap_is_a_click_and_locks_pointer():
    n, _, _ = play([([hand()], 5), ([hand(thumb="index")], 4), ([hand()], 5)])
    assert n == ["tap_index"]
    _, _, st = play([([hand()], 5), ([hand(thumb="index")], 3)])
    assert st["click_lock"] == 1.0


def test_two_quick_taps_make_a_double():
    assert names([([hand()], 5), ([hand(thumb="index")], 4), ([hand()], 4), ([hand(thumb="index")], 4), ([hand()], 5)]) == ["tap_index", "double_tap_index"]


def test_hold_starts_and_ends_drag_and_frees_pointer():
    n, ev, st = play([([hand()], 5), ([hand(thumb="index")], 15)])
    assert n == ["hold_index"] and ev[0][1]["phase"] == "start"
    assert st["click_lock"] == 0.0  # وقت السحب المؤشر لازم يتحرك
    n, ev, _ = play([([hand()], 5), ([hand(thumb="index")], 15), ([hand()], 5)])
    assert [e[1]["phase"] for e in ev] == ["start", "end"]


def test_hand_lost_during_drag_releases_the_button():
    _, ev, _ = play([([hand()], 5), ([hand(thumb="index")], 15), ([], 3)])
    assert [e[1]["phase"] for e in ev] == ["start", "end"]  # ما نخلي زر الماوس مضغوط أبداً


def test_medium_contact_is_ignored():
    assert names([([hand()], 5), ([hand(thumb="index")], 9), ([hand()], 5)]) == []  # 300 ms: لا نقرة ولا سحب


def test_middle_tap_and_hold():
    # الوسطى ممدودة وقت تنقر عليها بالإبهام (الرسم لازم يطابق اليد الحقيقية)
    assert names([([hand("two")], 5), ([hand("two", thumb="middle")], 4), ([hand("two")], 5)]) == ["tap_middle"]
    assert names([([hand("two")], 5), ([hand("two", thumb="middle")], 30), ([hand("two")], 5)]) == ["hold_middle"]


def test_thumb_resting_on_folded_middle_is_not_a_right_click():
    # وضع إشارة (الوسطى ملفوفة) والإبهام مرتاح فوكها: لا نقر يمين ولا قائمة
    assert names([([hand()], 5), ([hand(thumb="tucked")], 30), ([hand()], 5)]) == []


def test_open_palm_is_clutch_and_fast_sideways_palm_swipes_once():
    _, _, st = play([([hand("open")], 5)])
    assert st["clutch"] is True
    ev = names([([hand("open")], 3)] + [([hand("open", dx=0.08 * i)], 1) for i in range(1, 6)] + [([hand("open", dx=0.4)], 10)])
    assert ev == ["palm_swipe"]


def test_two_fingers_moving_up_scroll_up():
    _, ev, _ = play([([hand("two")], 3)] + [([hand("two", dy=-0.01 * i)], 1) for i in range(20)])
    assert ev and all(e[0] == "two_finger_move" and e[1]["dy"] > 0 for e in ev)


def test_two_fingers_still_do_not_scroll():
    assert names([([hand("two")], 30)]) == []


def test_three_fingers_vertical_zoom_and_horizontal_swipe():
    _, ev, _ = play([([hand("three")], 3)] + [([hand("three", dy=-0.01 * i)], 1) for i in range(20)])
    assert ev and all(e[0] == "three_finger_vertical" for e in ev)
    n = names([([hand("three")], 3)] + [([hand("three", dx=0.06 * i)], 1) for i in range(1, 8)])
    assert n.count("three_finger_swipe") == 1


def test_still_fist_for_one_second_is_emergency_stop_once():
    n, _, st = play([([hand("fist")], 40)])
    assert n == ["fist_hold"]
    _, _, st = play([([hand("fist")], 15)])
    assert 0.4 < st["fist_progress"] < 0.6
    # قبضة تتحرك ما توقف (يمكن تحرك إيدك بالصدفة وهي مسكّرة)
    assert names([([hand("fist", dx=0.01 * i)], 1) for i in range(40)]) == []


def test_fist_never_counts_as_a_tap():
    assert "tap_index" not in names([([hand()], 5), ([hand("fist")], 4), ([hand()], 5)])


def test_both_open_palms_for_two_seconds_activate_once():
    two = [hand("open"), hand("open", dx=0.3)]
    assert names([(two, 70)]) == ["both_palms"]
    assert names([(two, 40)]) == []


def test_jittery_idle_hand_produces_no_events():
    random.seed(7)
    seq = []
    for _ in range(300):  # 10 ثواني يد مؤشرة ترجف شوية
        j = lambda: random.uniform(-0.004, 0.004)  # noqa: E731
        seq.append(([hand(dx=j(), dy=j())], 1))
    assert names(seq) == []
