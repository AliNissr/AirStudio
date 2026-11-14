from aircontrol.radial import RadialMenu
from aircontrol.keyboard import KeyboardModel, Predictor
from aircontrol.actions import Command, validate

# ===== القائمة الدائرية =====


def test_radial_sectors_start_at_top_clockwise():
    m = RadialMenu(["a", "b", "c", "d"], center=(500, 500), radius=120, inner=40)
    assert m.hit(500, 400) == 0    # فوك
    assert m.hit(600, 500) == 1    # يمين
    assert m.hit(500, 600) == 2    # جوه
    assert m.hit(400, 500) == 3    # يسار


def test_radial_center_and_far_away_are_cancel():
    m = RadialMenu(["a", "b", "c"], center=(500, 500))
    assert m.hit(505, 505) is None   # بالنص = إلغاء
    assert m.hit(1500, 500) is None  # بعيد هواية = إلغاء

# ===== لوحة المفاتيح =====


def kb(lang="en"):
    k = KeyboardModel(width=1000, height=320, predictor=Predictor())
    k.lang = lang
    return k


def press_label(k, label):
    return k.press(k.key_by_label(label))


def test_hit_finds_the_key_under_the_pointer():
    k = kb()
    key = k.key_by_label("q")
    x, y, w, h = key.rect
    assert k.hit(x + w / 2, y + h / 2) == key  # == مو is: الأزرار تنبني من جديد كل مرة
    assert k.hit(-5, -5) is None


def test_letters_type_text_and_every_command_is_allowed():
    k = kb()
    cmds = press_label(k, "h") + press_label(k, "i") + press_label(k, "⌫") + press_label(k, "⏎")
    assert cmds == [Command("type_text", {"text": "h"}), Command("type_text", {"text": "i"}),
                    Command("key", {"name": "backspace"}), Command("key", {"name": "enter"})]
    for c in cmds:
        validate(c)


def test_arabic_layout_and_lam_alef_key():
    k = kb()
    press_label(k, "ع")  # تبديل اللغة
    assert k.lang == "ar"
    assert press_label(k, "ب") == [Command("type_text", {"text": "ب"})]
    assert press_label(k, "لا") == [Command("type_text", {"text": "لا"})]


def test_shift_and_symbols_for_code():
    k = kb()
    press_label(k, "⇧")
    assert press_label(k, "A") == [Command("type_text", {"text": "A"})]
    assert k.key_by_label("a")  # الـ Shift يرجع بعد حرف واحد
    press_label(k, "#+=")
    assert press_label(k, "{") == [Command("type_text", {"text": "{"})]


def test_suggestion_types_only_the_missing_part():
    k = kb()
    for ch in "hel":
        press_label(k, ch)
    assert "hello" in k.suggestions()
    cmds = k.pick("hello")
    assert cmds == [Command("type_text", {"text": "lo "})]  # بدون مسح: نكمل الناقص بس
    assert k.word == ""


def test_dictation_and_close():
    k = kb()
    assert press_label(k, "🎤") == [Command("dictation")]
    assert press_label(k, "✕") == [Command("_close_keyboard")]


def test_predictor_learns_locally():
    p = Predictor()
    for _ in range(3):
        p.learn("helicopter")
    assert p.suggest("hel")[0] == "helicopter"
    assert p.suggest("") == []


def test_predictor_ignores_junk_learning():
    p = Predictor()
    p.learn("x" * 60)
    p.learn("a1b2")
    assert all(len(w) < 40 for w in p.learned)
