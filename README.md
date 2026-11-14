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

### AirControl (ويندوز، وضع تجريبي Dry-run)

```bash
.venv\Scripts\python control-app\run.py
```

- **تفعيل:** الكفين مفتوحين ثانيتين، أو `Ctrl+Alt+Shift+A`. **إيقاف طارئ:** قبضة ثابتة ثانية، أو `Ctrl+Alt+Shift+Q`.
- لمس الماوس أو الكيبورد الحقيقي يوقفه 3 ثواني.
- بهاي المرحلة **ما ينرسل أي أمر لويندوز**: يرسم ويسجّل بس (السجل من أيقونة الـ tray).
- حدود ويندوز: ما يكدر يتحكم بنوافذ "كمسؤول" ولا بشاشة UAC أو القفل، وما يطلب صلاحية مدير.

اختبارات الويب (تحتاج Node و Chrome أو Edge):

```bash
npm install
npm test
npm run test:visual
```
