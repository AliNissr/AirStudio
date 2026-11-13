# مكتبات خارجية محفوظة داخل المشروع (حتى الصفحة تشتغل بدون إنترنت)

| المجلد | المكتبة | الإصدار | الترخيص | الملفات |
|---|---|---|---|---|
| `mediapipe/` | [@mediapipe/tasks-vision](https://www.npmjs.com/package/@mediapipe/tasks-vision) | 1.2.3 | Apache-2.0 (https://www.apache.org/licenses/LICENSE-2.0) | `vision_bundle.esm.js` (نفس `vision_bundle.mjs` بالحزمة، غيّرنا الامتداد لأن بعض السيرفرات ما تعرف .mjs), `wasm/vision_wasm_internal.{js,wasm}` |
| `three/` | [three.js](https://threejs.org) | 0.187.0 | MIT (`three/LICENSE`) | `three.module.js`, `three.core.js` |

النموذج `engine/models/hand_landmarker.task` من Google MediaPipe، ترخيص Apache-2.0.

التحديث: `npm pack @mediapipe/tasks-vision@<إصدار> three@<إصدار>` ونسخ نفس الملفات. انسخ `vision_bundle.mjs` باسم `vision_bundle.esm.js`. لازم ملفات wasm من نفس الإصدار.
