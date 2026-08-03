"""真实平台验证：组头展开/收起不改变窗口高度（问题 A 修复验证）
注意：必须真实 win32 平台运行（offscreen 下 sizeHint 恒 0 不可靠）。
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

import core
import i18n
from main_window import FloatWindow, GroupHeader

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


fa = FakeApp()
# 跨年跨月数据（模拟 55 条测试数据的分布）
seed = [
    ("todo", "2026-08-01 09:00", "2026任务A"),
    ("todo", "2026-08-02 09:00", "2026任务B"),
    ("todo", "2026-08-03 09:00", "2026任务C"),
    ("todo", "2026-08-04 09:00", "2026任务D"),
    ("todo", "2026-07-15 09:00", "2026七月任务"),
    ("record", "2025-03-10 10:00", "2025记录A"),
    ("record", "2025-11-20 10:00", "2025记录B"),
    ("todo", "2024-05-05 09:00", "2024任务"),
    ("record", "2023-01-01 10:00", "2023记录"),
]
for ty, created, title in seed:
    it = core.new_item(ty, title)
    it["created"] = created
    if ty == "todo":
        it["deadline"] = created
    fa.store.items.append(it)

i18n.set_lang("zh")
win = FloatWindow(fa)
fa.win = win
win.show()
app.processEvents()
app.processEvents()

# 找到 2026 年组头（渲染在顶部）
headers = [h for h in win.findChildren(GroupHeader) if h.title.text() == "2026年"]
assert headers, "未找到 2026 年组头"
h2026 = headers[0]

h0 = win.height()
print(f"初始窗口高度: {h0}")

# 1) 折叠 2026 年 → 高度应不变
QTest.mouseClick(h2026, Qt.LeftButton)
app.processEvents()
app.processEvents()
h1 = win.height()
print(f"折叠 2026 年后高度: {h1}")
assert h1 == h0, f"FAIL: 折叠后高度变化 {h0} -> {h1}"
print("PASS: 折叠不改变高度")

# 2) 再展开 → 高度仍不变
QTest.mouseClick(h2026, Qt.LeftButton)
app.processEvents()
app.processEvents()
h2 = win.height()
print(f"重新展开后高度: {h2}")
assert h2 == h0, f"FAIL: 展开后高度变化 {h0} -> {h2}"
print("PASS: 展开不改变高度")

# 3) 折叠月份组头（2026年8月）→ 高度不变
m_headers = [h for h in win.findChildren(GroupHeader) if h.title.text() == "8月"]
if m_headers:
    QTest.mouseClick(m_headers[0], Qt.LeftButton)
    app.processEvents()
    app.processEvents()
    h3 = win.height()
    print(f"折叠 8 月后高度: {h3}")
    assert h3 == h0, f"FAIL: 折叠月份后高度变化 {h0} -> {h3}"
    print("PASS: 折叠月份不改变高度")

win.close()
print("ALL PASS")
