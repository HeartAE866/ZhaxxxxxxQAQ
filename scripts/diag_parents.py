"""精确定位 SHELLDLL_DefView 及其父链、所有 WorkerW 的真实层级"""
import ctypes
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.IsWindowVisible.restype = wt.BOOL
u.GetAncestor.restype = wt.HWND


def cls(h):
    b = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(h, b, 128)
    return b.value


def rect(h):
    r = wt.RECT()
    u.GetWindowRect(wt.HWND(h), ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


found = []


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def cb(hwnd, lparam):
    c = cls(hwnd)
    if c in ("Progman", "WorkerW") or c == "SHELLDLL_DefView":
        found.append(hwnd)
    return True


u.EnumWindows(cb, 0)

for h in found:
    c = cls(h)
    chain = []
    cur = h
    for _ in range(8):
        chain.append(f"{cls(cur)}({cur})")
        p = u.GetAncestor(cur, 1)  # GA_PARENT
        if not p or p == cur:
            break
        cur = p
    r = rect(h)
    print(f"{c} {h} rect={r} visible={u.IsWindowVisible(h)} 父链: {' <- '.join(chain)}")
