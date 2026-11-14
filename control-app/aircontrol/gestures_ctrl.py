"""إيماءات AirControl الزمنية. نقي: ياخذ أيادي (21 نقطة بالبكسل) والوقت، ويرجع أحداث + حالة.

النقر وأخواته تعتمد على المدة، مو على إطار واحد:
  الإبهام يلمس جانب السبابة ويفك بسرعة (< 250 ms) = tap_index، ومرتين بسرعة = double_tap_index
  يبقى أكثر من 350 ms = hold_index (بداية سحب)، والفك = نهايته
  الإبهام على الوسطى: tap_middle، أو hold_middle بعد 500 ms (القائمة الدائرية)
  إصبعين/3 أصابع تتحرك = تمرير/تكبير، 3 أصابع سحبة سريعة = تبديل نوافذ
  كف مفتوحة = رفع الماوس، وسحبة سريعة بيها = نقل للشاشة الثانية
  قبضة ثابتة ثانية = إيقاف طارئ، كفين مفتوحين ثانيتين = تفعيل
"""
import math

from airengine.gestures import hand_size, is_extended

CTRL_DEFAULTS = {
    "tap_enter": 0.18, "tap_exit": 0.28, "approach": 0.45,  # ÷ حجم الكف
    "tap_max": 0.25, "hold_index": 0.35, "hold_middle": 0.5, "double_s": 0.4, "double_move": 0.01,
    "scroll_gain": 50, "scroll_min_speed": 0.05, "swipe_speed": 1.0, "palm_swipe_speed": 1.5, "swipe_cooldown": 0.8,
    "fist_hold": 1.0, "fist_still": 0.03, "palms_hold": 2.0, "extend_ratio": 1.1,
}
SEGMENTS = {"index": (5, 6), "middle": (10, 12)}  # الجزء اللي يلمسه الإبهام من كل إصبع


def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    k = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2)) if l2 else 0.0
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def pose_of(pts, ratio):
    ext = {f: is_extended(pts, f, ratio) for f in ("index", "middle", "ring", "pinky")}
    if not any(ext.values()):
        return "fist"
    if all(ext.values()):
        return "open"
    if ext["index"] and ext["middle"] and ext["ring"] and not ext["pinky"]:
        return "three"
    if ext["index"] and ext["middle"] and not ext["ring"] and not ext["pinky"]:
        return "two"
    return "point"


