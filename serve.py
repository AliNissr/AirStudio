"""سيرفر التطوير: نفس python -m http.server بس يكول للمتصفح "لا تخزن الملفات".

ليش؟ السيرفر العادي ما يكول شي عن التخزين، فالمتصفح يخمّن ويعرض نسخة قديمة بعد كل تعديل.
التشغيل (من مجلد المشروع):  .venv\\Scripts\\python serve.py   ثم افتح http://127.0.0.1:8765/web-studio/
"""
import http.server
import mimetypes
from functools import partial
from pathlib import Path

mimetypes.add_type("text/javascript", ".js")  # ويندوز أحياناً يسجّل .js بنوع غلط بالـ Registry


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")  # يسأل السيرفر كل مرة إذا الملف تغيّر
        super().end_headers()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765  # مثلاً: python serve.py 8766
    handler = partial(NoCacheHandler, directory=str(Path(__file__).parent))
    print(f"AirStudio: http://127.0.0.1:{port}/web-studio/")
    # 127.0.0.1 بس: الجهاز نفسه، مو كل الشبكة
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
