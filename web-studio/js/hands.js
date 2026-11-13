// الوصلة بين الكاميرا والصفحة: يشغّل الكاميرا والتتبع، ويرسل إطار جاهز للواجهة.
// المنطق الحقيقي (أرقام اليدين، الإيماءات، التنعيم) بـ two_hand.js حتى نختبره بدون متصفح.
import { openCamera, createTracker } from './tracker.js';
import { HandPipeline } from './two_hand.js';

const IDLE_AFTER_MS = 1000; // بدون يد ثانية = وضع الراحة
const IDLE_EVERY_MS = 200;  // بوضع الراحة نفحص 5 مرات بالثانية بس
const SLOW_CAMERA_FPS = 20; // أقل من هذا نبلّغ إن الكاميرا بطيئة
const DARK_LEVEL = 40;      // نفس engine/gestures.json

export async function loadConfig() {
  return (await fetch(new URL('../../engine/gestures.json', import.meta.url))).json();
}

// متوسط الإضاءة: نصغّر الصورة لـ 32x24 ونحسب (أرخص من الصورة كاملة بـ 400 مرة)
const probe = Object.assign(document.createElement('canvas'), { width: 32, height: 24 });
const probeCtx = probe.getContext('2d', { willReadFrequently: true });
function brightness(video) {
  probeCtx.drawImage(video, 0, 0, 32, 24);
  const d = probeCtx.getImageData(0, 0, 32, 24).data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) sum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  return sum / (d.length / 4);
}

/**
 * يبدي التتبع. onFrame({hands, two}) كل إطار، onStatus(code, data) للتنبيهات (DARK, CAMERA_SLOW, ...).
 * يرجع {stop(), info}. إذا فشلت الكاميرا يرمي TrackerError.
 */
export async function startHands({ video, onFrame, onStatus = () => {} }) {
  const config = await loadConfig();
  const pipeline = new HandPipeline(config);
  const stopCamera = await openCamera(video);
  let tracker;
  try {
    tracker = await createTracker({ numHands: 'auto' });
  } catch (e) {
    stopCamera();
    throw e;
  }
  const settings = video.srcObject.getVideoTracks()[0].getSettings();
  const info = { delegate: tracker.delegate, numHands: tracker.numHands, requestedFps: 30, reportedFps: settings.frameRate, cameraFps: null };
  if (tracker.numHands === 1) onStatus('ONE_HAND_CPU');

  let running = true, lastHand = 0, lastRun = 0, lastDarkCheck = 0;
  let camFrames = 0, camWindow = performance.now(), slowReported = false;

  const step = (now) => {
    if (!running) return;
    video.requestVideoFrameCallback(step);
    // نعد إطارات الكاميرا الحقيقية (مو اللي تكوله الإعدادات)
    camFrames++;
    if (now - camWindow >= 3000) {
      info.cameraFps = (camFrames * 1000) / (now - camWindow);
      if (info.cameraFps < SLOW_CAMERA_FPS && !slowReported) {
        onStatus('CAMERA_SLOW', { fps: Math.round(info.cameraFps) });
        slowReported = true;
      } else if (info.cameraFps >= SLOW_CAMERA_FPS) slowReported = false;
      camFrames = 0;
      camWindow = now;
    }
    const idle = now - lastHand > IDLE_AFTER_MS;
    if (idle && now - lastRun < IDLE_EVERY_MS) return; // وضع الراحة: نتجاوز هذا الإطار
    lastRun = now;
    if (now - lastDarkCheck > 2000) {
      lastDarkCheck = now;
      onStatus(brightness(video) < DARK_LEVEL ? 'DARK' : 'OK');
    }
    const raw = tracker.detect(video, now);
    if (raw.length) lastHand = now;
    onFrame(pipeline.process(raw, now / 1000, video.videoWidth, video.videoHeight));
  };
  video.requestVideoFrameCallback(step);

  // للاختبارات بس (?test بالرابط): ندخل يدين جاهزة بدل الكاميرا
  if (new URLSearchParams(location.search).has('test')) {
    window.__airInject = (raw, w = 640, h = 480) => onFrame(pipeline.process(raw, performance.now() / 1000, w, h));
  }

  return {
    info,
    stop() {
      running = false;
      tracker.close();
      stopCamera();
    },
  };
}
