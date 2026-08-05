# -*- coding: utf-8 -*-
"""InputDialog 与主题自动加载回归测试（离屏）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QDialog, QPushButton

import core
import i18n
import theme as theme_mod
from widgets import InputDialog

app = QApplication([])
tmp = tempfile.mkdtemp()
i18n.set_lang("zh")
t = dict(theme_mod.DEFAULT_THEME)
PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"PASS: {name}")


# ---- 1. get_text 模式
d2 = InputDialog(None, t, "保存主题", "主题名称：", text="我的主题")
check("get_text 有输入框", d2._line is not None)
check("get_text 初始值", d2._line.text() == "我的主题")
check("get_text 无下拉", d2._combo is None)

# ---- 2. get_item 模式
d3 = InputDialog(None, t, "导出格式", "选择格式：", items=["JSON", "CSV"], current=1)
check("get_item 有下拉", d3._combo is not None)
check("get_item 当前项", d3._combo.currentText() == "CSV")
check("get_item 无输入框", d3._line is None)
check("get_item 取值", d3._finish() == "CSV")

# ---- 3. 取消路径
d4 = InputDialog(None, t, "重命名", "新的名称：", text="旧名")
d4.reject()
check("reject 后非 Accepted", d4.result() != QDialog.Accepted)


# ---- 4. 主题下拉自动加载（无加载按钮）
class FakeStore:
    items = []

    def all_tags(self):
        return []

    def find(self, i):
        return i


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = FakeStore()
        self.t = self.config.get("theme")

    def apply_theme(self, kind="all"):
        pass


import settings as settings_mod

fa = FakeApp()
sw = settings_mod.SettingsWindow(fa)
loaded = []
orig = sw._load_theme


def spy():
    loaded.append(sw.theme_combo.currentText())
    return orig()


sw._load_theme = spy
sw.theme_combo.setCurrentIndex(sw.theme_combo.findText("亮色磨砂"))
sw.theme_combo.activated.emit(sw.theme_combo.currentIndex())
check("主题下拉选择触发加载", "亮色磨砂" in loaded)
btns = [b.text() for b in sw.findChildren(QPushButton)]
check("无加载按钮", "加载" not in btns)

print(f"ALL PASS: {PASS} checks")
