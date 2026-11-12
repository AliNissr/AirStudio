from airengine.perf import AdaptiveRate


def test_active_runs_at_30fps():
    r = AdaptiveRate()
    assert r.next_interval(True, cpu=5, now=0.0) == 1 / 30


def test_idle_drops_to_5fps():
    r = AdaptiveRate()
    r.next_interval(True, cpu=5, now=0.0)
    # اليد اختفت لحظة (أقل من ثانية): نبقى سريعين حتى ما نضيعها إذا رجعت
    assert r.next_interval(False, cpu=5, now=0.5) == 1 / 30
    # اختفت أكثر من ثانية: ننزل لـ 5 إطارات
    assert r.next_interval(False, cpu=5, now=1.6) == 1 / 5


def test_high_cpu_reduces_rate():
    r = AdaptiveRate(cpu_limit=25)
    assert r.next_interval(True, cpu=40, now=0.0) == 1 / 15


def test_hand_returns_restores_rate():
    r = AdaptiveRate()
    r.next_interval(False, cpu=5, now=0.0)
    r.next_interval(False, cpu=5, now=5.0)
    assert r.next_interval(True, cpu=5, now=5.1) == 1 / 30
