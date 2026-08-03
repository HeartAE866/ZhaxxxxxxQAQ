"""诊断 Explorer 重启后的桌面结构"""
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


found = []


@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def cb(h, lparam):
    c = cls(h)
    if c in ("Progman", "WorkerW", "SHELLDLL_DefView"):
        found.append(h)
    return True


u.EnumWindows(cb, 0)
for h in found:
    chain = []
    cur = h
    for _ in range(6):
        chain.append(cls(cur))
        p = u.GetAncestor(cur, 1)
        if not p or p == cur:
            break
        cur = p
    r = wt.RECT()
    u.GetWindowRect(wt.HWND(h), ctypes.byref(r))
    vis = u.IsWindowVisible(h)
    print(f"{cls(h)} {h} rect=({r.left},{r.top},{r.right},{r.bottom}) visible={vis} parentchain={'<'.join(chain)}")
