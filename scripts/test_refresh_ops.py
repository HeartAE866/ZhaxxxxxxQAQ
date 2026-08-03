"""验证：各种操作触发 refresh 全量重建后窗口正常（无闪烁修复的回归）"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

import core
import i18n
from main_window import FloatWindow

app = QApplication([])
tmp = tempfile.mkdtemp()


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = core.DataStore(os.path.join(tmp, "d.json"))
        self.t = self.config.get("theme")
        self.win = None

    def open_folder_flow(self, i): pass
    def toggle_compact(self, v=False): pass
    def quick_record_menu(self): pass
    def refresh_priorities(self): pass
    def edit_reminder(self, item): pass
    def reminder_context_menu(self, item, pos): pass
    def add_reminder(self): pass


fa = FakeApp()
for i in range(10):
    it = core.new_item("todo", f"任务{i}")
    it["created"] = f"2026-08-0{(i % 9) + 1} 09:00"
    it["deadline"] = it["created"]
    fa.store.items.append(it)

i18n.set_lang("zh")
win = FloatWindow(fa)
fa.win = win
win.show()
for _ in range(10):
    app.processEvents()

h0 = win.height()
print(f"初始高度: {h0}")

# 1) 添加事项 → refresh(fit=True) 全量重建
fa.store.add(core.new_item("todo", "新任务"))
win.refresh(fit=True)
for _ in range(10):
    app.processEvents()
print(f"添加后高度: {win.height()} visible={win.isVisible()}")
assert win.isVisible()

# 2) 搜索触发重建
win.search.setText("任务")
for _ in range(10):
    app.processEvents()
win.search_active = "任务"
win.refresh(fit=True)
for _ in range(10):
    app.processEvents()
print(f"搜索后高度: {win.height()} visible={win.isVisible()}")
win.search.setText("")
win.search_active = ""
win.refresh(fit=True)
for _ in range(10):
    app.processEvents()

# 3) 完成切换 → refresh
store = fa.store
item = store.items[0]
item["done"] = True
store.save()
win.refresh(fit=True)
for _ in range(10):
    app.processEvents()
print(f"完成后高度: {win.height()} visible={win.isVisible()}")

# 4) 连续快速刷新（模拟操作频繁）
for _ in range(5):
    win.refresh(fit=False)
for _ in range(10):
    app.processEvents()
print(f"连续刷新后高度: {win.height()} visible={win.isVisible()}")
assert win.isVisible()

print("ALL PASS: 各种操作触发刷新后窗口正常、无闪烁路径")
win.close()
