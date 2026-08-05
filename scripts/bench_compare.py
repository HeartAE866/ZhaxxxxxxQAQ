"""Benchmark: 1.3.0up(优化版) vs 1.2.1 — memory / idle CPU / threads / size.
启动两个源码版（同一解释器），纯待机采样 10 轮，ctypes 读取进程指标。
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
b3 = os.path.join(root, "app", "main.py")
DETACHED = 0x00000008


def prepare_121():
    """临时运行目录：1.2.1 源码 + 与 beta3 相同的数据（公平对比）。"""
    tmp = os.path.join(tempfile.gettempdir(), "zhaxx_bench121")
    if os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    for d in ("app", "data", "resources"):
        shutil.copytree(os.path.join(v121, d), os.path.join(tmp, d))
    shutil.copy(os.path.join(v121, "config.json"), os.path.join(tmp, "config.json"))
    shutil.copy(os.path.join(root, "data", "data.json"), os.path.join(tmp, "data", "data.json"))
    return os.path.join(tmp, "app", "main.py")


def kill_all():
    import subprocess as sp
    r = sp.run(["powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
               capture_output=True)
    time.sleep(3)


def launch(path):
    p = subprocess.Popen([py, "-X", "utf8", path], cwd=os.path.dirname(path),
                         creationflags=DETACHED)
    return p


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def open_proc(pid):
    k = ctypes.windll.kernel32
    return k.OpenProcess(0x0400 | 0x0010, False, pid)  # QUERY_INFORMATION|QUERY_LIMITED


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
        cpu_100ns = (kt.dwHighDateTime << 32 | kt.dwLowDateTime) + \
                    (ut.dwHighDateTime << 32 | ut.dwLowDateTime)
        # 线程数
        threads = 0
        snap = k.CreateToolhelp32Snapshot(0x00000004, pid)  # TH32CS_SNAPTHREAD
        if snap and snap != -1:
            class TE(ctypes.Structure):
                _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                            ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
                            ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG),
                            ("dwFlags", wintypes.DWORD)]
            te = TE(); te.dwSize = ctypes.sizeof(TE)
            if k.Thread32First(snap, ctypes.byref(te)):
                while True:
                    if te.th32OwnerProcessID == pid:
                        threads += 1
                    if not k.Thread32Next(snap, ctypes.byref(te)):
                        break
            k.CloseHandle(snap)
        return mc.WorkingSetSize / (1024 * 1024), cpu_100ns / 1e7, threads
    finally:
        k.CloseHandle(h)


def find_real(launcher_pid):
    """venv python.exe 是重定向器：找其子进程（真实 GUI 进程）。"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={launcher_pid}').ProcessId"],
        capture_output=True, text=True)
    pids = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    return pids[0] if pids else launcher_pid


def main():
    kill_all()
    p121 = prepare_121()
    print("启动 1.2.1 与 1.3.0beta3（同数据）...", flush=True)
    l1 = launch(p121)
    l2 = launch(b3)
    print(f"launcher 1.2.1={l1.pid}  beta3={l2.pid}", flush=True)
    time.sleep(18)
    pid1 = find_real(l1.pid)
    pid2 = find_real(l2.pid)
    print(f"真实进程 1.2.1={pid1}  beta3={pid2}", flush=True)
    mem1, mem2, cpu1, cpu2, thr1, thr2 = [], [], [], [], [], []
    for i in range(10):
        s1 = sample(pid1)
        s2 = sample(pid2)
        if s1:
            mem1.append(s1[0]); cpu1.append(s1[1]); thr1.append(s1[2])
        if s2:
            mem2.append(s2[0]); cpu2.append(s2[1]); thr2.append(s2[2])
        time.sleep(2)
        print(f"  round{i+1}: 1.2.1 mem={s1[0]:.1f}MB cpu={s1[1]:.3f}s thr={s1[2]} | "
              f"beta3 mem={s2[0]:.1f}MB cpu={s2[1]:.3f}s thr={s2[2]}", flush=True)

    def avg(a):
        return sum(a) / len(a) if a else 0

    m1, m2 = avg(mem1), avg(mem2)
    c1, c2 = avg(cpu1), avg(cpu2)
    t1, t2 = avg(thr1), avg(thr2)
    print("\n===== 结果（10 轮均值）=====")
    print(f"内存 WorkingSet: 1.2.1={m1:.1f}MB  beta3={m2:.1f}MB  差={m2-m1:+.1f}MB ({(m2-m1)/m1*100:+.1f}%)")
    print(f"待机 CPU 累计:   1.2.1={c1:.3f}s  beta3={c2:.3f}s  差={c2-c1:+.3f}s ({(c2-c1)/c1*100:+.1f}%)")
    print(f"线程数:          1.2.1={t1:.0f}  beta3={t2:.0f}")
    import subprocess as sp
    exe121 = os.path.join(root, "版本存档", "v1.2.1", "ZhaxxxxxxQAQ_Setup_v1.2.1.exe")
    exeB3 = os.path.join(root, "build", "dist", "installer", "ZhaxxxxxxQAQ_Setup_v1.3.0.exe")
    print("\n===== 体量 =====")
    for name, p in (("安装包 1.2.1", exe121), ("安装包 beta3", exeB3)):
        if os.path.exists(p):
            print(f"{name}: {os.path.getsize(p)/1024/1024:.1f} MB")
    for name, d in (("源码 1.2.1", os.path.join(root, "版本存档", "v1.2.1", "app")),
                    ("源码 beta3", os.path.join(root, "app"))):
        n = sum(1 for f in os.listdir(d) if f.endswith(".py"))
        lines = sum(len(open(os.path.join(d, f), encoding="utf-8").readlines())
                    for f in os.listdir(d) if f.endswith(".py"))
        print(f"{name}: {n} 文件, {lines} 行")
    print("\n(两个版本窗口仍在运行，供人工检查；可手动关闭或下次实验自动清理)")


if __name__ == "__main__":
    main()

