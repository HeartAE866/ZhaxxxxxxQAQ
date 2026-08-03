"""实验：手动把 ZhaxxxxxxQAQ 窗口嵌入 Progman 并压 DefView，验证修复方案"""
import ctypes
import sys
from ctypes import wintypes as wt

sys.path.insert(0, r"C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ\app")
import widgets

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.IsWindowVisible.restype = wt.BOOL
u.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]

# 找到应用窗口
target_hwnd = None


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def cb(hwnd, lparam):
    global target_hwnd
    b = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(hwnd, b, 128)
    if b.value == "Qt6111QWindowToolSaveBits":
        r = wt.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        if u.IsWindowVisible(hwnd) and (r.right - r.left) > 300:
            target_hwnd = hwnd
    return True


u.EnumWindows(cb, 0)
if not target_hwnd:
    print("未找到应用窗口（应用未运行？）")
    sys.exit(1)

progman = u.FindWindowW("Progman", None)
defview = widgets._child_named(progman, "SHELLDLL_DefView")
print(f"应用窗口={target_hwnd} Progman={progman} DefView={defview}")

r = wt.RECT()
u.GetWindowRect(wt.HWND(target_hwnd), ctypes.byref(r))
print(f"嵌入前: rect=({r.left},{r.top},{r.right},{r.bottom}) visible={u.IsWindowVisible(wt.HWND(target_hwnd))}")

# 1) 模拟 embed_to_desktop：SetParent 到 Progman
hwnd = wt.HWND(target_hwnd)
u.SetParent(hwnd, wt.HWND(progman))
u.SetWindowPos(hwnd, wt.HWND(0), 0, 0, 0, 0,
               0x0001 | 0x0002 | 0x0010)  # NOSIZE|NOMOVE|NOACTIVATE
# 2) 压 DefView 到窗口之下
if defview:
    u.SetWindowPos(wt.HWND(defview), hwnd, 0, 0, 0, 0,
                   0x0001 | 0x0002 | 0x0010)
ctypes.windll.user32.SetWindowLongPtrW.restype = ctypes.c_longlong
style = u.GetWindowLongPtrW(hwnd, -16)
if not style & 0x40000000:
    u.SetWindowLongPtrW(hwnd, -16, style | 0x40000000)  # WS_CHILD

u.GetWindowRect(hwnd, ctypes.byref(r))
print(f"嵌入后: rect=({r.left},{r.top},{r.right},{r.bottom}) visible={u.IsWindowVisible(hwnd)}")
parent = u.GetParent(hwnd)
b = ctypes.create_unicode_buffer(128)
u.GetClassNameW(parent, b, 128)
print(f"父窗口={parent} ({b.value})")

# 3) Z 序检查：窗口是否在 DefView 之上
def z_below(a, b2):
    """a 是否在 b2 之下"""
    w = u.GetWindow(wt.HWND(0), 5)  # GW_HWNDFIRST? 用 GetTopWindow 层次
    return None

u.GetWindow.argtypes = [wt.HWND, ctypes.c_int]
u.GetWindow.restype = wt.HWND
# 枚举 Progman 子窗口顺序
children = []
c = u.GetWindow(wt.HWND(progman), 5)  # GW_CHILD
while c:
    cb2 = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(c, cb2, 128)
    children.append((c, cb2.value))
    c = u.GetWindow(c, 2)  # GW_HWNDNEXT
print("Progman 子窗口 Z 序:", [(hex(h), n) for h, n in children])
