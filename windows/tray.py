"""Read Pāli Aloud in the background on Windows (one process for everything):

  • tray icon (Settings, Pause Floating Popup, Help, Exit); closing the window
    only hides it in the tray
  • Ctrl+Shift+Y: read the selected text of any program
  • floating "▶ Read Pāli" button after text is selected with the mouse
  • text is read with UI Automation (uia.py), not the clipboard

Threads: Tk window (main thread) · Win32 thread (tray, hotkey, mouse hook,
popup button; must never wait) · worker thread (UI Automation, may be slow).
Uses only Windows' own DLLs through ctypes.
"""
import ctypes
import json
import os
import queue
import sys
import threading
import time
import winreg
from ctypes import wintypes as W

import hotkey  # clipboard fallback for Ctrl+Shift+Y
import uia

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, W.WPARAM, W.LPARAM)

APP_NAME = "Read Pāli Aloud"
HIDDEN_CLASS = "PaliTTS.TrayWindow"   # found by a second copy of the exe
POPUP_CLASS = "PaliTTS.Popup"
MUTEX_NAME = "Local\\PaliTTS.ReadPaliAloud.Tray"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Read Pali Aloud"
POPUP_LABEL = "▶  Read Pāli"

WM_DESTROY, WM_CLOSE, WM_PAINT, WM_COMMAND = 0x0002, 0x0010, 0x000F, 0x0111
WM_COPYDATA, WM_HOTKEY, WM_NULL = 0x004A, 0x0312, 0x0000
WM_MOUSEACTIVATE, MA_NOACTIVATE = 0x0021, 3
WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x0201, 0x0202, 0x0203
WM_RBUTTONDOWN, WM_RBUTTONUP, WM_MBUTTONDOWN = 0x0204, 0x0205, 0x0207
WM_TIMER = 0x0113
HOOK_TIMER_MS = 5 * 60 * 1000  # re-install the mouse hook now and then (see _wndproc)
WM_APP = 0x8000
WM_TRAY = WM_APP + 1          # tray icon mouse events
WM_SHOW_POPUP = WM_APP + 2    # worker → Win32 thread
WM_HIDE_POPUP = WM_APP + 3
WM_BALLOON = WM_APP + 4

WS_POPUP = 0x80000000
WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x8, 0x80, 0x08000000
SW_HIDE = 0
SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0010, 0x0040
HWND_TOPMOST = W.HWND(-1)
WH_MOUSE_LL = 14
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 1, 2, 4, 0x10
NIIF_INFO = 1
MF_STRING, MF_CHECKED, MF_SEPARATOR, MF_DEFAULT = 0, 8, 0x800, 0x1000
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x2, 0x100
IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
SM_CXSMICON, SM_CYSMICON, SM_CXDRAG, SM_CYDRAG = 49, 50, 68, 69
MONITOR_DEFAULTTONEAREST = 2
DT_CENTER, DT_VCENTER, DT_SINGLELINE = 1, 4, 0x20
TRANSPARENT = 1
IDC_HAND = 32649
VK_ESCAPE = 0x1B
MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x2, 0x4, 0x4000
VK_Y = 0x59
HOTKEY_ID, ESC_ID = 1, 2
ERROR_ALREADY_EXISTS = 183
CMD_SETTINGS, CMD_PAUSE, CMD_HELP, CMD_EXIT = 1, 2, 3, 4


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", W.UINT), ("style", W.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", W.HINSTANCE), ("hIcon", W.HICON), ("hCursor", W.HANDLE),
                ("hbrBackground", W.HBRUSH), ("lpszMenuName", W.LPCWSTR),
                ("lpszClassName", W.LPCWSTR), ("hIconSm", W.HICON)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", W.POINT), ("mouseData", W.DWORD), ("flags", W.DWORD),
                ("time", W.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("hWnd", W.HWND), ("uID", W.UINT), ("uFlags", W.UINT),
                ("uCallbackMessage", W.UINT), ("hIcon", W.HICON), ("szTip", W.WCHAR * 128),
                ("dwState", W.DWORD), ("dwStateMask", W.DWORD), ("szInfo", W.WCHAR * 256),
                ("uVersion", W.UINT), ("szInfoTitle", W.WCHAR * 64), ("dwInfoFlags", W.DWORD),
                ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", W.HICON)]


class COPYDATASTRUCT(ctypes.Structure):
    _fields_ = [("dwData", ctypes.c_size_t), ("cbData", W.DWORD), ("lpData", ctypes.c_void_p)]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", W.HDC), ("fErase", W.BOOL), ("rcPaint", W.RECT),
                ("fRestore", W.BOOL), ("fIncUpdate", W.BOOL), ("rgbReserved", W.BYTE * 32)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT),
                ("dwFlags", W.DWORD)]


