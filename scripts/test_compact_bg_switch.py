# -*- coding: utf-8 -*-
"""回归测试：切换主题后紧凑图片背景正确消失/恢复（离屏）。"""
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
        self.compact_bg = ("", "", 100)
        self.last_cs = None

    def refresh_theme(self):
        pass

    def _apply_compact_style(self):
        cfg = self.app.config.get("compact_style", default={}) or {}
        self.last_cs = dict(cfg)
        db = cfg.get("diy_bg") or {}
        if db.get("enabled"):
            c = (db.get("components") or {}).get("compact") or {}
            self.compact_bg = (c.get("color") or "", c.get("image") or "",
                               int(c.get("alpha", 100)))
        elif cfg.get("bg"):
            self.compact_bg = (cfg["bg"], "", 100)
        else:
            self.compact_bg = ("", "", 100)

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
            self.settings_win.t = self.config.get("theme_settings")
        if kind in ("compact_style", "all"):
            self.win._apply_compact_style()


fa = FakeApp()
fa.win = FakeWin(fa)
sw = settings_mod.SettingsWindow(fa)
fa.settings_win = sw
sw.show()
app.processEvents()

# ---- 准备主题A：带紧凑图片背景；主题B：无紧凑配置
img = os.path.join(tmp, "bg.png")
with open(img, "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n fake png data")
saved_img = core.save_theme_image(img)

themes = fa.config.get("saved_themes", default={})
themes["带图主题"] = {
    "theme": dict(theme_mod.DEFAULT_THEME),
    "theme_settings": dict(theme_mod.DEFAULT_THEME_SETTINGS),
    "compact_style": {
        "name": "带图主题", "components": ["clock"],
        "diy_bg": {"enabled": True,
                   "components": {"compact": {"image": saved_img, "alpha": 70}}},
    },
}
themes["纯色主题"] = {
    "theme": dict(theme_mod.DEFAULT_THEME),
    "theme_settings": dict(theme_mod.DEFAULT_THEME_SETTINGS),
    "compact_style": {},
}
fa.config.set("saved_themes", themes)
sw._refresh_theme_combo()

# ---- 1. 加载带图主题 → 紧凑条有图片
sw.theme_combo.setCurrentText("带图主题")
sw._load_theme()
app.processEvents()
check("带图主题：紧凑背景为图片", fa.win.compact_bg[1] == saved_img)

# ---- 2. 切换到纯色主题 → 图片消失
sw.theme_combo.setCurrentText("纯色主题")
sw._load_theme()
app.processEvents()
check("纯色主题：紧凑背景无图片", fa.win.compact_bg[1] == "")
check("纯色主题：紧凑背景无色", fa.win.compact_bg[0] == "")
check("加载后 compact_style.diy_bg.enabled 为 False",
      (fa.config.get("compact_style", "diy_bg") or {}).get("enabled") is False)

# ---- 3. 切回带图主题 → 图片恢复
sw.theme_combo.setCurrentText("带图主题")
sw._load_theme()
app.processEvents()
check("切回带图主题：图片恢复", fa.win.compact_bg[1] == saved_img)

# ---- 4. 旧格式主题条目（单 dict，无 compact_style）→ 也清空紧凑背景
themes["旧格式"] = {"theme": dict(theme_mod.DEFAULT_THEME),
                    "theme_settings": dict(theme_mod.DEFAULT_THEME_SETTINGS)}
fa.config.set("saved_themes", themes)
sw._refresh_theme_combo()
sw.theme_combo.setCurrentText("旧格式")
sw._load_theme()
app.processEvents()
check("旧格式主题：紧凑背景清空", fa.win.compact_bg[1] == "")

print(f"ALL PASS: {PASS} checks")
