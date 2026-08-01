# -*- coding: utf-8 -*-
"""主题定义与窗口作用域样式表生成。主窗口与设置窗口各用一套独立主题，互不影响。"""
from __future__ import annotations

from PySide6.QtGui import QColor

DEFAULT_THEME = {
    "name": "深色磨砂",
    "bg": "#1e1e28",          # 主背景色
    "bg_alpha": 208,          # 主背景不透明度 0-255
    "text": "#e8e8f0",        # 文字颜色
    "done_text": "#75758a",   # 已完成事项文字颜色
    "hover": "#3d3d52",       # 悬停高亮色
    "accent": "#4fc3f7",      # 强调色（图标/进度/选中）
    "high": "#ff5c6c",        # 优先级：高
    "mid": "#ffb84d",         # 优先级：中
    "low": "#7bd88f",         # 优先级：低
    "radius": 12,             # 窗口圆角
    "font_family": "Microsoft YaHei UI",
    "font_size": 10,
}

DEFAULT_THEMES = {
    "深色磨砂": dict(DEFAULT_THEME),
    "亮色磨砂": {
        "name": "亮色磨砂",
        "bg": "#f5f6fa", "bg_alpha": 215,
        "text": "#2b2b3a", "done_text": "#a0a0b0",
        "hover": "#dde3f0", "accent": "#2f8fdd",
        "high": "#e5484d", "mid": "#e8930c", "low": "#46a758",
        "radius": 12,
        "font_family": "Microsoft YaHei UI", "font_size": 10,
    },
}

# 设置窗口主题：不含主窗口专用的已完成文字色与优先级色
DEFAULT_THEME_SETTINGS = {
    k: v for k, v in DEFAULT_THEME.items()
    if k not in ("done_text", "high", "mid", "low")
}


def rgba(hex_color: str, alpha: int | None = None) -> str:
    c = QColor(hex_color)
    a = c.alpha() if alpha is None else alpha
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


def mix(c1: str, c2: str, ratio: float) -> str:
    a, b = QColor(c1), QColor(c2)
    r = int(a.red() * (1 - ratio) + b.red() * ratio)
    g = int(a.green() * (1 - ratio) + b.green() * ratio)
    bl = int(a.blue() * (1 - ratio) + b.blue() * ratio)
    return QColor(r, g, bl).name()


