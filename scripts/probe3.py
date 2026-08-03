import ctypes
from ctypes import wintypes as wt
u = ctypes.windll.user32
u.WindowFromPoint.restype = ctypes.c_void_p
u.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
u.GetWindowRect.restype = ctypes.c_bool
for (x, y) in [(1600, 100), (1600, 200), (1505, 45), (1830, 45), (1600, 300)]:
    h = u.WindowFromPoint(wt.POINT(x, y))
    r = wt.RECT()
    if h:
        u.GetWindowRect(wt.HWND(h), ctypes.byref(r))
        print(f'({x},{y}) -> hwnd={h} rect=({r.left},{r.top},{r.right},{r.bottom})')
    else:
        print(f'({x},{y}) -> NULL')
