"""验证：用户自定义高度锁定（_user_resized）——缩放后锁定，操作/重启后高度保持。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

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


def make_win(cfg_path, store_path):
    fa = FakeApp()
    fa.config = core.Config(cfg_path)
    fa.store = core.DataStore(store_path)
    fa.t = fa.config.get("theme")
    i18n.set_lang("zh")
    win = FloatWindow(fa)
    fa.win = win
    win.show()
    # 等 _fit_height_async 完成
    for _ in range(20):
        app.processEvents()
    return fa, win


def pump(n=25):
    for _ in range(n):
        app.processEvents()


fa0 = FakeApp()
for i in range(8):
    it = core.new_item("todo", f"任务{i}")
    it["created"] = f"2026-08-0{(i % 9) + 1} 09:00"
    it["deadline"] = it["created"]
    fa0.store.items.append(it)

cfg_p = os.path.join(tmp, "c.json")
store_p = os.path.join(tmp, "d.json")
fa0.config.save()

# ---- 第一次启动：内容自适应高度
fa, win = make_win(cfg_p, store_p)
h_fit = win.height()
print(f"首次自适应高度: {h_fit}")
assert h_fit >= 160, "fit 应至少到最小高度 160"
assert win._user_resized is False

# ---- 模拟用户缩放高度（边缘拖拽释放 → 置 user_resized + save_geometry）
win.resize(win.width(), h_fit + 300)
win._user_resized = True   # 释放处理中置位（事件路径等价）
win.save_geometry()
h_user = win.height()
print(f"用户自定义高度: {h_user}")

# ---- 操作（添加事项 → refresh fit）→ 高度保持
fa.store.add(core.new_item("todo", "新任务"))
win.refresh(fit=True)
pump()
print(f"添加后高度: {win.height()} (期望保持 {h_user})")
assert win.height() == h_user, "操作后高度不应重置"
win.close()
pump()

# ---- 重启：新实例从 config 恢复 user_resized + h
fa2, win2 = make_win(cfg_p, store_p)
print(f"重启恢复高度: {win2.height()} user_resized={win2._user_resized}")
assert win2._user_resized is True
assert win2.height() == h_user, "重启后应恢复用户自定义高度"
# 重启后操作 → 高度保持
fa2.store.add(core.new_item("todo", "重启后新任务"))
win2.refresh(fit=True)
pump()
assert win2.height() == h_user, "重启后操作不应重置高度"
print(f"重启后操作高度: {win2.height()} (保持)")
win2.close()

# ---- 展开状态记忆：折叠 → 重启恢复
fa3, win3 = make_win(cfg_p, store_p)
ykey = "y2026"
assert win3.expanded.get(ykey, True), "首次默认展开"
win3.toggle_group(ykey)
pump()
print(f"折叠后 expanded[{ykey}]={win3.expanded.get(ykey)} "
      f"config={fa3.config.get('window', 'expanded', default={}).get(ykey)}")
assert win3.expanded.get(ykey) is False
assert fa3.config.get("window", "expanded", default={}).get(ykey) is False, "折叠状态应写入 config"
win3.close()
pump()
fa4, win4 = make_win(cfg_p, store_p)
print(f"重启后 expanded[{ykey}]={win4.expanded.get(ykey)} (期望 False=保持折叠)")
assert win4.expanded.get(ykey) is False, "重启后应恢复折叠状态"
# 重启后 toggle 也应持久化
win4.toggle_group(ykey)
pump()
assert fa4.config.get("window", "expanded", default={}).get(ykey) is True
print(f"再展开后 config={fa4.config.get('window','expanded',default={}).get(ykey)} (期望 True)")
win4.close()

print("ALL PASS: 用户自定义高度锁定+持久化正常；展开状态记忆正常")
