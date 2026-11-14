"""القائمة الدائرية: أزرار كبيرة حول المؤشر. نقي (الحساب بس، الرسم بـ overlay.py)."""
import math

LABELS = {
    "media_play_pause": "تشغيل/إيقاف", "copy": "نسخ", "paste": "لصق", "undo": "تراجع", "select_all": "تحديد الكل",
    "volume_up": "صوت +", "volume_down": "صوت −", "volume_mute": "كتم", "show_desktop": "سطح المكتب",
    "keyboard": "لوحة المفاتيح", "dictation": "إملاء", "close_window": "إغلاق النافذة", "alt_tab": "تبديل النوافذ",
    "click": "نقر", "double_click": "نقر مزدوج", "right_click": "نقر يمين",
}


class RadialMenu:
    def __init__(self, items, center, radius=130, inner=40):
        self.items, self.center, self.radius, self.inner = list(items), center, radius, inner

    def hit(self, x, y):
        """رقم الزر تحت النقطة، أو None (بالنص أو بعيد = إلغاء). الأزرار تبدي من فوك وتدور مع عقارب الساعة."""
        dx, dy = x - self.center[0], y - self.center[1]
        d = math.hypot(dx, dy)
        if d < self.inner or d > self.radius * 1.6:
            return None
        a = (math.atan2(dy, dx) + math.pi / 2) % (2 * math.pi)  # y بالشاشة ينزل لتحت
        step = 2 * math.pi / len(self.items)
        return int(((a + step / 2) % (2 * math.pi)) // step)  # كل زر بنص قطاعه

    def item_center(self, i):
        a = -math.pi / 2 + i * 2 * math.pi / len(self.items)
        return (self.center[0] + self.radius * math.cos(a), self.center[1] + self.radius * math.sin(a))
