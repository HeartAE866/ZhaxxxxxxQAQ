# -*- coding: utf-8 -*-
"""数据规模阶梯测试：两版分别加载 0 / 50 / 150 条数据，测私有内存与启动后 CPU。
模拟"用户录入越来越多事项"后的资源表现。"""
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
v121 = os.path.join(root, "版本存档", "v1.2.1")
DETACHED = 0x00000008


def make_data(n):
    """生成 n 条数据。"""
    import uuid
    from datetime import datetime, timedelta
    now = datetime.now().replace(second=0, microsecond=0)
    items = []
    for i in range(n):
        ty = ["record", "todo", "recur", "remind"][i % 4]
        it = {
            "id": uuid.uuid4().hex[:12], "type": ty, "title": f"模拟事项 {i}",
            "created": (now - timedelta(days=i % 90)).strftime("%Y-%m-%d %H:%M"),
            "priority": "mid", "tags": [], "folder": None, "folder_rule": None,
            "order": 0, "deadline": None, "remind_advance": None,
            "remind_time": None, "notified_for": None, "done": False,
            "recur": None, "completed_instances": [],
        }
        if ty == "todo":
            it["deadline"] = (now + timedelta(days=(i % 30) + 1,
                                               hours=12)).strftime("%Y-%m-%d %H:%M")
        elif ty == "recur":
            # 周期设到未来的下一期（避免实验期间反复弹提醒）
            it["recur"] = {"period": "day", "time": "23:59"}
        elif ty == "remind":
            it["remind_time"] = (now + timedelta(days=(i % 10) + 1,
                                                 hours=12)).strftime("%Y-%m-%d %H:%M")
        items.append(it)
    return items


def setup(version_dir, n, inplace=False):
    """构建临时运行目录。"""
    if inplace:
        # 当前版：直接用项目目录（app 已在位），仅替换数据/配置
        tmp = root
        import json as j
        cfg = j.load(open(os.path.join(tmp, "config.json"), encoding="utf-8"))
        cfg.get("hotkeys", {})["custom"] = {}
        j.dump(cfg, open(os.path.join(tmp, "config.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)
        j.dump({"items": make_data(n)},
               open(os.path.join(tmp, "data", "data.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=1)
        return os.path.join(tmp, "app", "main.py")
    tmp = os.path.join(tempfile.gettempdir(), f"zhaxx_scale_{n}_{os.path.basename(version_dir)}")
    if os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    for d in ("app", "data", "resources"):
        shutil.copytree(os.path.join(version_dir, d), os.path.join(tmp, d))
    # config：清理自定义热键和窗口位置，保持默认
    import json as j
    cfg = j.load(open(os.path.join(version_dir, "config.json"), encoding="utf-8"))
    cfg.get("hotkeys", {})["custom"] = {}
    j.dump(cfg, open(os.path.join(tmp, "config.json"), "w", encoding="utf-8"),
           ensure_ascii=False, indent=2)
    # 数据
    j.dump({"items": make_data(n)},
           open(os.path.join(tmp, "data", "data.json"), "w", encoding="utf-8"),
           ensure_ascii=False, indent=1)
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


def run_round(n):
    print(f"\n===== 数据量 {n} 条 =====", flush=True)
    p121 = setup(os.path.join(root, "版本存档", "v1.2.1"), n)
    pcur = setup(root, n, inplace=True)
    l1 = subprocess.Popen([py, "-X", "utf8", p121], cwd=os.path.dirname(p121),
                          creationflags=DETACHED)
    l2 = subprocess.Popen([py, "-X", "utf8", pcur], cwd=os.path.dirname(pcur),
                          creationflags=DETACHED)
    time.sleep(18)
    pid1, pid2 = find_real(l1.pid), find_real(l2.pid)
    m1, m2, c1, c2 = [], [], [], []
    for _ in range(5):
        s1, s2 = sample(pid1), sample(pid2)
        if s1: m1.append(s1[0]); c1.append(s1[1])
        if s2: m2.append(s2[0]); c2.append(s2[1])
        time.sleep(4)
    m1 = sum(m1) / len(m1); m2 = sum(m2) / len(m2)
    c1 = sum(c1) / len(c1); c2 = sum(c2) / len(c2)
    print(f"  私有内存: 1.2.1={m1:.1f}MB  当前={m2:.1f}MB  差={m2-m1:+.1f}MB ({(m2-m1)/m1*100:+.1f}%)")
    print(f"  CPU累计:  1.2.1={c1:.3f}s  当前={c2:.3f}s  差={c2-c1:+.3f}s ({(c2-c1)/c1*100:+.1f}%)")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                   capture_output=True)
    time.sleep(3)


def main():
    for n in (0, 50, 150):
        run_round(n)


if __name__ == "__main__":
    main()
