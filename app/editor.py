# -*- coding: utf-8 -*-
"""事项编辑对话框、详情面板、提醒弹窗。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateTimeEdit, QDialog,
                               QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QPushButton, QWidget)
import core
from i18n import tr, current_lang
from widgets import FramelessDialog, ColorDialog

ADVANCE_OPTIONS = [("截止时提醒", 0), ("提前5分钟", 5), ("提前15分钟", 15),
                   ("提前30分钟", 30), ("提前1小时", 60), ("提前1天", 1440),
                   ("不提醒", -1)]


def _form_row(label: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    lbl = QLabel(tr(label))
    lbl.setFixedWidth(64)
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


def _find_config(widget):
    """从任意父级控件向上查找 Config 对象（窗口或对话框）。"""
    w = widget
    while w is not None:
        c = getattr(w, "config", None)
        if c is None and hasattr(w, "app"):
            c = getattr(getattr(w, "app", None), "config", None)
        if c is not None:
            return c
        w = w.parentWidget()
    return None


class ItemEditDialog(FramelessDialog):
    """添加 / 编辑 工作记录、待办事项、循环任务。非模态，不阻塞其他窗口。"""
    saved = Signal(object)          # 保存成功时发出 result_item

    def __init__(self, parent, t: dict, item_type: str, item: dict | None = None,
                 record_now: bool = True, config=None):
        if item_type == "todo":
            title = tr("开始新工作") if item is None else tr("编辑待办事项")
        else:
            base = core.type_name(item_type)
            title = (tr("编辑{name}") if item else tr("添加{name}")) \
                .replace("{name}", base)
        super().__init__(parent, t, title, width=400)
        self.setWindowModality(Qt.NonModal)
        self.item_type = item_type
        self.item = item
        self.config = config or _find_config(parent)

        self.title_edit = QLineEdit(item["title"] if item else "")
        self.title_edit.setPlaceholderText(tr("请输入事项名称…"))
        self.body.addLayout(_form_row("名称", self.title_edit))

        # ---- 工作记录：时间（支持登记以往工作）
        if item_type == "record":
            self.time_custom = QCheckBox(tr("自定义时间（登记以往工作）"))
            created_dt = core.parse_dt(item["created"]) if item else core.now()
            self.record_time = QDateTimeEdit(QDateTime(created_dt))
            self.record_time.setDisplayFormat("yyyy-MM-dd HH:mm")
            self.record_time.setCalendarPopup(True)
            self.record_time.setEnabled(False)
            self.time_custom.toggled.connect(self.record_time.setEnabled)
            if not record_now and item is None:
                self.time_custom.setChecked(True)
            self.body.addWidget(self.time_custom)
            self.body.addLayout(_form_row("时间", self.record_time))

        # ---- 网址直达：网址 + 名称前竖条颜色
        if item_type == "link":
            self.url_edit = QLineEdit((item or {}).get("url") or "")
            self.url_edit.setPlaceholderText("https://…")
            self.body.addLayout(_form_row("网址", self.url_edit))

            crow = QHBoxLayout()
            lbl_color = QLabel(tr("名称前竖条颜色"))
            lbl_color.setFixedWidth(64)
            crow.addWidget(lbl_color)
            self.bar_color = (item or {}).get("bar_color") or t["accent"]
            self.color_btn = QPushButton(fixedWidth=64, fixedHeight=26)
            self.color_btn.clicked.connect(self._pick_bar_color)
            self._update_color_btn()
            crow.addWidget(self.color_btn)
            crow.addStretch()
            self.body.addLayout(crow)

        # ---- 优先级（默认自动，可手动选择；网址直达不需要）
        if item_type != "link":
            self.priority = QComboBox()
            self.priority.addItem(tr("自动（推荐）"), "auto")
            for k in ("high", "mid", "low"):
                self.priority.addItem(core.priority_name(k), k)
            cur = (item or {}).get("priority")
            idx = self.priority.findData(cur if cur in ("high", "mid", "low") else "auto")
            self.priority.setCurrentIndex(max(0, idx))
            self.priority.setToolTip(tr("自动：已完成→低；剩余两天以内→高；其他→中"))
            self.body.addLayout(_form_row("优先级", self.priority))

        # ---- 待办：截止时间 + 提前提醒
        if item_type == "todo":
            self.has_deadline = QCheckBox(tr("设置截止时间"))
            self.body.addWidget(self.has_deadline)
            self.deadline = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
            self.deadline.setDisplayFormat("yyyy-MM-dd HH:mm")
            self.deadline.setCalendarPopup(True)
            self.deadline.setEnabled(False)
            self.has_deadline.toggled.connect(self.deadline.setEnabled)
            if item and item.get("deadline"):
                self.has_deadline.setChecked(True)
                d = core.parse_dt(item["deadline"])
                self.deadline.setDateTime(QDateTime(d))
            self.body.addLayout(_form_row("截止时间", self.deadline))

            self.advance = QComboBox()
            for name, v in ADVANCE_OPTIONS:
                self.advance.addItem(tr(name), v)
            cur = (item or {}).get("remind_advance")
            idx = next((i for i, (_, v) in enumerate(ADVANCE_OPTIONS) if v == cur), 0)
            self.advance.setCurrentIndex(idx)
            self.body.addLayout(_form_row("提醒", self.advance))

        # ---- 循环任务：周期 + 时间
        if item_type == "recur":
            r = (item or {}).get("recur") or {}
            self.period = QComboBox()
            for k, v in core.PERIODS.items():
                self.period.addItem(core.period_name(k), k)
            self.period.setCurrentIndex(
                list(core.PERIODS).index(r.get("period", "day")))
            self.body.addLayout(_form_row("循环周期", self.period))

            self.time_row = QWidget()
            tl = QHBoxLayout(self.time_row)
            tl.setContentsMargins(0, 0, 0, 0)
            try:
                _th, _tm = str(r.get("time", "09:00")).split(":")
                _th, _tm = int(_th), int(_tm)
            except Exception:
                _th, _tm = 9, 0
            self.recur_hour = QComboBox()
            self.recur_hour.addItems([f"{i:02d}" for i in range(24)])
            self.recur_hour.setCurrentIndex(_th)
            self.recur_min = QComboBox()
            self.recur_min.addItems([f"{i:02d}" for i in range(60)])
            self.recur_min.setCurrentIndex(_tm)
            lbl_time = QLabel(tr("提醒时间"))
            lbl_time.setFixedWidth(64)
            tl.addWidget(lbl_time)
            tl.addWidget(self.recur_hour)
            tl.addWidget(self.recur_min)
            tl.addStretch()
            self.body.addWidget(self.time_row)

            # 每周 → 星期
            self.week_row = QWidget()
            wl = QHBoxLayout(self.week_row)
            wl.setContentsMargins(0, 0, 0, 0)
            self.weekday = QComboBox()
            wd_items = (("Mon", 0), ("Tue", 1), ("Wed", 2), ("Thu", 3),
                        ("Fri", 4), ("Sat", 5), ("Sun", 6)) if current_lang() == "en" \
                else (("星期一", 0), ("星期二", 1), ("星期三", 2), ("星期四", 3),
                      ("星期五", 4), ("星期六", 5), ("星期日", 6))
            for text, i in wd_items:
                self.weekday.addItem(text, i)
            self.weekday.setCurrentIndex(r.get("weekday", datetime.now().weekday()))
            lbl = QLabel(tr("星期"))
            lbl.setFixedWidth(64)
            wl.addWidget(lbl)
            wl.addWidget(self.weekday, 1)
            self.body.addWidget(self.week_row)

            # 每月/每季 → 日
            self.day_row = QWidget()
            dl = QHBoxLayout(self.day_row)
            dl.setContentsMargins(0, 0, 0, 0)
            self.monthday = QComboBox()
            self.monthday.addItems([str(i) for i in range(1, 32)])
            self.monthday.setCurrentIndex(
                max(0, int(r.get("monthday", datetime.now().day)) - 1))
            lbl2 = QLabel(tr("日期(日)"))
            lbl2.setFixedWidth(64)
            dl.addWidget(lbl2)
            dl.addWidget(self.monthday, 1)
            self.body.addWidget(self.day_row)

            # 每年 → 月+日
            self.ym_row = QWidget()
            yl = QHBoxLayout(self.ym_row)
            yl.setContentsMargins(0, 0, 0, 0)
            self.month = QComboBox()
            self.month.addItems([str(i) for i in range(1, 13)])
            self.month.setCurrentIndex(
                max(0, int(r.get("month", datetime.now().month)) - 1))
            lbl3 = QLabel(tr("月份(月)"))
            lbl3.setFixedWidth(64)
            yl.addWidget(lbl3)
            yl.addWidget(self.month, 1)
            self.body.addWidget(self.ym_row)

            self.period.currentIndexChanged.connect(self._period_changed)
            self._period_changed()

        # ---- 标签
        self.tags_edit = QLineEdit(", ".join((item or {}).get("tags", [])))
        self.tags_edit.setPlaceholderText(tr("多个标签用逗号分隔，如：紧急, 周报"))
        self.body.addLayout(_form_row("标签", self.tags_edit))

        # ---- 文件夹绑定（可选用任意一条平行生成规则，规则在 设置→文件夹 中自定义）
        # 网址直达不需要文件夹绑定
        if item_type != "link":
            self.folder_mode = QComboBox()
            existing_folder = (item or {}).get("folder")
            if existing_folder:
                short = existing_folder if len(existing_folder) <= 34 \
                    else "…" + existing_folder[-33:]
                self.folder_mode.addItem(
                    tr("保持绑定：{path}").replace("{path}", short), "keep")
            base = (self.config.get("base_folder") if self.config else None) \
                or core.DEFAULT_BASE_FOLDER
            rules_list = core.folder_rules_list(
                self.config.get("folder_rules", default={}) if self.config else {})
            for i, rule in enumerate(rules_list):
                name = rule.get("name") or f"规则{i + 1}"
                self.folder_mode.addItem(
                    tr("按规则「{name}」创建").replace("{name}", name), f"rule:{i}")
            for name in ((self.config.get("custom_folders") if self.config else None) or []):
                self.folder_mode.addItem(f"📂 {name}", core.custom_folder_path(base, name))
            self.folder_mode.addItem(tr("自定义选择文件夹…"), "manual")
            if existing_folder:
                self.folder_mode.setCurrentIndex(0)          # 保持绑定
            else:
                self.folder_mode.setCurrentIndex(
                    self.folder_mode.findData("rule:0"))      # 默认第一条生成规则
            self.body.addLayout(_form_row("文件夹", self.folder_mode))

            self.folder_row = QWidget()
            fl = QHBoxLayout(self.folder_row)
            fl.setContentsMargins(0, 0, 0, 0)
            self.folder_edit = QLineEdit(placeholderText=tr("选择要绑定的已有文件夹"))
            btn_browse = QPushButton(tr("浏览…"), fixedWidth=64)

            def _browse():
                d = QFileDialog.getExistingDirectory(self, tr("选择要绑定的文件夹"))
                if d:
                    self.folder_edit.setText(d)
            btn_browse.clicked.connect(_browse)
            fl.addWidget(self.folder_edit, 1)
            fl.addWidget(btn_browse)
            self.folder_row.setVisible(False)
            self.folder_mode.currentIndexChanged.connect(
                lambda _: self._folder_mode_changed())
            self.body.addWidget(self.folder_row)

        # ---- 按钮
        row = QHBoxLayout()
        row.addStretch()
        btn_cancel = QPushButton(tr("取消"))
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(tr("保存"), objectName="AccentButton")
        btn_ok.setDefault(True)              # 回车 = 保存
        btn_ok.clicked.connect(self._save)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        self.body.addLayout(row)
        self.title_edit.setFocus()

    def _folder_mode_changed(self):
        self.folder_row.setVisible(self.folder_mode.currentData() == "manual")
        self.adjustSize()

    def _update_color_btn(self):
        self.color_btn.setStyleSheet(
            f"background-color:{self.bar_color};"
            f"border:1px solid rgba(128,128,128,120);border-radius:4px;")

    def _pick_bar_color(self):
        d = ColorDialog(self, self.t, QColor(self.bar_color), with_alpha=False)
        if d.exec() == QDialog.Accepted:
            self.bar_color = d.color.name(QColor.HexArgb).upper()
            self._update_color_btn()

    def _period_changed(self):
        p = self.period.currentData()
        # 长期：无周期、无提醒时间，隐藏全部时间/星期/日期行
        self.time_row.setVisible(p != "long")
        self.week_row.setVisible(p == "week")
        self.day_row.setVisible(p in ("month", "quarter"))
        self.ym_row.setVisible(p == "year")
        self.adjustSize()

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            self.title_edit.setPlaceholderText(tr("⚠ 名称不能为空"))
            return
        tags = [s.strip() for s in self.tags_edit.text().replace("，", ",").split(",")
                if s.strip()]
        if self.item:
            it = self.item
        else:
            it = core.new_item(self.item_type, title)
        it["title"] = title
        it["tags"] = tags
        if self.item_type == "record":
            if self.time_custom.isChecked():
                qdt = self.record_time.dateTime().toPython()
                it["created"] = core.dt_str(qdt.replace(second=0, microsecond=0))
            elif self.item is None:
                it["created"] = core.dt_str(core.now())
        if self.item_type == "link":
            it["url"] = self.url_edit.text().strip()
            it["bar_color"] = self.bar_color
            it["priority"] = "mid"
        if self.item_type != "link":
            # 文件夹绑定方式（默认按所选生成规则，规则在 设置→文件夹 中自定义）
            fmode = self.folder_mode.currentData()
            if fmode == "manual":
                p = self.folder_edit.text().strip()
                it["folder"] = p if p else None
            elif isinstance(fmode, str) and fmode.startswith("rule:"):
                rules_list = core.folder_rules_list(
                    self.config.get("folder_rules", default={}) if self.config else {})
                idx = int(fmode.split(":", 1)[1])
                idx = idx if idx < len(rules_list) else 0
                it["folder"] = None
                it["folder_rule"] = rules_list[idx].get("name") or None
            elif fmode == "keep":
                pass                                   # 保持原绑定不变
            else:
                it["folder"] = fmode                   # 自定义子文件夹完整路径
        if self.item_type == "todo":
            if self.has_deadline.isChecked():
                qdt = self.deadline.dateTime().toPython()
                it["deadline"] = core.dt_str(qdt.replace(second=0, microsecond=0))
            else:
                it["deadline"] = None
            adv = self.advance.currentData()
            it["remind_advance"] = None if adv == -1 else adv
        if self.item_type == "recur":
            p = self.period.currentData()
            if p == "long":
                it["recur"] = {"period": "long"}
            else:
                r = {"period": p, "time": f"{self.recur_hour.currentText()}:{self.recur_min.currentText()}"}
                if p == "week":
                    r["weekday"] = self.weekday.currentData()
                if p in ("month", "quarter"):
                    r["monthday"] = int(self.monthday.currentText())
                if p == "year":
                    r["month"] = int(self.month.currentText())
                    r["monthday"] = int(self.monthday.currentText())
                it["recur"] = r
        if self.item_type != "link":
            p = self.priority.currentData()
            it["priority"] = core.auto_priority(it) if p == "auto" else p
        self.saved.emit(it)
        self.accept()


class ReminderEditDialog(FramelessDialog):
    """添加 / 编辑 一次性提醒：仅「名称 + 时间」，不绑定文件夹。非模态。"""
    saved = Signal(object)

    def __init__(self, parent, t: dict, item: dict | None = None):
        super().__init__(parent, t, tr("编辑提醒") if item else tr("添加提醒"),
                         width=400)
        self.setWindowModality(Qt.NonModal)
        self.item = item

        self.title_edit = QLineEdit(item["title"] if item else "")
        self.title_edit.setPlaceholderText(tr("请输入提醒内容，如：开周会…"))
        self.body.addLayout(_form_row("提醒", self.title_edit))

        rt = core.parse_dt(item["remind_time"]) if item else \
            core.now() + timedelta(hours=1)
        self.remind_time = QDateTimeEdit(QDateTime(rt))
        self.remind_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.remind_time.setCalendarPopup(True)
        self.body.addLayout(_form_row("时间", self.remind_time))

        self.advance = QComboBox()
        for name, v in ADVANCE_OPTIONS[:-1]:
            self.advance.addItem(tr(name), v)
        cur = (item or {}).get("remind_advance")
        idx = next((i for i, (_, v) in enumerate(ADVANCE_OPTIONS[:-1]) if v == cur), 0)
        self.advance.setCurrentIndex(idx)
        self.body.addLayout(_form_row("提前提醒", self.advance))

        tip = QLabel(tr("到点后将在右下角弹窗提醒，无需绑定文件夹。"))
        tip.setWordWrap(True)
        self.body.addWidget(tip)

        row = QHBoxLayout()
        row.addStretch()
        btn_cancel = QPushButton(tr("取消"))
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(tr("保存"), objectName="AccentButton")
        btn_ok.setDefault(True)              # 回车 = 保存
        btn_ok.clicked.connect(self._save)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        self.body.addLayout(row)
        self.title_edit.setFocus()

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            self.title_edit.setPlaceholderText(tr("⚠ 内容不能为空"))
            return
        if self.item:
            it = self.item
        else:
            it = core.new_item("remind", title)
        it["title"] = title
        qdt = self.remind_time.dateTime().toPython()
        it["remind_time"] = core.dt_str(qdt.replace(second=0, microsecond=0))
        it["remind_advance"] = self.advance.currentData()
        it["notified_for"] = None
        self.saved.emit(it)
        self.accept()


class DetailDialog(FramelessDialog):
    """详情面板：查看 / 编辑 / 完成 / 文件夹绑定 / 标签。非模态。"""
    changed = Signal()

    def __init__(self, parent, t: dict, store: core.DataStore, item: dict,
                 config: core.Config):
        super().__init__(parent, t, tr("事项详情"), width=440)
        self.setWindowModality(Qt.NonModal)
        self.store, self.item, self.config = store, item, config
        self._build()

    def _build(self):
        it = self.item
        # 清空 body
        while self.body.count():
            w = self.body.takeAt(0)
            if w.widget():
                w.widget().deleteLater()
            elif w.layout():
                sub = w.layout()
                while sub.count():
                    w2 = sub.takeAt(0)
                    if w2.widget():
                        w2.widget().deleteLater()

        type_name = core.type_name(it["type"])
        prio_name = core.priority_name(it.get("priority", "mid"))
        info = QLabel(tr("类型：{t}    优先级：{p}\n创建：{c}")
                      .replace("{t}", type_name).replace("{p}", prio_name)
                      .replace("{c}", it.get("created", "-")))
        self.body.addWidget(info)

        title = QLabel(it["title"], wordWrap=True)
        title.setStyleSheet("font-size:13pt;font-weight:bold;")
        self.body.addWidget(title)

        if it["type"] == "todo":
            dl = core.parse_dt(it.get("deadline"))
            self.body.addWidget(QLabel(
                tr("截止时间：{d}").replace("{d}", it['deadline'] if dl else tr("未设置"))))
            self.chk_done = QCheckBox(tr("已完成"))
            self.chk_done.setChecked(it.get("done", False))
            self.chk_done.toggled.connect(self._todo_done)
            self.body.addWidget(self.chk_done)

        if it["type"] == "recur":
            self.body.addWidget(QLabel(
                tr("周期：{desc}").replace("{desc}", core.recur_desc(it))))
            pend = core.pending_instance(it)
            if pend:
                self.body.addWidget(QLabel(
                    tr("当期应完成：{p}（未完成）").replace("{p}", pend)))
                btn = QPushButton(tr("✔ 完成当期任务"), objectName="AccentButton")
                btn.clicked.connect(self._complete_instance)
                self.body.addWidget(btn)
            else:
                self.body.addWidget(QLabel(
                    tr("下一次提醒：{n}").replace(
                        "{n}", core.dt_str(core.next_occur(it, core.now())))))
            hist = it.get("completed_instances", [])
            self.body.addWidget(QLabel(
                tr("历史完成次数：{n}").replace("{n}", str(len(hist)))))
            if hist:
                lw = QListWidget(maximumHeight=110)
                for h in sorted(hist, reverse=True)[:30]:
                    lw.addItem(h)
                self.body.addWidget(lw)

        if it["type"] == "link":
            self.body.addWidget(QLabel(
                tr("网址：{u}").replace("{u}", it.get("url") or "-")))
            btn_open = QPushButton(tr("🌐 打开网址"), objectName="AccentButton")
            btn_open.clicked.connect(
                lambda: core.open_url(it.get("url")))
            self.body.addWidget(btn_open)

        # 标签
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("标签")))
        self.tags_edit = QLineEdit(", ".join(it.get("tags", [])))
        self.tags_edit.editingFinished.connect(self._tags_changed)
        row.addWidget(self.tags_edit, 1)
        self.body.addLayout(row)

        # 文件夹（网址直达不需要）
        if it["type"] != "link":
            folder = it.get("folder")
            self.folder_lbl = QLabel(folder or tr("未绑定文件夹"), wordWrap=True)
            if folder:
                self.folder_lbl.setStyleSheet(f"color:{self.t['accent']};")
            self.body.addWidget(self.folder_lbl)
            frow = QHBoxLayout()
            btn_open = QPushButton(tr("📂 打开/创建"))
            btn_open.clicked.connect(self._open_folder)
            btn_bind = QPushButton(tr("重新绑定"))
            btn_bind.clicked.connect(self._rebind)
            btn_unbind = QPushButton(tr("解除绑定"))
            btn_unbind.clicked.connect(self._unbind)
            frow.addWidget(btn_open)
            frow.addWidget(btn_bind)
            frow.addWidget(btn_unbind)
            frow.addStretch()
            self.body.addLayout(frow)

        brow = QHBoxLayout()
        btn_edit = QPushButton(tr("✏ 编辑"), objectName="AccentButton")
        btn_edit.setDefault(True)            # 回车 = 编辑
        btn_edit.clicked.connect(self._edit)
        brow.addStretch()
        brow.addWidget(btn_edit)
        self.body.addLayout(brow)

    # ---------------- 操作
    def _refresh(self):
        self.store.save()
        self.changed.emit()
        self._build()
        self.adjustSize()

    def _todo_done(self, checked):
        self.item["done"] = checked
        self.item["priority"] = core.auto_priority(self.item)
        core.log.info(f"待办{'完成' if checked else '取消完成'}: {self.item['title']}")
        self._refresh()

    def _complete_instance(self):
        pend = core.pending_instance(self.item)
        if pend:
            self.item.setdefault("completed_instances", []).append(pend)
            core.log.info(f"循环任务完成当期: {self.item['title']} @ {pend}")
        self._refresh()

    def _tags_changed(self):
        self.item["tags"] = [s.strip() for s in
                             self.tags_edit.text().replace("，", ",").split(",")
                             if s.strip()]
        self._refresh()

    def _open_folder(self):
        folder = self.item.get("folder")
        if not folder or not os.path.isdir(folder):
            base = self.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
            rules = self.config.get("folder_rules", default={})
            idx = core.folder_rule_index(rules, self.item.get("folder_rule"))
            folder = core.create_bound_folder(self.item, base, rules, rule_index=idx)
            self.item["folder"] = folder
            self._refresh()
        core.open_folder(folder)

    def _rebind(self):
        d = QFileDialog.getExistingDirectory(self, "选择要绑定的文件夹",
                                             self.item.get("folder") or
                                             self.config.get("base_folder"))
        if d:
            self.item["folder"] = d
            self._refresh()

    def _unbind(self):
        self.item["folder"] = None
        self._refresh()

    def _edit(self):
        d = ItemEditDialog(self, self.t, self.item["type"], self.item)
        d.saved.connect(lambda it: self._refresh())
        d.show()


class ReminderDialog(FramelessDialog):
    """提醒弹窗：完成 / 稍后提醒（5/30/60/自定义）/ 关闭。"""
    action = Signal(str, int)     # ("done"/"snooze"/"close", minutes)

    def __init__(self, parent, t: dict, item: dict, message: str):
        super().__init__(parent, t, tr("⏰ 提醒"), width=360, closable=False)
        self.item = item
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        lbl = QLabel(message, wordWrap=True)
        lbl.setStyleSheet("font-size:11pt;")
        self.body.addWidget(lbl)
        name = QLabel(item["title"], wordWrap=True)
        name.setStyleSheet(f"font-weight:bold;color:{t['accent']};")
        self.body.addWidget(name)

        btn_done = QPushButton(tr("✔ 完成"), objectName="AccentButton")
        btn_done.clicked.connect(lambda: self._emit("done", 0))
        self.body.addWidget(btn_done)

        row = QHBoxLayout()
        for text, mins in [("5分钟后", 5), ("30分钟后", 30), ("1小时后", 60)]:
            b = QPushButton(tr(text))
            b.clicked.connect(lambda _=False, m=mins: self._emit("snooze", m))
            row.addWidget(b)
        self.body.addLayout(row)

        row2 = QHBoxLayout()
        self.custom_combo = QComboBox()
        for m in (5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240):
            self.custom_combo.addItem(f"{m}{tr(' 分钟后')}", m)
        self.custom_combo.setCurrentIndex(2)     # 默认 15 分钟
        btn_custom = QPushButton(tr("自定义稍后"))
        btn_custom.clicked.connect(
            lambda: self._emit("snooze", self.custom_combo.currentData()))
        row2.addWidget(self.custom_combo, 1)
        row2.addWidget(btn_custom)
        self.body.addLayout(row2)

        btn_close = QPushButton(tr("关闭"), objectName="FlatButton")
        btn_close.clicked.connect(lambda: self._emit("close", 0))
        self.body.addWidget(btn_close)

    def _emit(self, act: str, mins: int):
        self.action.emit(act, mins)
        self.accept()
