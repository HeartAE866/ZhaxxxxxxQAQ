# -*- coding: utf-8 -*-
"""设置窗口：个性化 / 文件夹 / 提醒 / 快捷键 / 数据管理 / 日志 / 关于。"""
from __future__ import annotations

import json
import os
import shutil
import traceback
from datetime import datetime

from PySide6.QtCore import QTime, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QInputDialog,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QScrollArea, QSizePolicy, QSlider,
                               QStackedWidget, QTextEdit, QTimeEdit,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

import core
import theme as theme_mod
import updater
from i18n import tr
from widgets import (FramelessDialog, ColorDialog, ConfirmDialog, HotkeyEdit,
                     Toast, combo_text, rounded_pixmap, BgFrame, CountdownDialog)

MAIN_COLOR_ITEMS = [
    ("bg", "主背景色", True), ("text", "文字颜色", False),
    ("done_text", "已完成文字色", False), ("hover", "悬停高亮色", False),
    ("accent", "强调色", False), ("high", "优先级·高", False),
    ("mid", "优先级·中", False), ("low", "优先级·低", False),
]

SETTINGS_COLOR_ITEMS = [
    ("bg", "主背景色", True), ("text", "文字颜色", False),
    ("hover", "悬停高亮色", False), ("accent", "强调色", False),
]

CUSTOM_ACTIONS = [("quick_record", "快速添加工作记录"),
                  ("quick_todo", "快速开始新工作"),
                  ("quick_recur", "快速添加循环任务"),
                  ("search", "聚焦搜索框"),
                  ("toggle_compact", "切换紧凑模式"),
                  ("show_hide", "显示/隐藏主界面")]


