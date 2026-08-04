# -*- coding: utf-8 -*-
"""核心模块：路径、配置、数据存储、日志、开机自启、文件夹规则、导入导出、循环任务计算。
所有数据均保存在程序目录内，完全本地离线。"""
from __future__ import annotations

import calendar
import csv
import json
import logging
import os
import re
import sys
import traceback
import uuid
import webbrowser
import winreg
from datetime import datetime, timedelta

# ---------------------------------------------------------------- 路径
if getattr(sys, "frozen", False):
    # 打包后：可写目录 = exe 所在目录；资源目录 = 打包内只读目录
    ROOT = os.path.dirname(sys.executable)
    APP_DIR = ROOT
    RES_DIR = os.path.join(getattr(sys, "_MEIPASS", ROOT), "resources")
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(APP_DIR)
    RES_DIR = os.path.join(ROOT, "resources")
DATA_DIR = os.path.join(ROOT, "data")
LOG_DIR = os.path.join(ROOT, "logs")
EXPORT_DIR = os.path.join(ROOT, "导出")
DEFAULT_BASE_FOLDER = os.path.join(ROOT, "工作文件夹")
CONFIG_PATH = os.path.join(ROOT, "config.json")
DATA_PATH = os.path.join(DATA_DIR, "data.json")
ICON_PATH = os.path.join(RES_DIR, "icon.jpg")
LOGO_PATH = os.path.join(RES_DIR, "logo.png")
VBS_PATH = os.path.join(ROOT, "ZhaxxxxxxQAQ.vbs")
APP_NAME = "ZhaxxxxxxQAQ"
APP_VERSION = "1.3.0beta3"
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# 托盘图标：优先用户桌面上的 图标.png（按当前用户主目录推导，不硬编码个人路径），
# 不存在（如他人机器）则用打包内图标
_USER_DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
TRAY_ICON_PATH = os.path.join(_USER_DESKTOP, "图标.png")
if not os.path.exists(TRAY_ICON_PATH):
    TRAY_ICON_PATH = os.path.join(RES_DIR, "tray.png")

# 打赏码：优先用户桌面 赞赏码.png，删除后回退到打包内资源
DONATION_IMG = os.path.join(_USER_DESKTOP, "赞赏码.png")
if not os.path.exists(DONATION_IMG):
    DONATION_IMG = os.path.join(RES_DIR, "donation.png")

for _d in (DATA_DIR, LOG_DIR, EXPORT_DIR, DEFAULT_BASE_FOLDER, RES_DIR):
    os.makedirs(_d, exist_ok=True)

FMT = "%Y-%m-%d %H:%M"          # 精确到分钟


def now() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def dt_str(dt: datetime) -> str:
    return dt.strftime(FMT)


from functools import lru_cache


@lru_cache(maxsize=512)
def _parse_cached(s: str):
    # 兼容 ISO 风格（T 分隔，如 2026-08-03T15:57），统一按空格格式解析
    if "T" in s:
        s = s.replace("T", " ")
    try:
        return datetime.strptime(s, FMT)
    except (ValueError, TypeError):
        return None


def parse_dt(s: str | None) -> datetime | None:
    """解析时间字符串（带缓存：常驻后台每 tick 高频解析同一批时间）。"""
    if not s:
        return None
    return _parse_cached(s)


# ---------------------------------------------------------------- 日志
def setup_logging() -> logging.Logger:
    logger = logging.getLogger("zhax")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    # 用户操作 / 运行日志（按天滚动，保留 14 天）
    from logging.handlers import TimedRotatingFileHandler
    h1 = TimedRotatingFileHandler(os.path.join(LOG_DIR, "app.log"), when="midnight",
                                  backupCount=14, encoding="utf-8")
    h1.setLevel(logging.INFO)
    h1.setFormatter(fmt)
    # 错误日志
    h2 = logging.FileHandler(os.path.join(LOG_DIR, "error.log"), encoding="utf-8")
    h2.setLevel(logging.ERROR)
    h2.setFormatter(fmt)
    logger.addHandler(h1)
    logger.addHandler(h2)
    return logger


log = setup_logging()


