# -*- coding: utf-8 -*-
"""通用 UI 组件：无边框磨砂基类、自绘菜单、Toast 提示、确认对话框、
取色器（含屏幕吸管）、快捷键捕获框等。所有组件共用统一风格。"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

import theme as theme_mod

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QCursor, QGuiApplication, QImage,
                           QKeySequence, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QSlider, QVBoxLayout, QWidget)


def rounded_pixmap(pm: QPixmap, radius_ratio: float = 0.18) -> QPixmap:
    """给图片加圆角（四角透明），radius_ratio 为圆角占边长的比例。"""
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    if w <= 0 or h <= 0:
        return pm
    out = QImage(w, h, QImage.Format_ARGB32)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    r = int(min(w, h) * radius_ratio)
    path.addRoundedRect(QRectF(0, 0, w, h), r, r)
    p.setClipPath(path)
    p.drawImage(0, 0, img)
    p.end()
    return QPixmap.fromImage(out)


class BgFrame(QFrame):
    """支持纯色或图片背景的容器：图片铺满、按圆角裁剪、不透明度 0-100；未设置时透明（走主题 QSS）。"""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._bg_color = ""
        self._bg_image = ""
        self._bg_alpha = 100
        self._bg_radius = 12
        self._bg_cache_key = None
        self._bg_cache_pm = None

    def set_bg(self, color: str = "", image: str = "", alpha: int = 100):
        self._bg_color = color or ""
        self._bg_image = image or ""
        self._bg_alpha = int(alpha if alpha is not None else 100)
        self.update()

    def _cached_bg(self):
        """按当前尺寸缓存缩放好的背景图，避免每次重绘都重新读盘+缩放。"""
        key = (self._bg_image, self.width(), self.height())
        if self._bg_cache_key != key:
            pm = QPixmap(self._bg_image)
            self._bg_cache_pm = None if pm.isNull() else pm.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self._bg_cache_key = key if self._bg_cache_pm is not None else None
        return self._bg_cache_pm

    def set_bg_radius(self, r):
        self._bg_radius = int(r or 12)
        self.update()

    def paintEvent(self, e):
        if self._bg_image and os.path.exists(self._bg_image) or self._bg_color:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            r = self._bg_radius
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), r, r)
            p.setClipPath(path)
            if self._bg_image and os.path.exists(self._bg_image):
                pm = self._cached_bg()
                if pm is not None:
                    p.setRenderHint(QPainter.SmoothPixmapTransform)
                    p.setOpacity(self._bg_alpha / 100.0)
                    sx = (pm.width() - self.width()) // 2
                    sy = (pm.height() - self.height()) // 2
                    p.drawPixmap(0, 0, self.width(), self.height(),
                                 pm, sx, sy, self.width(), self.height())
            else:
                c = QColor(self._bg_color)
                if c.isValid():
                    c.setAlpha(int(self._bg_alpha / 100.0 * 255))
                    p.fillRect(self.rect(), c)
            p.end()
            return
        super().paintEvent(e)


# ---------------------------------------------------------------- Win32 圆角
def apply_window_corners(win: QWidget, t: dict):
    """按主题应用窗口圆角（区域裁剪）。已移除 DWM 毛玻璃，避免缩放/拖拽显示问题。"""
    apply_rounded_region(win, t.get("radius", 12))


def apply_frosted(win: QWidget, t: dict):
    """旧接口保留：仅应用圆角（不再使用 DWM 毛玻璃，避免缩放显示不全/拖拽卡顿）。"""
    apply_window_corners(win, t)


def apply_rounded_region(win: QWidget, radius: int):
    """把窗口裁剪为圆角矩形，使磨砂边缘也呈圆角。"""
    try:
        gdi32 = ctypes.windll.gdi32
        user32 = ctypes.windll.user32
        w, h = win.width(), win.height()
        if w <= 0 or h <= 0:
            return
        gdi32.CreateRoundRectRgn.restype = ctypes.c_void_p
        gdi32.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 4 + [ctypes.c_int, ctypes.c_int]
        user32.SetWindowRgn.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_bool]
        r = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, radius * 2, radius * 2)
        if r:
            user32.SetWindowRgn(wintypes.HWND(int(win.winId())), r, True)
    except Exception:
        pass


def set_click_through(win: QWidget, enable: bool):
    """鼠标穿透：窗口不接收任何鼠标事件。"""
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x20
    WS_EX_LAYERED = 0x80000
    try:
        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(int(win.winId()))
        style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        if enable:
            style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            style &= ~WS_EX_TRANSPARENT
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass
    win.setAttribute(Qt.WA_TransparentForMouseEvents, enable)


# ---------------------------------------------------------------- 矢量图标按钮
class _VectorButton(QPushButton):
    """用 QPainter 绘制矢量图标的按钮（比文本符号更清晰可缩放）。"""

    def paintEvent(self, e):
        super().paintEvent(e)              # 先画 QSS 背景/边框
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.paint_icon(p, self.rect())
        p.end()

    def paint_icon(self, p, rect):
        raise NotImplementedError


class CloseIconButton(_VectorButton):
    """矢量 ✕ 关闭按钮：白色圆头交叉线（以按钮中心对称）。"""

    def paint_icon(self, p, rect):
        pen = QPen(QColor(255, 255, 255), max(2, rect.width() // 8))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = rect.center().x(), rect.center().y()
        half = min(rect.width(), rect.height()) * 0.30
        p.drawLine(cx - half, cy - half, cx + half, cy + half)
        p.drawLine(cx + half, cy - half, cx - half, cy + half)


class CompactIconButton(_VectorButton):
    """矢量 − 紧凑模式按钮：横向短横（线条用字体色，背景用强调色由 QSS 提供）。"""

    def __init__(self, *a, text=None, **kw):
        super().__init__(*a, **kw)
        self._line = text or "#e8e8f0"

    def paint_icon(self, p, rect):
        pen = QPen(QColor(self._line), max(2, rect.width() // 8))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = rect.center().x(), rect.center().y()
        half = rect.width() * 0.28
        p.drawLine(cx - half, cy, cx + half, cy)


# ---------------------------------------------------------------- 无边框对话框基类
class FramelessDialog(QDialog):
    """统一风格的无边框磨砂对话框。自带标题栏（可拖动）与关闭按钮。"""

    def __init__(self, parent, t: dict, title: str = "", width: int = 420,
                 closable: bool = True):
        super().__init__(parent)
        self.t = t
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self._drag_pos = None
        self._resize_dir = None
        self._resize_start = None
        self.setMouseTracking(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.panel = BgFrame(objectName="FrostedPanel")
        outer.addWidget(self.panel)
        lay = QVBoxLayout(self.panel)
        lay.setContentsMargins(12, 8, 12, 12)
        lay.setSpacing(8)

        # 标题栏
        bar = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight:bold;")
        bar.addWidget(self.title_label)
        bar.addStretch()
        if closable:
            btn_close = CloseIconButton(objectName="CloseButton", fixedWidth=30)
            btn_close.setFixedHeight(26)
            btn_close.setToolTip("关闭")
            btn_close.setAutoDefault(False)   # 防止回车触发 ✕ 误关对话框
            btn_close.clicked.connect(self.reject)
            bar.addWidget(btn_close)
        lay.addLayout(bar)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        lay.addLayout(self.body)
        if width:
            self.setMinimumWidth(width)
        self.panel.setMouseTracking(True)
        self.panel.installEventFilter(self)
        self._diy_timer = QTimer(self, interval=500, timeout=self._live_diy)
        self._diy_timer.start()

    def _find_diy_app(self):
        """向上找持有 app 的父级（只找一次，之后缓存）。"""
        if getattr(self, "_diy_app_ref", None) is None:
            parent = self.parentWidget()
            while parent is not None:
                app = getattr(parent, "app", None)
                if app is not None:
                    self._diy_app_ref = app
                    break
                parent = parent.parentWidget()
        return self._diy_app_ref

    def _apply_diy_dialog_bg(self):
        """把桌面应用 DIY 背景中的「对话框」部件应用到本对话框面板。
        仅在配置有变化时更新，避免无谓重绘。"""
        try:
            app = self._find_diy_app()
            if app is None or not hasattr(app, "config"):
                return
            cfg = app.config.get("diy_bg", default={})
            radius = (self.t or {}).get("radius", 12)
            if cfg.get("enabled"):
                comp = (cfg.get("components") or {}).get("dialog") or {}
                color = comp.get("color") or ""
                image = comp.get("image") or ""
                alpha = int(comp.get("alpha", 100))
            else:
                color, image, alpha = "", "", 100
            if (self.panel._bg_color == color and self.panel._bg_image == image
                    and self.panel._bg_alpha == alpha
                    and self.panel._bg_radius == radius):
                return
            self.panel.set_bg_radius(radius)
            self.panel.set_bg(color, image, alpha)
        except Exception:
            pass

    def _live_diy(self):
        """可见时定时重读对话框 DIY 背景，实现实时生效。"""
        if not self.isVisible():
            return
        self._apply_diy_dialog_bg()

    def showEvent(self, e):
        super().showEvent(e)
        apply_frosted(self, self.t)
        self._apply_diy_dialog_bg()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        apply_window_corners(self, self.t)  # 更新圆角裁剪区域

    # ---------------- 八向边缘缩放
    _RESIZE_CURSORS = {
        "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
        "w": Qt.SizeHorCursor, "e": Qt.SizeHorCursor,
        "nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
        "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
    }

    def _edge_zone(self, pos):
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
        if obj is self.panel:
            typ = ev.type()
            if typ == QEvent.MouseMove:
                if self._resize_dir:
                    self._do_resize(ev.globalPosition().toPoint())
                    return True
                if not (ev.buttons() & Qt.LeftButton):
                    zone = self._edge_zone(ev.position())
                    if zone:
                        self.panel.setCursor(self._RESIZE_CURSORS[zone])
                    else:
                        self.panel.unsetCursor()
                return False
            if typ == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                zone = self._edge_zone(ev.position())
                if zone:
                    self._resize_dir = zone
                    self._resize_start = (ev.globalPosition().toPoint(),
                                          self.geometry())
                    self.panel.grabMouse()
                    return True
            if typ == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                if self._resize_dir:
                    self._resize_dir = None
                    self._resize_start = None
                    self.panel.releaseMouse()
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

    # 标题栏拖动
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 40:
            self._drag_pos = e.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)


def styled_menu(parent=None) -> QMenu:
    """自绘无边框磨砂菜单（托盘/右键统一使用）。"""
    m = QMenu(parent)
    m.setWindowFlags(m.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
    m.setAttribute(Qt.WA_TranslucentBackground)
    return m


# ---------------------------------------------------------------- Toast 屏幕角提示
class Toast(QWidget):
    _instance = None

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool |
                            Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(objectName="FrostedPanel")
        self.label.setStyleSheet("padding:10px 18px;")
        lay.addWidget(self.label)
        self._timer = QTimer(self, singleShot=True, timeout=self.hide)

    @classmethod
    def show_text(cls, text: str, ms: int = 1800):
        if cls._instance is None:
            cls._instance = Toast()
        inst = cls._instance
        inst.label.setText(text)
        inst.adjustSize()
        scr = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        inst.move(g.right() - inst.width() - 24, g.top() + 24)
        inst.show()
        inst._timer.start(ms)


# ---------------------------------------------------------------- 确认对话框（防误删）
class ConfirmDialog(FramelessDialog):
    def __init__(self, parent, t, title, message, checkbox: str | None = None,
                 ok_text="确定", danger=True):
        super().__init__(parent, t, title, width=420)
        from PySide6.QtWidgets import QCheckBox
        lbl = QLabel(message, wordWrap=True)
        self.body.addWidget(lbl)
        self.checkbox = None
        if checkbox:
            self.checkbox = QCheckBox(checkbox)
            self.checkbox.setChecked(False)
            self.body.addWidget(self.checkbox)
        row = QHBoxLayout()
        row.addStretch()
        btn_no = QPushButton("取消")
        btn_no.clicked.connect(self.reject)
        btn_yes = QPushButton(ok_text, objectName="AccentButton")
        if danger:
            danger_color = t.get("high", "#e5484d")
            btn_yes.setStyleSheet(
                f"background-color:{theme_mod.rgba(danger_color,170)};"
                f"border:1px solid {theme_mod.rgba(danger_color,220)};")
        btn_yes.clicked.connect(self.accept)
        row.addWidget(btn_no)
        row.addWidget(btn_yes)
        self.body.addLayout(row)
        btn_yes.setDefault(True)

    @classmethod
    def ask(cls, parent, t, title, message, checkbox=None, ok_text="确定"):
        d = cls(parent, t, title, message, checkbox, ok_text)
        ok = d.exec() == QDialog.Accepted
        return ok, (d.checkbox.isChecked() if d.checkbox else False)


# ---------------------------------------------------------------- 屏幕吸管取色
class EyeDropper(QDialog):
    """全屏取色：移动显示放大镜，单击取色，ESC 取消。
    用全局坐标换算到截图（设备像素）坐标，多屏/缩放比例下取色依然准确。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        scr = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self._scr_geo = scr.geometry()
        self._dpr = scr.devicePixelRatio()
        self.shot = scr.grabWindow(0)          # 先冻结屏幕（设备像素）
        self.setGeometry(self._scr_geo)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Dialog)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.color = None
        self._pos = QCursor.pos()
        self.setModal(True)

    def _shot_point(self, gpos):
        """全局鼠标坐标 → 截图设备像素坐标。"""
        return (int((gpos.x() - self._scr_geo.x()) * self._dpr),
                int((gpos.y() - self._scr_geo.y()) * self._dpr))

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.shot)
        # 放大镜
        gx, gy = self._pos.x(), self._pos.y()
        x, y = gx - self._scr_geo.x(), gy - self._scr_geo.y()
        sx, sy = self._shot_point(self._pos)
        size, zoom = 15, 8
        src = self.shot.copy(max(0, sx - size // 2), max(0, sy - size // 2), size, size)
        mag = src.scaled(size * zoom, size * zoom)
        mx = min(x + 20, self.width() - size * zoom - 4)
        my = min(y + 20, self.height() - size * zoom - 44)
        p.fillRect(mx - 2, my - 2, size * zoom + 4, size * zoom + 4, QColor(0, 0, 0, 180))
        p.drawPixmap(mx, my, mag)
        # 中心准星
        c = size * zoom // 2
        p.setPen(QColor(255, 255, 255))
        p.drawRect(mx + c - zoom // 2, my + c - zoom // 2, zoom, zoom)
        # 颜色值
        img = self.shot.toImage()
        if 0 <= sx < img.width() and 0 <= sy < img.height():
            col = img.pixelColor(sx, sy)
            p.drawText(mx, my + size * zoom + 20, col.name().upper())

    def mouseMoveEvent(self, e):
        self._pos = e.globalPosition().toPoint()
        self.update()

    def mousePressEvent(self, e):
        img = self.shot.toImage()
        sx, sy = self._shot_point(e.globalPosition().toPoint())
        if 0 <= sx < img.width() and 0 <= sy < img.height():
            self.color = img.pixelColor(sx, sy)
        self.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.reject()


class ColorDialog(FramelessDialog):
    """颜色选择：预览 + 十六进制输入 + 透明度滑条 + 屏幕吸管。"""

    def __init__(self, parent, t, initial: QColor, with_alpha=True):
        super().__init__(parent, t, "选择颜色", width=360)
        self.color = QColor(initial)
        self.with_alpha = with_alpha

        row = QHBoxLayout()
        self.preview = QFrame(fixedWidth=52, fixedHeight=36)
        row.addWidget(self.preview)
        self.hex_edit = QLineEdit(self.color.name(QColor.HexArgb).upper())
        self.hex_edit.setPlaceholderText("#RRGGBB 或 #AARRGGBB")
        self.hex_edit.editingFinished.connect(self._from_hex)
        row.addWidget(self.hex_edit, 1)
        self.body.addLayout(row)

        if with_alpha:
            ar = QHBoxLayout()
            ar.addWidget(QLabel("不透明度"))
            self.alpha_slider = QSlider(Qt.Horizontal, minimum=20, maximum=255,
                                        value=self.color.alpha())
            self.alpha_slider.valueChanged.connect(self._from_slider)
            ar.addWidget(self.alpha_slider, 1)
            self.alpha_val = QLabel(str(self.color.alpha()))
            self.alpha_val.setFixedWidth(30)
            ar.addWidget(self.alpha_val)
            self.body.addLayout(ar)

        # 常用色板
        palette = ["#1e1e28", "#2b2b3a", "#f5f6fa", "#ffffff", "#4fc3f7",
                   "#2f8fdd", "#ff5c6c", "#ffb84d", "#7bd88f", "#b39ddb",
                   "#4db6ac", "#f06292", "#8d6e63", "#90a4ae", "#000000"]
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, c in enumerate(palette):
            b = QPushButton(fixedWidth=30, fixedHeight=24)
            b.setStyleSheet(f"background-color:{c};border:1px solid rgba(128,128,128,120);"
                            f"border-radius:4px;")
            b.clicked.connect(lambda _=False, cc=c: self._set(QColor(cc)))
            grid.addWidget(b, i // 8, i % 8)
        self.body.addLayout(grid)

        row2 = QHBoxLayout()
        btn_pick = QPushButton("🖊 吸取屏幕颜色")
        btn_pick.clicked.connect(self._pick_screen)
        row2.addWidget(btn_pick)
        row2.addStretch()
        btn_ok = QPushButton("确定", objectName="AccentButton")
        btn_ok.setDefault(True)              # 回车 = 确定
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        row2.addWidget(btn_cancel)
        row2.addWidget(btn_ok)
        self.body.addLayout(row2)
        self._refresh()

    def _refresh(self):
        self.preview.setStyleSheet(
            f"background-color:{self.color.name(QColor.HexArgb)};"
            f"border:1px solid rgba(128,128,128,120);border-radius:6px;")
        self.hex_edit.setText(self.color.name(QColor.HexArgb).upper())

    def _set(self, c: QColor):
        if self.with_alpha:
            c.setAlpha(self.color.alpha())
        self.color = c
        self._refresh()

    def _from_hex(self):
        txt = self.hex_edit.text().strip()
        c = QColor(txt)
        if c.isValid():
            if self.with_alpha and len(txt) <= 7:
                c.setAlpha(self.color.alpha())
            self.color = c
            if self.with_alpha:
                self.alpha_slider.setValue(c.alpha())
        self._refresh()

    def _from_slider(self, v):
        self.color.setAlpha(v)
        self.alpha_val.setText(str(v))
        self._refresh()

    def _pick_screen(self):
        # 注意：不能 hide() 本对话框——模态 exec 循环会因隐藏立即以 Rejected 结束，
        # 导致 exec() 返回 0、取色结果被丢弃。吸管窗口全屏置顶会自然盖住本对话框。
        d = EyeDropper(self.parent())
        if d.exec() == QDialog.Accepted and d.color:
            self._set(d.color)

    @classmethod
    def get_color(cls, parent, t, initial: QColor, with_alpha=True):
        d = cls(parent, t, initial, with_alpha)
        if d.exec() == QDialog.Accepted:
            return d.color
        return None


# ---------------------------------------------------------------- 快捷键捕获
MOD_NAMES = {"ctrl", "alt", "shift", "win"}

VK_MAP = {
    "ctrl": {0xA2, 0xA3, 0x11}, "shift": {0xA0, 0xA1, 0x10},
    "alt": {0xA4, 0xA5, 0x12}, "win": {0x5B, 0x5C},
    "space": {0x20}, "tab": {0x09}, "enter": {0x0D}, "esc": {0x1B},
    "backspace": {0x08}, "delete": {0x2E}, "home": {0x24}, "end": {0x23},
    "up": {0x26}, "down": {0x28}, "left": {0x25}, "right": {0x27},
}
for _c in "abcdefghijklmnopqrstuvwxyz":
    VK_MAP[_c] = {ord(_c.upper())}
for _d in "0123456789":
    VK_MAP[_d] = {ord(_d)}
for _i in range(1, 25):
    VK_MAP[f"f{_i}"] = {0x6F + _i}

_QT_MOD_KEYS = {Qt.Key_Control: "ctrl", Qt.Key_Shift: "shift",
                Qt.Key_Alt: "alt", Qt.Key_Meta: "win"}


def combo_text(combo: list[str]) -> str:
    order = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
    return "+".join(sorted(combo, key=lambda k: (order.get(k, 9), k)))


class HotkeyEdit(QLineEdit):
    """快捷键捕获框：聚焦后按下组合键（支持四键），全部松开即完成录入。"""
    combo_changed = Signal(list)

    def __init__(self, combo: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("点击后按下组合键…")
        self._combo: list[str] = list(combo or [])
        self._active: set[str] = set()
        self._down: set[str] = set()
        self._refresh()

    def combo(self) -> list[str]:
        return list(self._combo)

    def set_combo(self, combo: list[str]):
        self._combo = list(combo)
        self._refresh()

    def _refresh(self):
        self.setText(combo_text(self._combo))

    def keyPressEvent(self, e):
        if e.isAutoRepeat():
            return
        key = e.key()
        if key in _QT_MOD_KEYS:
            name = _QT_MOD_KEYS[key]
        else:
            name = QKeySequence(key).toString().lower()
            if not name:
                return
        self._down.add(name)
        self._active.add(name)
        self.setText(combo_text(sorted(self._active)))

    def keyReleaseEvent(self, e):
        if e.isAutoRepeat():
            return
        key = e.key()
        name = _QT_MOD_KEYS.get(key) or QKeySequence(key).toString().lower()
        self._down.discard(name)
        if not self._down and self._active:
            combo = sorted(self._active)
            if any(k not in MOD_NAMES for k in combo):   # 至少一个普通键
                self._combo = combo
                self.combo_changed.emit(combo)
            self._active = set()
            self._refresh()

    def focusOutEvent(self, e):
        self._active = set()
        self._down = set()
        self._refresh()
        super().focusOutEvent(e)
