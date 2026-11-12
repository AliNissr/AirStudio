# AirStudio — خطة التنفيذ

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**الهدف:** منصة تحكم بالأيدي عبر كاميرا اللابتوب: وحدة ويب للتصميم (AirStudio Design) ووحدة ويندوز تستبدل الماوس والكيبورد (AirControl)، على محرك تتبع يد واحد.

**المعمارية:** "المحرك الواحد" = نفس قواعد الإيماءات ونفس الفلتر، مكتوبة مرتين (Python للتطبيق و JavaScript للمتصفح) لأن المتصفح ما يقدر يشغّل Python بدون سيرفر. اللي يضمن إنهم "محرك واحد" فعلاً: ملف إعدادات مشترك (`engine/gestures.json`) + نفس ملفات الاختبار (`engine/fixtures/*.json`) تمر على النسختين. أي تغيير بقاعدة إيماءة لازم ينجح بالنسختين.

**التقنيات:** MediaPipe Tasks (HandLandmarker) بـ Python و JS، OpenCV للكاميرا، Three.js للـ 3D، ctypes (مدمج بـ Python) لـ SendInput والاختصارات العامة، psutil للأداء، pystray للـ tray، PySide6 للواجهات فوق الشاشة (قرار نأكده بالمرحلة 3)، pytest و `node --test` للاختبارات، PyInstaller + Inno Setup للتغليف.

**المواصفات:** رسالة المستخدم بالمحادثة (2026-11-12) + "وضع المعلّم". ملخصها بقسم القيود تحت.

## القيود العامة (تنطبق على كل مهمة)

- مكان المشروع: `D:\Claude\Projects\AirStudio`، مستودع Git، commit بعد كل خطوة برسالة واضحة.
- المجلدات: `engine/` و `web-studio/` و `control-app/` و `docs/` (و `docs/learn/`).
- Windows + Python 3.11 (موجود)، CPU فقط، بدون صلاحيات Administrator (التثبيت per-user).
- الكاميرا 640x480، أقصى 30 fps، 5 fps تقريباً لما ماكو يد، تخفيف تلقائي إذا CPU فوق 25% (قيمة بالإعدادات).
- أولوية العملية Below Normal.
- خصوصية: صفر اتصال إنترنت وقت التشغيل، ملفات النموذج والـ wasm محفوظة داخل المشروع (مو من CDN)، صفر حفظ للصور، مؤشر واضح إن الكاميرا شغالة.
- AirControl: التحكم مطفي افتراضياً، Dry-run هو الوضع الافتراضي بأول تشغيل، إيقاف طارئ `Ctrl+Alt+Shift+Q` + إيماءة، توقف تلقائي 3 ثواني عند استخدام الماوس/الكيبورد الحقيقي.
- قائمة بيضاء: ممنوع حذف/نقل/إعادة تسمية ملفات، ممنوع Delete و Alt+F4 و Win+R والطرفية و PowerShell وإيقاف التشغيل. الإجراءات الحساسة (إغلاق نافذة) تحتاج تأكيد بالإيماءة ثانية وحدة.
- تعليقات الكود بالعربي، رسائل الأخطاء للمستخدم بالعربي.
- أي تنزيل لمكتبة أو نموذج: أخبر المستخدم بالحجم قبل التنزيل.
- وضع المعلّم: `docs/learn/NN-اسم.md` لكل مرحلة، `00-خريطة-المشروع.md` (Mermaid) يتحدث، `glossary.md` يكبر، وبنهاية كل مرحلة: 5 نقاط + 3 أسئلة + تمارين اختيارية.
- نتوقف بعد كل مرحلة حتى يجربها المستخدم.

## التنزيلات المتوقعة (تقريبية، نأكدها قبل التنزيل)

