# -*- coding: utf-8 -*-
"""桌面悬浮主窗：无边框、磨砂半透明，按日期分组 + 循环任务区，支持
折叠/展开、拖拽排序、搜索、边缘缩放、紧凑模式。"""
from __future__ import annotations

import ctypes
import traceback
from ctypes import wintypes
from datetime import date, datetime, timedelta

from PySide6.QtCore import QEvent, QRect, Qt, QTimer
from PySide6.QtGui import QCursor, QFont, QGuiApplication
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

import core
import theme as theme_mod
from core import log
from i18n import tr, current_lang
from widgets import (BgFrame, CompactIconButton,
                     set_click_through, set_window_z_order, apply_frosted,
                     embed_to_desktop_if_needed,
                     shell_tray_alive, unembed_from_desktop, apply_window_corners)

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday",
               "Friday", "Saturday", "Sunday"]


# ---------------------------------------------------------------- 提醒行（独立区域）
class ReminderChip(QFrame):
    """提醒栏里的单条提醒：时间 + 内容，超长自动换行；左键编辑，右键菜单。
    左侧拖拽手柄支持自由排序（与循环任务/网址直达一致）。"""

    def __init__(self, win, item: dict):
        super().__init__()
        self.win, self.item = win, item
        self.group_key = "reminder"
        self.setObjectName("ReminderChip")
        self.setCursor(Qt.PointingHandCursor)
        t = win.t
        self.t = t
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.setSpacing(4)
        lay.addWidget(DragHandle(self), 0, Qt.AlignVCenter)
        rt = core.parse_dt(item.get("remind_time"))
        overdue = bool(rt and rt < core.now())
        time_txt = rt.strftime("%m-%d %H:%M") if rt else item.get("remind_time", "")
        color = t["high"] if overdue else t["text"]
        full = f"⏰ {time_txt} {item['title']}"
        self.lbl = QLabel(full)
        self.lbl.setWordWrap(True)
        self.lbl.setStyleSheet(f"color:{color};")
        self.lbl.setToolTip(full)
        lay.addWidget(self.lbl)
        self.setStyleSheet(
            f"#ReminderChip{{background-color:{theme_mod.rgba(t['accent'],60)};"
            f"border-radius:8px;}}")

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.win.app.reminder_context_menu(self.item, QCursor.pos())
        elif e.button() == Qt.LeftButton:
            self.win.app.edit_reminder(self.item)


# ---------------------------------------------------------------- 拖拽手柄
class DragHandle(QLabel):
    def __init__(self, row):
        super().__init__("≡")
        self.row = row
        self.setFixedWidth(14)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip(tr("拖拽排序"))
        self.setStyleSheet(f"color:{row.t['done_text']};padding:0 1px;")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.row.win._drag_start(self.row)

    def mouseMoveEvent(self, e):
        self.row.win._drag_move(QCursor.pos())

    def mouseReleaseEvent(self, e):
        self.row.win._drag_end()


# ---------------------------------------------------------------- 事项行
class ItemRow(QFrame):
    def __init__(self, win, item: dict, group_key: str | None):
        super().__init__()
        self.win, self.item, self.group_key = win, item, group_key
        self.t = win.t
        self._hovering = False
        self.setObjectName("ItemRow")
        t = self.t
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 3, 4, 3)
        lay.setSpacing(4)

        # 优先级色条（网址直达用自定义颜色）
        if item["type"] == "link":
            pcolor = item.get("bar_color") or t["accent"]
        else:
            pcolor = t.get(item.get("priority", "mid"), t["mid"])
        strip = QFrame(fixedWidth=4, fixedHeight=22)
        strip.setStyleSheet(f"background-color:{pcolor};border-radius:2px;")
        if item["type"] == "link":
            strip.setToolTip(item.get("url") or "")
        else:
            pname = core.priority_name(item.get("priority", "mid"))
            strip.setToolTip(f"Priority: {pname}" if current_lang() == "en"
                             else f"优先级：{pname}")
        lay.addWidget(strip, 0, Qt.AlignVCenter)

        # 待办拖拽手柄（待办/循环任务/网址直达 可手动排序）
        if item["type"] in ("todo", "recur", "link") \
                and not item.get("done") and group_key:
            lay.addWidget(DragHandle(self), 0, Qt.AlignVCenter)

        # 标题（删除线，超长自动换行）
        done = self.is_done()
        self.title_lbl = QLabel(item["title"])
        self.title_lbl.setWordWrap(True)
        f = QFont()
        f.setStrikeOut(done)
        self.title_lbl.setFont(f)
        overdue = self.is_overdue()
        color = t["high"] if overdue else (t["done_text"] if done else t["text"])
        self.title_lbl.setStyleSheet(f"color:{color};")
        lay.addWidget(self.title_lbl, 1)

        # 标签
        for tag in item.get("tags", [])[:3]:
            tl = QLabel(tag)
            tl.setStyleSheet(f"color:{t['accent']};border:1px solid {theme_mod.rgba(t['accent'],120)};"
                             f"border-radius:6px;padding:0 5px;font-size:8pt;")
            lay.addWidget(tl, 0, Qt.AlignVCenter)

        # 时间/状态（网址直达显示网址）
        self.time_lbl = QLabel(self.time_text())
        self.time_lbl.setStyleSheet(f"color:{t['done_text']};font-size:8.5pt;")
        if item["type"] == "link":
            self.time_lbl.setToolTip(item.get("url") or "")
        lay.addWidget(self.time_lbl, 0, Qt.AlignVCenter)

        # 一键直达：网址直达 → 打开网站；其余 → 打开工作目录
        if item["type"] == "link":
            btn = QLabel("🌐")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tr("打开网址"))
            btn.mousePressEvent = lambda e: win.app.open_link(self.item)
        else:
            btn = QLabel("📁")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tr("打开工作目录"))
            btn.mousePressEvent = lambda e: win.app.open_folder_flow(self.item)
        lay.addWidget(btn, 0, Qt.AlignVCenter)

        self._apply_hover(False)
        if win.highlight_id == item["id"]:
            self.setStyleSheet(
                f"#ItemRow{{background-color:{theme_mod.rgba(t['accent'],70)};"
                f"border:1px solid {theme_mod.rgba(t['accent'],180)};border-radius:8px;}}")

    # ---------------- 状态
    def is_done(self) -> bool:
        it = self.item
        if it["type"] == "recur":
            # 循环任务永远处于未完成状态（总有下一期，不划线标记完成）
            return False
        return it.get("done", False)

    def is_overdue(self) -> bool:
        it = self.item
        now = core.now()
        if it["type"] == "todo" and not it.get("done") and it.get("deadline"):
            d = core.parse_dt(it["deadline"])
            return bool(d and d < now)
        if it["type"] == "recur":
            pend = core.pending_instance(it)
            if pend:
                p = core.parse_dt(pend)
                # 当期提醒时间已过且距下次提醒之前都算逾期未完成
                return bool(p and p < now - timedelta(minutes=1))
        return False

    def time_text(self) -> str:
        it = self.item
        if it["type"] == "todo":
            dl = core.parse_dt(it.get("deadline"))
            if dl:
                today = date.today()
                if dl.date() == today:
                    return f"{tr('截止 ')}{dl.strftime('%H:%M')}"
                return f"{tr('截止 ')}{dl.strftime('%m-%d %H:%M')}"
        if it["type"] == "link":
            u = (it.get("url") or "").strip()
            if not u:
                return ""
            return u if len(u) <= 22 else u[:22] + "…"
        return ""

    def refresh_soft(self):
        """就地更新随时间变化的显示（完成状态、逾期、时间文案），不重建控件。"""
        done = self.is_done()
        overdue = self.is_overdue()
        t = self.t
        f = QFont()
        f.setStrikeOut(done)
        self.title_lbl.setFont(f)
        color = t["high"] if overdue else (t["done_text"] if done else t["text"])
        self.title_lbl.setStyleSheet(f"color:{color};")
        self.time_lbl.setText(self.time_text())
        if self.win.highlight_id == self.item["id"]:
            self.setStyleSheet(
                f"#ItemRow{{background-color:{theme_mod.rgba(t['accent'],70)};"
                f"border:1px solid {theme_mod.rgba(t['accent'],180)};border-radius:8px;}}")
        else:
            self._apply_hover(self._hovering)

    # ---------------- 交互
    def _apply_hover(self, on: bool):
        self._hovering = on
        if self.win.highlight_id == self.item["id"]:
            return
        t = self.t
        bg = theme_mod.rgba(t["hover"], 130) if on else "transparent"
        self.setStyleSheet(f"#ItemRow{{background-color:{bg};border-radius:8px;}}")

    def enterEvent(self, e):
        self._apply_hover(True)

    def leaveEvent(self, e):
        self._apply_hover(False)

    def mouseDoubleClickEvent(self, e):
        self.win.app.show_detail(self.item)

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.win.highlight_id = None
            self.win.app.item_context_menu(self.item, QCursor.pos())
        elif e.button() == Qt.LeftButton and self.win.highlight_id == self.item["id"]:
            self.win.highlight_id = None
            self.win.refresh()


