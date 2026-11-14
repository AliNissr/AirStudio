"""الطبقة الرفيعة ويه ويندوز (ctypes، مدمج ويه Python). كلها "قراءة" بس:
الشاشات، الاختصارات العامة، كشف الماوس/الكيبورد الحقيقي، وهل النافذة الأمامية مرفوعة الصلاحية.
بهذا الملف ماكو أي شي يرسل إدخال لويندوز (SendInput). هذا مقصود بمرحلة Dry-run.
"""
import ctypes
import threading
import time
from ctypes import wintypes as wt

from .screens import Monitor

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)
user32.CallNextHookEx.argtypes = (wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM)
user32.CallNextHookEx.restype = LRESULT
user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD)
user32.SetWindowsHookExW.restype = wt.HHOOK


def set_dpi_awareness():
    """Per-Monitor DPI Aware V2: كل الأرقام بكسل حقيقي حتى لو شاشة 150% وشاشة 100%. لازم قبل QApplication."""
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass  # ويندوز قديم: Qt يسوي الأفضل اللي يكدر


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD), ("szDevice", wt.WCHAR * 32)]


def monitors():
    """كل الشاشات بالبكسل الحقيقي، مع اسمها (مثل \\\\.\\DISPLAY1) حتى نطابقها ويه شاشات Qt."""
    found = []
    PROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)

    def cb(hmon, _hdc, _rect, _lp):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcMonitor
            found.append(Monitor(r.left, r.top, r.right, r.bottom, info.szDevice))
        return True

    user32.EnumDisplayMonitors(None, None, PROC(cb), 0)
    return found


def foreground_elevated():
    """True إذا النافذة الأمامية لبرنامج "كمسؤول": ويندوز يمنعنا نتحكم بيها (UIPI). None = ما نعرف."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    proc = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not proc:
        return ctypes.get_last_error() == 5  # ACCESS_DENIED: غالباً عملية محمية أو مرفوعة
    try:
        token = wt.HANDLE()
        if not advapi32.OpenProcessToken(proc, 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
            return None
        try:
            elevated, size = wt.DWORD(), wt.DWORD()
            ok = advapi32.GetTokenInformation(token, 20, ctypes.byref(elevated), 4, ctypes.byref(size))  # TokenElevation
            return bool(elevated.value) if ok else None
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(proc)


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wt.POINT), ("mouseData", wt.DWORD), ("flags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


MOD = 0x0002 | 0x0001 | 0x0004 | 0x4000  # Ctrl + Alt + Shift + بدون تكرار
HOTKEYS = {1: ("stop", 0x51), 2: ("activate", 0x41), 3: ("precision", 0x50), 4: ("monitor_right", 0x27), 5: ("monitor_left", 0x25)}
MODIFIER_VKS = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C}


class InputWatcher:
    """خيط بالخلفية: الاختصارات العامة (Ctrl+Alt+Shift+Q/A/P/←/→) + كشف الماوس والكيبورد الحقيقيين.
    on_event(name) ينادى من هذا الخيط، فلازم يكون سريع (نرسل إشارة Qt بس).
    إدخالنا الوهمي (بالمرحلة الجاية) عليه علامة INJECTED فما يحسب "حقيقي".
    """

    def __init__(self, on_event):
        self.on_event = on_event
        self.failed = []       # اختصارات ما انحجزت (برنامج ثاني ماسكها)
        self.thread_id = None
        self._last_real = 0.0
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        self._ready.wait(2)
        return self

    # shortcut: الـ hooks بـ Python تحتاج الـ GIL، فإذا خيط ثاني ماسكه، حركة الماوس الحقيقي تتأخر شوية،
    # وويندوز يشيل الـ hook إذا تأخر هواية. الكود هنا أقل ما يمكن. إذا لاحظت تقطيع بالماوس، ننقلها لـ C صغير.
    def _real(self):
        now = time.monotonic()
        if now - self._last_real > 0.1:  # أكثر شي 10 إشعارات بالثانية
            self._last_real = now
            self.on_event("real_input")

    def _run(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        for hid, (name, vk) in HOTKEYS.items():
            if not user32.RegisterHotKey(None, hid, MOD, vk):
                self.failed.append(name)

        def mouse_cb(code, wparam, lparam):
            if code == 0 and not ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents.flags & 0x01:  # LLMHF_INJECTED
                self._real()
            return user32.CallNextHookEx(None, code, wparam, lparam)

        def kbd_cb(code, wparam, lparam):
            if code == 0:
                k = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if not k.flags & 0x10 and k.vkCode not in MODIFIER_VKS:  # LLKHF_INJECTED، ونتجاهل Ctrl/Alt/Shift وحدها
                    self._real()
            return user32.CallNextHookEx(None, code, wparam, lparam)

        self._procs = (HOOKPROC(mouse_cb), HOOKPROC(kbd_cb))  # نحتفظ بيهم حتى ما ينمسحون من الذاكرة
        hooks = [user32.SetWindowsHookExW(14, self._procs[0], None, 0), user32.SetWindowsHookExW(13, self._procs[1], None, 0)]
        self._ready.set()
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                self.on_event(HOTKEYS[msg.wParam][0])
        for h in hooks:
            if h:
                user32.UnhookWindowsHookEx(h)
        for hid in HOTKEYS:
            user32.UnregisterHotKey(None, hid)

    def stop(self):
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)  # WM_QUIT
            self._thread.join(2)
