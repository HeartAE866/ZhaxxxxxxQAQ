# -*- coding: utf-8 -*-
"""回归测试：切换主题后紧凑栏样式（字体/字号/跟随色）自动刷新；紧凑主题结构统一（离屏）。"""
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

# 切换主题：字号 16、字体 Arial
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

# 紧凑主题设置固定文字色：优先于主题
cfg = fa.config.get("compact_style")
cfg["text"] = "#00ff00"
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("紧凑主题固定色优先", "color:#00ff00" in win.compact_lbl.styleSheet())

# 清除固定色后跟随主题（无 color 规则）
cfg = fa.config.get("compact_style")
cfg["text"] = ""
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("清除固定色后回退主题", "color:" not in win.compact_lbl.styleSheet())

# 紧凑主题背景：设置 bg → compact_bar 用该色
cfg = fa.config.get("compact_style")
cfg["bg"] = "#334455"
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("紧凑主题 bg 应用", win.compact_bar._bg_color == "#334455")

# 紧凑 DIY 背景：启用后优先于 bg
cfg = fa.config.get("compact_style")
cfg.setdefault("diy_bg", {})["enabled"] = True
cfg["diy_bg"]["components"] = {"compact": {"color": "", "image": "", "alpha": 70}}
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("紧凑 DIY 启用后透明（未设内容）", win.compact_bar._bg_image == "")

print(f"ALL PASS: {PASS} checks")
win.close()
