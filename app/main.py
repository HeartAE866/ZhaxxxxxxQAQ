# -*- coding: utf-8 -*-
"""ZhaxxxxxxQAQ 入口：系统托盘、全局快捷键、提醒调度、窗口协调。
待机时仅有一个 20s 定时器，CPU 占用接近 0。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import traceback
from datetime import timedelta

from PySide6.QtCore import QLockFile, QObject, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QIcon
from PySide6.QtWidgets import (QApplication, QDialog, QSystemTrayIcon)

import core
import i18n
import theme as theme_mod
from core import log
from i18n import tr
from hotkeys import HotkeyPoller
from main_window import FloatWindow
from widgets import (Toast, VK_MAP, ConfirmDialog, apply_frosted,
                     set_click_through, styled_menu)


class App(QObject):
    def __init__(self):
        super().__init__()
        core.install_excepthook()
        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)
        self.qapp.setApplicationName(core.APP_NAME)

        # 单实例
        self.lock = QLockFile(os.path.join(core.DATA_DIR, "app.lock"))
        if not self.lock.tryLock(3000):
            sys.exit(0)

        self.config = core.Config()
        i18n.set_lang(self.config.get("language", default="zh"))
        self.store = core.DataStore()
        self.t = self.config.get("theme")
        self.qapp.setStyleSheet(theme_mod.build_qss(self.t))
        self.qapp.setWindowIcon(QIcon(core.ICON_PATH))

        self.snoozed: dict[str, object] = {}
        self._reminder_dialogs: list = []
        self.settings_win: object | None = None
        self._update_nagged = False
        self._update_check_manual = False
        self.update_checker = None

        self.win = FloatWindow(self)
        self._build_tray()
        self._build_hotkeys()
        self.reload_hotkeys()

        # 提醒定时器
        self.remind_timer = QTimer(self, interval=20000,
                                   timeout=self.check_reminders)
        self.remind_timer.start()
        self.refresh_priorities()

        # 首次运行：开启自启
        if self.config.get("autostart", default=True) and not core.autostart_enabled():
            core.set_autostart(True)
        log.info(f"{core.APP_NAME} v{core.APP_VERSION} 启动")

        # 自动更新检查（启动 4 秒后静默进行）
        QTimer.singleShot(4000, self.check_updates)
        # 更新日志（本次更新内容，仅展示一次，可勾选不再显示）
        QTimer.singleShot(5000, self._maybe_show_changelog)

    # ---------------------------------------------------------------- 更新日志
    def _maybe_show_changelog(self):
        import updater
        last = self.config.get("update", "last_seen_changelog", default="")
        if last == core.APP_VERSION:
            return
        if not last:
            # 全新安装：不自动弹更新日志（可在 设置→关于→查看更新日志 中浏览）
            self.config.set("update", "last_seen_changelog", core.APP_VERSION)
            return
        d = updater.ChangelogDialog(self.win, self.t, core.APP_VERSION)
        self._changelog_dialog = d              # 持有引用防止回收
        d.finished.connect(lambda _: self._changelog_finished(d))
        d.show()

    def _changelog_finished(self, d):
        if d.result() == QDialog.Accepted and d.no_more.isChecked():
            self.config.set("update", "last_seen_changelog", core.APP_VERSION)

    # ---------------------------------------------------------------- 更新
    def check_updates(self, manual: bool = False):
        """检查 GitHub Releases 是否有新版本；manual=True 时来自设置页按钮。"""
        if not manual and not self.config.get("update", "check", default=True):
            return
        if not manual and self._update_nagged:
            return
        self._update_check_manual = manual
        if manual:
            Toast.show_text(tr("正在检查更新…"))
        if self.update_checker is None:
            import updater
            self.update_checker = updater.UpdateCheck()
            self.update_checker.result.connect(self._update_result)
        self.update_checker.run()

    def _update_result(self, res):
        import updater
        if not res:
            if self._update_check_manual:
                Toast.show_text(tr("已是最新版本"))
            return
        tag, url, name, body, source = res
        self.config.set("update", "last_source", source)
        if updater.version_tuple(tag) <= updater.version_tuple(core.APP_VERSION):
            if self._update_check_manual:
                Toast.show_text(tr("已是最新版本"))
            return
        if tag == self.config.get("update", "ignored_version", default=""):
            return
        self._update_nagged = True
        log.info(f"发现新版本: {tag}（来源: {source}）")
        d = updater.UpdateDialog(self.win, self.t, tag, url, name, body)
        d.ignored.connect(
            lambda: self.config.set("update", "ignored_version", tag))
        d.install_requested.connect(self.quit)
        d.show()

    # ---------------------------------------------------------------- 托盘
    def _build_tray(self):
        self.tray = QSystemTrayIcon(QIcon(core.TRAY_ICON_PATH), self.qapp)
        self.tray.setToolTip(core.APP_NAME)
        self.menu = styled_menu()
        self._rebuild_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _rebuild_menu(self):
        m = self.menu
        m.clear()
        wcfg = self.config.get("window", default={})

        act_show = m.addAction(tr("隐藏主界面") if self.win.isVisible() else tr("显示主界面"))
        act_show.triggered.connect(self.toggle_visible)
        m.addSeparator()
        m.addAction(tr("⚡ 来活了")).triggered.connect(self.quick_record_menu)
        m.addSeparator()

        def chk(text, key, fn):
            a = m.addAction(tr(text))
            a.setCheckable(True)
            a.setChecked(bool(wcfg.get(key)))
            a.triggered.connect(fn)
            return a

        chk("紧凑模式", "compact", lambda v: self.toggle_compact(v))
        chk("锁定位置", "locked", self.set_locked)
        chk("窗口置顶", "topmost", self.set_topmost)
        chk("鼠标穿透", "click_through", self.set_click_through)
        m.addSeparator()
        m.addAction(tr("⚙ 设置  Ctrl+Shift+Z+X")).triggered.connect(self.show_settings)
        m.addAction(tr("↻ 重启应用")).triggered.connect(self.restart)
        m.addAction(tr("退出程序")).triggered.connect(self.quit)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle_visible()

    # ---------------------------------------------------------------- 基本动作
    def toggle_visible(self):
        if self.win.isVisible():
            self.win.hide()
            self.win.set_user_hidden(True)
        else:
            self.win.set_user_hidden(False)
            self.win.show()
            if not self.config.get("window", "topmost"):
                self.win.raise_()
        self._rebuild_menu()

    def toggle_compact(self, on: bool | None = None):
        cur = self.config.get("window", "compact", default=False)
        new = (not cur) if on is None else on
        self.win.set_compact(new)
        self.config.set("window", "compact", new)
        self._rebuild_menu()

    def set_locked(self, v: bool):
        self.config.set("window", "locked", v)
        Toast.show_text(tr("位置已锁定") if v else tr("位置已解锁"))
        self._rebuild_menu()

    def set_topmost(self, v: bool):
        self.config.set("window", "topmost", v)
        self.win.save_geometry()
        self.win.apply_window_state()
        self._rebuild_menu()

    def set_click_through(self, v: bool | None = None):
        cur = self.config.get("window", "click_through", default=False)
        new = (not cur) if v is None else v
        self.config.set("window", "click_through", new)
        set_click_through(self.win, new)
        Toast.show_text(tr("鼠标穿透：开（Ctrl+Shift+Z+P 恢复）") if new
                        else tr("鼠标穿透：关"))
        self._rebuild_menu()

    # ---------------------------------------------------------------- 事项操作
    def quick_record_menu(self):
        """“来活了”：添加待办、登记以往工作或循环任务。"""
        m = styled_menu(self.win)
        m.addAction(tr("🚀 开始新工作")).triggered.connect(
            lambda: self.add_item("todo"))
        m.addAction(tr("🕐 登记以往工作（选择时间）")).triggered.connect(
            lambda: self.quick_record(True))
        m.addAction(tr("🔁 添加循环任务")).triggered.connect(
            lambda: self.add_item("recur"))
        m.addAction(tr("🔗 添加网址直达")).triggered.connect(
            lambda: self.add_item("link"))
        m.addAction(tr("⏰ 添加提醒")).triggered.connect(
            lambda: self.add_reminder())
        m.exec(QCursor.pos())

    def add_reminder(self):
        """添加一次性提醒（仅名称 + 时间，不绑定文件夹）。"""
        from editor import ReminderEditDialog
        d = ReminderEditDialog(self.win, self.t)
        d.saved.connect(self._commit_new_item)
        d.show()

    def edit_reminder(self, item: dict):
        from editor import ReminderEditDialog
        d = ReminderEditDialog(self.win, self.t, item)
        d.saved.connect(self._commit_edit_item)
        d.show()

    def reminder_context_menu(self, item: dict, gpos):
        m = styled_menu(self.win)
        m.addAction(tr("✏ 编辑")).triggered.connect(lambda: self.edit_reminder(item))
        m.addAction(tr("✔ 标记完成")).triggered.connect(
            lambda: self._complete_reminder(item))
        m.addSeparator()
        m.addAction(tr("🗑 删除")).triggered.connect(
            lambda: self._delete_reminder(item))
        m.exec(gpos)

    def _complete_reminder(self, item: dict):
        item["done"] = True
        item["notified_for"] = item.get("remind_time")
        log.info(f"提醒完成: {item['title']}")
        self.store.save()
        self.win.refresh()

    def _delete_reminder(self, item: dict):
        ok, _ = ConfirmDialog.ask(self.win, self.t, tr("删除提醒"),
                                  tr("删除提醒「{title}」？").replace("{title}", item["title"]),
                                  ok_text=tr("删除"))
        if ok:
            self.store.delete([item["id"]])
            self.win.refresh()

    def quick_record(self, custom_time: bool):
        from editor import ItemEditDialog
        d = ItemEditDialog(self.win, self.t, "record",
                           record_now=not custom_time, config=self.config)
        d.saved.connect(self._commit_new_item)
        d.show()

    def add_item(self, item_type: str):
        from editor import ItemEditDialog
        d = ItemEditDialog(self.win, self.t, item_type, config=self.config)
        d.saved.connect(self._commit_new_item)
        d.show()

    def _commit_new_item(self, it):
        if it["type"] == "todo":
            it["order"] = self.store.next_order()
        self.store.add(it)
        self.win.refresh()
        Toast.show_text(tr("已添加：{title}").replace("{title}", it["title"]))

    def edit_item(self, item: dict):
        from editor import ItemEditDialog
        d = ItemEditDialog(self.win, self.t, item["type"], item, config=self.config)
        d.saved.connect(self._commit_edit_item)
        d.show()

    def _commit_edit_item(self, it):
        self.store.update(it)
        self.win.refresh()

    def show_detail(self, item: dict):
        from editor import DetailDialog
        self.win.highlight_id = None
        d = DetailDialog(self.win, self.t, self.store, item, self.config)
        d.changed.connect(self.win.refresh)
        d.show()

    def item_context_menu(self, item: dict, gpos):
        m = styled_menu(self.win)
        m.addAction(tr("📋 详情")).triggered.connect(lambda: self.show_detail(item))
        m.addAction(tr("✏ 编辑")).triggered.connect(lambda: self.edit_item(item))
        if item["type"] == "todo":
            text = tr("↩ 取消完成") if item.get("done") else tr("✔ 标记完成")
            m.addAction(text).triggered.connect(lambda: self._toggle_todo(item))
        if item["type"] == "recur" and core.pending_instance(item):
            m.addAction(tr("✔ 完成当期")).triggered.connect(
                lambda: self._complete_instance(item))
        if item["type"] == "link":
            m.addAction(tr("🌐 打开网址")).triggered.connect(
                lambda: self.open_link(item))
        m.addSeparator()
        m.addAction(tr("🗑 删除")).triggered.connect(
            lambda: self.delete_item(item))
        if item["type"] != "link":
            m.addAction(tr("📂 打开工作目录")).triggered.connect(
                lambda: self.open_folder_flow(item))
        m.exec(gpos)

    def delete_item(self, item: dict):
        """右键删除事项；绑定文件夹的可勾选同时删除对应文件夹。"""
        folder = item.get("folder")
        has_folder = bool(folder and os.path.isdir(folder))
        msg = tr("删除事项「{title}」？").replace("{title}", item["title"])
        checkbox = None
        if has_folder:
            msg += "\n\n" + tr("已绑定工作文件夹，可勾选同时删除：\n{path}") \
                .replace("{path}", folder)
            checkbox = tr("同时删除绑定的工作文件夹（不可恢复！）")
        ok, del_folder = ConfirmDialog.ask(
            self.win, self.t, tr("确认删除"), msg,
            checkbox=checkbox, ok_text=tr("删除"))
        if not ok:
            return
        if del_folder and folder:
            try:
                shutil.rmtree(folder)
                log.info(f"删除文件夹: {folder}")
            except Exception:
                log.error(f"删除文件夹失败 {folder}:\n" + traceback.format_exc())
        self.store.delete([item["id"]])
        self.win.refresh()
        Toast.show_text(tr("已删除 {n} 条").replace("{n}", "1"))

    def _toggle_todo(self, item):
        item["done"] = not item.get("done", False)
        item["priority"] = core.auto_priority(item)
        log.info(f"待办{'完成' if item['done'] else '取消完成'}: {item['title']}")
        self.store.save()
        self.win.refresh()

    def _complete_instance(self, item):
        pend = core.pending_instance(item)
        if pend:
            item.setdefault("completed_instances", []).append(pend)
            log.info(f"循环任务完成当期: {item['title']} @ {pend}")
            self.store.save()
            self.win.refresh()
            Toast.show_text(tr("已完成当期：{title}").replace("{title}", item["title"]))

    def open_link(self, item: dict):
        core.open_url(item.get("url"))

    def open_folder_flow(self, item: dict):
        folder = item.get("folder")
        if not folder or not os.path.isdir(folder):
            base = self.config.get("base_folder", default=core.DEFAULT_BASE_FOLDER)
            rules = self.config.get("folder_rules", default={})
            idx = core.folder_rule_index(rules, item.get("folder_rule"))
            folder = core.create_bound_folder(item, base, rules, rule_index=idx)
            item["folder"] = folder
            self.store.save()
            self.win.refresh()
        core.open_folder(folder)

    # ---------------------------------------------------------------- 设置 / 主题
    def show_settings(self):
        from settings import SettingsWindow
        if self.settings_win is None:
            self.settings_win = SettingsWindow(self)
            self.settings_win.finished.connect(self._settings_closed)
        self.settings_win.show()
        self.settings_win.raise_()
        self.settings_win.activateWindow()

    def _settings_closed(self, *_):
        self.settings_win = None
        self.win.refresh()

    def apply_theme(self, kind="all"):
        if kind in ("theme", "all"):
            self.t = self.config.get("theme")
            self.qapp.setStyleSheet(theme_mod.build_qss(self.t))
            self.win.refresh_theme()
        if kind in ("theme_settings", "all"):
            if self.settings_win:
                ts = self.config.get("theme_settings")
                self.settings_win.t = ts
                self.settings_win.setStyleSheet(theme_mod.build_qss(ts))
                apply_frosted(self.settings_win, ts)

    # ---------------------------------------------------------------- 快捷键
    def _build_hotkeys(self):
        self.hk = HotkeyPoller(self)
        self.hk.fired.connect(self._hotkey_fired)

    def reload_hotkeys(self):
        hk = self.config.get("hotkeys", default={})
        combos = {}
        for action in ("settings", "click_through"):
            keys = hk.get(action) or []
            if keys and all(k in VK_MAP for k in keys):
                combos[action] = tuple(frozenset(VK_MAP[k]) for k in keys)
        for action, keys in (hk.get("custom") or {}).items():
            if keys and all(k in VK_MAP for k in keys):
                combos[action] = tuple(frozenset(VK_MAP[k]) for k in keys)
        self.hk.combos = combos

    def _hotkey_fired(self, action: str):
        if action == "settings":
            self.show_settings()
        elif action == "click_through":
            self.set_click_through(None)
        elif action == "quick_record":
            self.add_item("record")
        elif action == "quick_todo":
            self.add_item("todo")
        elif action == "quick_recur":
            self.add_item("recur")
        elif action == "search":
            self.win.show()
            self.win.raise_()
            self.win.search.setFocus()
            self.win.search.selectAll()
        elif action == "toggle_compact":
            self.toggle_compact(None)
        elif action == "show_hide":
            self.toggle_visible()

    # ---------------------------------------------------------------- 提醒
    def check_reminders(self):
        now = core.now()
        self.refresh_priorities()
        r = self.config.get("reminder", default={})
        due = []
        for it in self.store.items:
            snooze = self.snoozed.get(it["id"])
            if snooze and snooze > now:
                continue
            if it["type"] == "todo" and r.get("todo_enabled", True) \
                    and not it.get("done") and it.get("deadline"):
                dl = core.parse_dt(it["deadline"])
                adv = it.get("remind_advance")
                if adv is None:
                    adv = r.get("todo_advance_minutes", 0)
                if dl and now >= dl - timedelta(minutes=adv or 0) \
                        and it.get("notified_for") != it["deadline"]:
                    due.append((it, self._todo_msg(it, dl, now)))
            elif it["type"] == "recur" and r.get("recur_enabled", True):
                pend = core.pending_instance(it)
                if pend and now >= core.parse_dt(pend) \
                        and it.get("notified_for") != pend:
                    due.append((it, tr("循环任务到时间了（{desc}）")
                                .replace("{desc}", core.recur_desc(it))))
            elif it["type"] == "remind" and r.get("remind_enabled", True) \
                    and not it.get("done") and it.get("remind_time"):
                rt = core.parse_dt(it["remind_time"])
                adv = it.get("remind_advance") or 0
                if rt and now >= rt - timedelta(minutes=adv) \
                        and it.get("notified_for") != it["remind_time"]:
                    due.append((it, tr("提醒时间到（{time}）")
                                .replace("{time}", it['remind_time'])))
        for it, msg in due:
            self._fire_reminder(it, msg)
        if due:
            self.win.refresh()

    def refresh_priorities(self):
        changed = False
        for it in self.store.items:
            p = core.auto_priority(it)
            if it.get("priority") != p:
                it["priority"] = p
                changed = True
        if changed:
            self.store.save()
            self.win.refresh()

    def _todo_msg(self, it, dl, now):
        if now >= dl:
            return tr("待办截止时间已到（{deadline}）").replace("{deadline}", it['deadline'])
        mins = int((dl - now).total_seconds() // 60)
        return tr("待办将于 {mins} 分钟后截止（{deadline}）") \
            .replace("{mins}", str(mins)).replace("{deadline}", it['deadline'])

    def _fire_reminder(self, item, message):
        from editor import ReminderDialog
        log.info(f"提醒: {item['title']} - {message}")
        self.win.highlight_id = item["id"]
        self.win.refresh()
        try:
            self.tray.showMessage(core.APP_NAME + " 提醒",
                                  f"{message}\n{item['title']}",
                                  QSystemTrayIcon.Information, 8000)
        except Exception:
            pass
        d = ReminderDialog(self.win, self.t, item, message)
        self._reminder_dialogs.append(d)
        d.action.connect(lambda act, mins, it=item: self._reminder_done(it, act, mins))
        d.finished.connect(lambda _=None, dd=d: self._reminder_dialogs.remove(dd)
                           if dd in self._reminder_dialogs else None)
        d.show()
        # 移到屏幕右下角
        scr = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        d.adjustSize()
        d.move(g.right() - d.width() - 20, g.bottom() - d.height() - 20)

    def _reminder_done(self, item, act: str, mins: int):
        if item["type"] == "remind":
            if act == "done":
                item["done"] = True
                item["notified_for"] = item.get("remind_time")
                log.info(f"提醒中完成: {item['title']}")
            elif act == "snooze":
                self.snoozed[item["id"]] = core.now() + timedelta(minutes=mins)
                log.info(f"稍后提醒({mins}分钟): {item['title']}")
            else:  # close：本次提醒已处理，不再重复弹出
                item["notified_for"] = item.get("remind_time")
            self.store.save()
            self.win.highlight_id = None
            self.win.refresh()
            return
        key = item["deadline"] if item["type"] == "todo" else core.pending_instance(item)
        if act == "done":
            if item["type"] == "todo":
                item["done"] = True
                item["priority"] = core.auto_priority(item)
                log.info(f"提醒中完成待办: {item['title']}")
            else:
                pend = core.pending_instance(item)
                if pend:
                    item.setdefault("completed_instances", []).append(pend)
                    log.info(f"提醒中完成循环当期: {item['title']} @ {pend}")
            item["notified_for"] = key
            self.store.save()
        elif act == "snooze":
            self.snoozed[item["id"]] = core.now() + timedelta(minutes=mins)
            log.info(f"稍后提醒({mins}分钟): {item['title']}")
        else:  # close
            item["notified_for"] = key
            self.store.save()
        self.win.highlight_id = None
        self.win.refresh()

    # ---------------------------------------------------------------- 退出 / 重启
    def quit(self):
        """退出应用：确保事件循环与进程真正结束（失败也兜底强制退出）。"""
        try:
            log.info("程序退出")
            try:
                self.win.save_geometry()
            except Exception:
                pass
            try:
                self.config.save()
            except Exception:
                pass
            try:
                self.store.save()
            except Exception:
                pass
        finally:
            try:
                self.hk.shutdown()
            except Exception:
                pass
            try:
                self.tray.hide()
            except Exception:
                pass
            try:
                self.qapp.quit()
            except Exception:
                pass
            # 兜底：事件循环若未正常退出，1.5s 后强制结束进程
            QTimer.singleShot(1500, lambda: os._exit(0))

    def restart(self):
        """重启应用：启动新实例后退出当前进程（供出现异常时手动恢复）。"""
        log.info("重启应用")
        try:
            if getattr(sys, "frozen", False):
                cmd = [sys.executable]
            else:
                cmd = ["wscript.exe", core.VBS_PATH]
            subprocess.Popen(cmd)
        except Exception:
            log.error("重启启动失败:\n" + traceback.format_exc())
        self.quit()

    def run(self):
        Toast.show_text(tr("ZhaxxxxxxQAQ 已在桌面运行"))
        sys.exit(self.qapp.exec())


if __name__ == "__main__":
    App().run()