def install_excepthook():
    def hook(exc_type, exc, tb):
        log.error("未捕获异常:\n" + "".join(traceback.format_exception(exc_type, exc, tb)))
    sys.excepthook = hook


# ---------------------------------------------------------------- 配置
from theme import DEFAULT_THEME, DEFAULT_THEMES, DEFAULT_THEME_SETTINGS  # noqa: E402
from i18n import tr, current_lang  # noqa: E402

# 示例文件夹生成规则（帮助用户理解命名种类与层级用法）
EXAMPLE_FOLDER_RULES = [
    {"name": "财务规则（示例）", "levels": [
        {"template": "财务"},
        {"template": "{Y}年"},
        {"template": "{M}月"},
        {"template": "{name}"},
    ]},
    {"name": "运营规则（示例）", "levels": [
        {"template": "运营"},
        {"template": "{Y}年"},
        {"template": "{M}.{name}"},
    ]},
    {"name": "项目规则（示例）", "levels": [
        {"template": "项目"},
        {"template": "{name}"},
        {"template": "{Y}年"},
    ]},
]

DEFAULT_CONFIG = {
    "language": "en",
    "update": {"check": True, "ignored_version": "", "last_seen_changelog": "", "last_source": ""},
    "theme": dict(DEFAULT_THEME),
    "theme_settings": dict(DEFAULT_THEME_SETTINGS),
    "saved_themes": dict(DEFAULT_THEMES),
    "window": {"x": None, "y": None, "w": 330, "h": None,
               "locked": False, "topmost": False, "compact": False,
               "click_through": False, "show_clock": True},
    "base_folder": DEFAULT_BASE_FOLDER,
    "custom_folders": [],
    "diy_bg": {"enabled": False, "image": "", "alpha": 120, "components": {}},
    "diy_bg_settings": {"enabled": False, "image": "", "alpha": 120, "components": {}},
    "folder_rules": {
        "rules": [
            {"name": "默认规则", "levels": [
                {"template": "{Y}年"},
                {"template": "{M}月"},
                {"template": "{Y}.{M}.{D}{name}"},
            ]},
        ] + [dict(r) for r in EXAMPLE_FOLDER_RULES],
    },
    "show_recent_days": 7,
    "reminder": {"todo_enabled": True, "todo_advance_minutes": 0, "recur_enabled": True,
                 "remind_enabled": True},
    "offwork": {"enabled": False, "time": "18:00", "format": "min",
                "weekdays_only": True, "template": "距下班 {n}"},
    "compact_style": {
        "components": ["clock", "offwork", "urgent"],
        "text_color": "",
        "bg_color": "",
        "bg_image": "",
        "font_size": 0,
    },
    "hotkeys": {
        "settings": ["ctrl", "shift", "z", "x"],
        "click_through": ["ctrl", "shift", "z", "p"],
        "custom": {}          # {"quick_record": [...], "quick_todo": [...], ...}
    },
    "autostart": True,
}


class Config:
    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self.data = json.loads(json.dumps(DEFAULT_CONFIG))
        raw_rules = None
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
                    raw_rules = loaded.get("folder_rules")
                    self._merge(self.data, loaded)
            except Exception:
                log.error("读取 config.json 失败:\n" + traceback.format_exc())
        self._migrate(raw_rules)

    def _migrate(self, raw_rules=None):
        """旧版本配置升级。"""
        fr = self.data.get("folder_rules")
        if isinstance(fr, dict) and "levels" in fr:
            # v1.1.3 及以前：单条规则（无 rules 键）→ 转为规则列表
            fr["rules"] = [{"name": "默认规则", "levels": fr.pop("levels")}]
        # 预置示例规则（帮助理解文件生成规则）：当前规则中不含示例则补入
        if isinstance(fr, dict) and isinstance(fr.get("rules"), list) \
                and not any("（示例）" in (r.get("name") or "")
                            for r in fr["rules"]):
            fr["rules"].extend([dict(r) for r in EXAMPLE_FOLDER_RULES])

    def _merge(self, base: dict, extra: dict):
        for k, v in extra.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                self._merge(base[k], v)
            else:
                base[k] = v

    def get(self, *keys, default=None):
        cur = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def set(self, *keys_and_value):
        *keys, value = keys_and_value
        cur = self.data
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        cur[keys[-1]] = value
        self.save()

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            log.error("保存 config.json 失败:\n" + traceback.format_exc())


