"""真实平台验证：55 条测试数据下，2023/2024/2025/2026 各年份组是否全部渲染（问题 B）"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

import core
import i18n
from main_window import FloatWindow, GroupHeader

app = QApplication([])

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(ROOT, "config.json"))
        self.store = core.DataStore(os.path.join(ROOT, "data", "data.json"))
        self.t = self.config.get("theme")
        self.win = None

    def open_folder_flow(self, i): pass
    def toggle_compact(self, v=False): pass
    def quick_record_menu(self): pass
    def refresh_priorities(self): pass


fa = FakeApp()
print(f"数据条数: {len(fa.store.items)}")
from collections import Counter
print("类型分布:", dict(Counter(i["type"] for i in fa.store.items)))
import datetime
years = Counter(core.parse_dt(i["created"]).year for i in fa.store.items if core.parse_dt(i["created"]))
print("年份分布:", dict(sorted(years.items())))

i18n.set_lang("zh")
win = FloatWindow(fa)
fa.win = win
win.show()
for _ in range(5):
    app.processEvents()

headers = [h for h in win.findChildren(GroupHeader)]
texts = [h.title.text() for h in headers]
print("渲染的组头:", texts)
for y in ("2026年", "2025年", "2024年", "2023年"):
    if y in texts:
        print(f"  ✓ {y} 已渲染")
    else:
        print(f"  ✗ {y} 未渲染！")

# 滚动条情况
from PySide6.QtWidgets import QScrollArea
sc = win.findChild(QScrollArea)
if sc:
    print(f"滚动区: vertical bar max={sc.verticalScrollBar().maximum()} (0=无滚动, >0=可滚动)")
win.close()