def _sig(dll, name, res, *args):
    fn = getattr(dll, name)
    fn.restype, fn.argtypes = res, list(args)


_sig(user32, "RegisterClassExW", W.ATOM, ctypes.POINTER(WNDCLASSEXW))
_sig(user32, "CreateWindowExW", W.HWND, W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, ctypes.c_int,
     ctypes.c_int, ctypes.c_int, ctypes.c_int, W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID)
_sig(user32, "DefWindowProcW", LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
_sig(user32, "DestroyWindow", W.BOOL, W.HWND)
_sig(user32, "SetWindowsHookExW", W.HHOOK, ctypes.c_int, HOOKPROC, W.HINSTANCE, W.DWORD)
_sig(user32, "CallNextHookEx", LRESULT, W.HHOOK, ctypes.c_int, W.WPARAM, W.LPARAM)
_sig(user32, "UnhookWindowsHookEx", W.BOOL, W.HHOOK)
_sig(user32, "GetMessageW", W.BOOL, ctypes.POINTER(W.MSG), W.HWND, W.UINT, W.UINT)
_sig(user32, "TranslateMessage", W.BOOL, ctypes.POINTER(W.MSG))
_sig(user32, "DispatchMessageW", LRESULT, ctypes.POINTER(W.MSG))
_sig(user32, "PostMessageW", W.BOOL, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
_sig(user32, "SendMessageTimeoutW", LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM, W.UINT,
     W.UINT, ctypes.POINTER(ctypes.c_size_t))
_sig(user32, "PostQuitMessage", None, ctypes.c_int)
_sig(user32, "LoadImageW", W.HANDLE, W.HINSTANCE, W.LPCWSTR, W.UINT, ctypes.c_int,
     ctypes.c_int, W.UINT)
_sig(user32, "LoadCursorW", W.HANDLE, W.HINSTANCE, W.LPVOID)
_sig(user32, "SetCursor", W.HANDLE, W.HANDLE)
_sig(user32, "CreatePopupMenu", W.HMENU)
_sig(user32, "AppendMenuW", W.BOOL, W.HMENU, W.UINT, ctypes.c_size_t, W.LPCWSTR)
_sig(user32, "TrackPopupMenu", W.BOOL, W.HMENU, W.UINT, ctypes.c_int, ctypes.c_int,
     ctypes.c_int, W.HWND, W.LPVOID)
_sig(user32, "DestroyMenu", W.BOOL, W.HMENU)
_sig(user32, "SetForegroundWindow", W.BOOL, W.HWND)
_sig(user32, "GetForegroundWindow", W.HWND)
_sig(user32, "GetWindowThreadProcessId", W.DWORD, W.HWND, ctypes.POINTER(W.DWORD))
_sig(user32, "AllowSetForegroundWindow", W.BOOL, W.DWORD)
_sig(user32, "GetCursorPos", W.BOOL, ctypes.POINTER(W.POINT))
_sig(user32, "ShowWindow", W.BOOL, W.HWND, ctypes.c_int)
_sig(user32, "SetWindowPos", W.BOOL, W.HWND, W.HWND, ctypes.c_int, ctypes.c_int,
     ctypes.c_int, ctypes.c_int, W.UINT)
_sig(user32, "BeginPaint", W.HDC, W.HWND, ctypes.POINTER(PAINTSTRUCT))
_sig(user32, "EndPaint", W.BOOL, W.HWND, ctypes.POINTER(PAINTSTRUCT))
_sig(user32, "GetClientRect", W.BOOL, W.HWND, ctypes.POINTER(W.RECT))
_sig(user32, "FillRect", ctypes.c_int, W.HDC, ctypes.POINTER(W.RECT), W.HBRUSH)
_sig(user32, "FrameRect", ctypes.c_int, W.HDC, ctypes.POINTER(W.RECT), W.HBRUSH)
_sig(user32, "DrawTextW", ctypes.c_int, W.HDC, W.LPCWSTR, ctypes.c_int,
     ctypes.POINTER(W.RECT), W.UINT)
_sig(user32, "GetDC", W.HDC, W.HWND)
_sig(user32, "ReleaseDC", ctypes.c_int, W.HWND, W.HDC)
_sig(user32, "MonitorFromPoint", W.HMONITOR, W.POINT, W.DWORD)
_sig(user32, "GetMonitorInfoW", W.BOOL, W.HMONITOR, ctypes.POINTER(MONITORINFO))
_sig(user32, "RegisterHotKey", W.BOOL, W.HWND, ctypes.c_int, W.UINT, W.UINT)
_sig(user32, "UnregisterHotKey", W.BOOL, W.HWND, ctypes.c_int)
_sig(user32, "FindWindowW", W.HWND, W.LPCWSTR, W.LPCWSTR)
_sig(user32, "RegisterWindowMessageW", W.UINT, W.LPCWSTR)
_sig(user32, "SetTimer", ctypes.c_size_t, W.HWND, ctypes.c_size_t, W.UINT, W.LPVOID)
_sig(user32, "GetSystemMetrics", ctypes.c_int, ctypes.c_int)
_sig(user32, "GetDoubleClickTime", W.UINT)
_sig(user32, "MessageBoxW", ctypes.c_int, W.HWND, W.LPCWSTR, W.LPCWSTR, W.UINT)
_sig(user32, "DestroyIcon", W.BOOL, W.HICON)
_sig(gdi32, "CreateSolidBrush", W.HBRUSH, W.COLORREF)
_sig(gdi32, "DeleteObject", W.BOOL, W.HGDIOBJ)
_sig(gdi32, "SelectObject", W.HGDIOBJ, W.HDC, W.HGDIOBJ)
_sig(gdi32, "SetBkMode", ctypes.c_int, W.HDC, ctypes.c_int)
_sig(gdi32, "SetTextColor", W.COLORREF, W.HDC, W.COLORREF)
_sig(gdi32, "GetDeviceCaps", ctypes.c_int, W.HDC, ctypes.c_int)
_sig(gdi32, "CreateFontW", W.HFONT, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
     ctypes.c_int, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD,
     W.LPCWSTR)
_sig(kernel32, "GetModuleHandleW", W.HMODULE, W.LPCWSTR)
_sig(kernel32, "CreateMutexW", W.HANDLE, W.LPVOID, W.BOOL, W.LPCWSTR)
_sig(shell32, "Shell_NotifyIconW", W.BOOL, W.DWORD, ctypes.POINTER(NOTIFYICONDATAW))


def _rgb(r, g, b):
    return r | (g << 8) | (b << 16)


def _pid_of(hwnd):
    pid = W.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


# ── Run on Windows startup (HKCU\...\Run) ─────────────────────────────────────
def _startup_command():
    if getattr(sys, "frozen", False):
        return '"%s" --tray' % sys.executable
    here = os.path.dirname(os.path.abspath(__file__))
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    return '"%s" "%s" --tray' % (exe, os.path.join(here, "read_pali_aloud.py"))


def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_VALUE)
        return True
    except OSError:
        return False


def set_startup(enabled):
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, _startup_command())
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


