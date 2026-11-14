"""شغّل AirControl: .venv\\Scripts\\python control-app\\run.py"""
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):  # ويندوز يستخدم cp1252 وقت التوجيه لملف، وهو ما بيه عربي
    stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT.parent / "engine")]

from aircontrol.app import main  # noqa: E402

sys.exit(main())
