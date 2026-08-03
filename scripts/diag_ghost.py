"""幽灵窗口监控：轮询枚举所有顶层窗口，记录短暂出现/消失/几何突变的窗口。
用法：后台运行本脚本 → 用户做一次操作（添加/拖拽/设置）→ 观察 logs/ghost.log。
"""
import ctypes
import time
import datetime
from ctypes import wintypes

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetClassNameW = user32.GetClassNameW
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect
GetWindowLongPtrW = user32.GetWindowLongPtrW

LOG = r"C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ\logs\ghost.log"

def win_info(hwnd):
    try:
        if not IsWindowVisible(hwnd):
            return None
        n = GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        GetWindowTextW(hwnd, buf, n + 1)
        cls = ctypes.create_unicode_buffer(64)
        GetClassNameW(hwnd, cls, 64)
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        style = GetWindowLongPtrW(hwnd, -16)
        exstyle = GetWindowLongPtrW(hwnd, -20)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        parent = user32.GetParent(hwnd)
        return (hwnd, cls.value, buf.value, r.left, r.top, r.right - r.left,
                r.bottom - r.top, bool(style & 0x80000000) or bool(style & 0x40000000),
                bool(exstyle & 0x80), pid.value, parent,
                bool(style & 0x80000000),  # WS_POPUP
                bool(style & 0x40000000),  # WS_CHILD
                bool(exstyle & 0x10000000))  # WS_EX_TOOLWINDOW
    except Exception:
        return None

def snapshot():
    wins = {}

    def cb(hwnd, _):
        info = win_info(hwnd)
        if info:
            wins[hwnd] = info
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return wins

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%H:%M:%S.%f} {msg}\n")

def main():
    last = snapshot()
    log("=== ghost monitor started ===")
    while True:
        time.sleep(0.02)
        cur = snapshot()
        for hwnd, info in cur.items():
            if hwnd not in last:
                log(f"APPEAR hwnd={info[0]} cls={info[1]!r} title={info[2]!r} "
                    f"geo=({info[3]},{info[4]} {info[5]}x{info[6]}) "
                    f"tool={info[7]} layered={info[8]} pid={info[9]} "
                    f"parent={info[10]} popup={info[11]} child={info[12]} "
                    f"ex_tool={info[13]}")
            else:
                o = last[hwnd]
                if o[5] != info[5] or o[6] != info[6]:
                    log(f"RESIZE {info[0]} cls={info[1]!r} "
                        f"({o[5]}x{o[6]} -> {info[5]}x{info[6]})")
        for hwnd, info in last.items():
            if hwnd not in cur:
                log(f"DISAPPEAR {info[0]} cls={info[1]!r} title={info[2]!r} "
                    f"geo=({info[3]},{info[4]} {info[5]}x{info[6]})")
        last = cur

if __name__ == "__main__":
    main()
