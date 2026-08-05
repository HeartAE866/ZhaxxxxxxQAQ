# -*- coding: utf-8 -*-
"""单实例决定性对比：两版分别单独运行，各测 60s 待机 CPU 增量与私有内存。
消除并行共享页/调度噪音，得出干净结论。"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

root = r"C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ"
py = os.path.join(root, "venv", "Scripts", "python.exe")
DETACHED = 0x00000008


def build_env(src_root, tag):
    """构建独立运行目录（含相同数据/配置）。"""
    tmp = os.path.join(tempfile.gettempdir(), f"zhaxx_final_{tag}")
    if os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    for d in ("app", "data", "resources"):
        shutil.copytree(os.path.join(src_root, d), os.path.join(tmp, d))
    # 相同数据（37 条种子）
    shutil.copy(os.path.join(root, "data", "data.json"), os.path.join(tmp, "data", "data.json"))
    # 相同配置
    shutil.copy(os.path.join(root, "config.json"), os.path.join(tmp, "config.json"))
    return os.path.join(tmp, "app", "main.py")


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def sample(pid):
    k = ctypes.windll.kernel32
    ps = ctypes.windll.psapi
    h = k.OpenProcess(0x0400 | 0x0010, False, pid)
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
        return mc.PagefileUsage / 1048576, (kt + ut) / 1e7
    finally:
        k.CloseHandle(h)


def find_real(launcher_pid):
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={launcher_pid}').ProcessId"],
        capture_output=True, text=True)
    pids = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    return pids[0] if pids else launcher_pid


def run_once(main_path, label):
    l = subprocess.Popen([py, "-X", "utf8", main_path],
                         cwd=os.path.dirname(main_path), creationflags=DETACHED)
    time.sleep(18)
    pid = find_real(l.pid)
    # 60s 待机
    time.sleep(8)
    s0 = sample(pid)
    time.sleep(60)
    s1 = sample(pid)
    mem = (s0[0] + s1[0]) / 2
    cpu_inc = s1[1] - s0[1]
    print(f"{label}: 私有内存={mem:.1f}MB  60s待机CPU增量={cpu_inc:.3f}s ({cpu_inc:.2f}%)")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                   capture_output=True)
    time.sleep(3)
    return mem, cpu_inc


def main():
    print("===== 单实例决定性对比（同数据 37 条、同解释器、独立 60s 待机）=====")
    m121, c121 = run_once(build_env(os.path.join(root, "版本存档", "v1.2.1"), "121"), "1.2.1  ")
    mcur, ccur = run_once(build_env(root, "cur"), "当前版")
    print("\n===== 结果 =====")
    print(f"内存(私有): 1.2.1={m121:.1f}MB  当前={mcur:.1f}MB  差={mcur-m121:+.1f}MB ({(mcur-m121)/m121*100:+.1f}%)")
    print(f"CPU(60s):   1.2.1={c121:.3f}s  当前={ccur:.3f}s  差={ccur-c121:+.3f}s ({(ccur-c121)/c121*100:+.1f}%)")


if __name__ == "__main__":
    main()
