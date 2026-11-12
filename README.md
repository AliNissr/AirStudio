# AirStudio

منصة تحكم بالأيدي عبر كاميرا اللابتوب. (README كامل بالعربي والإنجليزي يجي بالمرحلة 5.)

## التشغيل من الكود (Windows)

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
cd engine && ..\.venv\Scripts\python -m airengine.demo
```
