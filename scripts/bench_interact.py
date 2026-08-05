# -*- coding: utf-8 -*-
"""操作模拟对比：对 1.2.1 与优化版同时施加相同操作序列，对比 CPU/内存增量。
通过 hotkey 模拟或直接调用 UI 不可行（跨进程），改为：
- 用 Win32 发送 WM_HOTKEY？不可靠。
- 更实际：直接对两个进程采样 CPU/内存，在操作期间统计（窗口已被 bench 启动）。
这里通过托盘菜单/快捷键不可控，改用定时采样两进程在"有窗口交互"状态下的表现。
实际对比动作由 PowerShell 侧发送键盘事件（Ctrl+Shift+Z+X 打开设置）实现。
"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

root = r"C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ"


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def open_proc(pid):
    return ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)


def sample(pid):
    k = ctypes.windll.kernel32
    ps = ctypes.windll.psapi
    h = open_proc(pid)
    if not h:
        return None
    try:
        mc = PMC(); mc.cb = ctypes.sizeof(PMC)
        ps.GetProcessMemoryInfo(wintypes.HANDLE(h), ctypes.byref(mc), mc.cb)
        ct, et, kt, ut = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        k.GetProcessTimes(wintypes.HANDLE(h), ctypes.byref(ct), ctypes.byref(et),
                          ctypes.byref(kt), ctypes.byref(ut))
        kt = (kt.dwHighDateTime << 32) | kt.dwLowDateTime
        ut = (ut.dwHighDateTime << 32) | ut.dwLowDateTime
        return mc.WorkingSetSize / (1024 * 1024), (kt + ut) / 1e7
    finally:
        k.CloseHandle(h)


def get_real_pids():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -like '*main.py*' -and $_.ExecutablePath -like '*pythoncore*' } | "
         "ForEach-Object { \"$($_.ProcessId) $($_.WorkingSetSize)\" }"],
        capture_output=True, text=True)
    rows = [x.split() for x in r.stdout.strip().splitlines() if x.strip()]
    rows.sort(key=lambda x: int(x[1]))   # 小=1.2.1(329MB) 大=优化版(85MB)? 反了, 按内存升序: 85MB(优化版) 在前
    rows.sort(key=lambda x: int(x[1]), reverse=True)  # 329MB(1.2.1) 在前
    return [int(x[0]) for x in rows]     # [pid121, pidUp]


def main():
    pids = get_real_pids()
    if len(pids) < 2:
        print("需要两个运行中的实例")
        return
    pid121, pidUp = pids[0], pids[1]
    print(f"1.2.1={pid121}  优化版={pidUp}")
    # 基线
    time.sleep(3)
    b121, bUp = sample(pid121), sample(pidUp)
    print(f"基线  mem: 1.2.1={b121[0]:.1f}MB 优化={bUp[0]:.1f}MB | "
          f"cpu: 1.2.1={b121[1]:.2f}s 优化={bUp[1]:.2f}s")
    # 施加 30 秒"操作"：反复开关设置窗（Ctrl+Shift+Z+X），开关紧凑模式等
    # 通过 PowerShell 发送组合键（发送到活动窗口，两个实例都会响应全局热键）
    for i in range(8):
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "$s=New-Object -ComObject WScript.Shell; $s.SendKeys('^+z')"],
                       capture_output=True)
        time.sleep(2)
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "$s=New-Object -ComObject WScript.Shell; $s.SendKeys('{ESC}')"],
                       capture_output=True)
        time.sleep(2)
    time.sleep(3)
    a121, aUp = sample(pid121), sample(pidUp)
    print(f"操作后 mem: 1.2.1={a121[0]:.1f}MB 优化={aUp[0]:.1f}MB | "
          f"cpu: 1.2.1={a121[1]:.2f}s 优化={aUp[1]:.2f}s")
    print(f"操作期间 CPU 增量: 1.2.1={a121[1]-b121[1]:.2f}s  优化={aUp[1]-bUp[1]:.2f}s")
    print(f"内存增量: 1.2.1={a121[0]-b121[0]:+.1f}MB  优化={aUp[0]-bUp[0]:+.1f}MB")


if __name__ == "__main__":
    main()
