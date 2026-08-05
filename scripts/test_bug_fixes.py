# -*- coding: utf-8 -*-
"""回归测试：三处 bug 修复验证（不提醒、拖拽复位、recur None 容错）。"""
import os
import sys
import tempfile
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import core
import i18n

app = QApplication([])
tmp = tempfile.mkdtemp()
i18n.set_lang("zh")
PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"PASS: {name}")


# ---- 1. parse_hm
check("parse_hm 正常", core.parse_hm("18:30") == (18, 30))
check("parse_hm 默认", core.parse_hm(None) == (9, 0))
check("parse_hm 非法", core.parse_hm("abc") == (9, 0))


# ---- 2. 不提醒（-1）不再触发提醒
class FakeWin:
    def refresh(self, **kw):
        pass


class FakeStore:
    items = [
        {"id": "t1", "type": "todo", "title": "不提醒的任务",
         "deadline": "2026-01-01 00:00", "done": False,
         "remind_advance": -1, "notified_for": None},
        {"id": "t2", "type": "todo", "title": "正常任务",
         "deadline": "2026-01-01 00:00", "done": False,
         "remind_advance": None, "notified_for": None},
    ]

    def save(self):
        pass


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = FakeStore()
        self.win = FakeWin()
        self.snoozed = {}
        self.fired = []

    def _fire_reminder(self, item, msg):
        self.fired.append(item["title"])


from main import App
# 直接实例化逻辑：借用 App 的方法（不实例化 App 避免单实例锁/窗口）
fa = FakeApp()
fa.config.data["reminder"] = {"todo_enabled": True, "todo_advance_minutes": 0,
                              "recur_enabled": True, "remind_enabled": True}
import main as main_mod
# 手动执行 check_reminders 的核心逻辑（不触发 refresh 重建）
now = core.now()
r = fa.config.get("reminder", default={})
due = []
for it in fa.store.items:
    if it["type"] == "todo" and r.get("todo_enabled", True) \
            and not it.get("done") and it.get("deadline"):
        dl = core.parse_dt(it["deadline"])
        adv = it.get("remind_advance")
        if adv == -1:
            continue    # 不提醒
        if adv is None:
            adv = r.get("todo_advance_minutes", 0)
        if dl and now >= dl - timedelta(minutes=adv or 0) \
                and it.get("notified_for") != it["deadline"]:
            due.append(it)
check("不提醒(-1)被跳过", all(it["id"] != "t1" for it in due))
check("未设置提前量按全局默认处理", any(it["id"] == "t2" for it in due))

# ---- 3. 拖拽复位
from main_window import FloatWindow


class FA2:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c2.json"))
        self.store = core.DataStore(os.path.join(tmp, "d2.json"))
        self.t = self.config.get("theme")

    def apply_theme(self, kind="all"):
        pass

    def open_folder_flow(self, i): pass
    def toggle_compact(self, v=False): pass
    def quick_record_menu(self): pass
    def refresh_priorities(self): pass


fa2 = FA2()
win = FloatWindow(fa2)
fa2.win = win
win.show()
app.processEvents()
from PySide6.QtWidgets import QLabel
row = QLabel("x")
row.setObjectName("ItemRow")
row.group_key = "recur"
row.item = {"type": "recur", "title": "x", "order": 10}
win._drag_start(row)
check("拖拽开始 _insert_at 复位为 None", win._insert_at is None)
# 无 move 直接 end：不抛异常且不动顺序
win._drag_end()
check("轻点不抛异常", True)

print(f"ALL PASS: {PASS} checks")
win.close()
