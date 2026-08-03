"""实验：把应用窗口挂到 SHELLDLL_DefView（图标层宿主）下"""
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
HWND_TOP = 0
GWL_STYLE = -16


def cls(h):
    b = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(h, b, 128)
    return b.value


def rect(h):
    r = wt.RECT()
    u.GetWindowRect(wt.HWND(h), ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


# 找应用主窗口
app_hwnd = 0


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def find_app(hwnd, lparam):
    global app_hwnd
    if cls(hwnd) == "Qt6111QWindowToolSaveBits":
        r = wt.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        if u.IsWindowVisible(hwnd) and (r.right - r.left) > 300:
            app_hwnd = hwnd
    return True


u.EnumWindows(find_app, 0)
if not app_hwnd:
    print("未找到应用主窗口")
    sys.exit(1)

# 找 DefView
defview = 0


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def find_dv(hwnd, lparam):
    global defview
    if cls(hwnd) == "SHELLDLL_DefView":
        defview = hwnd
    return True


u.EnumWindows(find_dv, 0)
print(f"应用窗口={app_hwnd} rect={rect(app_hwnd)} DefView={defview} rect={rect(defview) if defview else '?'}")

# 当前（嵌入 Progman 破坏后）状态
print(f"当前: rect={rect(app_hwnd)} visible={u.IsWindowVisible(app_hwnd)}")

# 挂到 DefView 下
u.SetParent(wt.HWND(app_hwnd), wt.HWND(defview))
u.SetWindowLongPtrW(wt.HWND(app_hwnd), GWL_STYLE,
                    u.GetWindowLongPtrW(wt.HWND(app_hwnd), GWL_STYLE) | WS_CHILD)
u.SetWindowPos(wt.HWND(app_hwnd), wt.HWND(HWND_TOP), 0, 0, 0, 0,
               0x0001 | 0x0002 | 0x0010)  # NOSIZE|NOMOVE|NOACTIVATE
time.sleep(1)
r = rect(app_hwnd)
print(f"挂 DefView 后: rect={r} visible={u.IsWindowVisible(app_hwnd)}")
print(f"父={hex(u.GetParent(app_hwnd))} ({cls(u.GetParent(app_hwnd))})")

# DefView 内子窗口 Z 序
children = []
c = u.GetWindow(wt.HWND(defview), 5)
while c:
    children.append((hex(c), cls(c)))
    c = u.GetWindow(c, 2)
print("DefView 子窗口 Z 序:", children)
