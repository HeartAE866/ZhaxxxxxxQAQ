# -*- coding: utf-8 -*-
"""三合一主题测试：保存/加载同步三配置；删除恢复默认；主题栏仅设置栏页显示（离屏）。"""
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import core
import i18n
import theme as theme_mod
import settings as settings_mod

app = QApplication([])
tmp = tempfile.mkdtemp()
i18n.set_lang("zh")
PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"PASS: {name}")


class FakeStore:
    items = []

    def all_tags(self):
        return []

    def find(self, i):
        return i


class FakeWin:
    def __init__(self, fa):
        self.app = fa
        self.refresh = 0
        self.compact = 0

    def refresh_theme(self):
        self.refresh += 1

    def _apply_compact_style(self):
        self.compact += 1

    def _update_compact_text(self):
        pass

    def apply_diy_bg(self, cfg):
        pass


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = FakeStore()
        self.t = self.config.get("theme")
        self.win = None
        self.settings_win = None

    def apply_theme(self, kind="all"):
        if kind in ("theme", "all"):
            self.t = self.config.get("theme")
            self.win.refresh_theme()
        if kind in ("theme_settings", "all") and self.settings_win:
            ts = self.config.get("theme_settings")
            self.settings_win.t = ts
        if kind in ("compact_style", "all"):
            self.win._apply_compact_style()


fa = FakeApp()
fa.win = FakeWin(fa)
sw = settings_mod.SettingsWindow(fa)
fa.settings_win = sw
sw.show()
app.processEvents()

# ---- 1. 主题栏仅在设置栏主题页可见
sw._target_changed("theme")
app.processEvents()
check("桌面页隐藏主题栏", sw._theme_bar.isHidden() is True)
sw._target_changed("compact_style")
app.processEvents()
check("紧凑页隐藏主题栏", sw._theme_bar.isHidden() is True)
sw._target_changed("theme_settings")
app.processEvents()
check("设置栏页显示主题栏", sw._theme_bar.isHidden() is False)

# ---- 2. 保存三合一：改三个主题后另存
fa.config.data["theme"]["bg"] = "#111111"
fa.config.data["theme_settings"]["bg"] = "#222222"
fa.config.data["compact_style"]["bg"] = "#333333"
sw._save_current_theme()   # combo 默认选中第一个（深色磨砂）→ 覆盖保存
themes = fa.config.get("saved_themes", default={})
first = next(iter(themes))
entry = themes[first]
check("保存条目为三合一", "theme" in entry and "theme_settings" in entry
      and "compact_style" in entry)
check("保存含桌面bg", entry["theme"].get("bg") == "#111111")
check("保存含设置栏bg", entry["theme_settings"].get("bg") == "#222222")
check("保存含紧凑bg", entry["compact_style"].get("bg") == "#333333")

# ---- 3. 加载三合一：改当前配置后加载 → 三处同步恢复
fa.config.data["theme"]["bg"] = "#999999"
fa.config.data["theme_settings"]["bg"] = "#999999"
fa.config.data["compact_style"]["bg"] = "#999999"
sw.theme_combo.setCurrentText(first)
sw._load_theme()
check("加载恢复桌面bg", fa.config.get("theme", "bg") == "#111111")
check("加载恢复设置栏bg", fa.config.get("theme_settings", "bg") == "#222222")
check("加载恢复紧凑bg", fa.config.get("compact_style", "bg") == "#333333")

# ---- 4. 删除主题 → 恢复默认
sw.theme_combo.setCurrentText(first)
orig_ask = settings_mod.ConfirmDialog.ask
settings_mod.ConfirmDialog.ask = staticmethod(
    lambda *a, **k: (True, False))
sw._delete_theme()
settings_mod.ConfirmDialog.ask = orig_ask
check("删除后主题栏移除该条目", first not in fa.config.get("saved_themes", default={}))
check("删除后桌面恢复默认", fa.config.get("theme", "bg") == theme_mod.DEFAULT_THEME["bg"])

# ---- 5. 旧格式迁移：单 dict → 三合一
old = {
    "theme": dict(theme_mod.DEFAULT_THEME),
    "theme_settings": dict(theme_mod.DEFAULT_THEME_SETTINGS),
    "saved_themes": {"旧主题": dict(theme_mod.DEFAULT_THEME)},
}
p2 = os.path.join(tmp, "c2.json")
with open(p2, "w", encoding="utf-8") as f:
    json.dump(old, f)
cfg2 = core.Config(p2)
e2 = cfg2.data["saved_themes"]["旧主题"]
check("旧条目迁移为三合一", "theme" in e2 and e2["theme"].get("bg"))

print(f"ALL PASS: {PASS} checks")