| الشي | الحجم | الترخيص |
|---|---|---|
| mediapipe (Python wheel) | ~50 MB | Apache-2.0 |
| opencv-python | ~40 MB | Apache-2.0 |
| نموذج `hand_landmarker.task` | ~7.5 MB | Apache-2.0 |
| psutil, pytest, pystray, Pillow | ~5 MB | BSD / MIT / LGPL-3.0 / HPND |
| `@mediapipe/tasks-vision` (JS + wasm) | ~10–20 MB | Apache-2.0 |
| three.js (ملف module واحد) | ~1.3 MB | MIT |
| PySide6-Essentials (المرحلة 3) | ~75 MB | LGPL-3.0 |
| Inno Setup (المرحلة 5، برنامج) | ~5 MB | ترخيص Inno المجاني |

ملاحظة: الـ API القديم `mp.solutions.hands` (اللي بيه model_complexity=0 "الخفيف") صار deprecated. نستخدم `HandLandmarker` الجديد بنموذج float16، ونخففه بدقة 640x480 وفلترة الإطارات. نأكد هذا من Context7 وقت البناء.

## تركيز المراجعة (حالات ممكن تكسر التجربة ومحد طلبها صراحة)

1. يدين بالصورة بالوحدة 2 → نتحكم بيد وحدة بس (الأوضح/الأكبر)، والثانية تنهمل إلا لإيماءة التفعيل. اختبار: `test_controller_uses_single_hand`.
2. اليد تطلع وترجع بسرعة → المؤشر ما يقفز، والقرص المفتوح يتلغى (ما يبقى "ماسك" سحب للأبد). اختبار: `test_drag_released_when_hand_lost`.
3. قرص على الحد (يرتجف بين مفتوح/مسكّر) → hysteresis (عتبة دخول 0.25 وخروج 0.35) حتى ما يصير نقرات متكررة. اختبار: `test_pinch_hysteresis_no_flicker`.
4. الكاميرا مستخدمة من برنامج ثاني (Teams/Zoom) → رسالة عربي واضحة بدل crash. اختبار: `test_camera_busy_message`.
5. الشاشات المتعددة أو الـ DPI scaling 125/150% → المؤشر يوصل لحواف الشاشة بالضبط. اختبار: `test_map_to_screen_covers_edges`.

---

## المرحلة 1: المحرك (مفصّلة)

### Task 1: الهيكل والبيئة

**Files:**
- Create: `README.md` (مؤقت)، `.gitignore`، `requirements.txt`، `requirements-dev.txt`
- Create: `engine/airengine/__init__.py`، `engine/gestures.json`، `engine/fixtures/`
- Create: `docs/learn/00-خريطة-المشروع.md`، `docs/learn/glossary.md`

- [ ] `git init`، إنشاء `.venv`، `pip install -r requirements.txt` (بعد إخبار المستخدم بالحجم).
- [ ] تنزيل `hand_landmarker.task` إلى `engine/models/` (7.5 MB، بعد الإخبار).
- [ ] تحقق: `python -c "import mediapipe, cv2; print('ok')"` → `ok`.
- [ ] Commit: `chore: project skeleton and dev environment`

### Task 2: فلتر One Euro (TDD)

**Files:** Create `engine/airengine/one_euro.py`، Test `engine/tests/test_one_euro.py`

**Interfaces — Produces:** `OneEuroFilter(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)` و `.filter(x: float, t: float) -> float` و `.reset()`.

- [ ] اختبارات: `test_first_value_passthrough` (أول قيمة ترجع نفسها)، `test_reduces_jitter` (ضوضاء ±5 حول 100 → الانحراف المعياري للناتج أقل من نص الأصلي)، `test_follows_fast_motion` (قفزة 0→100 → بعد 10 إطارات الناتج > 90).
- [ ] تشغيل `pytest engine/tests/test_one_euro.py` → FAIL، ثم التنفيذ، ثم PASS.
- [ ] Commit: `feat(engine): add One Euro filter`

### Task 3: مصنّف الإيماءات (TDD)

**Files:** Create `engine/airengine/gestures.py`، `engine/fixtures/{open_palm,fist,pinch,middle_pinch,two_fingers,none}.json`، Test `engine/tests/test_gestures.py`

