"""طبقة شفافة فوق كل شاشة: ترسم المؤشر والحالة والقائمة الدائرية ولوحة المفاتيح.
ما تمسك الماوس (WindowTransparentForInput) وما تاخذ التركيز، فكلشي تحتها يشتغل عادي.
الإحداثيات من المتحكم بالبكسل الحقيقي؛ هنا نحولها لإحداثيات Qt لهاي الشاشة (÷ نسبة التكبير).
"""
import math

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PySide6.QtWidgets import QWidget

from ..radial import LABELS
from ..safety.state import OFF, ACTIVE, PAUSED

COLORS = {OFF: QColor("#93a0b1"), ACTIVE: QColor("#e8b341"), PAUSED: QColor("#ff9d4d")}
MODE_AR = {OFF: "مطفي", ACTIVE: "شغال", PAUSED: "موقف (لمست الماوس)"}
POSE_AR = {"open": "كف (رفع)", "point": "إشارة", "two": "إصبعين", "three": "3 أصابع", "fist": "قبضة"}
INK, PANEL, TEXT, RED = QColor("#18212c"), QColor(33, 44, 58, 235), QColor("#e4e8ee"), QColor("#ff5a52")


class Overlay(QWidget):
    def __init__(self, screen, monitor, primary):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.mon, self.dpr, self.primary = monitor, screen.devicePixelRatio(), primary
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.ctrl, self.extra = None, {}

    def local(self, x, y):
        return QPointF((x - self.mon.left) / self.dpr, (y - self.mon.top) / self.dpr)

    def mine(self, x, y):
        return self.mon.contains(x, y)

    def refresh(self, ctrl, extra):
        self.ctrl, self.extra = ctrl, extra
        self.update()

    def paintEvent(self, _):
        c = self.ctrl
        if not c or not c.view:
            return
        g = QPainter(self)
        g.setRenderHint(QPainter.Antialiasing)
        v, mode = c.view, c.view["mode"]
        if self.primary:
            self.badge(g, c, v)
        if c.radial and self.mine(*c.radial.center):
            self.radial(g, c)
        if c.keyboard and self.mine(*c.keyboard.origin):
            self.keyboard(g, c)
        if v.get("anchor") is not None and self.mine(*v["pos"]):
            self.pointer(g, v, mode)
        g.end()

    def text(self, g, rect, s, size=13, color=TEXT, bold=False, align=Qt.AlignCenter):
        g.setFont(QFont("Segoe UI", size, QFont.DemiBold if bold else QFont.Normal))
        g.setPen(color)
        g.drawText(rect, align, s)

    def badge(self, g, c, v):
        """الشارة فوك: تجريبي + الحالة + الكاميرا شغالة + آخر شي صار."""
        w = 560
        r = QRectF((self.width() - w) / 2, 12, w, 74)
        g.setPen(Qt.NoPen)
        g.setBrush(PANEL)
        g.drawRoundedRect(r, 12, 12)
        g.setBrush(RED)
        g.drawEllipse(QPointF(r.left() + 20, r.top() + 22), 6, 6)
        mode = v["mode"]
        status = f"تجريبي: ما ينرسل أي أمر لويندوز    |    {MODE_AR[mode]}    |    الكاميرا شغالة"
        if v.get("precision"):
            status += "    |    دقة"
        self.text(g, QRectF(r.left() + 32, r.top() + 6, w - 44, 30), status, 12, COLORS[mode], True)
        msg = self.extra.get("message") or c.message or (
            "افتح كفينك ثانيتين حتى تفعّل، وقبضة ثابتة ثانية توقف" if mode == OFF else "")
        self.text(g, QRectF(r.left() + 12, r.top() + 38, w - 24, 30), msg, 12)
        for progress, color in ((v.get("palms_progress", 0), COLORS[ACTIVE]), (v.get("fist_progress", 0), RED)):
            if progress > 0:
                g.setPen(QPen(color, 4))
                g.drawLine(QPointF(r.left() + 12, r.bottom() - 4), QPointF(r.left() + 12 + (w - 24) * progress, r.bottom() - 4))

    def pointer(self, g, v, mode):
        p, color = self.local(*v["pos"]), COLORS[mode]
        pose, lock = v.get("pose"), v.get("click_lock", 0)
        r = 16 - 7 * lock
        g.setBrush(Qt.NoBrush)
        for width, col in ((6, QColor(24, 33, 44, 170)), (2.5, color)):  # ظل غامق حتى يبين فوك أي خلفية
            pen = QPen(col, width)
            pen.setCapStyle(Qt.RoundCap)
            g.setPen(pen)
            g.drawEllipse(p, r, r)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                g.drawLine(p + QPointF(dx * (r + 4), dy * (r + 4)), p + QPointF(dx * (r + 12), dy * (r + 12)))
        if pose == "fist":
            g.setPen(Qt.NoPen)
            g.setBrush(RED)
            g.drawEllipse(p, 10, 10)
            g.setPen(QPen(RED, 4))
            g.setBrush(Qt.NoBrush)
            g.drawArc(QRectF(p.x() - 26, p.y() - 26, 52, 52), 90 * 16, int(-360 * 16 * v.get("fist_progress", 0)))
        elif lock > 0:
            g.setPen(Qt.NoPen)
            c = QColor(color)
            c.setAlpha(140 + int(115 * lock))
            g.setBrush(c)
            g.drawEllipse(p, r * lock, r * lock)
        label = POSE_AR.get(pose, "")
        self.text(g, QRectF(p.x() - 80, p.y() + r + 14, 160, 22), label, 11, TEXT, True)

    def radial(self, g, c):
        m, (px, py) = c.radial, c.view["pos"]
        hover = m.hit(px, py)
        center = self.local(*m.center)
        g.setPen(Qt.NoPen)
        g.setBrush(QColor(24, 33, 44, 150))
        g.drawEllipse(center, (m.radius + 52) / self.dpr, (m.radius + 52) / self.dpr)
        for i, item in enumerate(m.items):
            q = self.local(*m.item_center(i))
            g.setBrush(COLORS[ACTIVE] if i == hover else PANEL)
            g.drawEllipse(q, 44 / self.dpr * 1.4, 44 / self.dpr * 1.4)
            self.text(g, QRectF(q.x() - 60, q.y() - 14, 120, 28), LABELS.get(item, item), 11,
                      INK if i == hover else TEXT, True)
        self.text(g, QRectF(center.x() - 60, center.y() - 12, 120, 24), "إلغاء", 10)

    def keyboard(self, g, c):
        k, (px, py) = c.keyboard, c.view["pos"]
        hover = k.hit(px, py)
        ox, oy = k.origin
        g.setPen(Qt.NoPen)
        g.setBrush(QColor(24, 33, 44, 230))
        top = self.local(ox, oy)
        g.drawRoundedRect(QRectF(top.x() - 8, top.y() - 8, k.model.width / self.dpr + 16, k.model.height / self.dpr + 16), 14, 14)

        def cell(x, y, w, h, label, hot, size=14):
            a = self.local(ox + x + 3, oy + y + 3)
            rect = QRectF(a.x(), a.y(), (w - 6) / self.dpr, (h - 6) / self.dpr)
            g.setPen(Qt.NoPen)
            g.setBrush(COLORS[ACTIVE] if hot else QColor("#2b3a4c"))
            g.drawRoundedRect(rect, 8, 8)
            self.text(g, rect, label, size, INK if hot else TEXT, True)

        for word, (x, y, w, h) in k.model.suggestion_rects():
            cell(x, y, w, h, word, hover == word, 13)
        for key in k.model.keys:
            cell(*key.rect, "مسافة" if key.label == " " else key.label, hover == key)
