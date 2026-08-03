"""进程内复现幽灵窗口：全局监控 QEvent::Show/Hide，找出被反复 show/hide 的顶层 QWidget。
模拟真实操作（添加/拖拽/对话框/设置窗），观察幽灵窗口的身份（类型/名称/父级）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QFrame
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtTest import QTest

import core
import i18n
from main_window import FloatWindow

app = QApplication([])
tmp = tempfile.mkdtemp()

SHOWN = {}
HIDDEN = {}


class Watcher(QObject):
    def eventFilter(self, obj, ev):
        try:
            if isinstance(obj, QWidget) and obj.isWindow():
                if ev.type() == QEvent.Show:
                    key = (type(obj).__name__, obj.objectName(), obj.windowTitle())
                    SHOWN[key] = SHOWN.get(key, 0) + 1
                    parent = obj.parentWidget()
                    print(f"SHOW  type={type(obj).__name__} name={obj.objectName()!r} "
                          f"title={obj.windowTitle()!r} geo={obj.geometry().getRect()} "
                          f"flags={int(obj.windowFlags())} parent={type(parent).__name__ if parent else None}")
                elif ev.type() == QEvent.Hide:
                    key = (type(obj).__name__, obj.objectName(), obj.windowTitle())
                    HIDDEN[key] = HIDDEN.get(key, 0) + 1
                    print(f"HIDE  type={type(obj).__name__} name={obj.objectName()!r} "
                          f"title={obj.windowTitle()!r}")
        except Exception as e:
            print("watcher err", e)
        return False


app.installEventFilter(Watcher())


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
for i in range(5):
    it = core.new_item("todo", f"任务{i}")
    it["created"] = f"2026-08-0{(i % 9) + 1} 09:00"
    it["deadline"] = it["created"]
    fa.store.items.append(it)

i18n.set_lang("zh")
print("=== creating window ===")
win = FloatWindow(fa)
fa.win = win
win.show()
for _ in range(10):
    app.processEvents()

print("=== 操作1: 添加事项 → refresh(fit=True) ===")
fa.store.add(core.new_item("todo", "新任务"))
win.refresh(fit=True)
for _ in range(10):
    app.processEvents()
print(f"高度={win.height()} visible={win.isVisible()}")

print("=== 操作2: 完成切换 → refresh ===")
fa.store.items[0]["done"] = True
fa.store.save()
win.refresh(fit=True)
for _ in range(10):
    app.processEvents()

print("=== 操作3: 连续 refresh ===")
for _ in range(3):
    win.refresh(fit=True)
for _ in range(10):
    app.processEvents()

print("=== 操作4: 拖拽指示条 setParent(None) 流程 ===")
ind = QFrame(fixedHeight=3)
ind.setStyleSheet("background-color:red;")
lay = win.content_lay
ind.setParent(None)
lay.insertWidget(0, ind)
ind.show()
for _ in range(3):
    app.processEvents()
ind.setParent(None)
for _ in range(3):
    app.processEvents()
ind.deleteLater()
for _ in range(3):
    app.processEvents()

print("=== 汇总 ===")
for k, v in SHOWN.items():
    print(f"SHOW x{v}: {k}")
for k, v in HIDDEN.items():
    print(f"HIDE x{v}: {k}")
win.close()