# ---------------------------------------------------------------- 分组标题
class GroupHeader(QFrame):
    def __init__(self, win, title: str, key: str):
        super().__init__()
        self.win, self.key = win, key
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        self.arrow = QLabel()
        self.arrow.setFixedWidth(14)
        lay.addWidget(self.arrow)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-weight:bold;")
        lay.addWidget(self.title)
        lay.addStretch()
        self.refresh_arrow()

    def refresh_arrow(self):
        expanded = self.win.expanded.get(self.key, False)
        self.arrow.setText("▼" if expanded else "▶")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # 就地切换组容器可见性：不重建内容、不改变窗口高度、
            # 避免全量重建导致的窗口闪烁（“幽灵窗口”）
            self.win.toggle_group(self.key)


# ---------------------------------------------------------------- 悬浮主窗
class FloatWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.t = app.config.get("theme")
        self.expanded: dict[str, bool] = {}
        self.highlight_id = None
        self._move_pos = None
        self._search_drag = None
        self._drag_row = None
        self._indicator = None
        self._resize_dir = None
        self._resize_start = None
        self._compact_pressed = False
        self._compact_moved = False
        self._rows: list[ItemRow] = []
        self._group_headers: dict[str, GroupHeader] = {}  # key → 组头（展开/收起就地切换用）
        self._user_resized = False     # 用户手动缩放过窗口高度后，展开/收起不再重算高度
        self._pre_compact_h = None     # 进入紧凑模式前的高度（退出时恢复，不覆盖用户调整）
        self.setWindowTitle(core.APP_NAME)
        self.setMinimumWidth(240)
        self._build_shell()
        self.apply_window_state()
        self.refresh()
        self.apply_diy_bg(app.config.get("diy_bg", default={}))

    # ---------------- 框架
    def _build_shell(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.panel = BgFrame(objectName="FrostedPanel")
        outer.addWidget(self.panel)
        self.main_lay = QVBoxLayout(self.panel)
        self.main_lay.setContentsMargins(8, 6, 8, 8)
        self.main_lay.setSpacing(4)

        # 头部：来活了 + 搜索（独立部件，可 DIY 背景）
        self.header = BgFrame(objectName="FrostedPanel")
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        self.btn_huo = QPushButton(tr("⚡ 来活了"), objectName="AccentButton")
        self.btn_huo.setToolTip(tr("快速记录工作 / 登记以往工作"))
        self.btn_huo.clicked.connect(lambda: self.app.quick_record_menu())
        hl.addWidget(self.btn_huo)
        self.search = QLineEdit(placeholderText=tr("🔍 搜索…"))
        self._search_timer = QTimer(self, singleShot=True, interval=150,
                                    timeout=self.refresh)
        self.search.textChanged.connect(lambda _: self._search_timer.start())
        hl.addWidget(self.search, 1)
        self.btn_min = CompactIconButton(objectName="CompactButton", fixedWidth=30,
                                         text=self.t.get("text", "#e8e8f0"))
        self.btn_min.setFixedHeight(28)
        self.btn_min.setToolTip(tr("最小化到紧凑模式"))
        self.btn_min.clicked.connect(lambda: self.app.toggle_compact(None))
        hl.addWidget(self.btn_min)
        self.main_lay.addWidget(self.header)

        # 横向独立提醒区（在窗口内横向铺满，提醒文字自动换行）
        self.reminder_panel = BgFrame(objectName="FrostedPanel")
        rp_lay = QVBoxLayout(self.reminder_panel)
        rp_lay.setContentsMargins(8, 4, 8, 4)
        rp_lay.setSpacing(4)
        self.reminder_lay = QVBoxLayout()
        self.reminder_lay.setSpacing(4)
        rp_lay.addLayout(self.reminder_lay, 1)
        btn_rm = QPushButton(tr("＋ 添加提醒"), objectName="FlatButton")
        btn_rm.setToolTip(tr("添加提醒（到点提醒你做什么事，不绑定文件夹）"))
        btn_rm.clicked.connect(lambda: self.app.add_reminder())
        rp_lay.addWidget(btn_rm)
        self.reminder_panel.setVisible(False)
        self.reminder_panel.setProperty("group_key", "reminder")
        self.main_lay.insertWidget(1, self.reminder_panel)

        # 内容区：按 年→月 分组平铺；内容超高时滚动查看（滚轮，无滚动条）
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        self.content = BgFrame()
        self.content_lay = QVBoxLayout(self.content)
        self.content_lay.setContentsMargins(0, 0, 0, 0)
        self.content_lay.setSpacing(3)
        self.scroll.setWidget(self.content)
        self.main_lay.addWidget(self.scroll, 1)

        # 边缘缩放：面板/头部/时钟区/紧凑条都跟踪鼠标并安装事件过滤器
        self.panel.setMouseTracking(True)
        self.header.setMouseTracking(True)
        self.setMouseTracking(True)
        self.panel.installEventFilter(self)
        self.header.installEventFilter(self)
        self.search.installEventFilter(self)

        # 底部时钟区（独立区域，可在设置中关闭；含下班倒计时）
        self._show_clock = bool(self.app.config.get(
            "window", "show_clock", default=True))
        self._offwork_on = bool(self.app.config.get(
            "offwork", "enabled", default=False))
        self.clock_panel = BgFrame(objectName="FrostedPanel")
        cp_lay = QVBoxLayout(self.clock_panel)
        cp_lay.setContentsMargins(10, 6, 10, 8)
        cp_lay.setSpacing(0)
        self.clock_time_lbl = QLabel(alignment=Qt.AlignCenter)
        self.clock_time_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.clock_time_lbl.setStyleSheet(
            f"font-size:22pt;font-weight:bold;color:{self.t['text']};letter-spacing:2px;")
        self.clock_date_lbl = QLabel(alignment=Qt.AlignCenter)
        self.clock_date_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.clock_date_lbl.setStyleSheet(
            f"font-size:9pt;color:{self.t['done_text']};")
        self.clock_off_lbl = QLabel(alignment=Qt.AlignCenter)
        self.clock_off_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.clock_off_lbl.setStyleSheet(
            f"font-size:10pt;font-weight:bold;color:{self.t['text']};")
        self.clock_time_lbl.setVisible(self._show_clock)
        self.clock_date_lbl.setVisible(self._show_clock)
        self.clock_off_lbl.setVisible(self._offwork_on)
        cp_lay.addWidget(self.clock_time_lbl)
        cp_lay.addWidget(self.clock_date_lbl)
        cp_lay.addWidget(self.clock_off_lbl)
        self.clock_panel.setVisible(self._show_clock or self._offwork_on)
        self.clock_panel.setMouseTracking(True)
        self.clock_panel.installEventFilter(self)
        outer.addWidget(self.clock_panel)

        # 紧凑模式条（长按拖拽移动、点击展开、边缘横向缩放）
        self.compact_bar = BgFrame(objectName="FrostedPanel")
        cl = QHBoxLayout(self.compact_bar)
        cl.setContentsMargins(10, 4, 10, 4)
        self.compact_lbl = QLabel()
        self.compact_lbl.setWordWrap(True)
        cl.addWidget(self.compact_lbl)
        self.compact_bar.hide()
        outer.addWidget(self.compact_bar)
        self.compact_bar.setMouseTracking(True)
        self.compact_bar.installEventFilter(self)
        self.compact_bar.mousePressEvent = self._compact_press
        self.compact_bar.mouseMoveEvent = self._compact_move
        self.compact_bar.mouseReleaseEvent = self._compact_release

        self._clock = QTimer(self, timeout=self._tick, interval=20000)
        self._clock.start()
        self._clock_timer = QTimer(self, timeout=self._update_clock, interval=1000)
        self._clock_timer.stop()   # 按需启停（_sync_clock_timer）
        self._geo_timer = QTimer(self, singleShot=True, interval=600,
                                 timeout=self.save_geometry)
        # 桌面层体检：Explorer 崩溃/重启导致 WorkerW 重建后自动恢复嵌入
        self._embed_check = QTimer(self, interval=5000, timeout=self._embed_health)
        self._embed_check.start()
        self._expect_visible = True   # 窗口应显示状态（用于体检时区分用户隐藏）
        self._native_hwnd = 0
        self._update_clock()
        self._tick()

    def _compact_press(self, e):
        if e.button() == Qt.LeftButton:
            self._move_pos = e.globalPosition().toPoint() - self.pos()
            self._compact_pressed = True
            self._compact_moved = False

    def _compact_move(self, e):
        if self._compact_pressed and e.buttons() & Qt.LeftButton:
            g = e.globalPosition().toPoint()
            if not self._compact_moved and \
                    (g - self.pos() - self._move_pos).manhattanLength() > 5:
                self._compact_moved = True
            if self._compact_moved:
                self.move(g - self._move_pos)

    def _compact_release(self, e):
        if e.button() == Qt.LeftButton:
            self._compact_pressed = False
            if self._compact_moved:
                self.save_geometry()
            else:
                self.app.toggle_compact(False)

    def _update_clock(self):
        n = datetime.now()
        self.clock_time_lbl.setText(n.strftime("%H:%M:%S"))
        if current_lang() == "en":
            self.clock_date_lbl.setText(
                f"{WEEKDAYS_EN[n.weekday()]}, {n.year}-{n.month:02d}-{n.day:02d}")
        else:
            self.clock_date_lbl.setText(
                f"{n.year}年{n.month}月{n.day}日 星期{WEEKDAYS[n.weekday()]}")
        self._update_offwork()

    def _update_offwork(self):
        """按设置计算并刷新下班倒计时文案。"""
        cfg = self.app.config.get("offwork", default={})
        n = datetime.now()
        if not cfg.get("enabled"):
            self.clock_off_lbl.setText("")
            return
        if cfg.get("weekdays_only", True) and n.weekday() >= 5:
            self.clock_off_lbl.setText(tr("休息日"))
            return
        try:
            hh, mm = [int(x) for x in str(cfg.get("time", "18:00")).split(":")]
        except Exception:
            hh, mm = 18, 0
        target = n.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if n >= target:
            self.clock_off_lbl.setText(tr("已下班"))
            return
        secs = int((target - n).total_seconds())
        fmt = cfg.get("format", "min")
        if current_lang() == "en":
            h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
            if fmt == "sec":
                value = f"{secs} s"
            elif fmt == "hour":
                value = f"{h} h {m} min"
            else:
                value = f"{m} min {s:02d} s"
        else:
            if fmt == "sec":
                value = f"{secs} 秒"
            elif fmt == "hour":
                value = f"{secs // 3600}小时{(secs % 3600) // 60}分"
            else:
                value = f"{secs // 60}分{secs % 60:02d}秒"
        template = str(cfg.get("template", "距下班 {n}"))
        if template == "距下班 {n}":
            template = tr("距下班 {n}")
        self.clock_off_lbl.setText(template.replace("{n}", value))

    def _refresh_clock_panel_visibility(self):
        if self.app.config.get("window", "compact"):
            self.clock_panel.setVisible(False)
            self._sync_clock_timer()
            return
        show_clock = bool(self.app.config.get("window", "show_clock", default=True))
        off = bool(self.app.config.get("offwork", "enabled", default=False))
        self.clock_panel.setVisible((show_clock or off) and self.panel.isVisible())
        self.clock_time_lbl.setVisible(show_clock)
        self.clock_date_lbl.setVisible(show_clock)
        self.clock_off_lbl.setVisible(off)
        if show_clock or off:
            self._update_clock()
        self._sync_clock_timer()

    def _sync_clock_timer(self):
        """1s 时钟定时器按需启停：仅当窗口可见且时钟区实际显示时才运行，
        其余时间保持完全静默，待机零占用。"""
        need = (self.isVisible()
                and not self.app.config.get("window", "compact")
                and (bool(self.app.config.get("window", "show_clock", default=True))
                     or bool(self.app.config.get("offwork", "enabled", default=False))))
        if need and not self._clock_timer.isActive():
            self._clock_timer.start()
        elif not need and self._clock_timer.isActive():
            self._clock_timer.stop()

    def _tick(self):
        # 仅就地刷新逾期状态/时间文案，避免整窗重建造成瞬时闪烁
        self.refresh(soft=True)

    # ---------------- 窗口状态
    def apply_window_state(self):
        cfg = self.app.config.get("window")
        flags = Qt.FramelessWindowHint | Qt.Tool
        if cfg.get("topmost"):
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags |= Qt.WindowStaysOnBottomHint   # 贴在桌面层
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        w = cfg.get("w") or 330
        x, y = cfg.get("x"), cfg.get("y")
        if x is not None and y is not None:
            self.setGeometry(x, y, w, min(self.height() or 400, 500))
        else:
            scr = self.screen().availableGeometry()
            self.setGeometry(scr.right() - w - 40, scr.top() + 60, w, 420)
        self.set_compact(cfg.get("compact", False), save=False)
        set_click_through(self, cfg.get("click_through", False))
        self.show()
        if cfg.get("topmost"):
            set_window_z_order(self, True)   # 强制置顶 Z 序
            unembed_from_desktop(self)       # 解除桌面嵌入，还原为普通顶层窗口
        self.save_geometry()                 # 持久化位置，供崩溃重建后恢复

    def save_geometry(self):
        if self.app.config.get("window", "compact"):
            return
        self.app.config.data.setdefault("window", {}).update(
            x=self.x(), y=self.y(), w=self.width())
        self.app.config.save()

    def refresh_theme(self):
        self.t = self.app.config.get("theme")
        self.setStyleSheet(theme_mod.build_qss(self.t))
        self.btn_min._line = self.t.get("text", "#e8e8f0")   # 紧凑按钮线条色随主题刷新
        self.btn_min.update()
        self.clock_time_lbl.setStyleSheet(
            f"font-size:22pt;font-weight:bold;color:{self.t['text']};letter-spacing:2px;")
        self.clock_date_lbl.setStyleSheet(
            f"font-size:9pt;color:{self.t['done_text']};")
        self.clock_off_lbl.setStyleSheet(
            f"font-size:10pt;font-weight:bold;color:{self.t['text']};")
        apply_frosted(self, self.t)
        apply_window_corners(self, self.t)
        self.apply_diy_bg(self.app.config.get("diy_bg", default={}))
        self.refresh()

    def showEvent(self, e):
        super().showEvent(e)
        self._expect_visible = True
        self._track_native()
        apply_frosted(self, self.t)
        self._sync_clock_timer()
        self._ensure_desktop_embed()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._sync_clock_timer()

    def set_user_hidden(self, hidden: bool):
        """记录用户主动隐藏（托盘/快捷键），体检恢复时尊重该状态。"""
        self._expect_visible = not hidden

    def _embed_health(self):
        """5s 体检：桌面层嵌入已禁用——本机视频壁纸环境与 WorkerW 嵌入冲突
        （嵌入后窗口被压缩为窄条且不可见），保持普通悬浮窗（1.2.1 行为）。"""
        return
        # ---- 以下为原嵌入逻辑（保留代码备查，不再执行） ----
        if self.app.config.get("window", "topmost"):
            return
        try:
            hwnd = getattr(self, "_native_hwnd", 0)
            if not self._native_alive() \
                    or (self._expect_visible and hwnd
                        and not self._native_visible(hwnd)):
                # 原生窗口被销毁，或"应可见却隐藏"（Qt 在原生窗口被外部
                # 销毁后会静默重建一个隐藏的代理窗口，winId() 指向它，
                # 导致 IsWindow 误判存活）→ 一律走重建路径
                self._revive_window()
                return
            if not self._expect_visible:
                return
            if not self.isVisible():
                self.show()
            if shell_tray_alive() and not embed_to_desktop_if_needed(self):
                log.info("桌面嵌入失败，将在下轮体检重试")
            return
        except Exception:
            pass

    def _ensure_desktop_embed(self):
        """桌面嵌入已禁用——本机视频壁纸环境与 WorkerW 嵌入冲突
        （嵌入后窗口被压缩为窄条且不可见），保持普通悬浮窗。"""
        return
        # ---- 以下为原嵌入逻辑（保留代码备查，不再执行） ----
        if self.app.config.get("window", "topmost"):
            return
        try:
            if not self._native_alive():
                self._revive_window()
                return
            if not self.isVisible():
                return
            embed_to_desktop_if_needed(self)
        except Exception:
            pass

    def _native_alive(self) -> bool:
        """用上次记录的原生句柄判断窗口是否存活。
        不能直接调 winId()：Qt 在窗口被外部销毁后会静默重建一个隐藏的
        原生窗口并返回新句柄，导致检测不到 Explorer 崩溃。"""
        hwnd = getattr(self, "_native_hwnd", 0)
        if not hwnd:
            return True
        try:
            return bool(ctypes.windll.user32.IsWindow(hwnd))
        except Exception:
            return True

    def _native_visible(self, hwnd) -> bool:
        """原生窗口是否可见（Qt 的 isVisible 不感知外部 ShowWindow 隐藏）。"""
        try:
            return bool(ctypes.windll.user32.IsWindowVisible(
                wintypes.HWND(hwnd)))
        except Exception:
            return True

    def _track_native(self):
        try:
            self._native_hwnd = int(self.winId())
        except Exception:
            pass

    def _revive_window(self):
        """桌面层原生窗口随 Explorer 一起被系统销毁后重建。
        Qt 6.11 不会自动重建外部销毁的原生窗口（winId() 返回失效句柄、
        show() 空转），正确路径是销毁 QWindow 后重新 show。"""
        if getattr(self, "_reviving", False) or not self._expect_visible:
            return
        self._reviving = True
        log.info("桌面层原生窗口已销毁（Explorer 重启），正在重建…")
        try:
            wh = self.windowHandle()
            if wh is not None:
                wh.destroy()
            self.show()
            # Qt 重建窗口不会恢复配置里的位置，主动恢复（否则每次 Explorer 崩溃都会漂移）
            w = self.app.config.get("window")
            if w and w.get("x") is not None and w.get("y") is not None:
                self.move(int(w["x"]), int(w["y"]))
            wh = self.windowHandle()
            if wh is not None:
                wh.show()
            self._track_native()
            # 嵌入交给下一次体检，避免重建当帧立即 SetParent 触发异常
        except Exception:
            log.error("窗口重建失败:\n" + traceback.format_exc())
        finally:
            self._reviving = False

    # ---------------- DIY 背景模式
    def apply_diy_bg(self, cfg: dict):
        """应用 DIY 背景：各部件背景（纯色或图片，0-100 不透明度）。主面板即整体背景。"""
        cfg = cfg or {}
        enabled = bool(cfg.get("enabled"))
        comps = (cfg.get("components") or {}) if enabled else {}
        radius = self.t.get("radius", 12)
        targets = [("panel", self.panel), ("header", self.header),
                   ("reminder", self.reminder_panel),
                   ("clock", self.clock_panel), ("compact", self.compact_bar)]
        for key, w in targets:
            c = (comps.get(key) or {}) if enabled else {}
            color = c.get("color") or ""
            image = c.get("image") or ""
            alpha = int(c.get("alpha", 100))
            if isinstance(w, BgFrame):
                if enabled:
                    w.set_bg_radius(radius)
                    w.set_bg(color, image, alpha)
                else:
                    w.set_bg("", "", 100)
            elif enabled and color:
                w.setStyleSheet(f"background-color:{color};border-radius:{radius}px;")
            elif enabled and image:
                w.setStyleSheet(f"background-image:url({image});border-radius:{radius}px;")
            else:
                w.setStyleSheet("")
        self.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        apply_window_corners(self, self.t)   # 更新圆角裁剪区域，避免扩展后被裁剪
        if self.app.config.get("window", "compact"):
            QTimer.singleShot(0, self._fit_height)  # 横向缩放后重新换行并校正高度
        self._geo_timer.start()          # 防抖保存尺寸

    # ---------------- 八向边缘拖拽缩放（纯 Qt 事件实现，可靠） ----------------
    _RESIZE_CURSORS = {
        "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
        "w": Qt.SizeHorCursor, "e": Qt.SizeHorCursor,
        "nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
        "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
    }

    def _edge_zone(self, pos):
        if self.app.config.get("window", "locked"):
            return None
        g = self.rect()
        m = 6
        x, y = pos.x(), pos.y()
        left, right = x <= g.left() + m, x >= g.right() - m
        top, bottom = y <= g.top() + m, y >= g.bottom() - m
        if top and left:
            return "nw"
        if top and right:
            return "ne"
        if bottom and left:
            return "sw"
        if bottom and right:
            return "se"
        if left:
            return "w"
        if right:
            return "e"
        if top:
            return "n"
        if bottom:
            return "s"
        return None

    def eventFilter(self, obj, ev):
        if obj is self.search:
            # 空搜索框兼作拖拽手柄：按住移动=拖窗，轻点=聚焦输入
            typ = ev.type()
            if typ == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                if not self.app.config.get("window", "locked") \
                        and self.search.text() == "":
                    self._search_drag = ev.globalPosition().toPoint() - self.pos()
                    return True
            elif typ == QEvent.MouseMove and self._search_drag is not None \
                    and ev.buttons() & Qt.LeftButton:
                self.move(ev.globalPosition().toPoint() - self._search_drag)
                return True
            elif typ == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton \
                    and self._search_drag is not None:
                self._search_drag = None
                self.save_geometry()
                self.search.setFocus()   # 轻点→聚焦以输入
                return True
        if obj in (self.panel, self.header, self.clock_panel,
                   getattr(self, "compact_bar", None)):
            typ = ev.type()
            if typ == QEvent.MouseMove:
                if self._resize_dir:
                    self._do_resize(ev.globalPosition().toPoint())
                    return True
                if not (ev.buttons() & Qt.LeftButton):
                    pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                    zone = self._edge_zone(pos)
                    if zone:
                        obj.setCursor(self._RESIZE_CURSORS[zone])
                    else:
                        obj.unsetCursor()
                return False
            if typ == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                zone = self._edge_zone(pos)
                if zone:
                    self._resize_dir = zone
                    self._resize_start = (ev.globalPosition().toPoint(),
                                          self.geometry())
                    obj.grabMouse()
                    return True
            if typ == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                if self._resize_dir:
                    self._resize_dir = None
                    self._resize_start = None
                    obj.releaseMouse()
                    self.save_geometry()
                    return True
        return super().eventFilter(obj, ev)

    def _do_resize(self, gpos):
        start_pos, start_geo = self._resize_start
        dx = gpos.x() - start_pos.x()
        dy = gpos.y() - start_pos.y()
        x, y, w, h = (start_geo.x(), start_geo.y(),
                      start_geo.width(), start_geo.height())
        d = self._resize_dir
        if "w" in d:
            x = start_geo.x() + dx
            w = start_geo.width() - dx
        if "e" in d:
            w = start_geo.width() + dx
        if "n" in d:
            y = start_geo.y() + dy
            h = start_geo.height() - dy
        if "s" in d:
            h = start_geo.height() + dy
        mw, mh = self.minimumWidth(), self.minimumHeight()
        if w < mw:
            if "w" in d:
                x -= (mw - w)
            w = mw
        if h < mh:
            if "n" in d:
                y -= (mh - h)
            h = mh
        self.setGeometry(x, y, w, h)

    # ---------------- 紧凑模式
    def set_compact(self, on: bool, save=True):
        if save:
            self.app.config.set("window", "compact", on)
        self.panel.setVisible(not on)
        self.compact_bar.setVisible(on)
        if on:
            self._pre_compact_h = self.height()  # 记录进入紧凑前的高度
            self._update_compact_text()
            self.setFixedHeight(self.compact_bar.sizeHint().height() + 4)
            self.resize(self.width(), self.compact_bar.sizeHint().height() + 4)
        else:
            self.setMinimumHeight(160)
            self.setMaximumHeight(16777215)
            # 退出紧凑模式：恢复进入前的高度（不再固定 420 覆盖用户调整）
            h = self._pre_compact_h if self._pre_compact_h else None
            self._pre_compact_h = None
            if h:
                self.resize(self.width(), max(h, 160))
            self.refresh(fit=False)   # 展开时构建内容，不重算高度
        self._refresh_clock_panel_visibility()
        apply_window_corners(self, self.t)

    def _update_compact_text(self):
        item = self._most_urgent()
        if item is None:
            self.compact_lbl.setText(tr("✨ 暂无紧急事项，点击展开"))
        else:
            self.compact_lbl.setText(item['title'])
            self.compact_lbl.setStyleSheet(f"color:{self.t['high']};font-weight:bold;")
        self.compact_bar.setToolTip(tr("点击展开常规模式；长按拖拽移动；边缘可横向缩放"))
        QTimer.singleShot(0, self._fit_height)   # 字数过多换行后校正高度

    def _most_urgent(self):
        now = core.now()
        best, best_key = None, None
        for it in self.app.store.items:
            if it["type"] == "todo" and not it.get("done") and it.get("deadline"):
                d = core.parse_dt(it["deadline"])
                if d and (best_key is None or d < best_key):
                    best, best_key = it, d
            elif it["type"] == "recur":
                pend = core.pending_instance(it)
                if pend:
                    p = core.parse_dt(pend)
                    if p and (best_key is None or p < best_key):
                        best, best_key = it, p
            elif it["type"] == "remind" and not it.get("done") and it.get("remind_time"):
                p = core.parse_dt(it["remind_time"])
                if p and (best_key is None or p < best_key):
                    best, best_key = it, p
        return best

    # ---------------- 内容构建
    def refresh(self, soft=False, fit=True):
        if self.app.config.get("window", "compact"):
            self._update_compact_text()
            return

        if soft:
            for r in self._rows:
                r.refresh_soft()
            return

        # 全量重建期间禁用重绘：消除“幽灵窗口”（重建中间态闪烁），
        # 重建完成后一次性绘制最终内容
        self.setUpdatesEnabled(False)
        try:
            self._do_rebuild()
        finally:
            self.setUpdatesEnabled(True)
            self.update()
        if fit:
            # 布局要等事件循环一轮后才收敛（sizeHint 才准确），
            # 延迟适配高度，且 resize 在抑制重绘期间完成，一次绘制最终尺寸
            QTimer.singleShot(0, self._fit_height_async)

    def _fit_height_async(self):
        if not self.isVisible():
            return
        self.setUpdatesEnabled(False)
        try:
            self._fit_height()
            apply_window_corners(self, self.t)
        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def _do_rebuild(self):
        # 清空
        self._rows = []
        self._group_headers = {}
        self.expanded = {k: v for k, v in self.expanded.items()
                         if k.startswith(("y", "m")) or k in ("recur", "link")}
        while self.content_lay.count():
            w = self.content_lay.takeAt(0)
            if w.widget():
                w.widget().deleteLater()

        kw = self.search.text().strip().lower()

        def match(it):
            if kw and kw not in it["title"].lower() and \
                    not any(kw in tg.lower() for tg in it.get("tags", [])):
                return False
            return True

        # 循环任务独立区 + 其余按创建时间收纳：年 → 月 → 当月任务
        months: dict[int, dict[int, list]] = {}
        recurs = []
        reminds = []
        links = []
        for it in self.app.store.items:
            if not match(it):
                continue
            if it["type"] == "recur":
                recurs.append(it)
                continue
            if it["type"] == "remind":
                reminds.append(it)
                continue
            if it["type"] == "link":
                links.append(it)
                continue
            cd = core.parse_dt(it.get("created"))
            d = cd.date() if cd else date.today()
            months.setdefault(d.year, {}).setdefault(d.month, []).append(it)

        # 横向提醒栏（独立区域）
        self._rebuild_reminder_bar(reminds)

        # ------- 空状态引导
        if not months and not recurs and not reminds and not links:
            hint_lbl = QLabel(tr("✨ 暂无事项\n\n点击上方「⚡ 来活了」快速记录工作或添加循环任务"))
            hint_lbl.setAlignment(Qt.AlignCenter)
            hint_lbl.setWordWrap(True)
            hint_lbl.setStyleSheet(
                f"color:{self.t['done_text']};padding:18px 8px;")
            self.content_lay.addWidget(hint_lbl)

        # ------- 年 → 月 → 任务
        today = date.today()
        self._group_headers = {}
        for year in sorted(months.keys(), reverse=True):
            ykey = f"y{year}"
            y_open = self.expanded.get(ykey, True)
            self.expanded[ykey] = y_open
            yheader = GroupHeader(self, tr("{y}年").replace("{y}", str(year)), ykey)
            self._group_headers[ykey] = yheader
            self.content_lay.addWidget(yheader)
            ycont = QWidget()
            ylay = QVBoxLayout(ycont)
            ylay.setContentsMargins(10, 0, 0, 2)
            ylay.setSpacing(1)
            for month in sorted(months[year].keys(), reverse=True):
                mkey = f"m{year}_{month:02d}"
                m_open = self.expanded.get(mkey, True)
                self.expanded[mkey] = m_open
                mitems = months[year][month]
                mheader = GroupHeader(self, tr("{m}月").replace("{m}", str(month)), mkey)
                self._group_headers[mkey] = mheader
                ylay.addWidget(mheader)
                mcont = QWidget()
                mlay = QVBoxLayout(mcont)
                mlay.setContentsMargins(6, 0, 0, 2)
                mlay.setSpacing(1)
                for it in self._sorted_items(mitems, False):
                    row = ItemRow(self, it, mkey)
                    self._rows.append(row)
                    mlay.addWidget(row)
                mcont.setVisible(m_open)
                mcont.setProperty("group_key", mkey)
                ylay.addWidget(mcont)
            ycont.setVisible(y_open)
            ycont.setProperty("group_key", ykey)
            self.content_lay.addWidget(ycont)

        # ------- 循环任务独立区
        if recurs:
            self._add_recur_section(recurs)

        # ------- 网址直达独立区
        if links:
            self._add_link_section(links)

        self.content_lay.addStretch()
        # 平铺：窗口高度随内容自适应（无滚动条）；布局生效后再校正一次，
        # 因为新控件要等事件循环处理后 sizeHint 才准确
        self.content_lay.activate()
        apply_window_corners(self, self.t)
        self._refresh_clock_panel_visibility()

    def _rebuild_reminder_bar(self, reminds):
        """重建提醒区：未完成的提醒显示；已手动拖拽排序的按 order 在前，
        未排序的按提醒时间升序。文字自动换行。"""
        while self.reminder_lay.count():
            w = self.reminder_lay.takeAt(0)
            if w.widget():
                w.widget().deleteLater()
        active = [r for r in reminds if not r.get("done")]
        rest = [r for r in active if not (r.get("order") or 0) > 0]
        rest.sort(key=lambda r: core.parse_dt(r.get("remind_time")) or core.now())
        ordered = [r for r in active if (r.get("order") or 0) > 0]
        ordered.sort(key=lambda r: r.get("order", 0))
        for it in ordered + rest:
            self.reminder_lay.addWidget(ReminderChip(self, it))
        self.reminder_panel.setVisible(bool(active) and self.panel.isVisible())

    def _fit_height(self):
        if self.app.config.get("window", "compact"):
            # 紧凑模式：竖向固定，按文字换行后的实际高度调整
            fm = self.compact_lbl.fontMetrics()
            w = max(self.compact_bar.width() - 20, 50)
            rect = fm.boundingRect(QRect(0, 0, w, 100000),
                                   Qt.TextWordWrap, self.compact_lbl.text())
            self.setFixedHeight(max(rect.height() + 8, 24))
            return
        scr = QGuiApplication.primaryScreen().availableGeometry()
        if self._user_resized:
            # 用户手动调过高度：展开/收起不再重算，仅防止超出屏幕
            if self.height() > max(160, scr.height() - 60):
                self.resize(self.width(), max(160, scr.height() - 60))
            return
        # 内容超高时窗口最多长到屏幕高度-留边，超出部分在内容区滚动查看
        need = self.content.sizeHint().height() + 24
        if self.reminder_panel.isVisible():
            need += self.reminder_panel.sizeHint().height()
        if self.clock_panel.isVisible():
            need += self.clock_panel.sizeHint().height()
        # 修复：内容超高时窗口最高到屏幕外——窗口底部不超出屏幕底部
        # （窗口顶部在屏幕内时，按窗口位置收紧上限）
        limit = max(160, scr.height() - 60)
        if scr.top() <= self.y() <= scr.bottom():
            limit = max(160, min(limit, scr.bottom() - self.y()))
        self.resize(self.width(), min(max(need, 160), limit))

    def toggle_group(self, key: str):
        """组头展开/收起：就地切换容器可见性，不重建内容、不改变窗口高度、
        不触发全量重绘（消除每次操作的窗口闪烁“幽灵窗口”）。"""
        container = self._find_group_container(key)
        if container is None:
            self.refresh(fit=False)
            return
        new_state = not container.isVisible()
        container.setVisible(new_state)
        self.expanded[key] = new_state
        header = self._group_headers.get(key)
        if header is not None:
            header.refresh_arrow()

    def _add_recur_section(self, recurs):
        key = "recur"
        r_open = self.expanded.get(key, True)
        self.expanded[key] = r_open
        header = GroupHeader(self, tr("🔁 循环任务"), key)
        self._group_headers[key] = header
        self.content_lay.addWidget(header)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(10, 0, 0, 2)
        lay.setSpacing(1)
        for it in self._manual_sorted(self._sorted_items(recurs, True)):
            row = ItemRow(self, it, key)
            self._rows.append(row)
            lay.addWidget(row)
        cont.setVisible(r_open)
        cont.setProperty("group_key", key)
        self.content_lay.addWidget(cont)

    def _add_link_section(self, links):
        key = "link"
        l_open = self.expanded.get(key, True)
        self.expanded[key] = l_open
        header = GroupHeader(self, tr("🔗 网址直达"), key)
        self._group_headers[key] = header
        self.content_lay.addWidget(header)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(10, 0, 0, 2)
        lay.setSpacing(1)
        for it in self._manual_sorted(
                sorted(links, key=lambda i: i.get("created", ""), reverse=True)):
            row = ItemRow(self, it, key)
            self._rows.append(row)
            lay.addWidget(row)
        cont.setVisible(l_open)
        cont.setProperty("group_key", key)
        self.content_lay.addWidget(cont)

    def _manual_sorted(self, items):
        """已手动拖拽排序的按 order 在前，未排序的保持原时间序在后。"""
        ordered = [i for i in items if (i.get("order") or 0) > 0]
        rest = [i for i in items if not (i.get("order") or 0) > 0]
        ordered.sort(key=lambda i: i.get("order", 0))
        return ordered + rest

    def _sorted_items(self, items, is_recur):
        if is_recur:
            return sorted(items, key=lambda i: core.dt_str(
                core.next_occur(i, core.now())))
        todos = sorted((i for i in items if i["type"] == "todo"),
                       key=lambda i: (i.get("done", False), i.get("order", 0)))
        records = sorted((i for i in items if i["type"] == "record"),
                         key=lambda i: i.get("created", ""), reverse=True)
        others = sorted((i for i in items if i["type"] not in ("todo", "record")),
                        key=lambda i: i.get("created", ""), reverse=True)
        return todos + records + others

    # ---------------- 拖拽排序
    def _drag_start(self, row):
        if self.app.config.get("window", "locked"):
            return
        self._drag_row = row
        name = row.objectName() or "ItemRow"
        row.setStyleSheet(
            f"#{name}{{background-color:{theme_mod.rgba(self.t['accent'],60)};"
            f"border-radius:8px;}}")

    def _drag_move(self, gpos):
        if not self._drag_row:
            return
        key = self._drag_row.group_key
        container = self._find_group_container(key)
        if not container:
            return
        lay = self.reminder_lay if key == "reminder" else container.layout()
        rows = [lay.itemAt(i).widget() for i in range(lay.count())
                if isinstance(lay.itemAt(i).widget(), (ItemRow, ReminderChip))]
        # 指示条
        if self._indicator is None:
            self._indicator = QFrame(fixedHeight=3)
            self._indicator.setStyleSheet(
                f"background-color:{self.t['accent']};border-radius:1px;")
        pos = container.mapFromGlobal(gpos)
        insert_at = len(rows)
        for i, r in enumerate(rows):
            if pos.y() < r.y() + r.height() // 2:
                insert_at = i
                break
        self._indicator.setParent(None)
        lay.insertWidget(insert_at, self._indicator)
        self._indicator.show()
        self._insert_at = insert_at

    def _drag_end(self):
        row = self._drag_row
        self._drag_row = None
        if self._indicator:
            self._indicator.setParent(None)
            self._indicator.deleteLater()
            self._indicator = None
        if not row:
            return
        key = row.group_key
        container = self._find_group_container(key)
        if not container:
            self.refresh()
            return
        lay = self.reminder_lay if key == "reminder" else container.layout()
        rows = [lay.itemAt(i).widget() for i in range(lay.count())
                if isinstance(lay.itemAt(i).widget(), (ItemRow, ReminderChip))]
        itype = row.item["type"]
        if itype == "todo":
            group = [r.item for r in rows
                     if r.item["type"] == "todo" and not r.item.get("done")]
        elif itype in ("recur", "link", "remind"):
            group = [r.item for r in rows if r.item["type"] == itype]
        else:
            self.refresh()
            return
        src = group.index(row.item)
        dst = getattr(self, "_insert_at", src)
        # _insert_at 是布局索引（含非同类行），换算到同类序列
        dst_idx = 0
        for i, r in enumerate(rows):
            if i >= dst:
                break
            if r.item["type"] == itype and not (itype == "todo" and r.item.get("done")):
                dst_idx += 1
        if src < dst_idx:
            dst_idx -= 1
        dst_idx = max(0, min(dst_idx, len(group) - 1))
        if src != dst_idx:
            group.insert(dst_idx, group.pop(src))
            for n, it in enumerate(group):
                it["order"] = (n + 1) * 10
            self.app.store.save()
            core.log.info(f"手动排序({core.type_name(itype)}): {row.item['title']} -> 第{dst_idx + 1}位")
        self.refresh()

    def _find_group_container(self, key):
        if key == "reminder":
            return self.reminder_panel
        for i in range(self.content_lay.count()):
            w = self.content_lay.itemAt(i).widget()
            if not w:
                continue
            if w.property("group_key") == key:
                return w
            sub = w.layout()
            if sub:
                for j in range(sub.count()):
                    c = sub.itemAt(j).widget()
                    if c and c.property("group_key") == key:
                        return c
        return None

    # ---------------- 窗口拖动（标题栏区域）
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 34 \
                and not self.app.config.get("window", "locked") \
                and not self.search.hasFocus():
            self._move_pos = e.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._move_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._move_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._move_pos is not None:
            self._move_pos = None
            self.save_geometry()
        super().mouseReleaseEvent(e)

    def closeEvent(self, e):
        # 关闭按钮不退出，仅隐藏（托盘长期驻留）
        e.ignore()
        self.hide()
