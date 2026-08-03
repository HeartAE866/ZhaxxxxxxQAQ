"""测试方案：窗口保持顶层 + 把壁纸(CEF)压到窗口之下 + Win+D 行为"""
import ctypes
import sys
import time
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.EnumChildWindows.restype = wt.BOOL
u.IsWindowVisible.restype = wt.BOOL
u.GetAncestor.restype = wt.HWND
u.IsWindow.restype = wt.BOOL

WS_CHILD = 0x40000000
GWL_STYLE = -16


def cls(h):
    b = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(h, b, 128)
    return b.value


def rect(h):
    r = wt.RECT()
    u.GetWindowRect(wt.HWND(h), ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def find_app():
    results = []

    def walk(hwnd):
        c = cls(hwnd)
        if c == "Qt6111QWindowToolSaveBits":
            r = wt.RECT()
            u.GetWindowRect(wt.HWND(hwnd), ctypes.byref(r))
            if (r.right - r.left) > 300:
                results.append(hwnd)
        children = []

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(h, l):
            children.append(h)
            return True

        u.EnumChildWindows(hwnd, cb, 0)
        for ch in children[:3]:
            walk(ch)

    tops = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb2(h, l):
        tops.append(h)
        return True

    u.EnumWindows(cb2, 0)
    for h in tops:
        walk(h)
    return results


def find_cef():
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, l):
        if cls(h) == "CEF-OSC-WIDGET" and u.IsWindowVisible(h):
            found.append(h)
        return True

    u.EnumWindows(cb, 0)
    return found


app_wins = find_app()
if not app_wins:
    print("未找到应用主窗口")
    sys.exit(1)
hwnd = app_wins[0]
print(f"应用窗口={hwnd} rect={rect(hwnd)} visible={u.IsWindowVisible(hwnd)}")

# 1) 恢复为顶层
u.SetParent(wt.HWND(hwnd), wt.HWND(0))
style = u.GetWindowLongPtrW(wt.HWND(hwnd), GWL_STYLE)
u.SetWindowLongPtrW(wt.HWND(hwnd), GWL_STYLE, style & ~WS_CHILD)
u.ShowWindow(wt.HWND(hwnd), 5)
time.sleep(1)
print(f"恢复顶层后: rect={rect(hwnd)} visible={u.IsWindowVisible(hwnd)} parent={cls(u.GetAncestor(hwnd,1))}")

# 2) 压壁纸到窗口之下（窗口在壁纸之上）
cef_wins = find_cef()
print("壁纸窗口:", cef_wins)
for c in cef_wins:
    u.SetWindowPos(wt.HWND(c), wt.HWND(hwnd), 0, 0, 0, 0,
                   0x0001 | 0x0002 | 0x0010)  # NOSIZE|NOMOVE|NOACTIVATE
time.sleep(1)
print("壁纸已压到窗口之下")

# 3) 窗口 Z 序置底（普通窗口之下、壁纸之上）：先 HWND_BOTTOM 再压壁纸
u.SetWindowPos(wt.HWND(hwnd), wt.HWND(1), 0, 0, 0, 0,  # HWND_BOTTOM=1
               0x0001 | 0x0002 | 0x0010)
for c in cef_wins:
    u.SetWindowPos(wt.HWND(c), wt.HWND(hwnd), 0, 0, 0, 0,
                   0x0001 | 0x0002 | 0x0010)
time.sleep(1)
print(f"窗口置底+压壁纸后: visible={u.IsWindowVisible(hwnd)} rect={rect(hwnd)}")

# 4) Win+D
u.keybd_event(0x5B, 0, 0, 0)
u.keybd_event(ord("D"), 0, 0, 0)
u.keybd_event(ord("D"), 0, 2, 0)
u.keybd_event(0x5B, 0, 2, 0)
time.sleep(1.5)
alive = u.IsWindow(wt.HWND(hwnd))
vis = u.IsWindowVisible(wt.HWND(hwnd))
r = rect(hwnd)
print(f"Win+D 后: IsWindow={alive} visible={vis} rect={r}")
if alive and vis and (r[2] - r[0]) > 300:
    print("PASS: Win+D 后窗口保留且可见")
else:
    print("FAIL: Win+D 后窗口隐藏/销毁")
