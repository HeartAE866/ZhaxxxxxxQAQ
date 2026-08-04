"""DearPyGui 初始化与嵌入测试：vsync 关闭 + SetParent 到 Progman。
分步打印定位卡点；采样 hung 判断是否可用。"""
import ctypes
import sys
import time
from ctypes import wintypes


def main():
    print("1. import DG", flush=True)
    import dearpygui.dearpygui as dpg
    print("2. create_context", flush=True)
    dpg.create_context()
    print("3. set_vsync(False)", flush=True)
    dpg.set_vsync(False)
    print("4. build ui", flush=True)
    with dpg.window(tag="main"):
        dpg.add_text("DearPyGui 嵌入测试")
        dpg.add_button(label="点击", tag="btn")
        dpg.add_text("状态: 就绪", tag="st")
    print("5. create_viewport", flush=True)
    dpg.create_viewport(title="ZhaxxDGTest", width=413, height=480,
                        x_pos=1065, y_pos=425, resizable=False)
    print("6. setup_dearpygui", flush=True)
    dpg.setup_dearpygui()
    print("7. show_viewport", flush=True)
    dpg.show_viewport()
    print("8. find hwnd", flush=True)
    u = ctypes.windll.user32
    hwnd = u.FindWindowW(None, "ZhaxxDGTest")
    print("9. hwnd:", hwnd, flush=True)
    if not hwnd:
        print("FAIL: 找不到 DG 窗口", flush=True)
        return 1
    progman = u.FindWindowW("Progman", None)
    style = u.GetWindowLongPtrW(wintypes.HWND(hwnd), -16)
    u.SetWindowLongPtrW(wintypes.HWND(hwnd), -16, style | 0x40000000)
    u.SetParent(wintypes.HWND(hwnd), wintypes.HWND(progman))
    u.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(0),
                   1065, 425, 413, 480, 0x0010)
    print("10. 已嵌入 Progman", flush=True)
    ok = True
    for i in range(8):
        time.sleep(2)
        h = bool(u.IsHungAppWindow(wintypes.HWND(hwnd)))
        print(f"11. t+{(i + 1) * 2}s hung={h} vis={bool(u.IsWindowVisible(wintypes.HWND(hwnd)))}", flush=True)
        if h:
            ok = False
    print("RESULT:", "PASS(不卡)" if ok else "FAIL(卡)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
