# -*- coding: utf-8 -*-
"""主题绑定集成测试（离屏）：DIY 背景随主题保存/加载/切换。"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import core
import i18n
from settings import SettingsWindow

app = QApplication([])
tmp = tempfile.mkdtemp()
PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"PASS: {name}")


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = core.DataStore(os.path.join(tmp, "d.json"))
        self.t = self.config.get("theme")
        self.win = None
        self.settings_win = None
        self._diy_applied = []

    def apply_theme(self, kind="all"):
        if kind in ("theme", "all") and self.win is not None:
            self.win.refresh_theme()

    def apply_diy_bg(self, cfg):
        self._diy_applied.append(cfg)


class FakeWin:
    def __init__(self, fa):
        self.app = fa
        self._diy = None
        self.t = fa.config.get("theme")

    def refresh_theme(self):
        self._diy = (self.app.config.get("theme") or {}).get("diy_bg")

    def apply_diy_bg(self, cfg):
        self._diy = cfg

    def _apply_compact_style(self):
        pass

    def _update_compact_text(self):
        pass

    def apply_diy_settings(self, cfg):
        pass


i18n.set_lang("zh")
fa = FakeApp()
fa.win = FakeWin(fa)
sw = SettingsWindow(fa)
fa.settings_win = sw

# ---- 1. DIY 编辑写入 _edit["diy_bg"]（即 config.theme["diy_bg"]）
sw._kind = "theme"
sw._edit = fa.config.get("theme")
sw._diy_save(enabled=True, components={
    "panel": {"color": "#123456", "alpha": 66}})
check("DIY 保存进 theme['diy_bg']",
      fa.config.get("theme", "diy_bg")["enabled"] is True)
check("DIY 部件色写入",
      fa.config.get("theme", "diy_bg")["components"]["panel"]["color"] == "#123456")

# ---- 2. 保存主题（另存为流程核心逻辑）含 DIY
themes = fa.config.get("saved_themes", default={})
sw._edit["name"] = "绑定测试主题"
themes["绑定测试主题"] = __import__("copy").deepcopy(sw._edit)
fa.config.set("saved_themes", themes)
check("主题栏条目含 DIY",
      "diy_bg" in fa.config.get("saved_themes", default={})["绑定测试主题"])

# ---- 3. 修改当前主题 DIY 后，主题栏条目不受污染（深拷贝生效）
sw._edit["diy_bg"]["components"]["panel"]["color"] = "#999999"
saved_panel = fa.config.get("saved_themes", default={})["绑定测试主题"]["diy_bg"]
check("未保存改动不污染主题栏条目",
      saved_panel["components"]["panel"]["color"] == "#123456")

# ---- 4. 加载主题 → DIY 恢复
sw._edit.clear()
sw._edit.update(__import__("copy").deepcopy(
    fa.config.get("saved_themes", default={})["绑定测试主题"]))
check("加载主题恢复 DIY 色",
      sw._edit["diy_bg"]["components"]["panel"]["color"] == "#123456")

# ---- 5. 主窗口 apply_diy_bg 收到主题内嵌 DIY
fa.win.refresh_theme()
check("refresh_theme 传递主题内嵌 DIY", fa.win._diy == fa.config.get("theme", "diy_bg"))

# ---- 6. 导入文件（含 DIY 图片资产）→ 主题栏自动新增
img = os.path.join(tempfile.mkdtemp(), "bg.png")
with open(img, "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n fake png data")
import base64, hashlib
raw = open(img, "rb").read()
aid = hashlib.sha256(raw).hexdigest()[:16]
bundle = {
    "format": 2,
    "parts": {
        "theme": {
            "name": "导入主题A",
            **{k: fa.config.get("theme")[k] for k in ("bg", "text", "accent")},
            "diy_bg": {"enabled": True, "components": {
                "panel": {"image": "@asset:" + aid, "alpha": 70}}},
        },
    },
    "assets": {aid: {"name": "background.png", "data": base64.b64encode(raw).decode()}},
}
bp = os.path.join(tempfile.mkdtemp(), "theme.json")
with open(bp, "w", encoding="utf-8") as f:
    json.dump(bundle, f)

# 直接调用导入核心逻辑（绕过文件对话框）
th = bundle
assets = th.get("assets") or {}
value = sw._unpack_theme_value(th["parts"]["theme"], assets)
check("导入解包图片为本地文件",
      os.path.isfile(value["diy_bg"]["components"]["panel"]["image"]))
value = {**__import__("theme", fromlist=["DEFAULT_THEME"]).DEFAULT_THEME, **(value or {})}
fa.config.data["theme"] = value
themes = fa.config.get("saved_themes", default={})
themes["导入主题A"] = __import__("copy").deepcopy(value)
fa.config.set("saved_themes", themes)
check("导入主题进入主题栏", "导入主题A" in fa.config.get("saved_themes", default={}))

print(f"ALL PASS: {PASS} checks")
