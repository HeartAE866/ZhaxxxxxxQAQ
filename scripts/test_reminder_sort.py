"""真实平台验证：提醒栏拖拽排序 + 内容超高时窗口不超出屏幕底部"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QPoint

import core
import i18n
from main_window import FloatWindow, ReminderChip

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
# 3 条提醒（未完成，时间错开）+ 1 条已完成
for i, (title, t) in enumerate([
        ("提醒A", "2026-08-05 09:00"),
        ("提醒B", "2026-08-04 09:00"),
        ("提醒C", "2026-08-06 09:00")]):
    it = core.new_item("remind", title)
    it["remind_time"] = t
    fa.store.items.append(it)
done = core.new_item("remind", "已完成提醒")
done["remind_time"] = "2026-08-01 09:00"
done["done"] = True
fa.store.items.append(done)

i18n.set_lang("zh")
win = FloatWindow(fa)
fa.win = win
win.show()
for _ in range(10):
    app.processEvents()

container = win._find_group_container("reminder")
chips = [win.reminder_lay.itemAt(i).widget() for i in range(win.reminder_lay.count()) if isinstance(win.reminder_lay.itemAt(i).widget(), ReminderChip)]
titles = [c.item["title"] for c in chips]
print("提醒栏顺序:", titles)
assert titles == ["提醒B", "提醒A", "提醒C"], titles
print("PASS: 已完成提醒不显示，未完成按时间升序")

# 拖拽：把 提醒A 拖到最下方（第 3 位）
container = win._find_group_container("reminder")
assert container is not None, "reminder 容器未找到"
win._drag_start(chips[0])
gpos = container.mapToGlobal(QPoint(5, chips[2].y() + chips[2].height()))
win._drag_move(gpos)
win._drag_end()
for _ in range(5):
    app.processEvents()

# 拖拽后提醒栏顺序（refresh 后保持）
win.refresh(fit=False)
for _ in range(5):
    app.processEvents()
chips2 = [win.reminder_lay.itemAt(i).widget() for i in range(win.reminder_lay.count()) if isinstance(win.reminder_lay.itemAt(i).widget(), ReminderChip)]
titles2 = [c.item["title"] for c in chips2]
print("拖拽后顺序:", titles2)
assert titles2 == ["提醒A", "提醒C", "提醒B"], titles2
order_map = {c.item["title"]: c.item.get("order", 0) for c in chips2}
print("order:", order_map)
assert order_map["提醒A"] == 10 and order_map["提醒C"] == 20 and order_map["提醒B"] == 30
print("PASS: 提醒拖拽排序 + 持久化 order")

# 高度钳制：把窗口移到屏幕中部，内容超高时底部不超屏幕
from PySide6.QtGui import QGuiApplication
scr = QGuiApplication.primaryScreen().availableGeometry()
win.move(scr.right() - 500, scr.top() + 400)
win._user_resized = False
win._fit_height()
bottom = win.y() + win.height()
print(f"窗口 y={win.y()} 高={win.height()} 底部={bottom} 屏幕底={scr.bottom()}")
assert bottom <= scr.bottom(), f"窗口底部超出屏幕: {bottom} > {scr.bottom()}"
print("PASS: 内容超高时窗口不超出屏幕底部")

win.close()
print("ALL PASS")
