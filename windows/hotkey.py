"""Clipboard helpers: Ctrl+Shift+Y uses copy_selection() only when UI Automation
(uia.py) cannot read the selection. main() is the v2.2–v2.4 helper (now tray.py).

Runs in the background (started at login by a Startup-folder shortcut).
Uses only Windows' own user32/kernel32 through ctypes: no AutoHotkey needed.
"""
import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x4000
WM_HOTKEY = 0x0312
VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN = 0x11, 0x12, 0x10, 0x5B, 0x5C
VK_Y, VK_C = 0x59, 0x43
KEYEVENTF_KEYUP = 0x0002
CF_UNICODETEXT = 13
ERROR_ALREADY_EXISTS = 183
HOTKEY_ID = 1
HOTKEY_NAME = "Ctrl+Shift+Y"

user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.CreateMutexW.restype = wintypes.HANDLE
user32.GetAsyncKeyState.restype = ctypes.c_short


def _key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def _wait_keys_released(timeout=2.0):
    """Ctrl+C sent while Shift is still held would become Ctrl+Shift+C."""
    end = time.monotonic() + timeout
    keys = (VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN, VK_Y)
    while time.monotonic() < end and any(_key_down(k) for k in keys):
        time.sleep(0.02)


def _send_ctrl_c():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def _read_clipboard():
    for _ in range(10):  # another program may have it open for a moment
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def copy_selection():
    """Selected text of the active program ('' if nothing is selected)."""
    _wait_keys_released()
    before = user32.GetClipboardSequenceNumber()
    _send_ctrl_c()
    end = time.monotonic() + 1.0
    while time.monotonic() < end:
        if user32.GetClipboardSequenceNumber() != before:
            time.sleep(0.05)  # let the program finish writing
            return _read_clipboard().strip()
        time.sleep(0.02)
    return ""


def open_window(text):
    if getattr(sys, "frozen", False):
        cmd = [sys.executable]
    else:  # running from source: python windows/hotkey.py --hotkey
        here = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, os.path.join(here, "..", "pali_tts.py")]
    if text:
        fd, path = tempfile.mkstemp(prefix="pali_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        cmd += ["--input-file", path]  # pali_tts deletes the file after reading it
    subprocess.Popen(cmd, close_fds=True)


def _message(text):
    user32.MessageBoxW(None, text, "Read Pāli Aloud", 0x40)  # MB_ICONINFORMATION


def main():
    # Only one helper at a time (login + installer may both start it)
    kernel32.CreateMutexW(None, False, "Local\\PaliTTS.ReadPaliAloud.Hotkey")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return
    if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_Y):
        _message(HOTKEY_NAME + " is already used by another program, so the Read Pāli Aloud "
                 "shortcut is off.\nYou can still open Read Pāli Aloud from the Start menu.")
        return
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            try:
                open_window(copy_selection())
            except Exception:
                pass
    user32.UnregisterHotKey(None, HOTKEY_ID)


if __name__ == "__main__":
    main()
