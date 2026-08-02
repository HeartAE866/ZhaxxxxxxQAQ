# -*- coding: utf-8 -*-
"""自动更新：查询 GitHub Releases 最新版本，下载安装包并一键更新。
仅访问 GitHub 官方公开接口，不收集任何信息；无网络时静默跳过。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.request

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton)

from i18n import tr, current_lang
from widgets import FramelessDialog

REPO = "HeartAE866/ZhaxxxxxxQAQ"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
# 国内镜像：jsDelivr 托管仓库内的 update.json（国内可访问），安装包经 ghfast 加速代理
MIRROR_JSON = "https://fastly.jsdelivr.net/gh/HeartAE866/ZhaxxxxxxQAQ@main/update.json"
USER_AGENT = "ZhaxxxxxxQAQ-Updater/1.0"
TIMEOUT = 8

# 各版本更新日志（zh / en），新版本发布时在此追加条目；弹窗展示最近三个版本
CHANGELOGS = {
    "1.2.1": {
        "zh": "🌐 新增国内镜像源：\n"
              "· 🇨🇳 国内用户无需科学上网即可检查更新与下载安装包\n"
              "· 🔄 GitHub 不可达时自动切换国内镜像（jsDelivr + ghfast 加速）\n"
              "· 🏷 设置 → 关于 会显示当前更新源（GitHub / 国内镜像）",
        "en": "🌐 China mirror source added:\n"
              "· 🇨🇳 Chinese users can check updates & download without a VPN\n"
              "· 🔄 Auto-switches to the China mirror (jsDelivr + ghfast proxy) when GitHub is unreachable\n"
              "· 🏷 Settings → About shows the current update source (GitHub / China Mirror)",
    },
    "1.2.0": {
        "zh": "🎉 进入联网更新新阶段：\n"
              "· 🔄 新增自动更新：启动时检查 GitHub 新版本，发现更新后一键下载安装\n"
              "· 📜 新增更新日志：每次更新后展示本次更新内容（可勾选不再显示）\n"
              "· 🎨 关于页改版：版本号移至「软件更新」区域",
        "en": "🎉 A new stage with online updates:\n"
              "· 🔄 Auto-update: checks GitHub Releases on startup; one-click download & install\n"
              "· 📜 Changelog dialog: shown after each update (can be disabled)\n"
              "· 🎨 About page revamp: version moved to the Software Update section",
    },
    "1.1.4": {
        "zh": "· 🌐 中英双语界面：设置 → 个性化 可切换简体中文 / English\n"
              "· ✨ 平行文件夹生成规则：可建「财务」「运营」等多条规则，创建事项时自主选用\n"
              "· ♻ 恢复出厂设置：双重确认 + 10 秒倒计时，可勾选同时删除项目文件夹\n"
              "· 🐛 修复：窗口置顶无效；自定义子文件夹支持批量删除\n"
              "· ⚡ 性能深度优化，安装包精简至约 19MB",
        "en": "· 🌐 Bilingual UI: Simplified Chinese / English in Settings → Personalization\n"
              "· ✨ Multiple parallel folder rules (e.g. Finance / Operations), pick per task\n"
              "· ♻ Factory reset: double confirmation + 10s countdown, optional folder deletion\n"
              "· 🐛 Fixed: Always-on-Top; batch delete for custom subfolders\n"
              "· ⚡ Deep performance optimization, ~19 MB installer",
    },
    "1.1.3": {
        "zh": "· 🎨 全面界面美化与体验优化\n"
              "· 🐛 修复：屏幕吸管取色保存无效、设置界面回车误关、紧凑模式首次启动展开为空\n"
              "· ⚡ 安装包由 37MB 精简至 19MB",
        "en": "· 🎨 UI polish & experience improvements\n"
              "· 🐛 Fixed: eyedropper color not saving, Enter closing Settings, empty panel after first compact launch\n"
              "· ⚡ Installer slimmed from 37 MB to 19 MB",
    },
}


def changelog_versions(current: str) -> list:
    """返回应展示的版本列表（含当前版本在内，最多 3 个，新→旧）。"""
    cur = version_tuple(current)
    vers = [v for v in CHANGELOGS if version_tuple(v) <= cur]
    vers.sort(key=version_tuple, reverse=True)
    return vers[:3]


def version_tuple(v) -> tuple:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _fetch_json(url: str, timeout: int = TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def check_latest():
    """返回 (tag, 安装包下载地址, 安装包名, 更新说明, 来源) 或 None。
    来源: "github"=GitHub 官方接口 / "mirror"=国内镜像（GitHub 不可达时自动切换）。"""
    try:
        data = _fetch_json(API_URL)
        tag = data.get("tag_name") or ""
        body = (data.get("body") or "").strip()
        for a in data.get("assets") or []:
            name = a.get("name") or ""
            url = a.get("browser_download_url") or ""
            if name.lower().endswith(".exe") and url:
                return tag, url, name, body[:300], "github"
        return None
    except Exception:
        pass
    # 国内镜像：GitHub 不可达时读取 jsDelivr 上的 update.json
    try:
        data = _fetch_json(MIRROR_JSON)
        tag = data.get("tag") or ""
        name = data.get("name") or ""
        url = data.get("mirror_url") or data.get("url") or ""
        body = (data.get("body") or "").strip()
        if tag and url and name:
            return tag, url, name, body[:300], "mirror"
        return None
    except Exception:
        return None


class UpdateCheck(QObject):
    """后台线程查询最新版本，result 信号回传 (tag,url,name,body) 或 None。"""
    result = Signal(object)

    def run(self):
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        self.result.emit(check_latest())


class UpdateDownload(QObject):
    """后台线程下载安装包。"""
    progress = Signal(int)
    done = Signal(str)       # 本地文件路径
    error = Signal(str)

    def __init__(self, url: str, dest: str):
        super().__init__()
        self.url, self.dest = url, dest

    def run(self):
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            req = urllib.request.Request(self.url,
                                         headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                total = int(r.headers.get("Content-Length") or 0)
                with open(self.dest, "wb") as f:
                    done = 0
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            self.progress.emit(int(done * 100 / total))
            self.done.emit(self.dest)
        except Exception as e:
            self.error.emit(str(e))


def center_on_screen(win):
    """居中于主屏幕（而不是居中于父窗口，父窗口可能贴在桌面层）。"""
    scr = QGuiApplication.screenAt(win.mapToGlobal(win.rect().center())) \
        or QGuiApplication.primaryScreen()
    g = scr.availableGeometry()
    win.adjustSize()
    win.move(g.center().x() - win.width() // 2,
              g.center().y() - win.height() // 2)


class ChangelogDialog(FramelessDialog):
    """更新日志：每次更新后展示最近三个版本的更新内容；「以后不再显示」默认勾选。
    非模态 + 置顶 + 屏幕居中：避免遮挡主窗口、避免拦截主窗口点击。"""

    def __init__(self, parent, t: dict, version: str):
        super().__init__(parent, t, tr("更新日志"), width=480)
        self.setModal(False)                     # 不阻塞主窗口
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        lang = "en" if current_lang() == "en" else "zh"
        for v in changelog_versions(version):
            vtitle = QLabel(f"v{v}")
            vtitle.setStyleSheet("font-size:12pt;font-weight:bold;margin-top:6px;")
            self.body.addWidget(vtitle)
            text = (CHANGELOGS.get(v) or {}).get(lang) or ""
            lbl = QLabel(text, wordWrap=True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.body.addWidget(lbl)

        self.no_more = QCheckBox(tr("以后不再显示更新日志"))
        self.no_more.setChecked(True)      # 默认勾选：以后不再打扰
        self.body.addWidget(self.no_more)

        row = QHBoxLayout()
        row.addStretch()
        btn_ok = QPushButton(tr("知道了"), objectName="AccentButton")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        row.addWidget(btn_ok)
        self.body.addLayout(row)
        center_on_screen(self)


class UpdateDialog(FramelessDialog):
    """发现新版本：一键下载并安装更新。非模态 + 置顶 + 屏幕居中。"""
    ignored = Signal()                    # 用户选择忽略此版本
    install_requested = Signal()          # 安装器已启动，主程序应退出

    def __init__(self, parent, t: dict, tag: str, url: str, name: str,
                 body: str = ""):
        super().__init__(parent, t, tr("发现新版本"), width=460)
        self.setModal(False)                     # 不阻塞主窗口
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.url, self.name = url, name
        info = QLabel(tr("发现新版本 {v}，是否立即更新？").replace("{v}", tag))
        info.setStyleSheet("font-size:12pt;font-weight:bold;")
        self.body.addWidget(info)
        if body:
            b = QLabel(body, wordWrap=True)
            b.setStyleSheet("color:#8a8aa0;font-size:9pt;")
            self.body.addWidget(b)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.body.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.body.addWidget(self.status)

        row = QHBoxLayout()
        row.addStretch()
        btn_later = QPushButton(tr("稍后"))
        btn_later.clicked.connect(self.reject)
        btn_ignore = QPushButton(tr("忽略此版本"))
        btn_ignore.clicked.connect(self._ignore)
        btn_now = QPushButton(tr("立即更新"), objectName="AccentButton")
        btn_now.setDefault(True)
        btn_now.clicked.connect(self._download)
        row.addWidget(btn_later)
        row.addWidget(btn_ignore)
        row.addWidget(btn_now)
        self.body.addLayout(row)
        center_on_screen(self)

    def _ignore(self):
        self.ignored.emit()
        self.reject()

    def _download(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status.setText(tr("正在下载更新…"))
        dest = os.path.join(tempfile.gettempdir(), self.name)
        self.dl = UpdateDownload(self.url, dest)
        self.dl.progress.connect(self.progress.setValue)
        self.dl.error.connect(
            lambda e: self.status.setText(
                tr("下载失败：{e}").replace("{e}", e)))
        self.dl.done.connect(self._install)
        self.dl.run()

    def _install(self, path: str):
        self.status.setText(tr("下载完成，正在启动安装…"))
        try:
            subprocess.Popen([path, "/VERYSILENT", "/SUPPRESSMSGBOXES",
                              "/NORESTART"])
        except Exception:
            pass
        # 等安装器就绪后主程序再退出，避免文件占用冲突
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, self.install_requested.emit)
        self.accept()
