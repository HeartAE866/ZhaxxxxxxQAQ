"""诊断：查找 ZhaxxxxxxQAQ 悬浮窗的句柄/父窗口/可见性/位置"""
import ctypes
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.GetWindowTextLengthW.restype = ctypes.c_int
u.IsWindowVisible.restype = wt.BOOL
u.GetAncestor.restype = wt.HWND
u.GetParent.restype = wt.HWND
u.GetParent.argtypes = [wt.HWND]

results = []


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def enum_cb(hwnd, lparam):
    cls = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(hwnd, cls, 128)
    if cls.value == "QWindowIcon" or "Zhax" in cls.value or "Qt" in cls.value:
        ln = u.GetWindowTextLengthW(hwnd)
        title = ctypes.create_unicode_buffer(ln + 1)
        u.GetWindowTextW(hwnd, title, ln + 1)
        if "Zhax" in title.value or cls.value == "QWindowIcon":
            r = wt.RECT()
            u.GetWindowRect(hwnd, ctypes.byref(r))
            parent = u.GetParent(wt.HWND(hwnd))
            pcls = ctypes.create_unicode_buffer(128)
            u.GetClassNameW(parent, pcls, 128)
            results.append((hwnd, title.value, cls.value,
                            (r.left, r.top, r.right, r.bottom),
                            u.IsWindowVisible(wt.HWND(hwnd)), parent, pcls.value))
    return True


u.EnumWindows(enum_cb, 0)
for r in results:
    print(f"hwnd={r[0]} title=[{r[1]}] cls={r[2]} rect={r[3]} visible={r[4]} parent={r[5]}({r[6]})")
if not results:
    print("未找到窗口")