# ── A second copy of the exe hands its text to the running one ────────────────
def send_to_running(text, wait=5.0):
    """True if another copy is running and took the text (it shows its window)."""
    end = time.monotonic() + wait
    hwnd = user32.FindWindowW(HIDDEN_CLASS, None)
    while not hwnd and time.monotonic() < end and _other_copy_running():
        time.sleep(0.1)  # it is still starting
        hwnd = user32.FindWindowW(HIDDEN_CLASS, None)
    if not hwnd:
        return False
    user32.AllowSetForegroundWindow(_pid_of(hwnd))  # so its window may come to the front
    data = json.dumps({"text": text}).encode("utf-8")
    buf = ctypes.create_string_buffer(data, len(data))
    cds = COPYDATASTRUCT(1, len(data), ctypes.cast(buf, ctypes.c_void_p))
    result = ctypes.c_size_t()
    ok = user32.SendMessageTimeoutW(hwnd, WM_COPYDATA, 0, ctypes.addressof(cds), 0, 5000,
                                    ctypes.byref(result))
    return bool(ok and result.value)


_mutex = None


def _other_copy_running():
    """Creates our single-instance mutex; True if another process already holds it."""
    global _mutex
    if _mutex is None:
        _mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        _other_copy_running.result = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    return _other_copy_running.result


