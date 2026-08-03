"""分步实验：SetParent 的每一步对 Qt 窗口的影响"""
import ctypes
import sys
import time
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.IsWindowVisible.restype = wt.BOOL
u.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
u.GetAncestor.restype = wt.HWND

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
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        if cls(hwnd) == "Qt6111QWindowToolSaveBits":
            r = wt.RECT()
            u.GetWindowRect(hwnd, ctypes.byref(r))
            found.append((hwnd, (r.left, r.top, r.right, r.bottom),
                          u.IsWindowVisible(hwnd)))
        return True

    u.EnumWindows(cb, 0)
    return [f for f in found if f[2] and (f[1][2] - f[1][0]) > 300]


wins = find_app()
if not wins:
    print("未找到应用主窗口")
    sys.exit(1)
hwnd = wins[0][0]
print(f"应用窗口={hwnd} rect={wins[0][1]} visible={wins[0][2]}")

# 找 DefView
defview = 0


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def find_dv(h, l):
    global defview
    if cls(h) == "SHELLDLL_DefView":
        defview = h
    return True


u.EnumWindows(find_dv, 0)

# 步骤 1: SetParent 到 DefView
u.SetParent(wt.HWND(hwnd), wt.HWND(defview))
time.sleep(0.5)
print(f"[1] SetParent 后: rect={rect(hwnd)} visible={u.IsWindowVisible(hwnd)} parent={cls(u.GetParent(hwnd))}")

# 步骤 2: 加 WS_CHILD
style = u.GetWindowLongPtrW(wt.HWND(hwnd), GWL_STYLE)
u.SetWindowLongPtrW(wt.HWND(hwnd), GWL_STYLE, style | WS_CHILD)
time.sleep(0.5)
print(f"[2] +WS_CHILD 后: rect={rect(hwnd)} visible={u.IsWindowVisible(hwnd)}")

# 步骤 3: SetWindowPos TOP
u.SetWindowPos(wt.HWND(hwnd), wt.HWND(0), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
time.sleep(0.5)
print(f"[3] SetWindowPos 后: rect={rect(hwnd)} visible={u.IsWindowVisible(hwnd)}")

# 步骤 4: 显式显示
u.ShowWindow(wt.HWND(hwnd), 5)  # SW_SHOW
time.sleep(0.5)
print(f"[4] ShowWindow 后: rect={rect(hwnd)} visible={u.IsWindowVisible(hwnd)}")

# 步骤 5: Qt 是否响应（等 2 秒看 Qt 是否干预）
time.sleep(2)
print(f"[5] 2秒后: rect={rect(hwnd)} visible={u.IsWindowVisible(hwnd)}")