# ---------------------------------------------------------------- 数据存储
PRIORITIES = {"high": "高", "mid": "中", "low": "低"}
PERIODS = {"day": "每天", "week": "每周", "month": "每月", "quarter": "每季",
           "year": "每年", "long": "长期"}
TYPE_NAMES = {"record": "工作记录", "todo": "待办事项", "recur": "循环任务",
              "remind": "提醒", "link": "网址直达"}


def type_name(key: str) -> str:
    return tr(TYPE_NAMES.get(key, key))


def priority_name(key: str) -> str:
    return tr(PRIORITIES.get(key, key))


def period_name(key: str) -> str:
    return tr(PERIODS.get(key, key))


def auto_priority(item: dict) -> str:
    """自动优先级：已完成→低；剩余两天以内→高；其他→中。"""
    if not item:
        return "mid"
    if item.get("done"):
        return "low"
    dl = parse_dt(item.get("deadline"))
    if dl is not None and dl - now() <= timedelta(days=2):
        return "high"
    return "mid"


def new_item(item_type: str, title: str, **kw) -> dict:
    it = {
        "id": uuid.uuid4().hex[:12],
        "type": item_type,                    # record / todo / recur
        "title": title,
        "created": dt_str(now()),
        "priority": kw.get("priority", "mid"),
        "tags": kw.get("tags", []),
        "folder": kw.get("folder"),
        "folder_rule": kw.get("folder_rule"),       # 创建时选用的平行生成规则名
        "order": kw.get("order", 0),
        "deadline": kw.get("deadline"),       # todo 用，ISO 分钟
        "remind_advance": kw.get("remind_advance"),   # todo 提前提醒分钟数
        "remind_time": kw.get("remind_time"),         # remind 用：提醒时间（ISO 分钟）
        "notified_for": kw.get("notified_for"),       # 已触发提醒的时间标记
        "done": kw.get("done", item_type == "record"),
        "recur": kw.get("recur"),             # {"period","time","weekday","monthday","month"}
        "completed_instances": kw.get("completed_instances", []),  # recur 完成时间戳
        "url": kw.get("url"),                 # link 用：直达网址
        "bar_color": kw.get("bar_color"),     # link 用：名称前竖条颜色
    }
    return it


def open_url(url: str):
    """打开网址直达：无协议前缀自动补 https。"""
    u = (url or "").strip()
    if not u:
        return
    if "://" not in u:
        u = "https://" + u
    try:
        webbrowser.open(u)
    except Exception:
        log.error(f"打开网址失败 {u}:\n" + traceback.format_exc())


class DataStore:
    def __init__(self, path=DATA_PATH):
        self.path = path
        self.items: list[dict] = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8-sig") as f:
                    self.items = json.load(f).get("items", [])
            except Exception:
                log.error("读取 data.json 失败:\n" + traceback.format_exc())
                self.items = []

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"items": self.items}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except Exception:
            log.error("保存 data.json 失败:\n" + traceback.format_exc())

    def add(self, item: dict):
        self.items.append(item)
        self.save()
        log.info(f"添加{TYPE_NAMES.get(item['type'], item['type'])}: {item['title']}")

    def update(self, item: dict):
        self.save()
        log.info(f"修改事项: {item['title']}")

    def delete(self, ids: list[str]):
        self.items = [i for i in self.items if i["id"] not in ids]
        self.save()
        log.info(f"删除 {len(ids)} 条事项")

    def find(self, item_id: str) -> dict | None:
        for i in self.items:
            if i["id"] == item_id:
                return i
        return None

    def all_tags(self) -> list[str]:
        tags = set()
        for i in self.items:
            tags.update(i.get("tags", []))
        return sorted(tags)

    def next_order(self) -> int:
        orders = [i.get("order", 0) for i in self.items if i["type"] == "todo"]
        return (max(orders) + 1) if orders else 0


# ---------------------------------------------------------------- 循环任务时间计算
def _recur_time(item) -> tuple[int, int]:
    try:
        hh, mm = item["recur"].get("time", "09:00").split(":")
        return int(hh), int(mm)
    except Exception:
        return 9, 0