def build_qss(t: dict) -> str:
    """全局样式表：菜单、对话框、输入框、按钮、滚动条、提示等全部统一。"""
    bg = rgba(t["bg"], t.get("bg_alpha", 208))
    bg_solid = t["bg"]
    text = t["text"]
    hover = rgba(t["hover"], 200)
    accent = t["accent"]
    radius = t.get("radius", 12)
    r_small = max(4, radius - 6)
    border = rgba(t["text"], 30)
    font_family = t.get("font_family", "Microsoft YaHei UI")
    font_size = t.get("font_size", 10)

    return f"""
* {{
    font-family: "{font_family}";
    font-size: {font_size}pt;
    color: {text};
    outline: none;
}}
QToolTip {{
    background-color: {bg_solid};
    color: {text};
    border: 1px solid {border};
    border-radius: {r_small}px;
    padding: 4px 8px;
}}
/* ---------------- 主容器（无边框圆角半透明） ---------------- */
#FrostedPanel {{
    background-color: {bg};
    border: 1px solid {border};
    border-radius: {radius}px;
}}
/* ---------------- 按钮 ---------------- */
QPushButton {{
    background-color: {rgba(t['hover'], 120)};
    border: 1px solid {border};
    border-radius: {r_small}px;
    padding: 5px 12px;
}}
QPushButton:hover {{ background-color: {hover}; }}
QPushButton:pressed {{ background-color: {rgba(accent, 90)}; }}
QPushButton:disabled {{ color: {rgba(text, 100)}; }}
QPushButton:checked {{
    background-color: {rgba(accent, 170)};
    border: 1px solid {rgba(accent, 230)};
    color: {mix(bg_solid, '#ffffff', 0.9)};
    font-weight: bold;
}}
#ThemeToggle {{ padding: 8px 16px; font-weight: bold; }}
#ThemeToggle:checked {{ background-color: {rgba(accent, 200)}; }}
/* 关闭按钮：无外框，仅白色 ✕，悬停加深 */
#CloseButton {{
    background-color: transparent;
    border: none;
    color: #ffffff;
    padding: 0;
}}
#CloseButton:hover {{ background-color: rgba(0, 0, 0, 130); border-radius: {r_small}px; }}
#CloseButton:pressed {{ background-color: rgba(198, 40, 40, 160); }}
/* 紧凑模式按钮：背景用强调色，线条用字体色 */
#CompactButton {{
    background-color: {rgba(accent, 150)};
    border: 1px solid {rgba(accent, 230)};
    border-radius: {r_small}px;
    color: {text};
    padding: 0;
}}
#CompactButton:hover {{ background-color: {rgba(accent, 220)}; }}
#AccentButton {{
    background-color: {rgba(accent, 160)};
    border: 1px solid {rgba(accent, 220)};
    color: {mix(bg_solid, '#ffffff', 0.9)};
    font-weight: bold;
}}
#AccentButton:hover {{ background-color: {rgba(accent, 200)}; }}
#FlatButton {{
    background-color: transparent;
    border: none;
}}
#FlatButton:hover {{ background-color: {hover}; border-radius: {r_small}px; }}
/* ---------------- 输入框 ---------------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
QDateTimeEdit, QDateEdit, QTimeEdit, QComboBox {{
    background-color: {rgba(bg_solid, 120)};
    border: 1px solid {border};
    border-radius: {r_small}px;
    padding: 4px 8px;
    selection-background-color: {rgba(accent, 140)};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus,
QSpinBox:focus, QTimeEdit:focus {{
    border: 1px solid {rgba(accent, 200)};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: none; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 5px solid {text};
    margin-right: 8px; }}
QComboBox QAbstractItemView {{
    background-color: {rgba(bg_solid, 245)};
    border: 1px solid {border};
    border-radius: {r_small}px;
    selection-background-color: {rgba(accent, 120)};
    padding: 2px;
}}
/* ---------------- 菜单（自绘无边框磨砂风格） ---------------- */
QMenu {{
    background-color: {rgba(bg_solid, 235)};
    border: 1px solid {border};
    border-radius: {r_small + 2}px;
    padding: 5px;
}}
QMenu::item {{
    padding: 6px 24px 6px 20px;
    border-radius: {r_small}px;
    margin: 1px 2px;
}}
QMenu::item:selected {{ background-color: {rgba(accent, 100)}; }}
QMenu::separator {{
    height: 1px;
    background: {border};
    margin: 4px 10px;
}}
QMenu::indicator {{ width: 14px; height: 14px; }}
/* ---------------- 滚动区域与滚动条 ---------------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {rgba(text, 60)}; border-radius: 4px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {rgba(text, 100)}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 8px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {rgba(text, 60)}; border-radius: 4px; min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
/* ---------------- 日历控件（日期时间选择弹出） ---------------- */
QCalendarWidget {{ background-color: {bg_solid}; }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {rgba(bg_solid, 235)};
}}
QCalendarWidget QToolButton {{
    background: transparent; border: none; color: {text};
    border-radius: {r_small}px; padding: 2px 6px;
}}
QCalendarWidget QToolButton:hover {{ background-color: {hover}; }}
QCalendarWidget QSpinBox {{
    background: transparent; border: none; color: {text};
}}
QCalendarWidget QWidget {{ alternate-background-color: {rgba(bg_solid, 160)}; }}
QCalendarWidget QAbstractItemView {{
    background-color: {bg_solid};
    color: {text};
    selection-background-color: {rgba(accent, 140)};
    selection-color: {mix(bg_solid, '#ffffff', 0.9)};
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {rgba(text, 90)}; }}
/* ---------------- 其它控件 ---------------- */
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1px solid {border};
    border-radius: 4px;
    background: {rgba(bg_solid, 120)};
}}
QCheckBox::indicator:checked {{
    background: {rgba(accent, 200)};
    border: 1px solid {rgba(accent, 230)};
}}
QSlider::groove:horizontal {{
    height: 4px; background: {rgba(text, 50)}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; height: 14px; margin: -5px 0;
    border-radius: 7px; background: {accent};
}}
QSlider::sub-page:horizontal {{ background: {rgba(accent, 160)}; border-radius: 2px; }}
QTabWidget::pane {{ border: none; }}
QListWidget {{
    background-color: {rgba(bg_solid, 100)};
    border: 1px solid {border};
    border-radius: {r_small}px;
}}
QListWidget::item {{ padding: 5px 8px; border-radius: {r_small}px; }}
QListWidget::item:selected {{ background-color: {rgba(accent, 110)}; }}
QListWidget::item:hover {{ background-color: {hover}; }}
/* ---------------- 树形视图（文件夹规则树） ---------------- */
QTreeView, QTreeWidget {{
    background-color: {rgba(bg_solid, 100)};
    border: 1px solid {border};
    border-radius: {r_small}px;
    outline: none;
    show-decoration-selected: 0;
}}
QTreeView::item {{
    padding: 3px 6px;
    border-radius: {r_small}px;
    color: {text};
    min-height: 24px;
}}
QTreeView::item:hover {{ background-color: {hover}; }}
QTreeView::item:selected {{
    background-color: {rgba(accent, 110)};
    color: {mix(bg_solid, '#ffffff', 0.9)};
}}
QTreeView::branch {{ background: transparent; }}
QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children {{
    border-image: none; image: none;
}}
QTreeView::branch:open:has-children {{ border-image: none; image: none; }}
QTreeView::header::section {{ background-color: {rgba(bg_solid, 150)}; }}
QHeaderView::section {{
    background-color: {rgba(bg_solid, 150)};
    border: none; padding: 4px;
}}
"""
