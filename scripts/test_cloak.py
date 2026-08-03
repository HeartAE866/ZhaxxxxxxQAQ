"""验证 Win+D 的 DWM cloak 机制：置底 vs 置顶 下挂件是否被 cloak（合成隐藏）。
DWMWA_CLOAKED=14。自动化（无需人工看屏）。"""
import ctypes
import sys
import time
from ctypes import wintypes

u = ctypes.windll.user32
dwm = ctypes.windll.dwmapi
dwm.DwmGetWindowAttribute.restype = ctypes.c_long
dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, ctypes.c_uint32,
                                      ctypes.c_void_p, ctypes.c_uint32]
KEYEVENTF_KEYUP = 0x0002


def wind():
    u.keybd_event(0x5B, 0, 0, 0)
    u.keybd_event(0x44, 0, 0, 0)
    u.keybd_event(0x44, 0, KEYEVENTF_KEYUP, 0)
    u.keybd_event(0x5B, 0, KEYEVENTF_KEYUP, 0)


def find_app():
    hwnds = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(64)
        u.GetClassNameW(h, buf, 64)
        if buf.value == "Qt6111QWindowToolSaveBits" and u.IsWindowVisible(h):
            r = wintypes.RECT()
            u.GetWindowRect(h, ctypes.byref(r))
            if r.right - r.left > 100:
                hwnds.append(int(h))
        return True

    u.EnumWindows(cb, 0)
    return hwnds[0] if hwnds else 0


def cloak(h):
    v = ctypes.c_int()
    dwm.DwmGetWindowAttribute(wintypes.HWND(h), 14, ctypes.byref(v),
                              ctypes.sizeof(v))
    return bool(v.value)


def sample(tag, h, n=5):
    vals = []
    for _ in range(n):
        vals.append(cloak(h))
        time.sleep(0.3)
    print(f"{tag}: cloak={vals}")


def main():
    h = find_app()
    if not h:
        print("FAIL: 未找到挂件")
        return 1
    progman = u.FindWindowW("Progman", None)
    print(f"挂件 hwnd={h} 初始 cloak={cloak(h)}")

    print("--- 置底(当前) + Win+D ---")
    sample("Win+D 前", h, 2)
    wind()
    sample("Win+D 后", h, 5)
    wind()  # 恢复
    time.sleep(1)
    print(f"恢复后 cloak={cloak(h)}")

    print("--- 置顶 + Win+D ---")
    u.SetWindowPos(wintypes.HWND(h), wintypes.HWND(-1), 0, 0, 0, 0,
                   0x0001 | 0x0002 | 0x0010)  # HWND_TOPMOST
    time.sleep(0.5)
    print(f"置顶后 cloak={cloak(h)}")
    wind()
    sample("置顶+Win+D 后", h, 5)
    wind()  # 恢复
    time.sleep(1)
    print(f"恢复后 cloak={cloak(h)} (topmost)")
    # 还原置底
    if progman:
        prev = u.GetWindow(wintypes.HWND(progman), 3)
        u.SetWindowPos(wintypes.HWND(h), wintypes.HWND(int(prev) if prev else 0),
                       0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
    return 0


if __name__ == "__main__":
    sys.exit(main())
