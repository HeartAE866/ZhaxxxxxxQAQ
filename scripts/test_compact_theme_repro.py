# -*- coding: utf-8 -*-
"""回归测试：切换主题后紧凑栏样式（字体/字号/跟随色）自动刷新（离屏）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import core
import i18n
from main_window import FloatWindow

app = QApplication([])
tmp = tempfile.mkdtemp()
i18n.set_lang("zh")
PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"PASS: {name}")


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = core.DataStore(os.path.join(tmp, "d.json"))
        self.t = self.config.get("theme")

    def apply_theme(self, kind="all"):
        if kind in ("theme", "all"):
            self.t = self.config.get("theme")
            self.win.refresh_theme()

    def open_folder_flow(self, i): pass
    def toggle_compact(self, v=False): pass
    def quick_record_menu(self): pass
    def refresh_priorities(self): pass


fa = FakeApp()
win = FloatWindow(fa)
fa.win = win
win.show()
fa.config.set("window", "compact", True)
win._update_compact_text()
app.processEvents()

check("初始字号跟随主题", "font-size:10pt" in win.compact_lbl.styleSheet())

# 切换主题：字号 16、字体 Arial、文字黑色
fa.config.set("theme", {
    **fa.config.get("theme"),
    "font_size": 16, "font_family": "Arial", "text": "#123456",
    "bg": "#ffffff", "bg_alpha": 255, "name": "大字主题",
})
fa.apply_theme("theme")
app.processEvents()

ss = win.compact_lbl.styleSheet()
check("紧凑栏字号随主题刷新", "font-size:16pt" in ss)
check("紧凑栏字体随主题刷新", "font-family:'Arial'" in ss)
check("紧凑栏无固定色时继承主题文字色", "#123456" not in ss)

# 紧凑主题设置固定色：不应被主题覆盖
fa.config.set("compact_style", {**fa.config.get("compact_style"), "text_color": "#00ff00"})
win._apply_compact_style()
check("紧凑主题固定色优先", "color:#00ff00" in win.compact_lbl.styleSheet())

# 取消固定色后跟随主题
fa.config.set("compact_style", {**fa.config.get("compact_style"), "text_color": ""})
win._apply_compact_style()
check("取消固定色后回退主题色", "color:" not in win.compact_lbl.styleSheet())

print(f"ALL PASS: {PASS} checks")
win.close()
