// الكاميرا + MediaPipe بالمتصفح. كلشي يشتغل محلياً، والصور ما تطلع من الجهاز أبداً.
import { FilesetResolver, HandLandmarker } from '../vendor/mediapipe/vision_bundle.esm.js';

const WASM = new URL('../vendor/mediapipe/wasm', import.meta.url).href;
const MODEL = new URL('../../engine/models/hand_landmarker.task', import.meta.url).href;

export class TrackerError extends Error {
  constructor(code) {
    super(code);
    this.code = code; // مفتاح من messages.js
  }
}

// أسماء أخطاء المتصفح ← أكوادنا
const CAMERA_ERRORS = {
  NotAllowedError: 'DENIED',
  SecurityError: 'DENIED',
  NotFoundError: 'NOT_FOUND',
  OverconstrainedError: 'NOT_FOUND',
  NotReadableError: 'BUSY', // برنامج ثاني ماسك الكاميرا
};

export async function openCamera(video) {
  if (!navigator.mediaDevices?.getUserMedia) throw new TrackerError('NO_CAMERA_API');
  try {
    video.srcObject = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { max: 30 }, facingMode: 'user' },
      audio: false,
    });
  } catch (e) {
    throw new TrackerError(CAMERA_ERRORS[e.name] ?? 'NOT_FOUND');
  }
  await video.play();
  return () => video.srcObject?.getTracks().forEach((t) => t.stop()); // دالة تطفي الكاميرا
}

let vision; // نحمّل الـ wasm مرة وحدة بس
export async function createTracker({ numHands = 2, delegate = 'GPU' } = {}) {
  vision ??= await FilesetResolver.forVisionTasks(WASM);
  let lm;
  try {
    lm = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: MODEL, delegate },
      runningMode: 'VIDEO',
      numHands,
    });
  } catch (e) {
    if (delegate === 'GPU') return createTracker({ numHands, delegate: 'CPU' }); // ماكو WebGL؟ نرجع للمعالج
    throw new TrackerError('NO_MODEL');
  }
  let lastTs = -1;
  return {
    delegate,
    // يرجع اليدين بالبكسل ومعكوسة مثل المراية (يدك اليمين تبين يمين الشاشة)
    detect(video, tsMs) {
      const ts = Math.max(Math.round(tsMs), lastTs + 1); // الوقت لازم يتزايد دايماً
      lastTs = ts;
      const w = video.videoWidth, h = video.videoHeight;
      const r = lm.detectForVideo(video, ts);
      return r.landmarks.map((pts, i) => ({
        landmarks: pts.map((p) => [(1 - p.x) * w, p.y * h, p.z * w]),
        // MediaPipe يفترض صورة معكوسة؛ صورتنا مو معكوسة فنقلب الاسم
        side: r.handedness[i][0].categoryName === 'Left' ? 'Right' : 'Left',
      }));
    },
    close: () => lm.close(),
  };
}
