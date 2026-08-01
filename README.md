# ZhaxxxxxxQAQ —— 轻量桌面工作记事录 / Lightweight Desktop Work Journal

一个贴在桌面上的无边框磨砂悬浮记事挂件：自动创建项目文件夹、工作记录、待办事项、循环任务、定时提醒、下班倒计时。
A frameless, frosted-glass floating widget on your desktop: auto-created project folders, work logs, todos, recurring tasks, reminders, and an off-work countdown.

**完全本地离线运行，不联网、不收集任何信息 · 100% local and offline — no accounts, no cloud, no tracking.**

![Version](https://img.shields.io/badge/version-v1.1.4-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/Python-3.14+-8A2BE2)
![PySide6](https://img.shields.io/badge/UI-PySide6-4fc3f7)

![Main Window](docs/screenshots/main.png)

---

## English

### ✨ Killer Feature: Auto-Created Project Folders, One-Click Access

**A blessing for working people.** No more manual folder creation:

- When you log a task, a folder structure is auto-created: `Work Folder\2026\07\2026.7.31TaskName` (year/month/project levels are fully customizable; duplicates get auto-numbered)
- Recurring tasks go to `Work Folder\Recurring\TaskName`
- Click the **📁 icon** next to any item to open its folder instantly — bound folders open directly, unbound ones are created on the fly
- **Multiple parallel rules**: create several rules (e.g. Finance / Operations) and pick the right one per task — finance items go to the finance path, operations to the operations path
- Manual binding, custom subfolders, rebinding and unbinding are all supported
- Everything stays organized by Year → Month → Project automatically

![Auto-created folders](docs/screenshots/folder.png)

### Features

- **Frameless frosted floating window**: sits on the desktop layer, no taskbar entry, tray-only; drag, 8-direction edge resize, position memory
- **⚡ Get to Work**: one-click add todos, log past work (pick the time), recurring tasks, one-time reminders
- **Year → Month → Task grouping**: collapsible sections, window height auto-fits content
- **Recurring tasks**: daily/weekly/monthly/quarterly/yearly, with "complete current" and history
- **Reminders**: todo deadline reminders (with advance time), recurring task alerts, one-time reminder popups (Done / Snooze 5·30·60 min / custom)
- **Off-work countdown**: live clock + time-until-off-work (customizable text & format, workday-aware)
- **DIY backgrounds**: per-component background (solid color or image + opacity) for panel/header/reminder bar/clock/dialogs
- **Theming**: independent themes for the desktop window and settings window, on-screen color picker (eyedropper), fonts, opacity, corner radius, light/dark presets, theme import/export
- **Global hotkeys**: `Ctrl+Shift+Z+X` opens settings, `Ctrl+Shift+Z+P` toggles click-through; custom 4-key combos
- **Compact mode**: collapse into a mini bar showing the most urgent item; click to expand, drag to move
- **Data management**: full-text search, type filters, JSON/CSV export/import (duplicate-safe), guarded deletion, tag manager, recurring history
- **🌐 Bilingual**: Simplified Chinese / English UI, switchable in Settings → Personalization
- **Lightweight**: ~0% CPU when idle, ~19 MB installer

### Install

Download the latest installer from [Releases](https://github.com/HeartAE866/ZhaxxxxxxQAQ/releases)
(`ZhaxxxxxxQAQ_Setup_v1.1.4.exe`) and run it.

> Windows 10/11 (64-bit). Fully offline — uninstall by deleting the app folder.

---

## 简体中文

### ✨ 核心亮点：自动创建项目文件夹，一键直达

**打工人福音。** 记录一项工作时，无需再手动建文件夹：

- 添加事项时自动按规则生成文件夹结构：`工作文件夹\2026年\7月\2026.7.31事项名`（年份/月份/项目层级可自定义，重名自动加序号）
- 循环任务自动归入 `工作文件夹\循环任务\任务名`
- 点击事项右侧的 **📁 图标一键打开**对应文件夹——已绑定直接进，未绑定自动创建
- **多条平行规则**：可创建如「财务规则」「运营规则」等多条规则，创建事项时自主选择——财务项目进财务路径，运营工作进运营路径
- 也可手动绑定任意文件夹 / 绑定自定义子文件夹，随时改绑、解绑
- 归档从此有条理：所有资料自动按 年 → 月 → 项目 归档，找东西再也不靠回忆

### 功能特性

- **无边框磨砂悬浮窗**：贴在桌面层、不进任务栏，仅系统托盘驻留；支持拖拽、八向边缘缩放、位置记忆
- **⚡ 来活了**：一键添加待办（开始新工作）、登记以往工作（自定义历史时间）、循环任务、一次性提醒
- **三层收纳**：工作记录/待办按「年 → 月 → 当月任务」折叠展开，窗口高度随内容自适应
- **循环任务**：每天/每周/每月/每季/每年，独立分区，支持"完成当期"与完成历史
- **定时提醒**：待办截止提醒（可提前）、循环任务提醒、一次性提醒弹窗（完成/稍后 5/30/60 分钟/自定义）
- **下班倒计时**：窗口底部时钟 + 距下班时间（可定制文案与格式，工作日自动识别）
- **DIY 背景**：每个部件（主面板/头部/提醒栏/时钟/对话框）可单独设置纯色或图片背景 + 透明度
- **个性化主题**：主窗口与设置窗独立配色，屏幕吸管取色、字体字号、背景透明度、圆角、明暗双主题、主题导入导出
- **全局快捷键**：默认 `Ctrl+Shift+Z+X` 呼出设置、`Ctrl+Shift+Z+P` 切换鼠标穿透；可自定义四键组合
- **紧凑模式**：缩成迷你悬浮条只显示最紧急事项，点击展开；长按拖拽移动、边缘横向缩放
- **数据管理**：全文搜索、类型筛选、JSON/CSV 导出导入（防重复）、防误删确认、标签管理、循环完成历史
- **🌐 中英双语**：设置 → 个性化 可切换简体中文 / English，全球用户均可使用
- **轻量**：待机 CPU 占用接近 0，安装包约 19MB

### 安装

在 [Releases](https://github.com/HeartAE866/ZhaxxxxxxQAQ/releases) 下载最新版安装包
（`ZhaxxxxxxQAQ_Setup_v1.1.4.exe`），双击安装即可。

> Windows 10/11（64 位）。完全本地离线，卸载只需删除安装目录。

---

## Run from Source / 源码运行（开发）

```bash
# Python 3.10+（开发环境使用 3.14）
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 日常静默启动（无黑窗口） / Silent launch (no console window)
wscript.exe ZhaxxxxxxQAQ.vbs

# 调试启动（带控制台） / Debug launch (with console)
启动 ZhaxxxxxxQAQ.bat
```

The tray icon prefers a `图标.png` on the user's Desktop and falls back to `resources\tray.png`; same for the donation QR (`赞赏码.png` on Desktop, fallback `resources\donation.png` — delete to hide the donation entry).
托盘图标默认优先读取用户桌面上的 `图标.png`，不存在时回退到打包内 `resources\tray.png`；打赏码同理回退 `resources\donation.png`，删除即可移除"关于"页打赏入口。

## Packaging / 打包发布

```bash
python -m PyInstaller --noconfirm --clean --windowed --name ZhaxxxxxxQAQ ^
  --icon "resources\tray_round.ico" --add-data "resources;resources" ^
  --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.QtPdf --exclude-module PySide6.QtOpenGL ^
  --exclude-module PySide6.QtOpenGLWidgets --exclude-module PySide6.QtNetwork ^
  --exclude-module PySide6.QtSvg --exclude-module PySide6.QtVirtualKeyboard ^
  --exclude-module PySide6.QtWebSockets --exclude-module PySide6.QtTest app\main.py
# Then prune unused Qt DLLs in dist\ZhaxxxxxxQAQ\_internal\PySide6\ and build with Inno Setup.
```

## Directory Layout / 目录结构

```
ZhaxxxxxxQAQ\
├── ZhaxxxxxxQAQ.vbs         Silent launcher / 静默启动器（开机自启指向它）
├── 启动 ZhaxxxxxxQAQ.bat     Debug launcher / 调试用启动器（带控制台）
├── requirements.txt          Python dependencies
├── app\                     Source code / 程序源码（main.py 入口）
├── resources\               Icons, logo / 图标、logo、默认打赏码
├── config.json              Settings (runtime) / 全部设置（运行时生成，不入库）
├── data\data.json           Item data (runtime) / 全部事项数据（运行时生成，不入库）
├── logs\                    Logs (runtime) / 运行/错误日志（运行时生成，不入库）
└── 工作文件夹\                Default work folder (runtime) / 事项绑定的默认工作目录（运行时生成，不入库）
```

## License / 许可证

[MIT](LICENSE) © ZhaxxxxxxQAQ

本应用完全开源且免费，任何向你收费的都是骗子。
This app is fully open source and free. Anyone charging you for this app is a scammer.
