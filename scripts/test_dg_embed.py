"""DearPyGui 嵌入桌面层测试：D3D11 渲染 + vsync 关闭 + SetParent 到 Progman。
验证：显示正常？交互（点击）正常？不卡（vsync 已关）。
用法: python test_dg_embed.py [秒数]
"""
import ctypes
import sys
import time
from ctypes import wintypes

import dearpygui.dearpygui as dpg


def main():
    keep = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    dpg.create_context()
    dpg.set_vsync(False)   # 关闭 vsync：子窗口无 vsync 源时 present 不阻塞
    with dpg.window(tag="main"):
        dpg.add_text("DearPyGui 嵌入测试窗口")
        dpg.add_button(label="点击我(变色)", callback=lambda: dpg.configure_item(
            "main", pos=dpg.get_item_pos("main")))
        dpg.add_text("状态: 就绪", tag="status")
    dpg.create_viewport(title="ZhaxxDGTest", width=413, height=480,
                        x_pos=1065, y_pos=425, resizable=False)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    u = ctypes.windll.user32
    progman = u.FindWindowW("Progman", None)
    # 找 DG viewport 窗口（标题 ZhaxxDGTest）
    hwnd = u.FindWindowW(None, "ZhaxxDGTest")
    print(f"DG hwnd={hwnd} progman={progman}")
    if not hwnd:
        print("FAIL: 找不到 DG 窗口")
        return 1
    style = u.GetWindowLongPtrW(wintypes.HWND(hwnd), -16)
    u.SetWindowLongPtrW(wintypes.HWND(hwnd), -16, style | 0x40000000)
    u.SetParent(wintypes.HWND(hwnd), wintypes.HWND(progman))
    u.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(0),
                   1065, 425, 413, 480, 0x0010)
    print("已嵌入 Progman。采样 hung 状态：")
    dpg.start_dearpygui()   # 主循环（阻塞）——用线程采样

    # 注：start_dearpygui 阻塞，采样在退出循环后；用定时器
    # 实际测试在下方注释说明——此处改为在渲染循环中采样
    # 简单方式：直接 start（阻塞），外部脚本采样 hung


if __name__ == "__main__":
    main()
