"""فحوصات على ويندوز الحقيقي (قراءة بس، ما ترسل أي إدخال)."""
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="ويندوز بس")


def test_monitors_found_with_names():
    from aircontrol.winapi import monitors, set_dpi_awareness
    set_dpi_awareness()
    ms = monitors()
    assert ms, "ما لكينا ولا شاشة"
    for m in ms:
        assert m.right > m.left and m.bottom > m.top and m.name.startswith("\\\\.\\DISPLAY")


def test_foreground_check_never_crashes():
    from aircontrol.winapi import foreground_elevated
    assert foreground_elevated() in (True, False, None)


def test_watcher_starts_registers_and_stops():
    from aircontrol.winapi import InputWatcher
    events = []
    w = InputWatcher(events.append).start()
    assert w.thread_id
    w.stop()
    assert not w._thread.is_alive()
