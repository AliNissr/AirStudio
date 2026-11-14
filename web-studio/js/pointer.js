// شكل المؤشر حسب الإيماءة. نقي حتى نختبره.
//   يد مفتوحة = حلقة فارغة، تقرّب الإبهام = الحلقة تمتلي وتصغر بالتدريج، قرص = ممتلية وصغيرة، قبضة = دائرة مملوءة.
const FAR = 0.6, PINCHED = 0.25; // نسبة القرص (÷ حجم الكف): 0.6 بعيد، 0.25 = عتبة القرص بـ gestures.json
const BIG = 16, SMALL = 9;

export function pointerStyle(gesture, pinchRatio) {
  if (gesture === 'FIST') return { radius: 12, fill: 1, solid: true };
  const fill = gesture === 'PINCH' ? 1 : Math.min(1, Math.max(0, (FAR - pinchRatio) / (FAR - PINCHED)));
  return { radius: BIG - (BIG - SMALL) * fill, fill, solid: false };
}