def _at(d, hh, mm) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm)


def next_occur(item: dict, after: datetime) -> datetime:
    """下一次提醒时间（严格晚于 after）；长期任务无循环，返回 None。"""
    r = item.get("recur") or {}
    period = r.get("period", "day")
    if period == "long":
        return None
    hh, mm = _recur_time(item)
    created = parse_dt(item.get("created")) or now()
    if period == "day":
        cand = _at(after, hh, mm)
        if cand <= after:
            cand += timedelta(days=1)
        return cand
    if period == "week":
        wd = r.get("weekday", created.weekday())
        delta = (wd - after.weekday()) % 7
        cand = _at(after + timedelta(days=delta), hh, mm)
        if cand <= after:
            cand += timedelta(days=7)
        return cand
    if period in ("month", "quarter"):
        md = int(r.get("monthday", created.day))
        base_m = int(r.get("month", created.month))
        y, m = after.year, after.month
        for _ in range(300):
            if period == "month" or (m - base_m) % 3 == 0:
                day = min(md, calendar.monthrange(y, m)[1])
                cand = datetime(y, m, day, hh, mm)
                if cand > after:
                    return cand
            m += 1
            if m > 12:
                m, y = 1, y + 1
        return after + timedelta(days=365)
    # year
    md = int(r.get("monthday", created.day))
    base_m = int(r.get("month", created.month))
    y = after.year
    for _ in range(120):
        day = min(md, calendar.monthrange(y, base_m)[1])
        cand = datetime(y, base_m, day, hh, mm)
        if cand > after:
            return cand
        y += 1
    return after + timedelta(days=365)


def prev_occur(item: dict, before: datetime) -> datetime | None:
    """最近一次的应提醒时间（<= before 且 >= 创建时间），无则 None。
    从 before 逆向定位，无需从创建日起逐次前推。"""
    created = parse_dt(item.get("created")) or before
    if before < created:
        return None
    r = item.get("recur") or {}
    period = r.get("period", "day")
    if period == "long":
        return None
    hh, mm = _recur_time(item)
    if period == "day":
        cand = _at(before, hh, mm)
        if cand > before:
            cand -= timedelta(days=1)
        return cand if cand >= created else None
    if period == "week":
        wd = r.get("weekday", created.weekday())
        cand = _at(before - timedelta(days=(before.weekday() - wd) % 7), hh, mm)
        if cand > before:
            cand -= timedelta(days=7)
        return cand if cand >= created else None
    # month / quarter / year：逐月向前找（最多 40 年）
    md = int(r.get("monthday", created.day))
    base_m = int(r.get("month", created.month))
    y, m = before.year, before.month
    for _ in range(480):
        if (y, m) < (created.year, created.month):
            return None
        if period == "month" or \
                (period == "quarter" and (m - base_m) % 3 == 0) or \
                (period == "year" and m == base_m):
            day = min(md, calendar.monthrange(y, m)[1])
            cand = datetime(y, m, day, hh, mm)
            if cand <= before:
                return cand if cand >= created else None
        m -= 1
        if m < 1:
            m, y = 12, y - 1
    return None


def pending_instance(item: dict, t: datetime | None = None) -> str | None:
    """当前待完成的循环实例（应提醒时间 ISO），无则 None。"""
    t = t or now()
    last = prev_occur(item, t)
    if last is None:
        return None
    iso = dt_str(last)
    if iso in item.get("completed_instances", []):
        return None
    return iso


def recur_desc(item: dict) -> str:
    r = item.get("recur") or {}
    period = r.get("period", "day")
    if period == "long":
        return tr("长期")
    t = r.get("time", "09:00")
    en = current_lang() == "en"
    if period == "week":
        wd = r.get("weekday", 0)
        name = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[wd] if en \
            else ("一", "二", "三", "四", "五", "六", "日")[wd]
        return tr("每周{wd} {t}").replace("{wd}", name).replace("{t}", t)
    if period in ("month", "quarter"):
        d = r.get("monthday", 1)
        key = "每季 {d}日 {t}" if period == "quarter" else "每月 {d}日 {t}"
        return tr(key).replace("{d}", str(d)).replace("{t}", t)
    if period == "year":
        m, d = r.get("month", 1), r.get("monthday", 1)
        return tr("每年 {m}月{d}日 {t}").replace("{m}", str(m)) \
            .replace("{d}", str(d)).replace("{t}", t)
    return tr("每天 {t}").replace("{t}", t)


