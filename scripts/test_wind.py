"""测试：嵌入后按 Win+D（显示桌面），应用窗口应保留"""
import ctypes
import sys
import time
from ctypes import wintypes as wt

u = ctypes.windll.user32

# 模拟 Win+D
VK_LWIN = 0x5B
KEYEVENTF_KEYUP = 0x0002


def key_press(vk, scan=0):
    u.keybd_event(vk, scan, 0, 0)
    time.sleep(0.05)
    u.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)


def app_windows():
    """返回主窗口（可见且宽>300）"""
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        b = ctypes.create_unicode_buffer(128)
        u.GetClassNameW(hwnd, b, 128)
        if b.value == "Qt6111QWindowToolSaveBits":
            r = wt.RECT()
            u.GetWindowRect(hwnd, ctypes.byref(r))
            found.append((hwnd, (r.left, r.top, r.right, r.bottom),
                          u.IsWindowVisible(hwnd)))
        return True

    u.EnumWindows(cb, 0)
    return found


u.keybd_event(VK_LWIN, 0, 0, 0)
u.keybd_event(ord("D"), 0, 0, 0)
u.keybd_event(ord("D"), 0, KEYEVENTF_KEYUP, 0)
u.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
time.sleep(1.5)

wins = app_windows()
main_visible = [w for w in wins if w[2] and (w[1][2] - w[1][0]) > 300]
print("Win+D 后所有窗口:", wins)
print("主窗口（宽>300 可见）:", main_visible)
if main_visible:
    print("PASS: Win+D 显示桌面后应用窗口保留在桌面")
else:
    print("FAIL: Win+D 后应用窗口消失")

# 再按一次 Win+D 恢复桌面
u.keybd_event(VK_LWIN, 0, 0, 0)
u.keybd_event(ord("D"), 0, 0, 0)
u.keybd_event(ord("D"), 0, KEYEVENTF_KEYUP, 0)
u.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
time.sleep(1.0)
print("恢复桌面后窗口:", app_windows())
