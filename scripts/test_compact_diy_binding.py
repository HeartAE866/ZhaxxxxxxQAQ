# -*- coding: utf-8 -*-
"""回归测试：紧凑模式图片背景绑定主题，切换主题后自动跟随（离屏）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import core
import i18n
from main_window import FloatWindow

app = QApplication([])
tmp = tempfile.mkdtemp()
i18n.set_lang("zh")
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

    def apply_theme(self, kind="all"):
        if kind in ("theme", "all"):
            self.t = self.config.get("theme")
            self.win.refresh_theme()

    def open_folder_flow(self, i): pass
    def toggle_compact(self, v=False): pass
    def quick_record_menu(self): pass
    def refresh_priorities(self): pass


# 造两张测试图片
img_a = os.path.join(tmp, "a.png")
img_b = os.path.join(tmp, "b.png")
for p in (img_a, img_b):
    with open(p, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n fake png data")

fa = FakeApp()
win = FloatWindow(fa)
fa.win = win
win.show()
fa.config.set("window", "compact", True)
win._update_compact_text()
app.processEvents()

# ---- 1. 开启紧凑 DIY 并把背景图片写入主题 A
sa = core.save_theme_image(img_a)
cfg = fa.config.get("compact_style")
cfg.setdefault("diy", {})["enabled"] = True
fa.config.set("compact_style", cfg)
th = fa.config.get("theme")
th.setdefault("diy_bg", {}).setdefault("components", {})["compact"] = {
    "image": sa, "alpha": 80}
fa.config.set("theme", th)
win._apply_compact_style()
check("紧凑 DIY 启用时背景图来自主题", win.compact_bar._bg_image == sa)
check("紧凑 DIY 透明度应用", win.compact_bar._bg_alpha == 80)

# ---- 2. 切换到主题 B（不同背景图），refresh_theme 后紧凑条跟随
sb = core.save_theme_image(img_b)
fa.config.set("theme", {
    **fa.config.get("theme"),
    "name": "主题B",
    "diy_bg": {"enabled": False,
               "components": {"compact": {"image": sb, "alpha": 50}}},
})
fa.apply_theme("theme")
app.processEvents()
check("切换主题后紧凑背景图跟随", win.compact_bar._bg_image == sb)
check("切换主题后紧凑透明度跟随", win.compact_bar._bg_alpha == 50)

# ---- 3. 紧凑 DIY 未启用时跟随主题 QSS（透明背景）
cfg = fa.config.get("compact_style")
cfg.setdefault("diy", {})["enabled"] = False
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("紧凑 DIY 关闭时透明走 QSS", win.compact_bar._bg_image == "")

# ---- 4. 旧配置迁移：compact_style.diy.components.compact → theme.diy_bg
old = {
    "theme": dict(fa.config.get("theme")),
    "theme_settings": {},
    "compact_style": {
        "components": ["clock"], "diy": {
            "enabled": True,
            "components": {"compact": {"image": sa, "alpha": 70}}}},
}
p2 = os.path.join(tmp, "c2.json")
with open(p2, "w", encoding="utf-8") as f:
    import json
    json.dump(old, f)
cfg2 = core.Config(p2)
mig = (cfg2.data.get("theme") or {}).get("diy_bg", {}).get("components", {}) \
    .get("compact") or {}
check("迁移：紧凑背景入主题", mig.get("image") == sa)
check("迁移：透明度保留", mig.get("alpha") == 70)
check("迁移：enabled 开关保留",
      (cfg2.data.get("compact_style") or {}).get("diy", {}).get("enabled") is True)

print(f"ALL PASS: {PASS} checks")
win.close()
