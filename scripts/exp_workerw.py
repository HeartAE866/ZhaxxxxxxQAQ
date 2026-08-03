"""实验：手动创建 WorkerW 承载图标层（DefView），验证窗口挂入后正常"""
import ctypes
import sys
import time
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.IsWindowVisible.restype = wt.BOOL
u.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
u.CreateWindowExW.restype = wt.HWND

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
HWND_TOP = 0


def cls(hwnd):
    b = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(hwnd, b, 128)
    return b.value


def rect(hwnd):
    r = wt.RECT()
    u.GetWindowRect(wt.HWND(hwnd), ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


progman = u.FindWindowW("Progman", None)
# 找 DefView（Progman 内部）
defview = 0


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def find_dv(hwnd, lparam):
    global defview
    if cls(hwnd) == "SHELLDLL_DefView":
        defview = hwnd
    return True


u.EnumChildWindows(progman, find_dv, 0)
print(f"Progman={progman} DefView={defview}")

# 创建 WorkerW（挂 Progman 下，全屏）
sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
workerw = u.CreateWindowExW(
    0, "WorkerW", "", WS_CHILD | WS_VISIBLE,
    0, 0, sw, sh, progman, None, None, None)
print(f"创建 WorkerW={workerw} rect={rect(workerw)} visible={u.IsWindowVisible(workerw)}")

# 把 DefView 移入 WorkerW
if defview:
    u.SetParent(wt.HWND(defview), wt.HWND(workerw))
    u.SetWindowPos(wt.HWND(defview), wt.HWND(HWND_TOP), 0, 0, 0, 0,
                   0x0001 | 0x0002 | 0x0010)  # NOSIZE|NOMOVE|NOACTIVATE
    print(f"DefView 移入 WorkerW，rect={rect(defview)}")

# 找应用窗口并挂入
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

print(f"应用窗口={app_hwnd} 嵌入前 rect={rect(app_hwnd)}")
u.SetParent(wt.HWND(app_hwnd), wt.HWND(workerw))
u.SetWindowPos(wt.HWND(app_hwnd), wt.HWND(HWND_TOP), 0, 0, 0, 0,
               0x0001 | 0x0002 | 0x0010)
u.SetWindowLongPtrW(wt.HWND(app_hwnd), -16,
                    u.GetWindowLongPtrW(wt.HWND(app_hwnd), -16) | WS_CHILD)
time.sleep(1)
print(f"嵌入后 rect={rect(app_hwnd)} visible={u.IsWindowVisible(app_hwnd)}")
print(f"父窗口={hex(u.GetParent(app_hwnd))} ({cls(u.GetParent(app_hwnd))})")

# WorkerW 子窗口 Z 序
children = []
c = u.GetWindow(wt.HWND(workerw), 5)
while c:
    children.append((hex(c), cls(c)))
    c = u.GetWindow(c, 2)
print("WorkerW 子窗口 Z 序:", children)
