"""关联窗口与进程"""
import ctypes
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
u.GetWindowThreadProcessId.restype = wt.DWORD

results = []


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def enum_cb(hwnd, lparam):
    cls = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(hwnd, cls, 128)
    if cls.value == "Qt6111QWindowToolSaveBits":
        pid = wt.DWORD()
        u.GetWindowThreadProcessId(wt.HWND(hwnd), ctypes.byref(pid))
        r = wt.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        results.append((hwnd, pid.value, (r.left, r.top, r.right, r.bottom),
                        u.IsWindowVisible(wt.HWND(hwnd))))
    return True


u.EnumWindows(enum_cb, 0)
for r in results:
    print(f"hwnd={r[0]} pid={r[1]} rect={r[2]} visible={r[3]}")
