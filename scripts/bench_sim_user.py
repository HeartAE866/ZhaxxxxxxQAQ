# -*- coding: utf-8 -*-
"""模拟真实用户操作对比实验：1.2.1 vs 当前版（同数据同解释器）。
操作：打开/关闭设置、快速添加记录/待办/循环、切换紧凑、搜索聚焦（全局热键）。
"""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

root = r"C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ"
py = os.path.join(root, "venv", "Scripts", "python.exe")
v121 = os.path.join(root, "版本存档", "v1.2.1")
cur = os.path.join(root, "app", "main.py")
DETACHED = 0x00000008


HOTKEYS = {
    "quick_record": ["ctrl", "shift", "z", "r"],
    "quick_todo": ["ctrl", "shift", "z", "t"],
    "quick_recur": ["ctrl", "shift", "z", "c"],
    "toggle_compact": ["ctrl", "shift", "z", "b"],
    "show_hide": ["ctrl", "shift", "z", "h"],
}


def inject_hotkeys(cfg_path):
    """写入与实验匹配的自定义热键（两版相同）。"""
    import json
    d = json.load(open(cfg_path, encoding="utf-8"))
    d.setdefault("hotkeys", {})["custom"] = dict(HOTKEYS)
    json.dump(d, open(cfg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def prepare_121():
    """1.2.1 临时运行目录 + 与当前版相同的数据。"""
    tmp = os.path.join(tempfile.gettempdir(), "zhaxx_sim121")
    if os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    for d in ("app", "data", "resources"):
        shutil.copytree(os.path.join(v121, d), os.path.join(tmp, d))
    shutil.copy(os.path.join(v121, "config.json"), os.path.join(tmp, "config.json"))
    # 同数据
    shutil.copy(os.path.join(root, "data", "data.json"), os.path.join(tmp, "data", "data.json"))
    # 同配置（主题设置等）+ 相同自定义热键
    shutil.copy(os.path.join(root, "config.json"), os.path.join(tmp, "config.json"))
    inject_hotkeys(os.path.join(tmp, "config.json"))
    return os.path.join(tmp, "app", "main.py")


def kill_all():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process | Where-Object { ($_.Name -like 'python*') -and $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                   capture_output=True)
    time.sleep(3)


def launch(path):
    return subprocess.Popen([py, "-X", "utf8", path], cwd=os.path.dirname(path),
                            creationflags=DETACHED)


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
        # PrivateUsage = 进程私有内存（不含共享 DLL 页，对比更准确）
        return mc.PagefileUsage / (1024 * 1024), (kt + ut) / 1e7
    finally:
        k.CloseHandle(h)


def find_real(launcher_pid):
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={launcher_pid}').ProcessId"],
        capture_output=True, text=True)
    pids = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    return pids[0] if pids else launcher_pid


def send(keys):
    """SendKeys 发送按键序列。"""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"$s=New-Object -ComObject WScript.Shell; $s.SendKeys('{keys}')"],
                   capture_output=True)


def main():
    kill_all()
    p121 = prepare_121()
    inject_hotkeys(os.path.join(root, "config.json"))
    print("生成 1.2.1 环境并启动两个版本（同数据）...", flush=True)
    l1 = launch(p121)
    l2 = launch(cur)
    time.sleep(18)
    pid1 = find_real(l1.pid)
    pid2 = find_real(l2.pid)
    print(f"1.2.1={pid1}  当前版={pid2}", flush=True)

    def avg(a):
        return sum(a) / len(a) if a else 0

    # ---- 阶段1：纯待机基线（30s）
    time.sleep(5)
    m1, m2 = [], []
    c1, c2 = [], []
    for _ in range(6):
        s1, s2 = sample(pid1), sample(pid2)
        if s1: m1.append(s1[0]); c1.append(s1[1])
        if s2: m2.append(s2[0]); c2.append(s2[1])
        time.sleep(5)
    b_m1, b_m2 = avg(m1), avg(m2)
    print(f"阶段1 待机基线: 1.2.1={b_m1:.1f}MB cpu={avg(c1):.3f}s | 当前={b_m2:.1f}MB cpu={avg(c2):.3f}s", flush=True)

    # ---- 阶段2：拟人化操作（约 90s）
    print("阶段2 模拟用户操作中...", flush=True)
    ops = []
    # 打开设置 → 等待 → 关闭（3 轮）
    for i in range(3):
        send("^+z")
        time.sleep(2)
        send("{ESC}")
        time.sleep(1.5)
        ops.append("open/close settings")
    # 快速添加记录 / 待办 / 循环任务（对话框弹出后回车确认；随后 ESC 清场）
    for _ in range(2):
        send("^+zr")     # quick_record (ctrl+shift+z+r)
        time.sleep(1)
        send("{ENTER}")
        time.sleep(0.8)
        send("{ESC}")
        time.sleep(0.8)
    for _ in range(2):
        send("^+zt")     # quick_todo
        time.sleep(1)
        send("{ENTER}")
        time.sleep(0.8)
        send("{ESC}")
        time.sleep(0.8)
    # 切换紧凑模式（ctrl+shift+z+b）
    send("^+zb")
    time.sleep(1.5)
    # 显示/隐藏主界面（ctrl+shift+z+h）
    send("^+zh")
    time.sleep(1.5)
    send("^+zh")
    time.sleep(1.5)
    # 打开设置再关（模拟翻阅）
    send("^+z")
    time.sleep(2.5)
    send("{ESC}")
    time.sleep(1.5)
    ops.append("misc hotkeys")

    # ---- 阶段3：操作后采样（30s）
    m1, m2, c1, c2 = [], [], [], []
    for _ in range(6):
        s1, s2 = sample(pid1), sample(pid2)
        if s1: m1.append(s1[0]); c1.append(s1[1])
        if s2: m2.append(s2[0]); c2.append(s2[1])
        time.sleep(5)
    a_m1, a_m2 = avg(m1), avg(m2)
    a_c1, a_c2 = avg(c1), avg(c2)

    print("\n===== 实验结果 =====")
    print(f"内存:  1.2.1 待机={b_m1:.1f}MB 操作后={a_m1:.1f}MB | "
          f"当前 待机={b_m2:.1f}MB 操作后={a_m2:.1f}MB")
    print(f"内存差: 待机 {b_m2 - b_m1:+.1f}MB ({(b_m2-b_m1)/b_m1*100:+.1f}%) | "
          f"操作后 {a_m2 - a_m1:+.1f}MB ({(a_m2-a_m1)/a_m1*100:+.1f}%)")
    print(f"CPU累计: 1.2.1={a_c1:.3f}s 当前={a_c2:.3f}s 差={a_c2-a_c1:+.3f}s "
          f"({(a_c2-a_c1)/a_c1*100:+.1f}%)")
    print(f"操作数: {len(ops)} 组动作（设置开合/快速录入/紧凑/显隐）")


if __name__ == "__main__":
    main()
