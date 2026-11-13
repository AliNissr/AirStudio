# المرحلة 2: AirStudio Design — خطة التنفيذ

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**الهدف:** صفحة ويب ثابتة تتبع يدين بالكاميرا، ترسم مخطط غرفة على لوحة بيضاء، تحوله لغرفة 3D، تضع بيها أثاث بالإيماءات، وتحفظ وتصدّر.

**المعمارية:** ES modules بدون أي build step (تنفتح من أي سيرفر ثابت). المحرك من `engine/js/` نفسه (ما ننسخه). المكتبات والنموذج محفوظة داخل المشروع (`web-studio/vendor/`) حتى صفر اتصال بالإنترنت بعد ما تنفتح الصفحة. المنطق "النقي" (قياسات اليدين، المخطط، الحفظ) بملفات بدون DOM حتى نختبره بـ `node --test`؛ الواجهة نختبرها بـ Playwright.

**التقنيات:** `@mediapipe/tasks-vision` 1.2.3 (Apache-2.0)، `three` 0.187.0 (MIT)، Canvas 2D، localStorage.

**المواصفات:** طلب المستخدم الأصلي (الوحدة 1) + رسالة 2026-11-13: "تتبع يدين دائماً بالاستوديو، وقِس الأداء قبل اعتماد التصميم".

## القيود العامة

- يدين دائماً (`numHands: 2`)، 640x480، `delegate: "GPU"` ولو فشل نرجع لـ `"CPU"` تلقائياً.
- 5 fps لما ماكو يد أكثر من ثانية (نفس `perf` بـ `gestures.json`).
- واجهة داكنة، `dir="rtl"` و `lang="ar"`، تشتغل بالماوس أيضاً (بديل لكل إيماءة).
- مؤشر "الكاميرا شغالة" ظاهر دايماً، وزر يطفي الكاميرا.
- ماكو حفظ ولا إرسال لأي صورة. الحفظ = أرقام التصميم بس.
- الصفحة تنشر من جذر المستودع على GitHub Pages: `https://<اسمك>.github.io/AirStudio/web-studio/` (حتى `../engine/` يوصل).

## التنزيلات (نخبرك قبلها)

| الملف | الحجم التقريبي |
|---|---|
| `vision_bundle.mjs` + مجلد `wasm/` من tasks-vision | ~20 MB (نسختين wasm: SIMD وبدون) |
| `three.module.min.js` + `three.core.min.js` | ~0.8 MB |
| النموذج | نستخدم `engine/models/hand_landmarker.task` الموجود (7.5 MB) |

## تركيز المراجعة

1. **ملف JSON معطوب أو من شخص ثاني** → رسالة عربي واضحة، والتصميم الحالي ما ينمسح. اختبار: `test_import_rejects_bad_json`, `test_import_rejects_unknown_furniture`.
2. **يد وحدة طلعت بنص التكبير بيدين** → التكبير يوقف بمكانه، ما يقفز. اختبار: `two hand gesture ends cleanly when one hand lost`.
3. **سحب قطعة أثاث لبرة الجدران** → تبقى داخل حدود الغرفة. اختبار: `furniture clamped inside room`.
4. **المستخدم رفض إذن الكاميرا أو الكاميرا محجوزة** → رسالة عربي + الصفحة تبقى تشتغل بالماوس. اختبار Playwright: `camera denied shows message and mouse works`.
5. **اليدين يتبادلن (اليسار صار يمين)** → التتبع يعتمد على مكان اليد مو على اسمها بس. اختبار: `hands matched by position across frames`.

---

### Task 1: المكتبات + بوابة قياس الأداء بالمتصفح (قبل أي تصميم)

**Files:** Create `web-studio/vendor/` (المكتبات)، `web-studio/js/tracker.js`، `web-studio/bench.html`

**Interfaces — Produces:** `createTracker({numHands, delegate}) -> Promise<{detect(video, tsMs) -> Hand[], close()}>`، `Hand = {landmarks: [x,y,z][] بالبكسل, side: 'Left'|'Right'}`. يرمي `TrackerError(code)` بأكواد `DENIED`, `NOT_FOUND`, `BUSY`, `NO_WEBGL`.

