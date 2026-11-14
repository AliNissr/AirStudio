"""القائمة البيضاء: الأوامر الوحيدة اللي AirControl يكدر يسويها. أي شي برة هاي القائمة ينرفض.

كل أمر يمر على validate() قبل ما يوصل للإخراج، سواء جا من إيماءة أو ملف الإعدادات أو القائمة الدائرية.
"""
import math
import unicodedata
from dataclasses import dataclass, field


class Forbidden(Exception):
    """أمر مو مسموح. الرسالة تشرح ليش (للسجل)."""


@dataclass(frozen=True)
class Command:
    name: str
    args: dict = field(default_factory=dict)


# الأمر ← المفاتيح اللي يضغطها فعلاً (فاضي = أمر ماوس أو يتنفذ بطريقة ثانية)
ALLOWED = {
    "move": (), "click": (), "double_click": (), "right_click": (), "drag_start": (), "drag_end": (),
    "scroll": (), "zoom": ("ctrl",),  # zoom = Ctrl + عجلة الماوس
    "type_text": (),  # كل حرف يروح Unicode، مو مفاتيح
    "key": (),        # مفتاح وحد من TYPING_KEYS
    "copy": ("ctrl", "c"), "paste": ("ctrl", "v"), "undo": ("ctrl", "z"), "select_all": ("ctrl", "a"),
    "alt_tab": ("alt", "tab"), "show_desktop": ("win", "d"), "dictation": ("win", "h"),
    "media_play_pause": ("media_play_pause",), "volume_up": ("volume_up",), "volume_down": ("volume_down",),
    "volume_mute": ("volume_mute",),
    "close_window": (),  # برسالة WM_CLOSE للنافذة، مو Alt+F4
}
# مفاتيح الكتابة المسموحة. Delete مو بيها عن قصد (Backspace يكفي للكتابة، وحده محدود بـ state.py)
TYPING_KEYS = {"enter", "backspace", "tab", "esc", "left", "right", "up", "down", "home", "end", "pageup", "pagedown", "space"}
SENSITIVE = {"close_window"}  # تحتاج تأكيد ثانية وحدة

MAX_TEXT = 200


def combo_for(name: str) -> tuple:
    return ALLOWED[name]


def _num(v, limit):
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or abs(v) > limit:
        raise Forbidden(f"رقم غير صالح: {v!r}")


def validate(cmd: Command) -> Command:
    if cmd.name not in ALLOWED:
        raise Forbidden(f"أمر مو بالقائمة البيضاء: {cmd.name!r}")
    a = cmd.args
    if cmd.name == "move":
        _num(a.get("x"), 100_000)
        _num(a.get("y"), 100_000)
    elif cmd.name == "scroll":
        _num(a.get("dx", 0), 50)
        _num(a.get("dy", 0), 50)
    elif cmd.name == "zoom":
        _num(a.get("steps"), 10)
    elif cmd.name == "key":
        if a.get("name") not in TYPING_KEYS:
            raise Forbidden(f"مفتاح مو مسموح: {a.get('name')!r}")
    elif cmd.name == "type_text":
        text = a.get("text")
        if not isinstance(text, str) or not 0 < len(text) <= MAX_TEXT:
            raise Forbidden("النص فاضي أو أطول من 200 حرف")
        if any(unicodedata.category(ch) == "Cc" for ch in text):  # حروف تحكم مخفية (Esc، Ctrl+...)
            raise Forbidden("بالنص حروف تحكم مخفية")
    return cmd
