"""Selected text of the active program through Windows UI Automation.

No Ctrl+C and no clipboard: programs that watch the clipboard (GoldenDict...)
are not triggered. Works where the program shares its text with UI Automation
(Edge, Chrome, Word, Notepad, most text boxes); returns "" elsewhere.
Call only from one background thread: the first call sets it up (COM, MTA).
"""
import ctypes
import sys
from ctypes import wintypes

_uia = None
UIA = None
MAX_PARENTS = 15  # how far up from the focused element to look for the text


def _client():
    global _uia, UIA
    if _uia is None:
        sys.coinit_flags = 0  # COINIT_MULTITHREADED for this thread (read by comtypes on import)
        import comtypes
        import comtypes.client
        comtypes.CoInitializeEx(0)
        try:
            from comtypes.gen import UIAutomationClient
        except ImportError:  # not generated at build time: make it now
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient
        UIA = UIAutomationClient
        _uia = comtypes.client.CreateObject(UIA.CUIAutomation, interface=UIA.IUIAutomation)
    return _uia


def _selection_of(element):
    """Selected text in this element, "" if none, None if it has no text pattern."""
    try:
        pattern = element.GetCurrentPattern(UIA.UIA_TextPatternId)
        if not pattern:
            return None
        ranges = pattern.QueryInterface(UIA.IUIAutomationTextPattern).GetSelection()
        if not ranges:
            return ""
        parts = [ranges.GetElement(i).GetText(-1) for i in range(ranges.Length)]
        return "\n".join(p for p in parts if p)
    except Exception:  # COMError, element gone...
        return None


def _cursor_element(uia):
    pt = wintypes.POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return None
    return uia.ElementFromPoint(UIA.tagPOINT(pt.x, pt.y))


def selected_text():
    """Text selected in the focused program ('' if none or not readable)."""
    try:
        uia = _client()
    except Exception:
        return ""
    walker = uia.RawViewWalker
    for get in (uia.GetFocusedElement, lambda: _cursor_element(uia)):
        try:
            element = get()
        except Exception:
            continue
        # The focused element may be a link or a paragraph inside the page or
        # document that holds the selection: look at its parents too.
        for _ in range(MAX_PARENTS):
            if not element:
                break
            text = _selection_of(element)
            if text and text.strip():
                return text
            try:
                element = walker.GetParentElement(element)
            except Exception:
                break
    return ""
