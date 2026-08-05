# -*- coding: utf-8 -*-
"""回归测试：紧凑模式 DIY 背景与主题同构（compact_style.diy_bg），跟随主题切换（离屏）。"""
import os
import sys
import tempfile
import json

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

# ---- 1. 紧凑 DIY 背景：启用 + 设置图片（存 compact_style.diy_bg）
sa = core.save_theme_image(img_a)
cfg = fa.config.get("compact_style")
cfg.setdefault("diy_bg", {})["enabled"] = True
cfg["diy_bg"]["components"] = {"compact": {"color": "", "image": sa, "alpha": 80}}
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("紧凑 DIY 背景图应用", win.compact_bar._bg_image == sa)
check("紧凑 DIY 透明度应用", win.compact_bar._bg_alpha == 80)

# ---- 2. 修改紧凑 DIY 图片 → 应用
sb = core.save_theme_image(img_b)
cfg = fa.config.get("compact_style")
cfg["diy_bg"]["components"]["compact"]["image"] = sb
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("更新紧凑背景图", win.compact_bar._bg_image == sb)

# ---- 3. 紧凑 DIY 关闭 → 走紧凑 bg 或 QSS
cfg = fa.config.get("compact_style")
cfg["diy_bg"]["enabled"] = False
cfg["bg"] = "#334455"
fa.config.set("compact_style", cfg)
win._apply_compact_style()
check("DIY 关闭时用紧凑 bg", win.compact_bar._bg_color == "#334455")

# ---- 4. 旧结构迁移：text_color/diy → text/diy_bg
old = {
    "theme": dict(fa.config.get("theme")),
    "theme_settings": {},
    "compact_style": {
        "components": ["clock"], "text_color": "#ffaa00",
        "diy": {"enabled": True,
                "components": {"compact": {"image": sa, "alpha": 70}}}},
}
p2 = os.path.join(tmp, "c2.json")
with open(p2, "w", encoding="utf-8") as f:
    json.dump(old, f)
cfg2 = core.Config(p2)
cs2 = cfg2.data.get("compact_style") or {}
check("迁移：text_color → text", cs2.get("text") == "#ffaa00")
check("迁移：diy → diy_bg", (cs2.get("diy_bg") or {}).get("enabled") is True)
mig_comp = ((cs2.get("diy_bg") or {}).get("components") or {}).get("compact") or {}
check("迁移：紧凑背景保留", mig_comp.get("image") == sa)

print(f"ALL PASS: {PASS} checks")
win.close()