- [ ] تنزيل المكتبات (بعد إخبارك) وإضافة `web-studio/vendor/LICENSES.md`.
- [ ] `bench.html`: يشغّل 4 حالات × 10 ثواني: (يد 1 / يدين) × (GPU / CPU)، ويعرض جدول fps ووقت النموذج.
- [ ] **أنت تشغّله بيدينك قدام الكاميرا**، ونسجل الأرقام بالدرس. **بوابة:** إذا يدين + GPU أقل من 20 fps، نوقف ونقرر سوية قبل Task 2.
- [ ] Commit: `feat(web): vendored libs and browser tracking benchmark`

### Task 2: طبقة إدخال اليدين

**Files:** Create `web-studio/js/hands.js` (DOM)، `web-studio/js/two_hand.js` (نقي)، Test `web-studio/tests/two_hand.test.js`

**Interfaces — Produces:**
- `twoHandMetrics(a, b) -> {distance, angle, center}` (من نقطة 9 لكل يد).
- `matchHands(prev, current) -> current مرتبة حسب أقرب مكان للإطار السابق`.
- `TwoHandGesture` و `.update(handsWithGestures, t) -> {zoom: نسبة, rotate: راديان} | null` — يبدأ لما اليدين بنفس الوقت `FIST` أو `PINCH`، وينتهي بهدوء إذا يد اختفت.
- `startHands(onFrame)` بـ `hands.js`: كاميرا + tracker + `GestureClassifier` و `OneEuroFilter` من `engine/js` لكل يد. يرسل `{hands:[{id, gesture, pointer:{x,y}, landmarks}], two}` كل إطار. فيه `window.__airInject(frame)` للاختبارات بس (يتفعّل بـ `?test`).

- [ ] الاختبارات أول: `zoom ratio from distance change`، `rotate from angle change`، `two hand gesture ends cleanly when one hand lost`، `hands matched by position across frames`.
- [ ] FAIL ← تنفيذ ← PASS. Commit: `feat(web): two-hand input layer`

### Task 3: هيكل الواجهة + الشاشة التعليمية

**Files:** Create `web-studio/index.html`، `web-studio/css/app.css`، `web-studio/js/app.js`، `web-studio/js/onboarding.js`، `web-studio/js/messages.js`

- [ ] نستخدم skills: frontend-design و ui-ux-pro-max و impeccable للتصميم الداكن RTL.
- [ ] تخطيط: شريط أدوات (مخطط / 3D / حفظ / تصدير)، مساحة العمل، معاينة كاميرا صغيرة بالهيكل العظمي، مؤشر الكاميرا، رسائل الأخطاء.
- [ ] شاشة تعليمية أول زيارة (5 بطاقات، كل وحدة تطلب منك تسوي الإيماءة وتتقدم لما تكتشفها، وزر تخطي). علامة `localStorage` حتى ما تتكرر، وزر "?" يرجعها.
- [ ] أصوات تأكيد خفيفة بـ Web Audio (بدون ملفات صوت).
- [ ] Commit: `feat(web): app shell and onboarding`

### Task 4: اللوحة البيضاء (مخطط الغرفة)

**Files:** Create `web-studio/js/plan.js` (نقي)، `web-studio/js/plan_view.js` (Canvas)، Test `web-studio/tests/plan.test.js`

**Interfaces — Produces:** `Plan` بيه `walls: [{a:{x,y}, b:{x,y}}]` بالمتر، و `strokes` (رسم حر). دوال: `addWall(a, b)` (تنقطع على شبكة 10 سم وزوايا 15°)، `eraseAt(p, radius)`، `undo()`، `bounds()`.

الإيماءات: قرص وسحب = رسم جدار (الإفلات ينهيه)، تبديل لرسم حر بزر. كف مفتوحة تتحرك = ممحاة (دائرة حول الكف). كف مفتوحة ثابتة ثانية ونص = إيقاف/استئناف.

- [ ] اختبارات: `wall snaps to grid and 15 degrees`، `erase removes touched walls only`، `undo restores`، `tiny wall ignored` (أقل من 20 سم = قرص بالغلط).
- [ ] FAIL ← تنفيذ ← PASS. Commit: `feat(web): whiteboard room plan`