# ---------------------------------------------------------------- 文件夹规则
_INVALID = re.compile(r'[\\/:*?"<>|]')


def sanitize_name(name: str) -> str:
    s = _INVALID.sub("_", name).strip().strip(".")
    return s[:60] if s else "未命名"


def unique_path(path: str) -> str:
    """若文件夹已存在则追加序号 (2)(3)..."""
    if not os.path.exists(path):
        return path
    n = 2
    while os.path.exists(f"{path}({n})"):
        n += 1
    return f"{path}({n})"


def item_date(item: dict):
    """事项所属日期：一律按创建时间归档（创建文件夹时用）。"""
    return (parse_dt(item.get("created")) or now()).date()


def custom_folder_path(base_folder: str, name: str) -> str:
    """自定义子文件夹的完整路径（命名完全由用户定义）。"""
    return os.path.join(base_folder, sanitize_name(name))


def ensure_custom_folder(base_folder: str, name: str) -> str:
    path = custom_folder_path(base_folder, name)
    os.makedirs(path, exist_ok=True)
    return path


# 默认文件夹生成规则：父目录 → 年份 → 月份 → 项目（Y.M.D项目名）
DEFAULT_FOLDER_RULES = [
    {"template": "{Y}年"},
    {"template": "{M}月"},
    {"template": "{Y}.{M}.{D}{name}"},
]


def folder_rules_list(rules) -> list:
    """规范化文件夹规则配置 → 规则列表（含旧版单规则兼容）。"""
    rules = rules or {}
    lst = rules.get("rules")
    if isinstance(lst, list) and lst:
        return lst
    levels = rules.get("levels") or [dict(t) for t in DEFAULT_FOLDER_RULES]
    return [{"name": "默认规则", "levels": levels}]


def folder_rule_index(rules, name) -> int:
    """按规则名查找规则下标，未找到返回 0。"""
    if name:
        for i, r in enumerate(folder_rules_list(rules)):
            if r.get("name") == name:
                return i
    return 0


def render_folder_template(tpl: str, d, name: str) -> str:
    """把规则模板渲染为实际文件夹名。
    {Y}=年份 {M}=月份 {D}=日 {name}=事项名称。"""
    s = str(tpl or "")
    return (s.replace("{Y}", str(d.year)).replace("{M}", str(d.month))
             .replace("{D}", str(d.day)).replace("{name}", name))


def create_bound_folder(item: dict, base_folder: str, rules=None,
                        rule_index: int = 0) -> str:
    """按用户配置的规则逐层生成并创建绑定文件夹路径（平行规则：rule_index 选择第几条）。"""
    name = sanitize_name(item["title"])
    if item["type"] == "recur":
        path = unique_path(os.path.join(base_folder, "循环任务", name))
        os.makedirs(path, exist_ok=True)
        log.info(f"创建工作文件夹: {path}")
        return path
    rules_list = folder_rules_list(rules)
    rule = rules_list[min(max(rule_index, 0), len(rules_list) - 1)]
    levels = rule.get("levels")
    if not levels:
        levels = [dict(t) for t in DEFAULT_FOLDER_RULES]
    d = item_date(item)
    segs = [sanitize_name(render_folder_template(l.get("template", ""), d, name))
            for l in levels]
    path = unique_path(os.path.join(base_folder, *segs) if segs else base_folder)
    os.makedirs(path, exist_ok=True)
    log.info(f"创建工作文件夹: {path}")
    return path


def open_folder(path: str):
    try:
        os.startfile(path)
        log.info(f"打开文件夹: {path}")
    except Exception:
        log.error(f"打开文件夹失败 {path}:\n" + traceback.format_exc())


