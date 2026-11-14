"""حالة التحكم: البوابة اللي كل أمر لازم يعبرها.

    OFF ──تفعيل──► ACTIVE ──ماوس/كيبورد حقيقي──► PAUSED ──3 ث بدون لمس──► ACTIVE
    أي حالة ──إيقاف طارئ──► OFF
"""
from ..actions import Command, Forbidden, SENSITIVE, validate

OFF, ACTIVE, PAUSED = "off", "active", "paused"
PAUSE_SECONDS = 3.0
CONFIRM_SECONDS = 5.0
MAX_BACKSPACE = 20


class SafetyState:
    def __init__(self):
        self.mode = OFF
        self.paused_until = 0.0
        self.pending = None  # (أمر حساس، آخر وقت للتأكيد)
        self.backspaces = 0

    def activate(self, now: float) -> None:
        self.mode = ACTIVE
        self.pending = None

    def emergency_stop(self) -> None:
        self.mode = OFF
        self.pending = None

    def real_input(self, now: float) -> None:
        """لمست الماوس أو الكيبورد الحقيقي."""
        if self.mode in (ACTIVE, PAUSED):
            self.mode = PAUSED
            self.paused_until = now + PAUSE_SECONDS
            self.pending = None

    def tick(self, now: float) -> None:
        if self.mode == PAUSED and now >= self.paused_until:
            self.mode = ACTIVE

    def gate(self, cmd: Command, now: float) -> str:
        """"ok" أو "needs_confirm" أو "blocked:<السبب>". الترتيب مهم: الحالة أول، بعدين القائمة البيضاء."""
        self.tick(now)
        if self.mode != ACTIVE:
            return f"blocked:{self.mode}"
        try:
            validate(cmd)
        except Forbidden as e:
            return f"blocked:forbidden {e}"
        if cmd.name in SENSITIVE:
            self.pending = (cmd, now + CONFIRM_SECONDS)
            return "needs_confirm"
        if cmd == Command("key", {"name": "backspace"}):
            if self.backspaces >= MAX_BACKSPACE:
                return "blocked:backspace_limit"
            self.backspaces += 1
        elif cmd.name == "type_text":
            self.backspaces = 0
        return "ok"

    def confirm(self, now: float):
        """تأكيد الأمر الحساس المعلّق. يرجع الأمر إذا لحكت، وإلا None."""
        cmd, deadline = self.pending or (None, 0)
        self.pending = None
        return cmd if cmd and self.mode == ACTIVE and now <= deadline else None