class ControlGestures:
    def __init__(self, cfg):
        self.c = cfg
        self.reset()
        self.palms_since = None
        self.palms_fired = False

    def reset(self):
        self.contact = None       # الإصبع اللي الإبهام لازكه هسه
        self.contact_t0 = 0.0
        self.held = False
        self.last_tap = None      # (الوقت، المكان) لآخر نقرة سبابة
        self.prev = None          # (anchor, t)
        self.accum = {"scroll_x": 0.0, "scroll_y": 0.0, "zoom": 0.0}
        self.cooldown_until = 0.0
        self.fist_since = None
        self.fist_anchor = None
        self.fist_fired = False

    def update(self, hands, t, w, h):
        events = []
        c = self.c

        # تفعيل: كفين مفتوحين ثابتين ثانيتين (هنا بس نحتاج يدين)
        palms = len(hands) >= 2 and all(pose_of(p, c["extend_ratio"]) == "open" for p in hands[:2])
        if not palms:
            self.palms_since, self.palms_fired = None, False
        elif self.palms_since is None:
            self.palms_since = t
        palms_progress = min(1.0, (t - self.palms_since) / c["palms_hold"]) if palms else 0.0
        if palms and palms_progress >= 1.0 and not self.palms_fired:
            events.append(("both_palms", {}))
            self.palms_fired = True

        if not hands:
            if self.held:
                events.append(("hold_index", {"phase": "end"}))  # ما نخلي زر الماوس مضغوط أبداً
            self.reset()
            return events, {"clutch": False, "click_lock": 0.0, "anchor": None, "pose": None,
                            "fist_progress": 0.0, "palms_progress": palms_progress}

        pts = max(hands, key=hand_size)  # اليد المتحكمة = الأقرب (الأكبر)
        size = hand_size(pts)
        pose = pose_of(pts, c["extend_ratio"])
        anchor = ((0.7 * pts[5][0] + 0.3 * pts[6][0]) / w, (0.7 * pts[5][1] + 0.3 * pts[6][1]) / h)
        vx = vy = 0.0
        if self.prev:
            dt = max(t - self.prev[1], 1e-3)
            vx, vy = (anchor[0] - self.prev[0][0]) / dt, (anchor[1] - self.prev[0][1]) / dt
        delta = (anchor[0] - self.prev[0][0], anchor[1] - self.prev[0][1]) if self.prev else (0.0, 0.0)
        self.prev = (anchor, t)

        # ===== قبضة ثابتة = إيقاف طارئ =====
        fist_progress = 0.0
        if pose == "fist":
            if self.fist_since is None or math.dist(anchor, self.fist_anchor) > c["fist_still"]:
                self.fist_since, self.fist_anchor = t, anchor  # تحركت: نبدي العد من جديد
            fist_progress = min(1.0, (t - self.fist_since) / c["fist_hold"])
            if fist_progress >= 1.0 and not self.fist_fired:
                events.append(("fist_hold", {}))
                self.fist_fired = True
        else:
            self.fist_since, self.fist_fired = None, False

        # ===== لمسات الإبهام (نقر، سحب، قائمة) =====
        dist = {f: _seg_dist(pts[4], pts[a], pts[b]) / size for f, (a, b) in SEGMENTS.items()}
        if pose == "fist":
            touching = None  # بالقبضة الإبهام فوك الأصابع بالصدفة: مو نقرة
        elif self.contact and dist[self.contact] < c["tap_exit"]:
            touching = self.contact  # hysteresis: ما نفك إلا فوك tap_exit
        else:
            near = min(dist, key=dist.get)
            touching = near if dist[near] < c["tap_enter"] else None

        if touching != self.contact:
            if self.contact:  # فك
                dur = t - self.contact_t0
                if self.held and self.contact == "index":
                    events.append(("hold_index", {"phase": "end"}))
                elif not self.held and dur < c["tap_max"]:
                    if self.contact == "middle":
                        events.append(("tap_middle", {}))
                    elif self.last_tap and self.contact_t0 - self.last_tap[0] < c["double_s"] and math.dist(anchor, self.last_tap[1]) < c["double_move"]:
                        events.append(("double_tap_index", {}))
                        self.last_tap = None
                    else:
                        events.append(("tap_index", {}))
                        self.last_tap = (self.contact_t0, anchor)
            self.contact, self.contact_t0, self.held = touching, t, False
        if self.contact and not self.held and t - self.contact_t0 >= c[f"hold_{self.contact}"]:
            self.held = True
            events.append((f"hold_{self.contact}", {"phase": "start"}))

        # قفل النقر: كلما قرّب الإبهام من السبابة، المؤشر يتباطأ. وقت السحب لازم يتحرك عادي
        if self.contact and not self.held:
            click_lock = 1.0
        elif self.held:
            click_lock = 0.0
        else:
            click_lock = min(1.0, max(0.0, (c["approach"] - dist["index"]) / (c["approach"] - c["tap_enter"])))

        # ===== حركة بأصابع: تمرير، تكبير، تبديل نوافذ، نقل شاشة =====
        speed = math.hypot(vx, vy)
        swipe_ready = t >= self.cooldown_until
        if pose == "open" and swipe_ready and abs(vx) > c["palm_swipe_speed"] and abs(vx) > 2 * abs(vy):
            events.append(("palm_swipe", {"dir": 1 if vx > 0 else -1}))
            self.cooldown_until = t + c["swipe_cooldown"]
        elif pose == "three" and swipe_ready and abs(vx) > c["swipe_speed"] and abs(vx) > 2 * abs(vy):
            events.append(("three_finger_swipe", {"dir": 1 if vx > 0 else -1}))
            self.cooldown_until = t + c["swipe_cooldown"]
        elif pose in ("two", "three") and not self.contact and speed > c["scroll_min_speed"]:
            g = c["scroll_gain"]
            if pose == "two":
                self.accum["scroll_y"] += -delta[1] * g  # إيد لفوك = تمرير لفوك
                self.accum["scroll_x"] += delta[0] * g
                for axis, key in (("dy", "scroll_y"), ("dx", "scroll_x")):
                    while abs(self.accum[key]) >= 1:
                        step = 1 if self.accum[key] > 0 else -1
                        self.accum[key] -= step
                        events.append(("two_finger_move", {"dx": 0, "dy": 0, axis: step}))
            elif abs(vy) > abs(vx):
                self.accum["zoom"] += -delta[1] * g
                while abs(self.accum["zoom"]) >= 1:
                    step = 1 if self.accum["zoom"] > 0 else -1
                    self.accum["zoom"] -= step
                    events.append(("three_finger_vertical", {"steps": step}))
        if pose not in ("two", "three"):
            self.accum = {k: 0.0 for k in self.accum}

        return events, {"clutch": pose == "open", "click_lock": click_lock, "anchor": anchor, "pose": pose,
                        "fist_progress": fist_progress, "palms_progress": palms_progress}
