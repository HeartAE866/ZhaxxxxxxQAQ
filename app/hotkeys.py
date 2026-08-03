# -*- coding: utf-8 -*-
"""全局快捷键引擎：优先使用 Win32 低层键盘钩子（WH_KEYBOARD_LL）。
钩子只在按键事件发生时被系统唤醒，待机期间零定时器、零轮询、零 CPU；
钩子安装失败（个别杀软/权限环境）时自动回退到 100ms 低频 GetAsyncKeyState
轮询（先快速检查修饰键，任一修饰键未按下立即短路返回），保证功能永不失效。
接口与旧版 HotkeyPoller 完全兼容：combos 字典 + fired 信号。"""
from __future__ import annotations

import ctypes
from ctypes import POINTER, cast, c_bool, c_int, c_ssize_t

from PySide6.QtCore import QObject, QTimer, Signal

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105
LLKHF_UP = 0x80

# 修饰键 VK 全集（左/右 + 遗留常量），匹配时用 GetAsyncKeyState 读取物理状态
_MOD_VKS = {0xA2, 0xA3, 0x11, 0xA0, 0xA1, 0x10, 0xA4, 0xA5, 0x12, 0x5B, 0x5C}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", ctypes.c_ulong),
                ("scanCode", ctypes.c_ulong),
                ("flags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


HOOKPROC = ctypes.CFUNCTYPE(c_ssize_t, c_int,
                            ctypes.c_ulonglong, ctypes.c_ulonglong)


class HotkeyPoller(QObject):
    """全局快捷键（替代旧的 50ms 常驻轮询，接口不变）。"""
    fired = Signal(str)
    wind_pressed = Signal()   # 壁纸模式：Win+D 被拦截（由应用转发为 Win+M）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combos: dict[str, tuple] = {}   # action -> (VK组, ...)
        self.wind_intercept = False   # True：拦截 Win+D（桌面提升会盖住挂件）
        self._down: set[int] = set()
        self._active: set[str] = set()
        self._hook = None
        self._proc = None
        self._u32 = ctypes.windll.user32
        self._poll_timer = None
        if not self._install_hook():
            # 回退：100ms 低频轮询（快速路径：修饰键未按下立即返回）
            self._poll_timer = QTimer(self, interval=100, timeout=self._poll)
            self._poll_timer.start()

    # ------------------------------------------------------------ 低层钩子
    def _install_hook(self) -> bool:
        try:
            u32 = self._u32
            u32.SetWindowsHookExW.restype = ctypes.c_void_p
            u32.SetWindowsHookExW.argtypes = [c_int, HOOKPROC, ctypes.c_void_p,
                                              ctypes.c_ulong]
            u32.CallNextHookEx.restype = c_ssize_t
            u32.CallNextHookEx.argtypes = [ctypes.c_void_p, c_int,
                                           ctypes.c_ulonglong, ctypes.c_ulonglong]
            u32.UnhookWindowsHookEx.restype = c_bool
            u32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
            u32.GetAsyncKeyState.argtypes = [c_int]
            u32.GetAsyncKeyState.restype = ctypes.c_short
            self._proc = HOOKPROC(self._hook_cb)
            self._hook = u32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc,
                                               None, 0)
            return bool(self._hook)
        except Exception:
            self._hook = None
            return False

    def _hook_cb(self, n_code, w_param, l_param):
        try:
            if n_code >= 0:
                kbd = cast(l_param, POINTER(KBDLLHOOKSTRUCT))
                vk = int(kbd.contents.vkCode)
                if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    # 壁纸模式：拦截 Win+D（桌面提升会盖住挂件），转发为 Win+M
                    if self.wind_intercept and vk == 0x44:  # 'D'
                        if self._u32.GetAsyncKeyState(0x5B) & 0x8000:  # LWIN
                            self.wind_pressed.emit()
                            return 1   # 吞掉按键，不传给系统
                    self._key_down(vk)
                elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                    self._key_up(vk)
        except Exception:
            pass
        return self._u32.CallNextHookEx(self._hook, n_code, w_param, l_param)

    # ------------------------------------------------------------ 按键状态
    @staticmethod
    def _focus_in_edit() -> bool:
        try:
            from PySide6.QtWidgets import QApplication
            from widgets import HotkeyEdit
            return isinstance(QApplication.focusWidget(), HotkeyEdit)
        except Exception:
            return False

    def _key_down(self, vk: int):
        if self._focus_in_edit():
            self._down.clear()
            self._active.clear()
            return
        if vk in self._down:               # 系统自动重复，忽略
            return
        self._down.add(vk)
        self._evaluate()

    def _key_up(self, vk: int):
        self._down.discard(vk)
        self._active.clear()               # 组合松开后可再次触发

    def _group_down(self, group) -> bool:
        for vk in group:
            if vk in _MOD_VKS:
                if self._u32.GetAsyncKeyState(vk) & 0x8000:
                    return True
            elif vk in self._down:
                return True
        return False

    def _evaluate(self):
        if not self.combos:
            return
        for action, groups in self.combos.items():
            if not groups or action in self._active:
                continue
            if all(self._group_down(g) for g in groups):
                self._active.add(action)
                self.fired.emit(action)

    # ------------------------------------------------------------ 兜底轮询
    def _poll(self):
        try:
            if self._focus_in_edit():
                self._down.clear()
                return
            combos = self.combos
            if not combos:
                return
            # 快速路径：任一组合的修饰键都未按下 → 直接返回（零开销）
            mods = self._mods_any_down()
            if not mods:
                self._down.clear()
                self._active.clear()
                return
            for action, groups in combos.items():
                if not groups or action in self._active:
                    continue
                pressed = all(
                    any(self._u32.GetAsyncKeyState(vk) & 0x8000 for vk in g)
                    for g in groups)
                if pressed:
                    self._active.add(action)
                    self.fired.emit(action)
        except Exception:
            pass

    def _mods_any_down(self) -> bool:
        mods: set[int] = set()
        for groups in self.combos.values():
            for g in groups:
                for vk in g:
                    if vk in _MOD_VKS:
                        mods.add(vk)
        if not mods:
            return True
        return any(self._u32.GetAsyncKeyState(vk) & 0x8000 for vk in mods)

    def shutdown(self):
        """退出时卸载钩子，避免泄漏。"""
        if self._poll_timer:
            self._poll_timer.stop()
        if self._hook:
            try:
                self._u32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None
