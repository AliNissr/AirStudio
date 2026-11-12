"""محرك AirStudio: تتبع اليد والتعرف على الإيماءات."""
import json
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ENGINE_DIR / "models" / "hand_landmarker.task"


def load_config() -> dict:
    """يقرأ الإعدادات المشتركة بين نسخة Python ونسخة JavaScript."""
    return json.loads((ENGINE_DIR / "gestures.json").read_text(encoding="utf-8"))
