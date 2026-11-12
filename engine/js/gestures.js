// مصنّف الإيماءات: نفس engine/airengine/gestures.py بالضبط. أي تغيير هنا لازم ينعكس هناك.
const WRIST = 0, THUMB_TIP = 4, MIDDLE_MCP = 9;
const FINGERS = { index: [6, 8], middle: [10, 12], ring: [14, 16], pinky: [18, 20] };

export const Gesture = Object.freeze({
  NONE: 'NONE', PINCH: 'PINCH', MIDDLE_PINCH: 'MIDDLE_PINCH',
  OPEN_PALM: 'OPEN_PALM', FIST: 'FIST', TWO_FINGERS: 'TWO_FINGERS',
});

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
export const handSize = (pts) => dist(pts[WRIST], pts[MIDDLE_MCP]) || 1e-6;
export const pinchRatio = (pts, tip = 8) => dist(pts[THUMB_TIP], pts[tip]) / handSize(pts);

export function isExtended(pts, finger, ratio) {
  const [pip, tip] = FINGERS[finger];
  return dist(pts[WRIST], pts[tip]) > ratio * dist(pts[WRIST], pts[pip]);
}

export class GestureClassifier {
  constructor(config) {
    this.enter = config.pinch_enter;
    this.exit = config.pinch_exit;
    this.debounce = config.debounce_frames;
    this.extendRatio = config.extend_ratio;
    this.curlRatio = config.curl_ratio;
    this.reset();
  }

  reset() {
    this.pinch = { 8: false, 12: false };
    this.stable = Gesture.NONE;
    this.candidate = Gesture.NONE;
    this.count = 0;
  }

  pinched(pts, tip) {
    const finger = tip === 8 ? 'index' : 'middle';
    const curled = !isExtended(pts, finger, this.curlRatio);
    const r = pinchRatio(pts, tip);
    this.pinch[tip] = !curled && r < (this.pinch[tip] ? this.exit : this.enter);
    return this.pinch[tip];
  }

  classify(pts) {
    const ext = Object.fromEntries(Object.keys(FINGERS).map((f) => [f, isExtended(pts, f, this.extendRatio)]));
    const pinch = this.pinched(pts, 8), mpinch = this.pinched(pts, 12);
    const vals = Object.values(ext);
    if (!vals.some(Boolean)) return Gesture.FIST;
    if (pinch) return Gesture.PINCH;
    if (mpinch) return Gesture.MIDDLE_PINCH;
    if (vals.every(Boolean)) return Gesture.OPEN_PALM;
    if (ext.index && ext.middle && !ext.ring && !ext.pinky) return Gesture.TWO_FINGERS;
    return Gesture.NONE;
  }

  // pts: 21 نقطة [x, y, z] بنفس المقياس لـ x و y
  update(pts) {
    if (pts.length !== 21) throw new Error(`لازم 21 نقطة، وصلت ${pts.length}`);
    const g = this.classify(pts);
    if (g === this.candidate) this.count++;
    else { this.candidate = g; this.count = 1; }
    if (this.count >= this.debounce) this.stable = g;
    return this.stable;
  }
}
