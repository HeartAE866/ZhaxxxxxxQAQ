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

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QVBoxLayout)

from i18n import tr
from widgets import FramelessDialog

REPO = "HeartAE866/ZhaxxxxxxQAQ"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
USER_AGENT = "ZhaxxxxxxQAQ-Updater/1.0"
TIMEOUT = 8


def version_tuple(v) -> tuple:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _fetch_json(url: str, timeout: int = TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def check_latest():
    """返回 (tag, 安装包下载地址, 安装包名, 更新说明) 或 None（无网络/无资产）。"""
    try:
        data = _fetch_json(API_URL)
        tag = data.get("tag_name") or ""
        body = (data.get("body") or "").strip()
        for a in data.get("assets") or []:
            name = a.get("name") or ""
            url = a.get("browser_download_url") or ""
            if name.lower().endswith(".exe") and url:
                return tag, url, name, body[:300]
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


class UpdateDialog(FramelessDialog):
    """发现新版本：一键下载并安装更新。"""
    ignored = Signal()                    # 用户选择忽略此版本
    install_requested = Signal()          # 安装器已启动，主程序应退出

    def __init__(self, parent, t: dict, tag: str, url: str, name: str,
                 body: str = ""):
        super().__init__(parent, t, tr("发现新版本"), width=460)
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
