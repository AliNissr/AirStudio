import random
import statistics

from airengine.one_euro import OneEuroFilter

DT = 1 / 30  # إطار كل 33 ملي ثانية (30 fps)


def test_first_value_passthrough():
    # أول قيمة ماكو قبلها شي ننعّمه عليه، فترجع مثل ما هي
    assert OneEuroFilter().filter(42.0, 0.0) == 42.0


def test_reduces_jitter():
    # يد ثابتة على 100 بس الكاميرا ترجّف ±5
    random.seed(1)
    f = OneEuroFilter()
    raw = [100 + random.uniform(-5, 5) for _ in range(120)]
    out = [f.filter(x, i * DT) for i, x in enumerate(raw)]
    assert statistics.stdev(out[20:]) < statistics.stdev(raw[20:]) / 2


def test_follows_fast_motion():
    # حركة سريعة حقيقية: لازم المؤشر يلحك بدون تأخير كبير
    f = OneEuroFilter()
    for i in range(10):
        f.filter(0.0, i * DT)
    for i in range(10, 20):
        y = f.filter(100.0, i * DT)
    assert y > 90


def test_reset_forgets_history():
    f = OneEuroFilter()
    f.filter(0.0, 0.0)
    f.reset()
    assert f.filter(50.0, 1.0) == 50.0
