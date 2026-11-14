"""ربط الإيماءات بالأوامر من ملف المستخدم. الملف قابل للتعديل باليد، فنعامله كبيانات غير موثوقة:
أي شي غلط = نرفض الملف كله ونستخدم الافتراضي. وإيماءتي التفعيل والإيقاف الطارئ ما تتغير أبداً.
"""
import json
from pathlib import Path

from .actions import ALLOWED

# الإيماءات اللي يكشفها gestures_ctrl.py ويكدر المستخدم يغيّر أمرها
GESTURES = {"tap_index", "double_tap_index", "tap_middle", "hold_index", "hold_middle",
            "two_finger_move", "three_finger_vertical", "three_finger_swipe"}
# ما تنربط: قبضة = إيقاف طارئ، كفين = تفعيل، كف = رفع الماوس
FIXED = {"fist_hold", "both_palms", "open_palm"}
# أوامر تحتاج أرقام من الإيماءة نفسها، فما تنحط مباشرة
NEEDS_ARGS = {"move", "type_text", "key", "drag_start", "drag_end", "scroll", "zoom", "alt_tab"}
BINDABLE = (set(ALLOWED) - NEEDS_ARGS) | {"drag", "scroll", "zoom", "alt_tab", "radial_menu", "none"}
RADIAL_ITEMS = (set(ALLOWED) - NEEDS_ARGS) | {"keyboard"}
# حركات مستمرة تطلع عشرات الأحداث بالحركة الوحدة: ما تنربط بأمر مفرد (يتكرر عشر مرات)
CONTINUOUS = {"two_finger_move": {"scroll", "zoom", "none"}, "three_finger_vertical": {"scroll", "zoom", "none"}}

DEFAULT_BINDINGS = {
    "tap_index": "click", "double_tap_index": "double_click", "tap_middle": "right_click",
    "hold_index": "drag", "hold_middle": "radial_menu", "two_finger_move": "scroll",
    "three_finger_vertical": "zoom", "three_finger_swipe": "alt_tab",
}
DEFAULT_RADIAL = ["media_play_pause", "copy", "paste", "undo", "select_all", "volume_up",
                  "volume_down", "volume_mute", "show_desktop", "keyboard", "dictation", "close_window"]
MAX_BYTES = 64_000


def load_bindings(path: Path):
    """يرجع (bindings, radial, error). error = None أو "BAD_CONFIG"."""
    defaults = (dict(DEFAULT_BINDINGS), list(DEFAULT_RADIAL))
    path = Path(path)
    if not path.exists():
        return (*defaults, None)
    try:
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("كبير هواية")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("مو كائن JSON")
        b = raw.get("bindings", {})
        if not isinstance(b, dict) or any(g not in GESTURES or a not in BINDABLE or a not in CONTINUOUS.get(g, BINDABLE)
                                          for g, a in b.items()):
            raise ValueError("ربط غير صالح")
        radial = raw.get("radial", DEFAULT_RADIAL)
        if not isinstance(radial, list) or not 0 < len(radial) <= 12 or any(r not in RADIAL_ITEMS for r in radial):
            raise ValueError("قائمة دائرية غير صالحة")
    except (ValueError, OSError, TypeError):
        return (*defaults, "BAD_CONFIG")
    return {**DEFAULT_BINDINGS, **b}, list(radial), None