def _icon_path():
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False)
                                           else __file__))
    for p in (os.path.join(here, "AppIcon.ico"),
              os.path.join(here, "..", "assets", "AppIcon.ico"),
              os.path.join(getattr(sys, "_MEIPASS", here), "AppIcon.ico")):
        if os.path.exists(p):
            return p
    return None


class Background:
    """Tray icon, Ctrl+Shift+Y, mouse hook and the floating button."""

    def __init__(self, to_window, popup_enabled=True):
        self.to_window = to_window          # queue read by the Tk window
        self.popup_enabled = popup_enabled  # "Pause Floating Popup" = False
        self.jobs = queue.Queue()           # for the worker thread
        self.hwnd = None
        self.popup = None
        self.popup_visible = False
        self.popup_rect = (0, 0, 0, 0)
        self.popup_text = ""
        self.popup_at = (0, 0)
        self.press = None                   # (x, y) of the last left-button press
        self.last_up = (0, 0, 0)            # (x, y, time) of the last left-button release
        self.clicks = 0                     # counts presses: a newer press cancels a check
        self.hook = None
        self.hotkey_ok = True
        self.icon = None
        self.ready = threading.Event()
        self._procs = []                    # keep ctypes callbacks alive

    startup_enabled = staticmethod(startup_enabled)
    set_startup = staticmethod(set_startup)

    # ── Threads ───────────────────────────────────────────────────────────────
    def start(self):
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self._win32_thread, daemon=True).start()
        self.ready.wait(10)

    def stop(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def set_popup_enabled(self, enabled):
        self.popup_enabled = bool(enabled)
        if not enabled and self.hwnd:
            user32.PostMessageW(self.hwnd, WM_HIDE_POPUP, 0, 0)

    def balloon(self, title, text):
        self.balloon_msg = (title, text)
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_BALLOON, 0, 0)

    # ── Worker: UI Automation (may take a moment; never on the Win32 thread) ──
    def _worker(self):
        while True:
            job = self.jobs.get()
            try:
                if job[0] == "check":   # mouse released after selecting: any text?
                    _, seq, x, y = job
                    time.sleep(0.08)    # let the program finish the selection
                    if seq != self.clicks or not self.popup_enabled:
                        continue
                    if _pid_of(user32.GetForegroundWindow()) == os.getpid():
                        continue        # selecting in our own window
                    text = uia.selected_text()
                    if text.strip() and seq == self.clicks:
                        self.popup_text, self.popup_at = text, (x, y)
                        user32.PostMessageW(self.hwnd, WM_SHOW_POPUP, seq, 0)
                elif job[0] == "read":  # floating button clicked
                    text = uia.selected_text() or self.popup_text
                    self.to_window.put(("open", text, True))
                elif job[0] == "hotkey":
                    hotkey._wait_keys_released()
                    text = uia.selected_text()
                    if not text.strip():  # program without UI Automation text: copy instead
                        text = hotkey.copy_selection()
                    self.to_window.put(("open", text, False))
            except Exception:
                pass

    # ── Win32 thread ──────────────────────────────────────────────────────────
    def _win32_thread(self):
        hinst = kernel32.GetModuleHandleW(None)
        self.taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")
        main_proc, popup_proc = WNDPROC(self._wndproc), WNDPROC(self._popup_proc)
        mouse_proc = HOOKPROC(self._mouse_hook)
        self._procs += [main_proc, popup_proc, mouse_proc]
        for name, proc, cursor in ((HIDDEN_CLASS, main_proc, None),
                                   (POPUP_CLASS, popup_proc, IDC_HAND)):
            wc = WNDCLASSEXW()
            wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
            wc.lpfnWndProc = proc
            wc.hInstance = hinst
            wc.lpszClassName = name
            if cursor:
                wc.hCursor = user32.LoadCursorW(None, W.LPVOID(cursor))
            user32.RegisterClassExW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, HIDDEN_CLASS, APP_NAME, 0, 0, 0, 0, 0,
                                           None, None, hinst, None)
        self.popup = user32.CreateWindowExW(
            WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE, POPUP_CLASS, APP_NAME,
            WS_POPUP, 0, 0, 10, 10, None, None, hinst, None)
        self._make_font()
        self._add_tray_icon()
        self.hotkey_ok = bool(user32.RegisterHotKey(
            self.hwnd, HOTKEY_ID, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_Y))
        self.mouse_proc, self.hinst = mouse_proc, hinst
        self.hook = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_proc, hinst, 0)
        user32.SetTimer(self.hwnd, 1, HOOK_TIMER_MS, None)
        self.ready.set()
        msg = W.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        if self.hook:
            user32.UnhookWindowsHookEx(self.hook)

    def _make_font(self):
        hdc = user32.GetDC(None)
        self.dpi = gdi32.GetDeviceCaps(hdc, 88) or 96  # LOGPIXELSX
        user32.ReleaseDC(None, hdc)
        self.font = gdi32.CreateFontW(-round(9.5 * self.dpi / 72), 0, 0, 0, 600, 0, 0, 0,
                                      1, 0, 0, 5, 0, "Segoe UI")  # DEFAULT_CHARSET, CLEARTYPE

    def _notify_data(self):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        return nid

    def _add_tray_icon(self):
        path = _icon_path()
        if path and not self.icon:
            self.icon = user32.LoadImageW(None, path, IMAGE_ICON,
                                          user32.GetSystemMetrics(SM_CXSMICON),
                                          user32.GetSystemMetrics(SM_CYSMICON), LR_LOADFROMFILE)
        nid = self._notify_data()
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self.icon
        nid.szTip = APP_NAME + " (Ctrl+Shift+Y)"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def _show_menu(self):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING | MF_DEFAULT, CMD_SETTINGS, "Settings")
        user32.AppendMenuW(menu, MF_STRING | (0 if self.popup_enabled else MF_CHECKED),
                           CMD_PAUSE, "Pause Floating Popup")
        user32.AppendMenuW(menu, MF_STRING, CMD_HELP, "Help")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, CMD_EXIT, "Exit")
        pt = W.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)  # so the menu closes when clicking elsewhere
        cmd = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD, pt.x, pt.y, 0,
                                    self.hwnd, None)
        user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)
        self._command(cmd)

    def _command(self, cmd):
        if cmd == CMD_SETTINGS:
            self.to_window.put(("show",))
        elif cmd == CMD_PAUSE:
            self.set_popup_enabled(not self.popup_enabled)
            self.to_window.put(("popup", self.popup_enabled))
        elif cmd == CMD_HELP:
            self.to_window.put(("help",))
        elif cmd == CMD_EXIT:
            self.to_window.put(("exit",))

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_TRAY:
                if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    self.to_window.put(("show",))
                elif lparam == WM_RBUTTONUP:
                    self._show_menu()
                return 0
            if msg == WM_COMMAND:  # also sent by the automated tests
                self._command(wparam & 0xFFFF)
                return 0
            if msg == WM_HOTKEY:
                if wparam == HOTKEY_ID:
                    self._hide_popup()
                    self.jobs.put(("hotkey",))
                elif wparam == ESC_ID:
                    self._hide_popup()
                return 0
            if msg == WM_COPYDATA:
                cds = COPYDATASTRUCT.from_address(lparam)
                data = json.loads(ctypes.string_at(cds.lpData, cds.cbData).decode("utf-8"))
                text = data.get("text", "")
                self.to_window.put(("open", text, False) if text.strip() else ("show",))
                return 1
            if msg == WM_SHOW_POPUP:
                if wparam == self.clicks and self.popup_enabled:
                    self._show_popup(*self.popup_at)
                return 0
            if msg == WM_HIDE_POPUP:
                self._hide_popup()
                return 0
            if msg == WM_BALLOON:
                nid = self._notify_data()
                nid.uFlags = NIF_INFO
                nid.szInfoTitle, nid.szInfo = self.balloon_msg
                nid.dwInfoFlags = NIIF_INFO
                shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
                return 0
            if msg == WM_TIMER:
                # Windows silently drops a mouse hook that once answered too slowly
                # (e.g. the PC was very busy): install it again now and then.
                old = self.hook
                self.hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self.mouse_proc,
                                                     self.hinst, 0)
                if old:
                    user32.UnhookWindowsHookEx(old)
                return 0
            if msg == self.taskbar_created:  # Explorer restarted: icon again
                self._add_tray_icon()
                return 0
            if msg == WM_CLOSE:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._notify_data()))
                user32.UnregisterHotKey(self.hwnd, HOTKEY_ID)
                user32.DestroyWindow(self.popup)
                user32.DestroyWindow(hwnd)
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # ── Mouse: a press, drag and release (or a double-click) may select text ──
    def _mouse_hook(self, code, wparam, lparam):
        try:
            if code == 0:
                info = MSLLHOOKSTRUCT.from_address(lparam)
                x, y = info.pt.x, info.pt.y
                if wparam in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN):
                    if self.popup_visible and not self._in_popup(x, y):
                        user32.PostMessageW(self.hwnd, WM_HIDE_POPUP, 0, 0)
                    if wparam == WM_LBUTTONDOWN:
                        self.clicks += 1
                        self.press = (x, y)
                elif wparam == WM_LBUTTONUP and self.press:
                    px, py = self.press
                    self.press = None
                    dragged = (abs(x - px) > user32.GetSystemMetrics(SM_CXDRAG) or
                               abs(y - py) > user32.GetSystemMetrics(SM_CYDRAG))
                    lx, ly, lt = self.last_up
                    double = (info.time - lt <= user32.GetDoubleClickTime() and
                              abs(x - lx) < 6 and abs(y - ly) < 6)
                    self.last_up = (x, y, info.time)
                    if (dragged or double) and self.popup_enabled and not self._in_popup(x, y):
                        self.jobs.put(("check", self.clicks, x, y))
        except Exception:
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    # ── The floating button ───────────────────────────────────────────────────
    def _in_popup(self, x, y):
        left, top, right, bottom = self.popup_rect
        return self.popup_visible and left <= x < right and top <= y < bottom

    def _show_popup(self, x, y):
        scale = self.dpi / 96
        w, h = round(104 * scale), round(28 * scale)
        x, y = x + round(10 * scale), y + round(14 * scale)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(user32.MonitorFromPoint(W.POINT(x, y),
                                                          MONITOR_DEFAULTTONEAREST),
                                  ctypes.byref(mi)):
            work = mi.rcWork
            x = max(work.left, min(x, work.right - w))
            if y + h > work.bottom:
                y = y - h - round(28 * scale)  # above the cursor instead
            y = max(work.top, y)
        self.popup_rect = (x, y, x + w, y + h)
        user32.SetWindowPos(self.popup, HWND_TOPMOST, x, y, w, h,
                            SWP_NOACTIVATE | SWP_SHOWWINDOW)
        self.popup_visible = True
        # Esc hides the button (a hotkey only while it is shown: no keyboard hook)
        user32.RegisterHotKey(self.hwnd, ESC_ID, 0, VK_ESCAPE)

    def _hide_popup(self):
        if self.popup_visible:
            self.popup_visible = False
            user32.ShowWindow(self.popup, SW_HIDE)
            user32.UnregisterHotKey(self.hwnd, ESC_ID)

    def _popup_proc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_MOUSEACTIVATE:
                return MA_NOACTIVATE  # keep the selection's program focused
            if msg == WM_LBUTTONUP:
                self._hide_popup()
                self.jobs.put(("read",))
                return 0
            if msg == WM_PAINT:
                ps = PAINTSTRUCT()
                hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
                rc = W.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rc))
                bg = gdi32.CreateSolidBrush(_rgb(0x1F, 0x5F, 0xA8))
                border = gdi32.CreateSolidBrush(_rgb(0x14, 0x3F, 0x70))
                user32.FillRect(hdc, ctypes.byref(rc), bg)
                user32.FrameRect(hdc, ctypes.byref(rc), border)
                old = gdi32.SelectObject(hdc, self.font)
                gdi32.SetBkMode(hdc, TRANSPARENT)
                gdi32.SetTextColor(hdc, _rgb(255, 255, 255))
                user32.DrawTextW(hdc, POPUP_LABEL, -1, ctypes.byref(rc),
                                 DT_CENTER | DT_VCENTER | DT_SINGLELINE)
                gdi32.SelectObject(hdc, old)
                gdi32.DeleteObject(bg)
                gdi32.DeleteObject(border)
                user32.EndPaint(hwnd, ctypes.byref(ps))
                return 0
        except Exception:
            pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def main(show=False, text=""):
    """Run in the background. show: open the window at once (with text)."""
    if _other_copy_running():
        if show:
            send_to_running(text)
        return
    try:  # before any window, so Windows does not blur them
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    import pali_tts
    pali_tts.run_with_tray(Background, show, text)
