"""Win+D 模拟测试：按下 Win+D → 检查应用窗口(WorkerW 子窗口)是否保留可见 → 恢复。
用法：python test_wind2.py <应用窗口类名>"""
import ctypes
import sys
import time
from ctypes import wintypes

u = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002
VK_LWIN = 0x5B


def win_d_press():
    u.keybd_event(VK_LWIN, 0, 0, 0)
    u.keybd_event(0x44, 0, 0, 0)  # D
    u.keybd_event(0x44, 0, KEYEVENTF_KEYUP, 0)
    u.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)


def find_app():
    """应用是顶层 Tool 窗口（置底+守护模式）。"""
    cls = "Qt6111QWindowToolSaveBits"
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(64)
        u.GetClassNameW(h, buf, 64)
        if buf.value == cls and u.IsWindowVisible(h):
            r = wintypes.RECT()
            u.GetWindowRect(h, ctypes.byref(r))
            if r.right - r.left > 100:   # 排除 Toast 等小窗口
                found.append(int(h))
        return True

    u.EnumWindows(cb, 0)
    return found


def rect_of(h):
    r = wintypes.RECT()
    u.GetWindowRect(wintypes.HWND(h), ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def alive(h):
    return bool(u.IsWindow(wintypes.HWND(h))) and bool(u.IsWindowVisible(wintypes.HWND(h)))


def main():
    apps = find_app()
    print(f"可见应用窗口: {apps}")
    if not apps:
        print("FAIL: 未找到可见应用窗口")
        return 1
    h = apps[0]
    before = rect_of(h)
    print(f"嵌入应用窗口 hwnd={h} geo={before}")

    print("--- 按下 Win+D ---")
    win_d_press()
    time.sleep(2.5)
    if alive(h):
        after = rect_of(h)
        print(f"OK: Win+D 后窗口仍在 geo={after} 可见={alive(h)}")
    else:
        print("FAIL: Win+D 后窗口消失！")
        return 1

    print("--- 再按 Win+D 恢复 ---")
    win_d_press()
    time.sleep(2.5)
    print(f"恢复后可见={alive(h)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
