"""الشاشات والمؤشر: كلها شاشات وهمية، فالاختبار ما يحتاج شاشتك الحقيقية."""
import pytest

from aircontrol.screens import Desktop, Monitor
from aircontrol.pointer import PointerController

# لابتوب 1920x1080 + شاشة 2560x1440 على يمينه (الأعلى متساوي)
SIDE = Desktop([Monitor(0, 0, 1920, 1080), Monitor(1920, 0, 4480, 1440)])
# شاشة على اليسار بإحداثيات سالبة (شائع لما الشاشة الرئيسية هي اليمين)
LEFT = Desktop([Monitor(-2560, 0, 0, 1440), Monitor(0, 0, 1920, 1080)])

# ===== الشاشات =====


def test_bounds_cover_all_monitors():
    assert SIDE.bounds == (0, 0, 4480, 1440)
    assert LEFT.bounds == (-2560, 0, 1920, 1440)


def test_clamp_keeps_points_on_a_real_monitor():
    assert SIDE.clamp(500, 500) == (500, 500)
    # تحت اللابتوب = فراغ (اللابتوب أقصر): يرجع لأقرب نقطة على شاشة
    assert SIDE.clamp(1000, 1300) == (1000, 1079)
    assert SIDE.clamp(-50, 200) == (0, 200)
    assert SIDE.clamp(9999, 9999) == (4479, 1439)


def test_monitor_at_and_negative_coords():
    assert LEFT.monitor_at(-100, 10) == 0
    assert LEFT.monitor_at(100, 10) == 1


def test_next_monitor_center_by_position():
    # الترتيب حسب المكان على الشاشة (يسار ← يمين)، مو حسب ترتيب ويندوز
    assert SIDE.next_center(500, 500, +1) == (3200, 720)
    assert SIDE.next_center(3000, 500, +1) == (3200, 720)  # آخر شاشة: يبقى
    assert LEFT.next_center(100, 100, -1) == (-1280, 720)


def test_absolute_covers_virtual_desktop_edges():
    assert LEFT.to_absolute(-2560, 0) == (0, 0)
    assert LEFT.to_absolute(1919, 1439) == (65535, 65535)

# ===== المؤشر =====

CFG = {"gain_min": 600, "gain_max": 3000, "speed_low": 0.05, "speed_high": 1.0, "precision": 1 / 3,
       # min_cutoff كبير هواية = تنعيم شبه معدوم، حتى أرقام الاختبار تكون واضحة (التنعيم مختبر بالمحرك)
       "one_euro": {"min_cutoff": 1e6, "beta": 0.0, "d_cutoff": 1.0},
       "region": [0.2, 0.2, 0.8, 0.8]}


def run(pc, points, dt=1 / 30, t0=0.0, **kw):
    pos = None
    for i, p in enumerate(points):
        pos = pc.update(p, t0 + i * dt, **kw)
    return pos


def test_relative_small_slow_move_is_small():
    pc = PointerController(SIDE, CFG, start=(1000, 500))
    x, _ = run(pc, [(0.5 + i * 0.001, 0.5) for i in range(11)])  # 1% من الكاميرا ببطء
    assert 1000 < x < 1000 + 0.01 * 900  # قريب من التسارع الأدنى


def test_relative_fast_move_goes_further_per_unit():
    slow = PointerController(SIDE, CFG, start=(1000, 500))
    fast = PointerController(SIDE, CFG, start=(1000, 500))
    xs, _ = run(slow, [(0.5 + i * 0.002, 0.5) for i in range(11)])   # 2% ببطء
    xf, _ = run(fast, [(0.5 + i * 0.02, 0.5) for i in range(2)])     # 2% بسرعة
    assert (xf - 1000) > 2 * (xs - 1000)


def test_clutch_freezes_and_resumes_without_jump():
    pc = PointerController(SIDE, CFG, start=(1000, 500))
    run(pc, [(0.5, 0.5), (0.5, 0.5)])
    held = pc.update((0.9, 0.5), 0.1, clutch=True)     # رفعت إيدك وحرّكتها بعيد
    assert held == (1000, 500)
    back = pc.update((0.9, 0.5), 0.2)                  # رجعت لوضع الإشارة هناك
    assert back == (1000, 500)                         # ماكو قفزة


def test_click_lock_nearly_freezes_motion():
    free = PointerController(SIDE, CFG, start=(1000, 500))
    locked = PointerController(SIDE, CFG, start=(1000, 500))
    pts = [(0.5 + i * 0.01, 0.5) for i in range(5)]
    xf, _ = run(free, pts)
    xl, _ = run(locked, pts, click_lock=0.9)
    assert (xl - 1000) < 0.15 * (xf - 1000)


def test_precision_divides_by_three():
    norm = PointerController(SIDE, CFG, start=(1000, 500))
    prec = PointerController(SIDE, CFG, start=(1000, 500))
    prec.precision = True
    pts = [(0.5 + i * 0.01, 0.5) for i in range(5)]
    assert run(prec, pts)[0] - 1000 == pytest.approx((run(norm, pts)[0] - 1000) / 3, rel=0.05)


def test_relative_reaches_second_monitor_and_clamps():
    pc = PointerController(SIDE, CFG, start=(1800, 500))
    x, y = run(pc, [(0.2 + i * 0.1, 0.5) for i in range(7)])
    assert x > 1920 and pc.desktop.monitor_at(x, y) == 1
    x, y = run(pc, [(0.8 + i * 0.1, 0.5) for i in range(30)], t0=1.0)
    assert x == 4479


def test_absolute_maps_region_to_desktop():
    pc = PointerController(SIDE, CFG, mode="absolute")
    assert pc.update((0.2, 0.2), 0) == (0, 0)
    pc2 = PointerController(SIDE, CFG, mode="absolute")
    assert pc2.update((0.8, 0.8), 0) == (4479, 1439)


def test_jump_to_next_monitor():
    pc = PointerController(SIDE, CFG, start=(500, 500))
    pc.jump(+1)
    assert pc.pos == (3200, 720)