### Task 5: الغرفة 3D والأثاث

**Files:** Create `web-studio/js/room3d.js`، `web-studio/js/furniture.js`، `web-studio/js/layout.js` (نقي)، Test `web-studio/tests/layout.test.js`

**Interfaces — Produces:**
- `FURNITURE = {sofa, table, chair, bed, wardrobe}` كل وحدة `{w, d, h, build() -> THREE.Group}` (أشكال بسيطة من صناديق واسطوانات، بدون ملفات نماذج).
- `layout.js`: `place(item, pos, roomBounds) -> pos` مقصوص داخل الغرفة، `rotate(item, rad)`.
- `room3d.js`: جدران مرفوعة 2.6 م من `Plan.walls`، أرضية، إضاءة، وكاميرات: علوي / منظور / أمامي / جانبي.

الإيماءات: قرص على قطعة بالقائمة = تمسكها، تحريك = على الأرض (raycast)، إفلات = توضع. قبضة على قطعة موجودة = سحب وتحريك. يدين (قبضتين أو قرصين): تباعد = تكبير/تصغير، دوران = تدوير المنظر، أو تدوير القطعة إذا وحدة مختارة. كله بالماوس أيضاً.

- [ ] اختبارات: `furniture clamped inside room`، `rotate wraps to 0..2π`، `every furniture type builds` (بـ three بـ node).
- [ ] FAIL ← تنفيذ ← PASS. Commit: `feat(web): 3D room and furniture`

### Task 6: الحفظ والتصدير

**Files:** Create `web-studio/js/storage.js` (نقي)، Test `web-studio/tests/storage.test.js`

**Interfaces — Produces:** `serialize(plan, items) -> {version: 1, walls, strokes, items}`، `parseDesign(text) -> {ok, design} | {ok:false, error: كود}` (يتحقق من كل حقل: أرقام محدودة، أنواع أثاث معروفة، أقصى 500 جدار و 200 قطعة).

- [ ] اختبارات: `roundtrip keeps design`، `test_import_rejects_bad_json`، `test_import_rejects_unknown_furniture`، `rejects huge numbers`.
- [ ] حفظ تلقائي بـ localStorage كل تغيير (مع debounce نص ثانية)، تصدير JSON، استيراد JSON، تصدير PNG للمنظر الحالي.
- [ ] Commit: `feat(web): save, import and export`

### Task 7: اختبار الواجهة كاملة + النشر + الدرس

- [ ] Playwright بكاميرا وهمية (`--use-fake-device-for-media-stream`) + `__airInject` يعيد تشغيل `engine/fixtures`: رسم جدار بالقرص، مسح بالكف، وضع كنبة، تكبير بيدين، رفض الكاميرا، تصدير واستيراد.
- [ ] مراجعة بـ code-review. فحص أمان للاستيراد.
- [ ] نشر GitHub Pages: **تحتاج حسابك**. أجهز كلشي وأعطيك الخطوات، والدفع (push) ما يصير إلا بموافقتك.
- [ ] `docs/learn/02-الاستوديو.md` + تحديث الخريطة والقاموس + 5 نقاط و 3 أسئلة وتمارين.
- [ ] Commit: `docs(learn): phase 2 lesson` — **توقف وانتظر تجربتك.**

---

## ملاحظة لـ AirControl (المرحلة 3): الوضع التكيفي

الأرقام المقاسة: التبديل بين يد ويدين يكلف ~33 ms (إطار واحد)، فالتبديل رخيص. التصميم المقترح:
- **التحكم مطفي (ينتظر إيماءة التفعيل):** يدين، بـ 5–10 fps (رخيص، ويكفي لاكتشاف "الكفين مفتوحة ثانيتين").
- **التحكم شغال:** يد وحدة بـ 30 fps (المؤشر سريع).
- **رجوع ليدين:** بس عند إيماءة تحتاجها (مثلاً كف مفتوحة ثابتة ثانية = "أريد يدين")، ويرجع ليد وحدة بعد 3 ثواني بدون يد ثانية.
نقيس هذا بجهازك قبل ما نعتمده، بأداة `python -m airengine.bench_hands` (مضافة).