**Interfaces — Produces:**
- `Gesture` (Enum): `NONE, PINCH, MIDDLE_PINCH, OPEN_PALM, FIST, TWO_FINGERS`
- `GestureClassifier(config: dict)` و `.update(landmarks: list[tuple[float,float,float]]) -> Gesture` (21 نقطة، يحتفظ بالحالة للـ hysteresis والـ debounce)
- `pinch_ratio(landmarks, tip=8) -> float` = مسافة (الإبهام 4 ↔ الطرف) ÷ حجم اليد (الرسغ 0 ↔ قاعدة الوسطى 9)

قيم `gestures.json`: `pinch_enter=0.25`, `pinch_exit=0.35`, `debounce_frames=3`. إصبع "ممدود" = طرفه أبعد عن الرسغ من مفصله الوسطي (PIP) بـ 10%.

- [ ] fixtures مصنوعة يدوياً (هندسياً) لكل إيماءة + اختبار لكل وحدة، و `test_pinch_hysteresis_no_flicker` (سلسلة نسب 0.24→0.30→0.24→0.30 → يبقى PINCH)، و `test_debounce_requires_3_frames`.
- [ ] FAIL ← تنفيذ ← PASS.
- [ ] أداة `python -m airengine.record_fixture <اسم>` تسجل نقاط يدك الحقيقية لملف JSON (نقاط فقط، بدون صورة) — حتى تضيف fixtures حقيقية.
- [ ] Commit: `feat(engine): gesture classifier with shared fixtures`

### Task 4: الكاميرا والمتتبع مع معالجة الأخطاء

**Files:** Create `engine/airengine/camera.py`، `engine/airengine/tracker.py`، `engine/airengine/messages.py`، Test `engine/tests/test_camera.py`

**Interfaces — Produces:**
- `Camera(index=0, width=640, height=480)` و `.read() -> np.ndarray | None`، ترمي `CameraError(code)` بأكواد `NOT_FOUND`، `BUSY`.
- `HandTracker(model_path, num_hands=2)` و `.process(frame_rgb, timestamp_ms) -> list[Hand]`، `Hand = (landmarks, handedness, score)`.
- `frame_quality(frame) -> str | None`: `"DARK"` إذا متوسط الإضاءة < 40، `"UNCLEAR"` إذا score اليد < 0.6.
- `messages.AR[code] -> str` رسائل عربي (مثلاً BUSY: "الكاميرا مستخدمة من برنامج ثاني، سكّر Teams أو Zoom وجرب مرة ثانية").

- [ ] اختبارات بكاميرا وهمية (fake): `test_camera_not_found_message`، `test_camera_busy_message`، `test_dark_frame_detected`.
- [ ] FAIL ← تنفيذ ← PASS. Commit: `feat(engine): camera and tracker with Arabic error messages`

### Task 5: العرض المباشر + الأداء

**Files:** Create `engine/airengine/demo.py`، `engine/airengine/perf.py`، Test `engine/tests/test_perf.py`

**Interfaces — Produces:** `AdaptiveRate(active_fps=30, idle_fps=5, cpu_limit=25)` و `.next_interval(hand_present: bool, cpu: float) -> float`؛ `set_below_normal_priority()`.

- [ ] اختبارات: `test_idle_drops_to_5fps`، `test_high_cpu_reduces_rate`.
- [ ] `python -m airengine.demo`: نافذة فيها الـ 21 نقطة والعظام، اسم الإيماءة، FPS، CPU%، نقطة حمراء "الكاميرا شغالة"، رسائل الأخطاء بالعربي. زر Q للخروج.
- [ ] قياس فعلي: دقيقة بيد ودقيقة بدون يد، نسجل متوسط CPU و FPS بالتوثيق.
- [ ] Commit: `feat(engine): live keypoint viewer with adaptive frame rate`

### Task 6: نسخة JavaScript من المحرك

**Files:** Create `engine/js/one_euro.js`، `engine/js/gestures.js`، Test `engine/js/gestures.test.js`

