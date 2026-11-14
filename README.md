# AirStudio

منصة تحكم بالأيدي عبر كاميرا اللابتوب. (README كامل بالعربي والإنجليزي يجي بالمرحلة 5.)

## التشغيل من الكود (Windows)

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
cd engine && ..\.venv\Scripts\python -m airengine.demo
```

### الاستوديو بالمتصفح

```bash
.venv\Scripts\python serve.py
```

افتح `http://127.0.0.1:8765/web-studio/` (أضف `?perf` لأرقام الأداء). `serve.py` يمنع المتصفح يعرض نسخة قديمة بعد التعديل.

اختبارات الويب (تحتاج Node و Chrome أو Edge):

```bash
npm install
npm test
npm run test:visual
```
