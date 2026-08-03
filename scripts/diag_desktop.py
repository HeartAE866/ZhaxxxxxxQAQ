"""诊断本机桌面层结构：Progman / 各 WorkerW / SHELLDLL_DefView 的可见性与尺寸"""
import ctypes
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.IsWindowVisible.restype = wt.BOOL
u.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]


def cls(hwnd):
    b = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(hwnd, b, 128)
    return b.value


def rect(hwnd):
    r = wt.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def has_defview(hwnd):
    def find(h):
        c = u.GetWindow(h, 5)  # GW_CHILD
        while c:
            if cls(c) == "SHELLDLL_DefView":
                return True
            if find(c):
                return True
            c = u.GetWindow(c, 2)  # GW_HWNDNEXT
        return False
    return find(hwnd)


results = []


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def cb(hwnd, lparam):
    c = cls(hwnd)
    if c in ("Progman", "WorkerW") or c == "SHELLDLL_DefView":
        results.append((hwnd, c, rect(hwnd), u.IsWindowVisible(hwnd), has_defview(hwnd)))
    return True


u.EnumWindows(cb, 0)
for hwnd, c, r, vis, dv in results:
    mark = " <== 图标层候选" if (c == "WorkerW" and vis and dv) else ""
    mark2 = " <== 可见无DefView(视频壁纸?)" if (c == "WorkerW" and vis and not dv) else ""
    print(f"hwnd={hwnd} {c} rect={r} visible={vis} hasDefView={dv}{mark}{mark2}")