**Interfaces — Produces:** نفس الأسماء بـ camelCase: `new OneEuroFilter({...}).filter(x, t)`، `new GestureClassifier(config).update(landmarks)`.

- [ ] الاختبارات تقرأ نفس `engine/fixtures/*.json` و `engine/gestures.json` → `node --test engine/js` → PASS.
- [ ] Commit: `feat(engine): JS port sharing fixtures with Python`

### Task 7: توثيق المرحلة 1

- [ ] `docs/learn/01-المحرك.md`: شنو وليش، شرح ملف ملف ودالة دالة، المصطلحات (Frame، Keypoints، Landmark، Bounding Box، Preprocessing، FPS، Hysteresis، Debounce، Fixture)، الأرقام المقاسة، 5 نقاط، 3 أسئلة، تمارين (غيّر `pinch_enter` وشوف شنو يصير...).
- [ ] تحديث `00-خريطة-المشروع.md` و `glossary.md`. مراجعة بـ code-review.
- [ ] Commit: `docs(learn): phase 1 lesson` — **توقف وانتظر تجربة المستخدم.**

---

## المراحل الجاية (خطة مفصلة لكل وحدة تنكتب ببداية مرحلتها، بعد ما نتعلم من اللي قبلها)

### المرحلة 2: AirStudio Design (`web-studio/`)
صفحة ثابتة ES modules بدون build step. 2أ: الكاميرا + المحرك JS + لوحة بيضاء ورسم بالقرص، كف مفتوحة = ممحاة/إيقاف. 2ب: غرفة Three.js + 5 قطع أثاث مبنية من أشكال بسيطة (بدون ملفات نماذج خارجية)، قبضة = سحب، يدين = تكبير/دوران، أزرار زوايا كاميرا. 2ج: حفظ تلقائي بـ localStorage، تصدير PNG و JSON واستيراد JSON. واجهة داكنة RTL + شاشة تعليمية أول مرة. اختبار بـ Playwright (كاميرا وهمية). نشر GitHub Pages.

### المرحلة 3: AirControl Dry-run (`control-app/`)
- `safety/whitelist.py` (TDD أولاً): الإجراءات المسموحة فقط كقائمة مغلقة (`move, click, right_click, drag_start, drag_end, scroll, key_combo` مع combos محددة مثل Alt+Tab، Win+Tab، Win+D، Win+H)، وأي شي غيرها يترفض. اختبارات صريحة إن Delete و Alt+F4 و Win+R و Win+X و Ctrl+Shift+Esc مرفوضة.
- `safety/state.py` (TDD): آلة حالات OFF → ARMED → ACTIVE، تفعيل بكفين مفتوحين ثانيتين، إيقاف طارئ، توقف عند إدخال حقيقي (نميزه عن إدخالنا بعلامة `LLMHF_INJECTED` بالـ low-level hook)، تأكيد ثانية للإجراءات الحساسة.
- `output/dry_run.py`: overlay يرسم المؤشر والإيماءة بدون أي SendInput. شاشة المعايرة، tray بـ FPS/CPU وزر إيقاف، أصوات خفيفة.

### المرحلة 4: التحكم الحقيقي (بعد موافقتك على Dry-run)
`output/sendinput.py` عبر ctypes يمر إجبارياً من الـ whitelist. ثم لوحة المفاتيح الافتراضية (عربي/إنجليزي، تنبؤ كلمات من قائمة تكرار محلية + يتعلم من كتابتك محلياً، زر Win+H)، ثم متصفح الملفات (مجلدات تختارها بس، فتح فقط بـ `os.startfile`، ماكو حذف/نقل/تسمية بالكود أصلاً)، وإغلاق نافذة بـ WM_CLOSE مع تأكيد ثانية.

### المرحلة 5: الأداء والتغليف
قياس ونشر الأرقام، PyInstaller (onedir) + Inno Setup بتثبيت per-user، README عربي/إنجليزي، `THIRD_PARTY_LICENSES.md`، فحص أمان نهائي.