# ---------------------------------------------------------------- 开机自启
def autostart_command() -> str:
    """开机自启命令：打包后直接指向 exe，开发模式用 wscript 静默启动。"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'wscript.exe "{VBS_PATH}"'


def autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY) as k:
            val, _ = winreg.QueryValueEx(k, APP_NAME)
            return APP_NAME in val or "wscript" in val.lower()
    except OSError:
        return False


def set_autostart(enable: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ,
                                  autostart_command())
                log.info("已开启开机自启")
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                    log.info("已关闭开机自启")
                except FileNotFoundError:
                    pass
    except OSError:
        log.error("设置开机自启失败:\n" + traceback.format_exc())


# ---------------------------------------------------------------- 导入 / 导出
CSV_FIELDS = ["id", "type", "title", "created", "deadline", "priority", "done",
              "tags", "folder", "folder_rule", "order", "remind_advance",
              "remind_time", "notified_for",
              "recur_period", "recur_time", "recur_weekday", "recur_monthday",
              "recur_month", "completed_instances", "url", "bar_color"]


def _item_to_row(it: dict) -> dict:
    r = it.get("recur") or {}
    return {
        "id": it["id"], "type": it["type"], "title": it["title"],
        "created": it.get("created", ""), "deadline": it.get("deadline") or "",
        "priority": it.get("priority", "mid"), "done": int(bool(it.get("done"))),
        "tags": ";".join(it.get("tags", [])), "folder": it.get("folder") or "",
        "folder_rule": it.get("folder_rule") or "",
        "order": it.get("order", 0), "remind_advance": it.get("remind_advance") or "",
        "remind_time": it.get("remind_time") or "", "notified_for": it.get("notified_for") or "",
        "recur_period": r.get("period", ""), "recur_time": r.get("time", ""),
        "recur_weekday": r.get("weekday", ""), "recur_monthday": r.get("monthday", ""),
        "recur_month": r.get("month", ""),
        "completed_instances": ";".join(it.get("completed_instances", [])),
        "url": it.get("url") or "", "bar_color": it.get("bar_color") or "",
    }


def _row_to_item(row: dict) -> dict:
    recur = None
    if row.get("recur_period"):
        recur = {"period": row["recur_period"], "time": row.get("recur_time") or "09:00"}
        for k in ("weekday", "monthday", "month"):
            v = row.get(f"recur_{k}")
            if v not in ("", None):
                try:
                    recur[k] = int(v)
                except ValueError:
                    pass
    adv = row.get("remind_advance")
    return {
        "id": row.get("id") or uuid.uuid4().hex[:12],
        "type": row.get("type") or "record",
        "title": row.get("title") or "未命名",
        "created": row.get("created") or dt_str(now()),
        "deadline": row.get("deadline") or None,
        "priority": row.get("priority") or "mid",
        "done": str(row.get("done", "0")) in ("1", "true", "True"),
        "tags": [t for t in (row.get("tags") or "").split(";") if t],
        "folder": row.get("folder") or None,
        "folder_rule": row.get("folder_rule") or None,
        "order": int(row.get("order") or 0),
        "remind_advance": int(adv) if str(adv or "").isdigit() else None,
        "remind_time": row.get("remind_time") or None,
        "notified_for": row.get("notified_for") or None,
        "recur": recur,
        "completed_instances": [t for t in (row.get("completed_instances") or "").split(";") if t],
        "url": row.get("url") or None, "bar_color": row.get("bar_color") or None,
    }


def export_items(items: list[dict], fmt: str = "json") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt == "csv":
        path = os.path.join(EXPORT_DIR, f"export_{ts}.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()
            for it in items:
                w.writerow(_item_to_row(it))
    else:
        path = os.path.join(EXPORT_DIR, f"export_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, ensure_ascii=False, indent=1)
    log.info(f"导出 {len(items)} 条事项到 {path}")
    return path


def import_file(path: str) -> list[dict]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return [_row_to_item(r) for r in csv.DictReader(f)]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", data if isinstance(data, list) else [])
    for it in items:
        it.setdefault("id", uuid.uuid4().hex[:12])
        it.setdefault("completed_instances", [])
        it.setdefault("tags", [])
    return items


def dup_key(it: dict):
    return (it.get("type"), it.get("title"), it.get("created"))
