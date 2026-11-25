"""
Windows OS File Drag-and-Drop Helper
===================================
Lightweight ctypes WM_DROPFILES hook for Tkinter/CustomTkinter windows on Windows,
requiring no third-party packages. Gracefully no-ops on non-Windows platforms.
"""

from __future__ import annotations

import os
import sys
from typing import Callable


def filter_dropped_files(paths: list[str]) -> list[str]:
    """Return deduplicated existing file paths in original drop order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in paths:
        if not raw:
            continue
        norm = os.path.abspath(raw)
        if norm not in seen and os.path.isfile(norm):
            seen.add(norm)
            result.append(norm)
    return result


def enable_win_file_drop(window, on_files_dropped: Callable[[list[str]], None]) -> bool:
    """
    Enable native Windows Explorer file drag-and-drop onto a Tk/CTk window.
    Returns True if the hook was installed, False otherwise.
    """
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32

        WM_DROPFILES = 0x0233
        GWLP_WNDPROC = -4

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            LONG_PTR = ctypes.c_longlong
            SetWindowLongPtr = user32.SetWindowLongPtrW
        else:
            LONG_PTR = ctypes.c_long
            SetWindowLongPtr = user32.SetWindowLongW

        WNDPROC = ctypes.WINFUNCTYPE(
            LONG_PTR,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, WNDPROC]
        SetWindowLongPtr.restype = LONG_PTR

        user32.CallWindowProcW.argtypes = [
            LONG_PTR,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallWindowProcW.restype = LONG_PTR

        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        shell32.DragQueryFileW.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
            wintypes.LPWSTR,
            wintypes.UINT,
        ]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [wintypes.HANDLE]

        hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
        shell32.DragAcceptFiles(hwnd, True)

        prev_proc_holder = [0]

        def _wnd_proc(h, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                hdrop = wparam
                count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                dropped: list[str] = []
                for idx in range(count):
                    length = shell32.DragQueryFileW(hdrop, idx, None, 0)
                    buf = ctypes.create_unicode_buffer(length + 1)
                    shell32.DragQueryFileW(hdrop, idx, buf, length + 1)
                    dropped.append(buf.value)
                shell32.DragFinish(hdrop)
                valid = filter_dropped_files(dropped)
                if valid:
                    window.after(0, lambda files=valid: on_files_dropped(files))
                return 0
            return user32.CallWindowProcW(prev_proc_holder[0], h, msg, wparam, lparam)

        new_proc = WNDPROC(_wnd_proc)
        prev_proc = SetWindowLongPtr(hwnd, GWLP_WNDPROC, new_proc)
        prev_proc_holder[0] = prev_proc

        # Keep strong references on window so GC never frees the callback
        window._win_dnd_proc = new_proc
        window._win_dnd_prev_proc = prev_proc
        return True
    except Exception:
        return False
