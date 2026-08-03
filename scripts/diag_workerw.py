"""诊断壁纸层（WorkerW）结构：Progman → ZhaxxWorkerW → 应用窗口。
输出各层句柄/类名/位置/可见性，检查嵌入是否成功。"""
import ctypes
import sys
from ctypes import wintypes

sys.path.insert(0, r"C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ\app")
from widgets import _user32, _class_name

u = _user32()


def show(hwnd, indent=0):
    if not hwnd:
        return
    r = wintypes.RECT()
    u.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(r))
    vis = u.IsWindowVisible(wintypes.HWND(hwnd))
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid))
    style = u.GetWindowLongPtrW(wintypes.HWND(hwnd), -16)
    child = "CHILD" if style & 0x40000000 else "TOP "
    print(f"{'  ' * indent}{_class_name(hwnd)!r} hwnd={hwnd} "
          f"({r.left},{r.top} {r.right - r.left}x{r.bottom - r.top}) "
          f"vis={vis} pid={pid.value} {child}")


def children(hwnd, indent=0, depth=1):
    if not hwnd or depth > 2:
        return
    ch = u.GetWindow(wintypes.HWND(hwnd), 5)  # GW_CHILD
    while ch:
        show(ch, indent + 1)
        children(ch, indent + 1, depth + 1)
        ch = u.GetWindow(ch, 2)  # GW_HWNDNEXT


progman = u.FindWindowW("Progman", None)
print("=== Progman 结构 ===")
show(progman)
children(progman, 1)

print("\n=== 应用窗口(挂件)状态 ===")
hwnds2 = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def cb2(h, _):
    if _class_name(h) == "Qt6111QWindowToolSaveBits":
        hwnds2.append(int(h))
    return True


u.EnumWindows(cb2, 0)
for h in hwnds2:
    show(h)
    anc = u.GetAncestor(wintypes.HWND(h), 1)  # GA_PARENT
    print(f"    父窗口: {anc} ({_class_name(anc)})")
