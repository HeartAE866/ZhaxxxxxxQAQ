# -*- coding: utf-8 -*-
"""复现：模拟真实点击按钮路径，检查三主题调节后各目标窗口是否同步（离屏）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import core
import i18n
import settings as settings_mod

app = QApplication([])
tmp = tempfile.mkdtemp()
i18n.set_lang("zh")


class FakeStore:
    items = []

    def all_tags(self):
        return []

    def find(self, i):
        return i


class FakeWin:
    def __init__(self, fa):
        self.app = fa
        self.refresh_theme_calls = 0
        self.compact_calls = 0

    def refresh_theme(self):
        self.refresh_theme_calls += 1

    def _apply_compact_style(self):
        self.compact_calls += 1

    def _update_compact_text(self):
        pass


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = FakeStore()
        self.t = self.config.get("theme")
        self.win = None
        self.settings_win = None
        self.settings_style_rebuilds = 0

    def apply_theme(self, kind="all"):
        if kind in ("theme", "all"):
            self.t = self.config.get("theme")
            self.win.refresh_theme()
        if kind in ("theme_settings", "all") and self.settings_win:
            ts = self.config.get("theme_settings")
            self.settings_win.t = ts
            self.settings_style_rebuilds += 1
        if kind in ("compact_style", "all"):
            self.win._apply_compact_style()


fa = FakeApp()
fa.win = FakeWin(fa)
sw = settings_mod.SettingsWindow(fa)
fa.settings_win = sw
sw.show()
app.processEvents()

print("=== 初始 kind =", sw._kind)

# 场景1：点击桌面应用主题按钮 → 调节 bg
sw.rb_main_theme.click()
app.processEvents()
print("点击桌面按钮后 kind =", sw._kind)
sw._edit["bg"] = "#ff00ff"
sw._apply_theme()
app.processEvents()
print("  theme.bg =", fa.config.get("theme", "bg"),
      "| 主窗口刷新 =", fa.win.refresh_theme_calls,
      "| 设置栏样式重建 =", fa.settings_style_rebuilds)

# 场景2：点击紧凑模式主题按钮 → 调节 text
sw.rb_compact_theme.click()
app.processEvents()
print("点击紧凑按钮后 kind =", sw._kind)
sw._edit["text"] = "#00ff00"
sw._apply_theme()
app.processEvents()
print("  compact.text =", fa.config.get("compact_style", "text"),
      "| 紧凑应用 =", fa.win.compact_calls)

# 场景3：点击设置栏主题按钮 → 调节 bg
sw.rb_settings_theme.click()
app.processEvents()
print("点击设置栏按钮后 kind =", sw._kind)
sw._edit["bg"] = "#0000ff"
sw._apply_theme()
app.processEvents()
print("  theme_settings.bg =", fa.config.get("theme_settings", "bg"),
      "| 设置栏样式重建 =", fa.settings_style_rebuilds)

# 场景4：切换按钮后编辑区是否刷新为新目标的值
sw.rb_main_theme.click()
app.processEvents()
print("切回桌面 kind =", sw._kind, "| edit bg =", sw._edit.get("bg"))
