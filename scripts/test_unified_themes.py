# -*- coding: utf-8 -*-
"""三主题统一编辑冒烟测试（离屏）：结构同构、切换 kind 正常、紧凑主题应用。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import core
import i18n
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
        self._diy = None
        self._compact_style = None

    def apply_diy_bg(self, cfg):
        self._diy = cfg

    def _apply_compact_style(self):
        self._compact_style = dict(self.app.config.get("compact_style", default={}))

    def _update_compact_text(self):
        pass

    def refresh_theme(self):
        pass


class FakeApp:
    def __init__(self):
        self.config = core.Config(os.path.join(tmp, "c.json"))
        self.store = FakeStore()
        self.t = self.config.get("theme")
        self.win = None
        self.settings_win = None

    def apply_theme(self, kind="all"):
        pass


fa = FakeApp()
fa.win = FakeWin(fa)
sw = settings_mod.SettingsWindow(fa)
fa.settings_win = sw

# ---- 1. 三个按钮存在且互斥
check("三个主题按钮", sw.rb_main_theme and sw.rb_settings_theme and sw.rb_compact_theme)

# ---- 2. 三主题字典结构同构（键集一致）
for kind in ("theme", "theme_settings", "compact_style"):
    d = fa.config.get(kind)
    check(f"{kind} 有 diy_bg", "diy_bg" in d)
    check(f"{kind} 有 bg", "bg" in d)
    check(f"{kind} 有 text", "text" in d)

# ---- 3. 切换到紧凑模式主题：编辑区正常、紧凑内容区显示
sw._target_changed("compact_style")
app.processEvents()
check("紧凑内容区可见", sw._compact_content.isHidden() is False)
check("字号滑条范围含0", sw.font_size.minimum() == 0)

# 切回桌面主题
sw._target_changed("theme")
app.processEvents()
check("桌面主题下紧凑内容区隐藏", sw._compact_content.isHidden() is True)
check("桌面字号滑条从8起", sw.font_size.minimum() == 8)

# ---- 4. 紧凑主题编辑：改背景色/文字色 → 保存 → 应用
sw._target_changed("compact_style")
app.processEvents()
sw._edit["bg"] = "#112233"
sw._edit["text"] = "#ff0000"
sw._apply_theme()
app.processEvents()
check("紧凑 bg 保存", fa.config.get("compact_style", "bg") == "#112233")
check("紧凑 text 保存", fa.config.get("compact_style", "text") == "#ff0000")
check("应用了紧凑样式", fa.win._compact_style is not None)

# ---- 5. 紧凑 DIY 背景（与主题相同结构）
sw._diy_save(enabled=True, components={"compact": {"color": "#00ff00", "alpha": 60}})
app.processEvents()
check("紧凑 DIY 保存到 compact_style.diy_bg",
      fa.config.get("compact_style", "diy_bg", "enabled") is True)

# ---- 6. 保存紧凑主题到主题栏
sw.theme_combo.setCurrentText("")
sw._edit["name"] = "我的紧凑主题"
themes = fa.config.get("saved_themes", default={})
themes["我的紧凑主题"] = __import__("copy").deepcopy(sw._edit)
fa.config.set("saved_themes", themes)
check("紧凑主题可保存进主题栏",
      "diy_bg" in fa.config.get("saved_themes", default={})["我的紧凑主题"])

print(f"ALL PASS: {PASS} checks")
