"""إعدادات المستخدم بـ %APPDATA%\\AirStudio. الملفات قابلة للتعديل باليد، فنفحص كل قيمة.
aircontrol.json: الوضع، منطقة المعايرة، الأصوات (والربط والقائمة الدائرية يقراهم bindings.py من نفس الملف).
words.json: كلماتك اللي تعلمتها لوحة المفاتيح (محلي بس).
"""
import json
import os
from pathlib import Path

DIR = Path(os.environ.get("APPDATA", Path.home())) / "AirStudio"
CONFIG = DIR / "aircontrol.json"
WORDS = DIR / "words.json"
DEFAULTS = {"mode": "relative", "region": [0.2, 0.15, 0.8, 0.75], "sound": True}

POINTER = {"gain_min": 700, "gain_max": 3600, "speed_low": 0.05, "speed_high": 1.2, "precision": 1 / 3,
           "one_euro": {"min_cutoff": 1.5, "beta": 4.0, "d_cutoff": 1.0}}


def _read(path):
    try:
        if path.stat().st_size > 1_000_000:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load(path=CONFIG):
    raw, s = _read(Path(path)), dict(DEFAULTS)
    if raw.get("mode") in ("relative", "absolute"):
        s["mode"] = raw["mode"]
    r = raw.get("region")
    if (isinstance(r, list) and len(r) == 4 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in r)
            and r[2] - r[0] >= 0.1 and r[3] - r[1] >= 0.1):
        s["region"] = [float(v) for v in r]
    if isinstance(raw.get("sound"), bool):
        s["sound"] = raw["sound"]
    s["first_run"] = not Path(path).exists()
    return s


def save(settings, path=CONFIG):
    """نحفظ إعداداتنا ونخلي ربط الإيماءات (bindings/radial) اللي كتبه المستخدم مثل ما هو."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _read(path)
    raw.update({k: settings[k] for k in DEFAULTS})
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")


def load_words(path=WORDS):
    return _read(Path(path))


def save_words(learned, path=WORDS):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(learned, ensure_ascii=False), encoding="utf-8")
