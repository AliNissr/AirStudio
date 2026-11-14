"""لوحة المفاتيح فوق الشاشة: الأزرار، اللغتين، الرموز، وتنبؤ الكلمات. نقي.
كل ضغطة ترجع أوامر (type_text / key / dictation) تمر على القائمة البيضاء مثل أي أمر ثاني.
"""
from dataclasses import dataclass

from .actions import Command

LAYOUTS = {
    "en": ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"],
    "ar": ["1234567890", "ضصثقفغعهخحجد", "شسيبلاتنمكط", ["ئ", "ء", "ؤ", "ر", "لا", "ى", "ة", "و", "ز", "ظ"]],
    "sym": ["{}()[]<>", ";:=\"'/\\|", "&_-+*#$%", "!?,.@~^`"],
}
# الصف الأخير ثابت: (العنوان، العرض النسبي)
BOTTOM = [("⇧", 1), ("#+=", 1.2), ("ع", 1), (" ", 4), ("⌫", 1.3), ("⏎", 1.3), ("⇥", 1), ("🎤", 1), ("✕", 1)]
SPECIAL = {"⌫": ("key", "backspace"), "⏎": ("key", "enter"), "⇥": ("key", "tab")}

# بذرة صغيرة كتبناها إحنا (بدون ملفات خارجية). اللوحة تتعلم كلماتك محلياً وتقدّمها
SEED = {
    "en": "the and you that was for are with this have from your not but can all will one about what there when "
          "which their would make like time just know people into year good some could them see other than then "
          "now look only come its over think also back after use two how our work first well way even new want "
          "because any these give day most hello thanks please function return import const class print string "
          "true false null none self value list",
    "ar": "في من على إلى أن هذا التي الذي ما لا هل كان عن مع هو هي كل بعد قبل حتى إذا لكن أو ثم عند "
          "شكرا مرحبا السلام عليكم صباح الخير مساء اليوم غدا أمس شنو شلون وين ليش هسه زين هواية ماكو اكو "
          "يعني بس لازم أريد أكدر تكدر الملف الصورة البرنامج الموقع الكود",
}


class Predictor:
    def __init__(self, learned=None):
        self.seed = {w: len(ws) - i for lang in SEED for ws in [SEED[lang].split()] for i, w in enumerate(ws)}
        self.learned = {}
        for w, n in (learned or {}).items():  # المحفوظ من قبل: نفحصه مثل أي إدخال
            if self._ok(w) and isinstance(n, int) and 0 < n < 10**6:
                self.learned[w] = n

    @staticmethod
    def _ok(word):
        return isinstance(word, str) and 2 <= len(word) <= 30 and word.isalpha()

    def learn(self, word):
        if self._ok(word):
            self.learned[word] = self.learned.get(word, 0) + 1

    def suggest(self, prefix, n=3):
        if not prefix:
            return []
        p = prefix.lower()
        words = {w for w in (*self.seed, *self.learned) if w.lower().startswith(p) and len(w) > len(prefix)}
        # كلماتك أهم من البذرة: كل استخدام = 1000 نقطة
        return sorted(words, key=lambda w: (-(self.learned.get(w, 0) * 1000 + self.seed.get(w, 0)), w))[:n]


@dataclass
class Key:
    label: str
    rect: tuple  # (x, y, w, h) داخل اللوحة


class KeyboardModel:
    def __init__(self, width, height, predictor):
        self.width, self.height, self.predictor = width, height, predictor
        self.lang, self.symbols, self.shift = "en", False, False
        self.word = ""  # الكلمة اللي دتكتبها هسه (للتنبؤ)

    @property
    def keys(self):
        rows = LAYOUTS["sym" if self.symbols else self.lang]
        n = len(rows) + 2  # + صف الاقتراحات + الصف الأخير
        rh = self.height / n
        out = []
        for r, row in enumerate(rows):
            labels = [c.upper() if self.shift and self.lang == "en" else c for c in row]
            kw = self.width / len(labels)
            out += [Key(lab, (i * kw, (r + 1) * rh, kw, rh)) for i, lab in enumerate(labels)]
        total, x = sum(w for _, w in BOTTOM), 0.0
        for lab, w in BOTTOM:
            if lab == "ع" and self.lang == "ar":
                lab = "EN"
            kw = self.width * w / total
            out.append(Key(lab, (x, (n - 1) * rh, kw, rh)))
            x += kw
        return out

    def suggestion_rects(self):
        rh = self.height / (len(LAYOUTS["en"]) + 2)
        s = self.suggestions()
        return [(w, (i * self.width / 3, 0, self.width / 3, rh)) for i, w in enumerate(s)]

    def key_by_label(self, label):
        return next(k for k in self.keys if k.label == label)

    def hit(self, x, y):
        """الزر تحت النقطة (إحداثيات داخل اللوحة)، أو اقتراح كنص، أو None."""
        for w, (rx, ry, rw, rh) in self.suggestion_rects():
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return w
        return next((k for k in self.keys if k.rect[0] <= x < k.rect[0] + k.rect[2] and k.rect[1] <= y < k.rect[1] + k.rect[3]), None)

    def suggestions(self):
        return self.predictor.suggest(self.word)

    def pick(self, word):
        """اخترت اقتراح: نكتب الناقص بس + مسافة (بدون مسح الحروف اللي كتبتها)."""
        rest = word[len(self.word):] if word.lower().startswith(self.word.lower()) else word
        self.predictor.learn(word)
        self.word = ""
        return [Command("type_text", {"text": rest + " "})]

    def press(self, key):
        lab = key.label
        if lab == "⇧":
            self.shift = not self.shift
            return []
        if lab == "#+=":
            self.symbols = not self.symbols
            return []
        if lab in ("ع", "EN"):
            self.lang = "ar" if self.lang == "en" else "en"
            self.symbols = False
            return []
        if lab == "🎤":
            return [Command("dictation")]
        if lab == "✕":
            return [Command("_close_keyboard")]  # داخلي: يسكّر اللوحة، ما يوصل لويندوز
        if lab in SPECIAL:
            kind, name = SPECIAL[lab]
            if name == "backspace":
                self.word = self.word[:-1]
            else:
                self.predictor.learn(self.word)
                self.word = ""
            return [Command(kind, {"name": name})]
        if lab == " ":
            self.predictor.learn(self.word)
            self.word = ""
            return [Command("type_text", {"text": " "})]
        self.shift = False
        self.word = self.word + lab if lab.isalpha() else ""
        return [Command("type_text", {"text": lab})]