class SettingsWindow(FramelessDialog):
    changed = Signal()

    def __init__(self, app):
        super().__init__(None, app.config.get("theme_settings"), tr("设置"),
                         width=880)
        self.setWindowModality(Qt.NonModal)   # 设置窗不阻塞桌面主窗
        self.app = app
        self.t = app.config.get("theme_settings")
        for _k in ("done_text", "high", "mid", "low"):
            self.t.pop(_k, None)
        self._kind = "theme_settings"
        self._edit = self.t
        self.setStyleSheet(theme_mod.build_qss(self.t))
        self.setMinimumHeight(480)
        self._theme_timer = QTimer(self, singleShot=True, interval=120,
                                   timeout=self._apply_theme)
        self._diy_save_timer = QTimer(self, singleShot=True, interval=200,
                                      timeout=self.app.config.save)

        row = QHBoxLayout()
        self.nav = QListWidget(fixedWidth=130)
        self.nav.setUniformItemSizes(True)
        self.nav.setWordWrap(False)
        self.nav.setSpacing(2)
        self.pages = QStackedWidget()
        row.addWidget(self.nav)
        row.addWidget(self.pages, 1)
        self.body.addLayout(row)

        self._page_personal()
        self._page_folder()
        self._page_remind()
        self._page_hotkey()
        self._page_data()
        self._page_logs()
        self._page_about()
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        for i in range(self.nav.count()):
            self.nav.item(i).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # 设置窗内回车不应触发任何按钮（防止误关/误操作）
        for b in self.findChildren(QPushButton):
            b.setAutoDefault(False)
        self.apply_diy_settings(self.app.config.get("diy_bg_settings", default={}))

    def apply_diy_settings(self, cfg: dict):
        """应用设置栏 DIY 背景（面板背景色或图片，0-100 不透明度）。"""
        cfg = cfg or {}
        enabled = bool(cfg.get("enabled"))
        radius = (self.t or {}).get("radius", 12)
        if isinstance(self.panel, BgFrame):
            self.panel.set_bg_radius(radius)
            if enabled:
                c = (cfg.get("components") or {}).get("panel") or {}
                self.panel.set_bg(c.get("color") or "", c.get("image") or "",
                                  int(c.get("alpha", 100)))
            else:
                self.panel.set_bg("", "", 100)

    # ================================================================ 个性化
    def _page_personal(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignTop)
        # 内容较多，放入滚动区，支持滑条/滚轮向下查看；横向可滚动避免文字超出
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(w)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.nav.addItem(tr("🎨 个性化"))
        self.pages.addWidget(scroll)

        # 美化对象：桌面应用主题 / 设置栏主题（按钮式，选中高亮明显）
        # ---- 语言（切换后重启生效）
        lrow = QHBoxLayout()
        lrow.addWidget(QLabel(tr("语言")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("简体中文", "zh")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCurrentIndex(
            0 if self.app.config.get("language", default="zh") == "zh" else 1)
        self.lang_combo.currentIndexChanged.connect(self._lang_changed)
        lrow.addWidget(self.lang_combo, 1)
        lay.addLayout(lrow)

        trow0 = QHBoxLayout()
        trow0.addWidget(QLabel(tr("美化对象")))
        self.rb_main_theme = QPushButton(tr("🖥 桌面应用主题"), checkable=True,
                                         objectName="ThemeToggle")
        self.rb_settings_theme = QPushButton(tr("⚙ 设置栏主题"), checkable=True,
                                             objectName="ThemeToggle")
        self._theme_group = QButtonGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_group.addButton(self.rb_main_theme)
        self._theme_group.addButton(self.rb_settings_theme)
        self.rb_settings_theme.setChecked(True)
        for b, kind in [(self.rb_main_theme, "theme"),
                        (self.rb_settings_theme, "theme_settings")]:
            b.toggled.connect(
                lambda checked, k=kind: self._target_changed(k) if checked else None)
        trow0.addWidget(self.rb_main_theme)
        trow0.addWidget(self.rb_settings_theme)
        trow0.addStretch()
        lay.addLayout(trow0)

        self.color_hint = QLabel()
        lay.addWidget(self.color_hint)
        grid_w = QWidget()
        self._color_grid = QGridLayout(grid_w)
        self._color_grid.setHorizontalSpacing(14)
        self._color_btns = {}
        self._rebuild_color_grid()
        lay.addWidget(grid_w)

        # 字体
        frow = QHBoxLayout()
        frow.addWidget(QLabel(tr("界面字体")))
        self.font_combo = QComboBox()
        self.font_combo.addItems(QFontDatabase.families())
        self.font_combo.setCurrentText(self._edit.get("font_family", "Microsoft YaHei UI"))
        self.font_combo.currentTextChanged.connect(self._font_changed)
        frow.addWidget(self.font_combo, 1)
        lay.addLayout(frow)

        # 字号（滑条）
        srow = QHBoxLayout()
        srow.addWidget(QLabel(tr("字号")))
        self.font_size = QSlider(Qt.Horizontal, minimum=8, maximum=20,
                                 value=int(self._edit.get("font_size", 10)))
        self.font_size.valueChanged.connect(self._font_changed)
        srow.addWidget(self.font_size, 1)
        self.font_size_lbl = QLabel(str(self.font_size.value()))
        self.font_size.valueChanged.connect(
            lambda v: self.font_size_lbl.setText(str(v)))
        srow.addWidget(self.font_size_lbl)
        lay.addLayout(srow)

        # 背景不透明度（0-100，映射到 0-255 存配置）
        orow = QHBoxLayout()
        orow.addWidget(QLabel(tr("背景不透明度")))
        self.alpha_slider = QSlider(Qt.Horizontal, minimum=0, maximum=100,
                                    value=round(int(self._edit.get("bg_alpha", 208)) / 255 * 100))
        self.alpha_slider.valueChanged.connect(self._alpha_changed)
        orow.addWidget(self.alpha_slider, 1)
        self.alpha_lbl = QLabel(str(self.alpha_slider.value()))
        self.alpha_slider.valueChanged.connect(lambda v: self.alpha_lbl.setText(str(v)))
        orow.addWidget(self.alpha_lbl)
        lay.addLayout(orow)

        # ---- DIY 背景模式
        diysep = QLabel(tr("DIY 背景模式"))
        diysep.setStyleSheet(f"font-weight:bold;margin-top:10px;color:{self.t['accent']};")
        lay.addWidget(diysep)
        self.diy_chk = QCheckBox(
            tr("开启 DIY 背景模式（自定义每个部件的背景，原主题颜色自动失效）"))
        self.diy_chk.toggled.connect(self._diy_toggled)
        lay.addWidget(self.diy_chk)

        self.diy_box = QWidget()
        dbox = QVBoxLayout(self.diy_box)
        dbox.setContentsMargins(0, 0, 0, 0)
        # 各部件背景
        dlab = QLabel(tr("各部件背景（纯色或图片，留空=透明显示下层背景）"))
        dlab.setStyleSheet(f"color:{theme_mod.rgba(self.t['text'], 160)};")
        dbox.addWidget(dlab)
        self.diy_grid = QGridLayout()
        self.diy_grid.setHorizontalSpacing(6)
        self._diy_btns = {}
        self._rebuild_diy_grid()
        dbox.addLayout(self.diy_grid)
        lay.addWidget(self.diy_box)
        self.diy_box.setVisible(False)
        self._sync_diy_ui()

        # 圆角
        rrow = QHBoxLayout()
        rrow.addWidget(QLabel(tr("窗口圆角")))
        self.radius_slider = QSlider(Qt.Horizontal, minimum=0, maximum=24,
                                     value=int(self._edit.get("radius", 12)))
        self.radius_slider.valueChanged.connect(self._radius_changed)
        rrow.addWidget(self.radius_slider, 1)
        self.radius_lbl = QLabel(str(self.radius_slider.value()))
        self.radius_slider.valueChanged.connect(lambda v: self.radius_lbl.setText(str(v)))
        rrow.addWidget(self.radius_lbl)
        lay.addLayout(rrow)

        # 主题预设与导入导出
        lay.addWidget(QLabel(tr("主题")))
        trow = QHBoxLayout()
        self.theme_combo = QComboBox()
        self._refresh_theme_combo()
        trow.addWidget(self.theme_combo, 1)
        for text, fn in [("加载", self._load_theme), ("另存为", self._save_theme),
                         ("导入", self._import_theme), ("导出", self._export_theme)]:
            b = QPushButton(tr(text))
            b.clicked.connect(fn)
            trow.addWidget(b)
        lay.addLayout(trow)

        # 顶部时钟显示
        crow = QHBoxLayout()
        self.show_clock_chk = QCheckBox(tr("显示时钟（底部日期时间）"))
        self.show_clock_chk.setChecked(bool(self.app.config.get(
            "window", "show_clock", default=True)))
        self.show_clock_chk.toggled.connect(self._show_clock_changed)
        crow.addWidget(self.show_clock_chk)
        crow.addStretch()
        lay.addLayout(crow)

    def _show_clock_changed(self, v):
        self.app.config.set("window", "show_clock", v)
        self.app.win._refresh_clock_panel_visibility()

    def _lang_changed(self, idx):
        new = "zh" if idx == 0 else "en"
        cur = self.app.config.get("language", default="zh")
        if new == cur:
            return
        ok, _ = ConfirmDialog.ask(self, self.t, tr("选择语言"),
                                  tr("切换语言需要重启应用生效，立即重启？"),
                                  ok_text=tr("确定"))
        self.app.config.set("language", new if ok else cur)
        if ok:
            self.app.restart()

    def _target_changed(self, kind):
        if self._kind == kind:
            return
        self._kind = kind
        self._edit = self.app.config.get(kind)
        QTimer.singleShot(0, self._apply_target_change)

    def _apply_target_change(self):
        self._rebuild_color_grid()
        self._sync_controls()
        self._sync_diy_ui()

    def _rebuild_color_grid(self):
        items = MAIN_COLOR_ITEMS if self._kind == "theme" else SETTINGS_COLOR_ITEMS
        self.color_hint.setText(
            tr("桌面应用主题界面颜色（点击色块或输入十六进制，支持屏幕吸管）")
            if self._kind == "theme" else "")
        grid = self._color_grid
        while grid.count():
            item = grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._color_btns = {}
        rows = len(items) // 2
        for i, (key, name, _a) in enumerate(items):
            row, col = i % rows, (i // rows) * 3
            grid.addWidget(QLabel(tr(name)), row, col)
            btn = QPushButton(fixedWidth=64, fixedHeight=24)
            btn.clicked.connect(lambda _=False, k=key: self._pick_color(k))
            grid.addWidget(btn, row, col + 1)
            hexedit = QLineEdit(fixedWidth=110)
            hexedit.editingFinished.connect(
                lambda k=key, e=hexedit: self._hex_color(k, e))
            grid.addWidget(hexedit, row, col + 2)
            self._color_btns[key] = (btn, hexedit)
        self._refresh_color_rows()

    def _sync_controls(self):
        self._syncing = True
        try:
            self.font_combo.setCurrentText(
                self._edit.get("font_family", "Microsoft YaHei UI"))
            self.font_size.setValue(int(self._edit.get("font_size", 10)))
            self.alpha_slider.setValue(round(int(self._edit.get("bg_alpha", 208)) / 255 * 100))
            self.radius_slider.setValue(int(self._edit.get("radius", 12)))
            self._refresh_color_rows()
        finally:
            self._syncing = False

    def _refresh_color_rows(self):
        for key, (btn, hexedit) in self._color_btns.items():
            val = self._edit.get(key, "#ffffff")
            btn.setStyleSheet(f"background-color:{val};border:1px solid rgba(128,128,128,120);"
                              f"border-radius:5px;")
            hexedit.setText(val.upper())

    def _pick_color(self, key):
        c = ColorDialog.get_color(self, self.t, QColor(self._edit.get(key, "#ffffff")),
                                  with_alpha=False)
        if c:
            self._edit[key] = c.name()
            self._theme_updated()

    def _hex_color(self, key, edit):
        c = QColor(edit.text().strip())
        if c.isValid():
            self._edit[key] = c.name()
            self._theme_updated()

    def _font_changed(self):
        self._edit["font_family"] = self.font_combo.currentText()
        self._edit["font_size"] = self.font_size.value()
        self._theme_updated()

    def _alpha_changed(self, v):
        self._edit["bg_alpha"] = round(v / 100 * 255)
        self._theme_updated()

    def _radius_changed(self, v):
        self._edit["radius"] = v
        self._theme_updated()

    # ---------------- DIY 背景模式
    DIY_DESKTOP = [("panel", "主面板"), ("header", "头部工具栏"),
                   ("reminder", "提醒栏"),
                   ("clock", "时钟面板"), ("dialog", "对话框")]
    DIY_SETTINGS = [("panel", "设置栏背景")]

    def _diy_key(self):
        return "diy_bg" if self._kind == "theme" else "diy_bg_settings"

    def _diy_cfg(self):
        return self.app.config.get(self._diy_key(), default={}) or {}

    def _diy_save(self, **kw):
        cfg = dict(self._diy_cfg())
        cfg.update(kw)
        self.app.config.data[self._diy_key()] = cfg
        self._diy_save_timer.start()     # 拖动滑条时合并为一次落盘，界面实时生效
        self._apply_diy()

    def _diy_components(self):
        return self.DIY_DESKTOP if self._kind == "theme" else self.DIY_SETTINGS

    def _apply_diy(self):
        cfg = self._diy_cfg()
        if self._kind == "theme":
            win = getattr(self.app, "win", None)
            if win is not None and hasattr(win, "apply_diy_bg"):
                win.apply_diy_bg(cfg)
        else:
            # 设置栏 DIY 应用到本设置窗口自身
            self.apply_diy_settings(cfg)

    def _sync_diy_ui(self):
        if not hasattr(self, "diy_chk"):
            return
        self.diy_chk.setChecked(bool(self._diy_cfg().get("enabled")))
        self.diy_box.setVisible(self.diy_chk.isChecked())
        self._rebuild_diy_grid()

    def _diy_toggled(self, on):
        self._diy_save(enabled=bool(on))
        self.diy_box.setVisible(on)
        self._apply_diy()

    def _diy_comp_style(self, color, image):
        if color:
            return (f"background-color:{color};border:1px solid rgba(128,128,128,120);"
                    f"border-radius:5px;padding:2px 8px;")
        if image:
            return (f"background-color:rgba(128,128,128,60);border:1px solid rgba(128,128,128,120);"
                    f"border-radius:5px;padding:2px 8px;")
        return ("background-color:transparent;border:1px dashed rgba(128,128,128,160);"
                "border-radius:5px;padding:2px 8px;")

    def _rebuild_diy_grid(self):
        while self.diy_grid.count():
            it = self.diy_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self._diy_btns = {}
        comps = self._diy_cfg().get("components") or {}
        for i, (key, name) in enumerate(self._diy_components()):
            self.diy_grid.addWidget(QLabel(tr(name)), i, 0)
            c = comps.get(key) or {}
            color = c.get("color") or ""
            image = c.get("image") or ""
            alpha = int(c.get("alpha", 100))
            cb = QPushButton(tr("色") if color else tr("纯色"))
            cb.setStyleSheet(self._diy_comp_style(color, ""))
            cb.setToolTip(tr("点击设置背景色（与图片互斥）"))
            cb.clicked.connect(lambda _=False, k=key: self._pick_diy_color(k))
            self.diy_grid.addWidget(cb, i, 1)
            ib = QPushButton(tr("图") if image else tr("图片"))
            ib.setStyleSheet(self._diy_comp_style("", image))
            ib.setToolTip(image or tr("点击选择背景图片（与纯色互斥）"))
            ib.clicked.connect(lambda _=False, k=key: self._pick_diy_comp_image(k))
            self.diy_grid.addWidget(ib, i, 2)
            sp = QSlider(Qt.Horizontal, minimum=0, maximum=100, value=alpha,
                         fixedWidth=110)
            sp.setToolTip(tr("部件背景不透明度：{n}").replace("{n}", str(alpha)))
            sp.valueChanged.connect(
                lambda v, k=key, s=sp: (s.setToolTip(tr("部件背景不透明度：{n}").replace("{n}", str(v))),
                                        self._diy_comp_alpha(k, v)))
            self.diy_grid.addWidget(sp, i, 3)
            cl = QPushButton(tr("清除"))
            cl.setFixedWidth(48)
            cl.setStyleSheet("padding:2px 6px;")
            cl.clicked.connect(lambda _=False, k=key: self._clear_diy_comp(k))
            self.diy_grid.addWidget(cl, i, 4)
            self._diy_btns[key] = (cb, ib)

    def _diy_comp_alpha(self, key, v):
        self._diy_update_comp(key, alpha=int(v))

    def _diy_update_comp(self, key, **kw):
        comps = dict(self._diy_cfg().get("components") or {})
        c = dict(comps.get(key) or {})
        c.update(kw)
        comps[key] = c
        self._diy_save(components=comps)
        self._apply_diy()

    def _pick_diy_color(self, key):
        c = ColorDialog.get_color(self, self.t, QColor("#ffffff"), with_alpha=True)
        if c:
            self._diy_update_comp(key, color=c.name(), image="")

    def _pick_diy_comp_image(self, key):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择部件背景图", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self._diy_update_comp(key, image=path, color="")

    def _clear_diy_comp(self, key):
        comps = dict(self._diy_cfg().get("components") or {})
        comps.pop(key, None)
        self._diy_save(components=comps)
        self._rebuild_diy_grid()
        self._apply_diy()

    def _theme_updated(self):
        if getattr(self, "_syncing", False):
            return
        self._theme_timer.start()

    def _apply_theme(self):
        self.app.config.data[self._kind] = self._edit
        self.app.config.save()
        self.app.apply_theme(self._kind)
        self._refresh_color_rows()

    def _refresh_theme_combo(self):
        self.theme_combo.clear()
        self.theme_combo.addItems(self.app.config.get("saved_themes", default={}).keys())

    def _load_theme(self):
        name = self.theme_combo.currentText()
        saved = self.app.config.get("saved_themes", default={})
        if name in saved:
            self._edit.clear()
            self._edit.update(saved[name])
            self._prune_theme_keys()
            self.app.config.data[self._kind] = self._edit
            self.app.config.save()
            self.app.apply_theme(self._kind)
            self._sync_controls()

    def _prune_theme_keys(self):
        if self._kind == "theme_settings":
            for _k in ("done_text", "high", "mid", "low"):
                self._edit.pop(_k, None)

    def _save_theme(self):
        name, ok = QInputDialog.getText(self, tr("保存主题"), tr("主题名称："),
                                        text=self._edit.get("name", tr("自定义主题")))
        if ok and name.strip():
            name = name.strip()
            self._edit["name"] = name
            themes = self.app.config.get("saved_themes", default={})
            themes[name] = dict(self._edit)
            self.app.config.set("saved_themes", themes)
            self._refresh_theme_combo()
            self.theme_combo.setCurrentText(name)
            core.log.info(f"保存主题: {name}")

    def _import_theme(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("导入主题"), core.EXPORT_DIR,
                                              tr("主题文件 (*.json)"))
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    th = json.load(f)
                self._edit.clear()
                self._edit.update({**theme_mod.DEFAULT_THEME, **th})
                self._prune_theme_keys()
                self.app.config.data[self._kind] = self._edit
                self.app.config.save()
                self.app.apply_theme(self._kind)
                self._sync_controls()
                Toast.show_text(tr("主题已导入"))
            except Exception as e:
                core.log.error(f"导入主题失败: {e}")
                Toast.show_text(tr("主题文件无效"))

    def _export_theme(self):
        path = os.path.join(core.EXPORT_DIR,
                            f"theme_{self._edit.get('name', 'custom')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._edit, f, ensure_ascii=False, indent=2)
        core.log.info(f"导出主题: {path}")
        Toast.show_text(tr("已导出到 导出 目录"))

    # ================================================================ 文件夹设置
    def _page_folder(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignTop)
        self.nav.addItem(tr("📁 文件夹"))
        self.pages.addWidget(w)

        lay.addWidget(QLabel(tr("父目录（所有自动生成的文件夹都在这里）")))
        row = QHBoxLayout()
        self.base_edit = QLineEdit(self.app.config.get("base_folder",
                                                       default=core.DEFAULT_BASE_FOLDER))
        row.addWidget(self.base_edit, 1)
        btn = QPushButton(tr("浏览…"))
        btn.clicked.connect(self._browse_base)
        row.addWidget(btn)
        lay.addLayout(row)

        btn_open = QPushButton(tr("打开父目录"))
        btn_open.clicked.connect(lambda: core.open_folder(
            self.app.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)))
        lay.addWidget(btn_open)

        # ---- 平行生成规则管理（多条规则，创建事项时自主选用）
        lay.addSpacing(10)
        rrow = QHBoxLayout()
        rrow.addWidget(QLabel(tr("生成规则")))
        self.rule_combo = QComboBox()
        self.rule_combo.currentIndexChanged.connect(self._rule_combo_changed)
        rrow.addWidget(self.rule_combo, 1)
        for text, fn in [("＋ 新建", self._add_rule), ("✏ 重命名", self._rename_rule),
                         ("🗑 删除", self._delete_rule)]:
            b = QPushButton(tr(text))
            b.clicked.connect(fn)
            rrow.addWidget(b)
        lay.addLayout(rrow)
        rtips = QLabel(tr("可创建多条平行规则（如「财务规则」「运营规则」），在「⚡ 来活了」创建事项时可自主选择用哪条规则生成文件夹"))
        rtips.setWordWrap(True)
        rtips.setStyleSheet(f"color:{theme_mod.rgba(self.t['text'], 160)};")
        lay.addWidget(rtips)

        # ---- 文件夹生成规则树
        lay.addWidget(QLabel(tr("规则结构（层级可增删、上下移、改名）")))
        self.rule_tree = QTreeWidget()
        self.rule_tree.setColumnCount(3)
        self.rule_tree.setHeaderLabels([tr("结构"), tr("命名模板"), tr("示例")])
        self.rule_tree.setRootIsDecorated(True)
        self.rule_tree.setIndentation(18)
        self.rule_tree.setUniformRowHeights(True)
        self.rule_tree.setAlternatingRowColors(False)
        self.rule_tree.setColumnWidth(0, 110)
        self.rule_tree.setColumnWidth(1, 190)
        self.rule_tree.setColumnWidth(2, 220)
        lay.addWidget(self.rule_tree, 1)

        brow = QHBoxLayout()
        for text, fn in [("＋ 添加层级", self._add_rule_level),
                         ("▲ 上移", lambda: self._move_rule_level(-1)),
                         ("▼ 下移", lambda: self._move_rule_level(1)),
                         ("🗑 删除层级", self._remove_rule_level)]:
            b = QPushButton(tr(text))
            b.clicked.connect(fn)
            brow.addWidget(b)
        lay.addLayout(brow)

        rtip = QLabel(tr("模板占位符：{Y}=年份  {M}=月份  {D}=日  {name}=事项名称（层级可增删、上下移、改名）"))
        rtip.setWordWrap(True)
        rtip.setStyleSheet(f"color:{theme_mod.rgba(self.t['text'], 160)};")
        lay.addWidget(rtip)
        self._reload_rule_combo()
        self._reload_rule_tree()

        # ---- 快捷自定义子文件夹（可选直接绑定）
        lay.addSpacing(10)
        lay.addWidget(QLabel(tr("快捷自定义子文件夹（可选：可直接把事项绑定到这些文件夹）")))
        self.folder_list = QListWidget()
        self.folder_list.setSelectionMode(QListWidget.ExtendedSelection)  # 支持批量
        lay.addWidget(self.folder_list)
        brow2 = QHBoxLayout()
        for text, fn in [("＋ 新建", self._add_custom_folder),
                         ("✏ 重命名", self._rename_custom_folder),
                         ("🗑 移除", self._remove_custom_folder),
                         ("🗑 批量删除", self._remove_custom_folders),
                         ("📂 打开", self._open_custom_folder)]:
            b = QPushButton(tr(text))
            b.clicked.connect(fn)
            brow2.addWidget(b)
        lay.addLayout(brow2)
        self._reload_folder_list()

    # ---------------- 平行生成规则（多条）
    def _reload_rule_combo(self, select=None):
        if not hasattr(self, "rule_combo"):
            return
        rl = core.folder_rules_list(self.app.config.get("folder_rules", default={}))
        cur = select if select is not None else self.rule_combo.currentText()
        self.rule_combo.blockSignals(True)
        self.rule_combo.clear()
        self.rule_combo.addItems([r.get("name") or f"规则{i + 1}"
                                  for i, r in enumerate(rl)])
        self.rule_combo.setCurrentIndex(max(0, self.rule_combo.findText(cur)))
        self.rule_combo.blockSignals(False)
        self._rule_idx = max(0, self.rule_combo.currentIndex())

    def _rule_combo_changed(self, idx):
        self._rule_idx = max(0, idx)
        self._reload_rule_tree()

    def _add_rule(self):
        rl = core.folder_rules_list(self.app.config.get("folder_rules", default={}))
        name = f"规则{len(rl) + 1}"
        rl.append({"name": name, "levels": [dict(t) for t in core.DEFAULT_FOLDER_RULES]})
        self.app.config.set("folder_rules", {"rules": rl})
        self._reload_rule_combo(select=name)
        core.log.info(f"新建文件夹生成规则: {name}")

    def _rename_rule(self):
        old = self.rule_combo.currentText()
        name, ok = QInputDialog.getText(self, tr("重命名规则"), tr("规则名称："), text=old)
        if not ok or not name.strip() or name.strip() == old:
            return
        name = name.strip()
        rl = core.folder_rules_list(self.app.config.get("folder_rules", default={}))
        idx = min(self._rule_idx, len(rl) - 1)
        rl[idx]["name"] = name
        self.app.config.set("folder_rules", {"rules": rl})
        self._reload_rule_combo(select=name)
        core.log.info(f"重命名生成规则: {old} → {name}")

    def _delete_rule(self):
        rl = core.folder_rules_list(self.app.config.get("folder_rules", default={}))
        if len(rl) <= 1:
            Toast.show_text(tr("至少保留一条生成规则"))
            return
        name = self.rule_combo.currentText()
        ok, _ = ConfirmDialog.ask(self, self.t, tr("删除规则"),
                                  tr("删除生成规则「{name}」？\n（已创建的事项不受影响）")
                                  .replace("{name}", name),
                                  ok_text=tr("删除"))
        if not ok:
            return
        idx = min(self._rule_idx, len(rl) - 1)
        rl.pop(idx)
        self.app.config.set("folder_rules", {"rules": rl})
        self._reload_rule_combo()
        core.log.info(f"删除生成规则: {name}")

    # ---------------- 文件夹规则树
    def _reload_rule_tree(self):
        rules = self.app.config.get("folder_rules", default={})
        rl = core.folder_rules_list(rules)
        idx = min(getattr(self, "_rule_idx", 0), len(rl) - 1)
        self._rule_idx = idx
        levels = rl[idx].get("levels")
        if not levels:
            levels = [dict(t) for t in core.DEFAULT_FOLDER_RULES]
            rl[idx]["levels"] = levels
        self._rule_levels = levels
        base = self.app.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
        today = datetime.now().date()
        sample = "项目111"
        self.rule_tree.clear()
        root = QTreeWidgetItem([os.path.basename(base) or base, tr("父目录"), "—"])
        self.rule_tree.addTopLevelItem(root)
        root.setExpanded(True)
        self._rule_items = [root]
        for i, lvl in enumerate(levels):
            tpl = lvl.get("template", "")
            ex = core.render_folder_template(tpl, today, sample)
            it = QTreeWidgetItem([tr("第{n}层").replace("{n}", str(i + 1)), "", ex])   # 第2列文字由内嵌编辑框显示
            root.addChild(it)
            it.setExpanded(True)
            edit = QLineEdit(tpl)
            edit.setStyleSheet("background:transparent;border:none;padding:0 4px;")
            edit.setFixedHeight(24)
            edit.textChanged.connect(lambda t, idx=i: self._rule_template_changed(idx, t))
            self.rule_tree.setItemWidget(it, 1, edit)
            self._rule_items.append(it)
        self.rule_tree.expandAll()

    def _save_folder_rules(self):
        if not getattr(self, "_rule_levels", None):
            return
        rl = core.folder_rules_list(self.app.config.get("folder_rules", default={}))
        idx = min(getattr(self, "_rule_idx", 0), len(rl) - 1)
        rl[idx]["levels"] = self._rule_levels
        self.app.config.set("folder_rules", {"rules": rl})
        core.log.info("文件夹生成规则已更新")

    def _rule_template_changed(self, idx, text):
        if not getattr(self, "_rule_levels", None) or idx >= len(self._rule_levels):
            return
        self._rule_levels[idx]["template"] = text
        self._save_folder_rules()
        base = self.app.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
        today = datetime.now().date()
        ex = core.render_folder_template(text, today, "项目111")
        if idx + 1 < len(self._rule_items):
            self._rule_items[idx + 1].setText(2, ex)

    def _selected_rule_index(self):
        it = self.rule_tree.currentItem()
        if not it or not getattr(self, "_rule_items", None) or it is self._rule_items[0]:
            return -1
        try:
            return self._rule_items.index(it) - 1
        except ValueError:
            return -1

    def _add_rule_level(self):
        if not getattr(self, "_rule_levels", None):
            return
        self._rule_levels.append({"template": "子文件夹"})
        self._save_folder_rules()
        self._reload_rule_tree()

    def _remove_rule_level(self):
        idx = self._selected_rule_index()
        if 0 <= idx < len(self._rule_levels):
            self._rule_levels.pop(idx)
            self._save_folder_rules()
            self._reload_rule_tree()

    def _move_rule_level(self, delta):
        idx = self._selected_rule_index()
        j = idx + delta
        if 0 <= idx < len(self._rule_levels) and 0 <= j < len(self._rule_levels):
            self._rule_levels[idx], self._rule_levels[j] = \
                self._rule_levels[j], self._rule_levels[idx]
            self._save_folder_rules()
            self._reload_rule_tree()

    # ---------------- 快捷自定义子文件夹
    def _reload_folder_list(self):
        self.folder_list.clear()
        for name in self.app.config.get("custom_folders", default=[]):
            self.folder_list.addItem(name)

    def _selected_custom_folder(self):
        it = self.folder_list.currentItem()
        return it.text() if it else None

    def _add_custom_folder(self):
        name, ok = QInputDialog.getText(self, tr("新建子文件夹"), tr("子文件夹名称："))
        if not ok or not name.strip():
            return
        name = name.strip()
        base = self.app.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
        path = core.ensure_custom_folder(base, name)
        folders = self.app.config.get("custom_folders", default=[])
        if name not in folders:
            folders.append(name)
            self.app.config.set("custom_folders", folders)
        self._reload_folder_list()
        core.log.info(f"新建自定义子文件夹: {path}")
        Toast.show_text(tr("子文件夹已创建"))

    def _rename_custom_folder(self):
        old = self._selected_custom_folder()
        if not old:
            Toast.show_text(tr("请先选择一个子文件夹"))
            return
        name, ok = QInputDialog.getText(self, tr("重命名"), tr("新的名称："), text=old)
        if not ok or not name.strip() or name.strip() == old:
            return
        name = name.strip()
        base = self.app.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
        old_path, new_path = core.custom_folder_path(base, old), core.custom_folder_path(base, name)
        try:
            if os.path.isdir(old_path) and not os.path.isdir(new_path):
                os.rename(old_path, new_path)
        except Exception as e:
            core.log.error(f"重命名文件夹失败: {e}")
        folders = self.app.config.get("custom_folders", default=[])
        folders[folders.index(old)] = name
        self.app.config.set("custom_folders", folders)
        self._reload_folder_list()

    def _remove_custom_folder(self):
        name = self._selected_custom_folder()
        if not name:
            Toast.show_text(tr("请先选择一个子文件夹"))
            return
        ok, _ = ConfirmDialog.ask(self, self.t, tr("移除子文件夹"),
                                  tr("从列表中移除「{name}」？\n（不会删除磁盘上已存在的内容）")
                                  .replace("{name}", name),
                                  ok_text=tr("移除"))
        if not ok:
            return
        folders = self.app.config.get("custom_folders", default=[])
        if name in folders:
            folders.remove(name)
            self.app.config.set("custom_folders", folders)
        self._reload_folder_list()

    def _remove_custom_folders(self):
        names = [i.text() for i in self.folder_list.selectedItems()]
        if not names:
            Toast.show_text(tr("请先在列表中选择要删除的子文件夹（可多选）"))
            return
        msg = tr("从列表中移除 {n} 个子文件夹？\n（不会删除磁盘上已存在的内容）\n\n") \
            .replace("{n}", str(len(names))) + \
            "\n".join(f"· {n}" for n in names[:8])
        if len(names) > 8:
            msg += tr("…等共 {n} 个").replace("{n}", str(len(names)))
        ok, _ = ConfirmDialog.ask(self, self.t, tr("批量移除子文件夹"), msg,
                                  ok_text=tr("移除"))
        if not ok:
            return
        folders = [f for f in self.app.config.get("custom_folders", default=[])
                   if f not in names]
        self.app.config.set("custom_folders", folders)
        self._reload_folder_list()
        core.log.info(f"批量移除 {len(names)} 个子文件夹")
        Toast.show_text(tr("已移除 {n} 个").replace("{n}", str(len(names))))

    def _open_custom_folder(self):
        name = self._selected_custom_folder()
        if not name:
            Toast.show_text(tr("请先选择一个子文件夹"))
            return
        base = self.app.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
        core.open_folder(core.ensure_custom_folder(base, name))

    def _browse_base(self):
        d = QFileDialog.getExistingDirectory(self, tr("选择父目录"),
                                             self.base_edit.text())
        if d:
            self.base_edit.setText(d)
            self.app.config.set("base_folder", d)
            core.log.info(f"修改父目录: {d}")
            self._reload_rule_tree()

    # ================================================================ 提醒设置
    def _page_remind(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignTop)
        self.nav.addItem(tr("⏰ 提醒"))
        self.pages.addWidget(w)

        r = self.app.config.get("reminder", default={})
        self.todo_enabled = QCheckBox(tr("启用待办事项截止提醒"))
        self.todo_enabled.setChecked(r.get("todo_enabled", True))
        lay.addWidget(self.todo_enabled)

        arow = QHBoxLayout()
        arow.addWidget(QLabel(tr("默认提前提醒")))
        self.todo_advance = QComboBox()
        from editor import ADVANCE_OPTIONS
        for name, v in ADVANCE_OPTIONS[:-1]:
            self.todo_advance.addItem(tr(name), v)
        cur = r.get("todo_advance_minutes", 0)
        idx = next((i for i, (_, v) in enumerate(ADVANCE_OPTIONS) if v == cur), 0)
        self.todo_advance.setCurrentIndex(idx)
        arow.addWidget(self.todo_advance, 1)
        lay.addLayout(arow)

        self.recur_enabled = QCheckBox(tr("启用循环任务定时提醒"))
        self.recur_enabled.setChecked(r.get("recur_enabled", True))
        lay.addWidget(self.recur_enabled)

        self.remind_enabled = QCheckBox(tr("启用提醒事项"))
        self.remind_enabled.setChecked(r.get("remind_enabled", True))
        lay.addWidget(self.remind_enabled)

        # ---- 下班倒计时
        owsep = QLabel(tr("下班倒计时"))
        owsep.setStyleSheet("font-weight:bold;margin-top:10px;")
        lay.addWidget(owsep)
        ow = self.app.config.get("offwork", default={})
        self.off_enabled = QCheckBox(tr("启用下班倒计时（显示在窗口底部）"))
        self.off_enabled.setChecked(ow.get("enabled", False))
        lay.addWidget(self.off_enabled)

        owrow = QHBoxLayout()
        owrow.addWidget(QLabel(tr("下班时间")))
        self.off_time = QTimeEdit(QTime.fromString(str(ow.get("time", "18:00")), "HH:mm"))
        self.off_time.setDisplayFormat("HH:mm")
        owrow.addWidget(self.off_time, 1)
        lay.addLayout(owrow)

        offrow = QHBoxLayout()
        offrow.addWidget(QLabel(tr("倒计时格式")))
        self.off_format = QComboBox()
        for text, v in [("按秒", "sec"), ("按分", "min"), ("按时", "hour")]:
            self.off_format.addItem(tr(text), v)
        self.off_format.setCurrentIndex(
            {"sec": 0, "min": 1, "hour": 2}.get(ow.get("format", "min"), 1))
        offrow.addWidget(self.off_format, 1)
        lay.addLayout(offrow)

        self.off_weekdays = QCheckBox(tr("仅工作日（周末显示“休息日”）"))
        self.off_weekdays.setChecked(ow.get("weekdays_only", True))
        lay.addWidget(self.off_weekdays)

        owtrow = QHBoxLayout()
        owtrow.addWidget(QLabel(tr("倒计时文案")))
        self.off_template = QLineEdit(str(ow.get("template", "距下班 {n}")))
        self.off_template.setPlaceholderText(tr("用 {n} 表示剩余时间"))
        owtrow.addWidget(self.off_template, 1)
        lay.addLayout(owtrow)
        owtip = QLabel(tr("示例：距下班 {n} → “距下班 58分47秒”；也可写成 还有 {n} 下班"))
        owtip.setWordWrap(True)
        owtip.setStyleSheet(f"color:{theme_mod.rgba(self.t['text'], 160)};")
        lay.addWidget(owtip)

        self.autostart_chk = QCheckBox(tr("开机自动启动（注册表 Run 项）"))
        self.autostart_chk.setChecked(core.autostart_enabled())
        lay.addWidget(self.autostart_chk)

        btn = QPushButton(tr("保存提醒设置"), objectName="AccentButton")
        btn.clicked.connect(self._save_remind)
        lay.addWidget(btn)

    def _save_remind(self):
        self.app.config.set("reminder", {
            "todo_enabled": self.todo_enabled.isChecked(),
            "todo_advance_minutes": self.todo_advance.currentData(),
            "recur_enabled": self.recur_enabled.isChecked(),
            "remind_enabled": self.remind_enabled.isChecked()})
        self.app.config.set("offwork", {
            "enabled": self.off_enabled.isChecked(),
            "time": self.off_time.time().toString("HH:mm"),
            "format": self.off_format.currentData(),
            "weekdays_only": self.off_weekdays.isChecked(),
            "template": self.off_template.text().strip() or "距下班 {n}"})
        core.set_autostart(self.autostart_chk.isChecked())
        self.app.win._refresh_clock_panel_visibility()
        Toast.show_text(tr("提醒设置已保存"))

    # ================================================================ 快捷键
    def _page_hotkey(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignTop)
        self.nav.addItem(tr("⌨ 快捷键"))
        self.pages.addWidget(w)

        lay.addWidget(QLabel(tr("点击输入框后按下组合键（支持四键组合），全部松开即保存")))
        hk = self.app.config.get("hotkeys", default={})
        self._hk_edits = {}
        fixed = [("settings", "打开设置窗口"), ("click_through", "切换鼠标穿透")]
        for key, name in fixed + CUSTOM_ACTIONS:
            row = QHBoxLayout()
            lbl = QLabel(tr(name))
            lbl.setFixedWidth(150)
            row.addWidget(lbl)
            combo = hk.get(key) if key in ("settings", "click_through") \
                else hk.get("custom", {}).get(key)
            edit = HotkeyEdit(combo or [])
            edit.combo_changed.connect(lambda c, k=key: self._hotkey_changed(k, c))
            row.addWidget(edit, 1)
            btn = QPushButton(tr("清除"), fixedWidth=52)
            btn.clicked.connect(lambda _=False, k=key, e=edit: self._hotkey_changed(k, []))
            row.addWidget(btn)
            lay.addLayout(row)
            self._hk_edits[key] = edit

        tip = QLabel(tr("提示：快捷键冲突时后注册的可能失效；清除后保存即可停用。"))
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{theme_mod.rgba(self.t['text'], 160)};")
        lay.addWidget(tip)

    def _hotkey_changed(self, key, combo):
        cfg = self.app.config
        if key in ("settings", "click_through"):
            cfg.set("hotkeys", key, combo)
        else:
            custom = cfg.get("hotkeys", "custom", default={})
            if combo:
                custom[key] = combo
            else:
                custom.pop(key, None)
            cfg.set("hotkeys", "custom", custom)
        self.app.reload_hotkeys()
        core.log.info(f"快捷键更新: {key} = {combo_text(combo) if combo else '(无)'}")

    # ================================================================ 数据管理
    def _page_data(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.nav.addItem(tr("🗄 数据管理"))
        self.pages.addWidget(w)

        # 搜索 + 筛选
        row = QHBoxLayout()
        self.data_search = QLineEdit(placeholderText=tr("🔍 搜索全部事项…"))
        self._data_timer = QTimer(self, singleShot=True, interval=150,
                                  timeout=self._reload_data_list)
        self.data_search.textChanged.connect(lambda _: self._data_timer.start())
        row.addWidget(self.data_search, 1)
        self.data_type = QComboBox()
        for text, v in [("全部类型", None), ("工作记录", "record"),
                        ("待办事项", "todo"), ("循环任务", "recur"),
                        ("提醒", "remind")]:
            self.data_type.addItem(tr(text), v)
        self.data_type.currentIndexChanged.connect(self._reload_data_list)
        row.addWidget(self.data_type)
        lay.addLayout(row)

        self.data_list = QListWidget()
        self.data_list.setSelectionMode(QListWidget.ExtendedSelection)
        lay.addWidget(self.data_list, 1)

        brow = QHBoxLayout()
        for text, fn in [("导出选中", lambda: self._export(False)),
                         ("导出全部", lambda: self._export(True)),
                         ("导入…", self._import),
                         ("🗑 删除选中", self._delete_selected)]:
            b = QPushButton(tr(text))
            b.clicked.connect(fn)
            brow.addWidget(b)
        lay.addLayout(brow)

        # 循环任务完成历史
        lay.addWidget(QLabel(tr("循环任务完成历史")))
        hrow = QHBoxLayout()
        self.recur_combo = QComboBox()
        self.recur_combo.currentIndexChanged.connect(self._reload_recur_history)
        hrow.addWidget(self.recur_combo, 1)
        lay.addLayout(hrow)
        self.recur_history = QListWidget(maximumHeight=100)
        lay.addWidget(self.recur_history)

        # 标签管理
        lay.addWidget(QLabel(tr("标签管理（双击从所有事项中移除）")))
        self.tag_list = QListWidget(maximumHeight=80)
        self.tag_list.itemDoubleClicked.connect(self._remove_tag)
        lay.addWidget(self.tag_list)

        # 恢复出厂设置（双重确认 + 5 秒倒计时）
        lay.addSpacing(14)
        rrow = QHBoxLayout()
        rrow.addStretch()
        btn_reset = QPushButton(tr("♻ 恢复出厂设置"))
        btn_reset.setStyleSheet(
            "color:#e5484d;border:1px solid rgba(229,72,77,150);"
            "background-color:rgba(229,72,77,25);")
        btn_reset.setToolTip(tr("清除全部事项数据并恢复默认设置（双重确认 + 5 秒倒计时）"))
        btn_reset.clicked.connect(self._factory_reset)
        rrow.addWidget(btn_reset)
        lay.addLayout(rrow)

        self._reload_data_list()

    def _factory_reset(self):
        ok, del_folders = ConfirmDialog.ask(
            self, self.t, tr("恢复出厂设置 · 第一步确认"),
            tr("即将执行：\n· 清除全部事项数据\n· 恢复所有默认设置（主题 / 快捷键 / 窗口 / 文件夹规则等）\n\n"
               "此操作不可撤销！\n\n点击「继续」后将进入 10 秒倒计时二次确认。"),
            checkbox=tr("⚠ 同时删除所有项目文件夹（工作文件夹\\ 及其中全部内容，不可恢复！）"),
            ok_text=tr("继续"), warn_checkbox=True)
        if not ok:
            return
        d = CountdownDialog(
            self, self.t, tr("恢复出厂设置 · 二次确认"),
            tr("即将清除全部数据") + (tr("，并删除全部项目文件夹（不可恢复）") if del_folders else "")
            + tr("，请三思！"),
            seconds=10)
        if d.exec() != QDialog.Accepted:
            return
        core.log.warning("执行恢复出厂设置" + ("（含删除项目文件夹）" if del_folders else ""))
        base = self.app.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
        if del_folders and os.path.isdir(base):
            try:
                shutil.rmtree(base)
                core.log.warning(f"已删除项目文件夹: {base}")
            except Exception:
                core.log.error(f"删除项目文件夹失败 {base}:\n"
                               + traceback.format_exc())
        lang = self.app.config.get("language", default="en")
        self.app.config.data = json.loads(json.dumps(core.DEFAULT_CONFIG))
        self.app.config.data["language"] = lang   # 保留当前语言，重置后不跳变
        self.app.config.save()
        self.app.store.items = []
        self.app.store.save()
        self.close()
        self.app.apply_theme("all")
        self.app.win.refresh()
        Toast.show_text(tr("已恢复出厂设置"))

    def _reload_data_list(self):
        kw = self.data_search.text().strip().lower()
        tp = self.data_type.currentData()
        self.data_list.clear()
        for it in self.app.store.items:
            if tp and it["type"] != tp:
                continue
            if kw and kw not in it["title"].lower() and \
                    not any(kw in t.lower() for t in it.get("tags", [])):
                continue
            state = ""
            if it["type"] == "recur":
                state = f"（{core.recur_desc(it)}）"
            elif it["type"] == "remind" and it.get("remind_time"):
                state = f"（{it['remind_time']}）"
            elif it.get("done"):
                state = tr("（已完成）")
            text = f"[{core.type_name(it['type'])}] {it['title']} {state} " \
                   f"· {it.get('created', '')}"
            lw = QListWidgetItem(text)
            lw.setData(Qt.UserRole, it["id"])
            self.data_list.addItem(lw)
        # 循环任务下拉
        self.recur_combo.blockSignals(True)
        self.recur_combo.clear()
        for it in self.app.store.items:
            if it["type"] == "recur":
                self.recur_combo.addItem(it["title"], it["id"])
        self.recur_combo.blockSignals(False)
        self._reload_recur_history()
        # 标签
        self.tag_list.clear()
        for tg in self.app.store.all_tags():
            self.tag_list.addItem(tg)

    def _reload_recur_history(self):
        self.recur_history.clear()
        iid = self.recur_combo.currentData()
        it = self.app.store.find(iid) if iid else None
        if it:
            for h in sorted(it.get("completed_instances", []), reverse=True):
                self.recur_history.addItem(f"✔ {h}")
            if not it.get("completed_instances"):
                self.recur_history.addItem(tr("（暂无完成记录）"))

    def _selected_items(self):
        ids = [i.data(Qt.UserRole) for i in self.data_list.selectedItems()]
        return [self.app.store.find(i) for i in ids if self.app.store.find(i)]

    def _export(self, all_items):
        items = self.app.store.items if all_items else self._selected_items()
        if not items:
            Toast.show_text(tr("没有可导出的事项"))
            return
        fmt, ok = QInputDialog.getItem(self, tr("导出格式"), tr("选择格式："),
                                       ["JSON", "CSV"], 0, False)
        if not ok:
            return
        path = core.export_items(items, fmt.lower())
        Toast.show_text(tr("已导出到 导出 目录"))
        core.open_folder(core.EXPORT_DIR)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("导入数据"), core.EXPORT_DIR,
                                              tr("数据文件 (*.json *.csv)"))
        if not path:
            return
        try:
            new_items = core.import_file(path)
        except Exception as e:
            core.log.error(f"导入失败: {e}")
            Toast.show_text(tr("导入失败：文件格式错误"))
            return
        self._do_import(new_items)
        self._reload_data_list()
        self.app.win.refresh()

    def _do_import(self, new_items):
        existing = {core.dup_key(i): i for i in self.app.store.items}
        dups = [i for i in new_items if core.dup_key(i) in existing]
        overwrite = False
        if dups:
            ok, overwrite = ConfirmDialog.ask(
                self, self.t, tr("发现重复"),
                tr("导入的 {n} 条中有 {m} 条与现有数据重复。\n勾选下方复选框后确定 = 覆盖重复项；不勾选 = 跳过重复项。")
                .replace("{n}", str(len(new_items))).replace("{m}", str(len(dups))),
                checkbox=tr("覆盖重复项"), ok_text=tr("开始导入"))
            if not ok:
                return
        added = 0
        for it in new_items:
            key = core.dup_key(it)
            if key in existing:
                if overwrite:
                    self.app.store.items.remove(existing[key])
                else:
                    continue
            self.app.store.items.append(it)
            added += 1
        self.app.store.save()
        core.log.info(f"导入完成：新增 {added} 条（共 {len(new_items)} 条）")
        Toast.show_text(tr("导入完成：新增 {n} 条").replace("{n}", str(added)))

    def _delete_selected(self):
        items = self._selected_items()
        if not items:
            Toast.show_text(tr("请先在列表中选择要删除的事项"))
            return
        bound = [i for i in items if i.get("folder")]
        msg = tr("即将删除 {n} 条事项：\n").replace("{n}", str(len(items))) + \
              "\n".join(f"· {i['title']}" for i in items[:8])
        if len(items) > 8:
            msg += tr("…等共 {n} 条").replace("{n}", str(len(items)))
        checkbox = None
        if bound:
            msg += tr("其中 {n} 条已绑定工作文件夹。").replace("{n}", str(len(bound)))
            checkbox = tr("同时删除绑定的工作文件夹（不可恢复！）")
        ok, del_folder = ConfirmDialog.ask(self, self.t, tr("确认删除"), msg,
                                           checkbox=checkbox, ok_text=tr("删除"))
        if not ok:
            return
        if del_folder:
            for i in bound:
                try:
                    if i["folder"] and os.path.isdir(i["folder"]):
                        shutil.rmtree(i["folder"])
                        core.log.info(f"删除文件夹: {i['folder']}")
                except Exception:
                    core.log.error(f"删除文件夹失败 {i['folder']}")
        self.app.store.delete([i["id"] for i in items])
        self._reload_data_list()
        self.app.win.refresh()
        Toast.show_text(tr("已删除 {n} 条").replace("{n}", str(len(items))))

    def _remove_tag(self, lw_item):
        tag = lw_item.text()
        ok, _ = ConfirmDialog.ask(self, self.t, tr("移除标签"),
                                  tr("将从所有事项中移除标签「{tag}」？")
                                  .replace("{tag}", tag),
                                  ok_text=tr("移除"))
        if ok:
            for it in self.app.store.items:
                if tag in it.get("tags", []):
                    it["tags"].remove(tag)
            self.app.store.save()
            core.log.info(f"移除标签: {tag}")
            self._reload_data_list()
            self.app.win.refresh()

    # ================================================================ 日志
    def _page_logs(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.nav.addItem(tr("📜 日志"))
        self.pages.addWidget(w)

        row = QHBoxLayout()
        self.log_combo = QComboBox()
        self.log_combo.addItems([tr("运行日志 app.log"), tr("错误日志 error.log")])
        self.log_combo.currentIndexChanged.connect(self._reload_log)
        row.addWidget(self.log_combo)
        btn_refresh = QPushButton(tr("刷新"))
        btn_refresh.clicked.connect(self._reload_log)
        row.addWidget(btn_refresh)
        btn_export = QPushButton(tr("导出日志"))
        btn_export.clicked.connect(self._export_log)
        row.addWidget(btn_export)
        btn_open = QPushButton(tr("打开日志目录"))
        btn_open.clicked.connect(lambda: core.open_folder(core.LOG_DIR))
        row.addWidget(btn_open)
        lay.addLayout(row)

        self.log_view = QTextEdit(readOnly=True)
        self.log_view.setStyleSheet("font-family:Consolas,monospace;font-size:9pt;")
        lay.addWidget(self.log_view, 1)
        self._reload_log()

    def _log_path(self):
        return os.path.join(core.LOG_DIR,
                            "app.log" if self.log_combo.currentIndex() == 0
                            else "error.log")

    def _reload_log(self):
        path = self._log_path()
        text = ""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                text = "".join(lines[-800:])
            except Exception as e:
                text = f"读取失败: {e}"
        self.log_view.setPlainText(text or tr("（暂无日志）"))
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _export_log(self):
        src = self._log_path()
        if os.path.exists(src):
            dst = os.path.join(core.EXPORT_DIR, os.path.basename(src))
            shutil.copy2(src, dst)
            Toast.show_text(tr("日志已复制到 导出 目录"))

    def _upd_check_changed(self, v):
        self.app.config.set("update", "check", bool(v))

    def _show_changelog(self):
        d = updater.ChangelogDialog(self, self.t, core.APP_VERSION)
        self._changelog_dialog = d              # 持有引用防止回收
        d.show()

    # ================================================================ 关于
    def _page_about(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignTop)
        self.nav.addItem(tr("📄 关于"))
        self.pages.addWidget(w)

        title = QLabel(core.APP_NAME)
        title.setStyleSheet("font-size:15pt;font-weight:bold;")
        lay.addWidget(title)
        lay.addWidget(QLabel(tr("轻量桌面工作记事录 · 完全本地离线")))
        lay.addSpacing(6)
        lay.addWidget(QLabel(tr("作者：你的好邻居\n联系邮箱：1559573443@qq.com\nQQ：1559573443")))
        # 软件更新（版本号 + 自动检查 GitHub Releases）
        up_sep = QLabel(tr("软件更新"))
        up_sep.setStyleSheet(f"font-weight:bold;margin-top:10px;color:{self.t['accent']};")
        lay.addWidget(up_sep)
        lay.addWidget(QLabel(
            tr("当前版本：{v}").replace("{v}", "v" + core.APP_VERSION)))
        # 更新源标识（GitHub 不可达时自动切换国内镜像）
        src = self.app.config.get("update", "last_source", default="")
        src_txt = tr("当前更新源：国内镜像") if src == "mirror" \
            else tr("当前更新源：GitHub")
        self.upd_source_lbl = QLabel(src_txt)
        self.upd_source_lbl.setStyleSheet(
            f"color:{theme_mod.rgba(self.t['text'], 170)};")
        lay.addWidget(self.upd_source_lbl)
        self.upd_check_chk = QCheckBox(tr("启动时检查更新（仅连接 GitHub Releases 公共接口，不收集任何信息）"))
        self.upd_check_chk.setChecked(
            bool(self.app.config.get("update", "check", default=True)))
        self.upd_check_chk.toggled.connect(self._upd_check_changed)
        lay.addWidget(self.upd_check_chk)
        urow = QHBoxLayout()
        btn_log = QPushButton(tr("查看更新日志"))
        btn_log.clicked.connect(self._show_changelog)
        urow.addWidget(btn_log)
        btn_check = QPushButton(tr("检查更新"))
        btn_check.clicked.connect(lambda: self.app.check_updates(manual=True))
        urow.addWidget(btn_check)
        urow.addStretch()
        lay.addLayout(urow)
        unote = QLabel(tr("国内镜像：GitHub 无法访问时自动切换，无需科学上网即可更新"))
        unote.setWordWrap(True)
        unote.setStyleSheet(f"color:{theme_mod.rgba(self.t['text'], 140)};font-size:8pt;")
        lay.addWidget(unote)
        # 打赏作者（下移三行，与上方信息隔开）
        lay.addSpacing(45)
        donate = QLabel(tr("打赏作者"))
        donate.setStyleSheet(f"font-weight:bold;color:{self.t['accent']};")
        lay.addWidget(donate)
        lay.addWidget(QLabel(tr("请作者喝杯咖啡吧~")))
        if os.path.exists(core.DONATION_IMG):
            donate_img = QLabel()
            pm = QPixmap(core.DONATION_IMG).scaledToWidth(128, Qt.SmoothTransformation)
            donate_img.setPixmap(rounded_pixmap(pm, 0.18))
            donate_img.setToolTip(tr("微信/支付宝扫码打赏，感谢支持！"))
            lay.addWidget(donate_img)
        lay.addStretch(1)
        bottom = QHBoxLayout()
        bottom.setAlignment(Qt.AlignBottom)
        bottom.addStretch(1)
        btxt = QVBoxLayout()
        btxt.setSpacing(2)
        tip = QLabel(tr("所有数据保存在程序目录内，卸载只需删除本地文件夹。"),
                     alignment=Qt.AlignHCenter)
        tip.setWordWrap(False)
        tip.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tip.setStyleSheet(f"font-size:8pt;color:{theme_mod.rgba(self.t['text'], 160)};")
        btxt.addWidget(tip)
        warn = QLabel(tr("本应用完全开源且免费，任何向你收费的都是骗子。"),
                      alignment=Qt.AlignHCenter)
        warn.setWordWrap(False)
        warn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        warn.setStyleSheet(f"font-size:8pt;font-weight:bold;color:{self.t['accent']};")
        btxt.addWidget(warn)
        btxt_w = QWidget()
        btxt_w.setLayout(btxt)
        bottom.addWidget(btxt_w, alignment=Qt.AlignBottom)
        bottom.addStretch(1)
        if os.path.exists(core.LOGO_PATH):
            logo = QLabel()
            pm = QPixmap(core.LOGO_PATH)
            logo.setPixmap(pm.scaledToWidth(96, Qt.SmoothTransformation))
            bottom.addWidget(logo, alignment=Qt.AlignBottom)
        lay.addLayout(bottom)
