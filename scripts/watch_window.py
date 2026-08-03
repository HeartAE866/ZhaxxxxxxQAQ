"""监控：启动应用后每 2 秒枚举窗口状态，找出主窗口消失时机"""
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes as wt

u = ctypes.windll.user32
u.EnumWindows.restype = wt.BOOL
u.IsWindowVisible.restype = wt.BOOL
u.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]


def enum():
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        b = ctypes.create_unicode_buffer(128)
        u.GetClassNameW(hwnd, b, 128)
        if b.value == "Qt6111QWindowToolSaveBits":
            r = wt.RECT()
            u.GetWindowRect(hwnd, ctypes.byref(r))
            parent = u.GetAncestor(hwnd, 1)  # GA_PARENT
            pcls = ctypes.create_unicode_buffer(128)
            u.GetClassNameW(parent, pcls, 128)
            found.append((hwnd, (r.left, r.top, r.right, r.bottom),
                          u.IsWindowVisible(hwnd), hex(parent), pcls.value))
        return True

    u.EnumWindows(cb, 0)
    return found


# 启动应用（源码版）
subprocess.Popen(["C:\\Users\\张鑫\\Desktop\\ZhaxxxxxxQAQ\\venv\\Scripts\\pythonw.exe",
                  "C:\\Users\\张鑫\\Desktop\\ZhaxxxxxxQAQ\\app\\main.py"],
                 cwd="C:\\Users\\张鑫\\Desktop\\ZhaxxxxxxQAQ")

for i in range(20):
    time.sleep(2)
    wins = enum()
    mains = [w for w in wins if w[2] and (w[1][2] - w[1][0]) > 300]
    print(f"[{i*2+2}s] 窗口数={len(wins)} 主窗口={len(mains)}", end="")
    for w in mains:
        print(f" rect={w[1]} parent={w[3]}({w[4]})", end="")
    print()
