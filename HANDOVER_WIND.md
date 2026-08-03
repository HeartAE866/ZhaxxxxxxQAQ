# 交接文档：1.3.0beta2 Win+D 桌面化探索记录

> 交接时间：2026-08-04
> 交接状态：已回退 v1.3.0beta（功能完整、稳定），1.3.0beta2 的 Win+D/壁纸化探索暂未成功
> 目标：在另一台电脑继续 1.3.0beta2（攻克 Win+D，实现三原则之"桌面化"）

## 一、当前版本状态（必读）

- 主目录 = **v1.3.0beta 定格状态**（git tag `v1.3.0beta`），功能全部正常：
  幽灵窗口根治（先父化后显示）、记忆窗口尺寸、记忆展开状态、Toast 恢复、拖拽排序、网址直达等
- git 历史：`v1.3.0beta`（存档）→ beta2 探索（多 commit）→ `39da7e5`（回退）
- 构建链：`build\rebuild.ps1`（Inno Setup 在 `C:\Users\张鑫\AppData\Local\Programs\Inno Setup 6\ISCC.exe`）
- 安装版：`C:\迅雷下载\ZhaxxxxxxQAQ`（源码版验证后需同步）
- 回归脚本：`scripts\test_fit_fix.py`、`test_reminder_sort.py`、`test_refresh_ops.py`、`test_user_height.py`
- 测试约定：offscreen + `-X utf8`；不得实例化 `main.App()`（单实例锁）

## 二、Win+D/壁纸化探索全记录（beta2 已尝试，均失败）

### 用户需求（三原则·桌面化）
- Win+D（显示桌面）时挂件不消失；嵌于桌面（类似 wallpaper/TranslucentTB）
- 软件将上架 Gitee/GitHub，需兼容所有电脑（Win10/11、多显示器、各种 DPI）

### 已尝试路线与失败原因（按时间顺序）

| # | 方案 | 结果 | 根因 |
|---|------|------|------|
| 1 | 自建 `ZhaxxWorkerW`（同进程）挂 Progman + Win32 SetParent | 黑块 | **Progman 带 WS_EX_NOREDIRECTIONBITMAP（Win11 raised desktop，无重定向表面）**——普通子窗口 GDI 内容无处合成 |
| 2 | `QWindow.fromWinId(workerw)` + `QWindow::setParent`（Qt 原生父子） | 黑块 | Qt 认为窗口非顶层（isTopLevel=False）→ `QWindowsBackingStore::flush` 短路 |
| 3 | Lively 机制（Progman 子 + WS_EX_LAYERED + 保持 translucent/ULW） | 黑块 | ULW 对子窗口不呈现；手动 UpdateLayeredWindow 成功但屏幕无内容 |
| 4 | 手动 BitBlt / ULW 到窗口 DC（Qt 离屏 render 后 GDI 提交） | 黑块 | **Qt QWidget 软件渲染在"外部 SetParent"后呈现彻底失效**（第 5 次证实，任何手段无效） |
| 5 | 置底（Progman 之上、普通窗口之下）+ 800ms 守护（隐藏/最小化/Z 序检测） | Win+D 时消失 | Win+D 的「桌面提升」把 Progman 提到普通层顶（Z 序变化），置底窗口被桌面壁纸盖住 |
| 6 | 守护增强：桌面模式 hide-show / 1px 位移 / InvalidateRect / setExposed / 隐形窗口创建 | 均无效 | 提升是系统级 Z 序/合成层操作，单窗口动作无法对抗 |
| 7 | 键盘钩子拦截 Win+D → 转发 Win+M | 未完全验证（用户否决方向） | 劫持系统快捷键，不符合"上架兼容全球"要求（默认必须不劫持） |
| 8 | 经典方案：向 Progman 发 0x052C → 获取系统壁纸层 WorkerW → SetParent | 结构成功、**内容仍黑** | 同为 Qt 子窗口呈现失效（见 #4） |
| 9 | **Rainmeter 机制**：置底 + `WM_WINDOWPOSCHANGING→SWP_NOZORDER` 保护 + 桌面模式临时置顶（topmost 层） | 用户实测无效 | 原因未明——理论上 topmost 层高于被提升的普通层；可能系统仍将挂件压回，或本机环境（NVIDIA Overlay 等）干扰 |

### 关键诊断结论（已证实）
1. **本机桌面结构（Win11 raised desktop）**：`Progman[WS_EX_NOREDIRECTIONBITMAP] → SHELLDLL_DefView[layered 透明图标层] + WorkerW[壁纸层]`
2. **Qt QWidget（raster/软件渲染）无法在外部 SetParent 下呈现**——这是所有子窗口方案失败的根本（Lively 用 DX/D3D、Rainmeter 用 D2D 才能子窗口呈现）
3. **Win+D 的「桌面提升」**：把 Progman 提到普通层顶（EnumWindows 顺序证实），置底窗口被壁纸盖；Z 序对抗无效
4. **参考项目**（源码已复制到 `reference\`）：
   - **Lively Wallpaper**（`reference\lively\WinDesktopCore.cs`、`DesktopUtil.cs`、`WindowUtil.cs`）：SetParent 到 Progman/WorkerW + DX 呈现；微软官方注释（WS_EX_LAYERED 子窗口要求）
   - **Rainmeter**（`reference\rainmeter\System.cpp`、`Skin.cpp`）：普通顶层 Tool+layered 皮肤窗口，**SWP_NOZORDER Z 序保护 + WinEventHook 检测"显示桌面" + 桌面模式临时置顶（topmost 层底部）+ 辅助窗口（HelperWindow）机制**

## 三、下一步建议（按优先级）

1. **再研究 Rainmeter 的 topmost 细节**：本机无效可能因为：
   - 我们用的 `HWND_TOPMOST`（顶层）vs Rainmeter 的"**插入 topmost 层底部**"（`GetBackmostTopWindow` + 辅助窗口机制）
   - 需要**完整复刻 Rainmeter 的 HelperWindow 方案**（System.cpp：`PrepareHelperWindow` 在显示桌面时把辅助窗口置顶、皮肤插入其后）
   - 用 WinEventHook（EVENT_SYSTEM_FOREGROUND）替代轮询
2. **简单验证"置顶（悬浮）模式 + Win+D"**：如果挂件置顶（topmost）时按 Win+D 不消失，则壁纸模式可简化为"置顶"（悬浮，非嵌桌面）——10 分钟可验证（config `window.topmost=true` + Win+D 实测）
3. **QML/RHI 路线**（Qt D3D 渲染可子窗口呈现）：大改（UI 重写），仅在用户愿意时考虑
4. **放弃桌面化**（保持悬浮挂件，Win+D 按系统原生行为）：保守方案，上架安全

## 四、上架准备待办（Gitee/GitHub）

- [ ] README 更新（壁纸模式说明 + 兼容性边界）
- [ ] 开源许可证选择（GPL/MIT，用户决定）
- [ ] 代码清理（scripts 诊断脚本、hotkeys.py 的 wind_intercept 残留代码）
- [ ] 默认行为保守（不劫持系统快捷键——wallpaper 默认关闭）

## 五、环境说明

- 本机：Win11，2560x1440，Raised Desktop；有 NVIDIA GeForce Overlay 全屏窗口（`CEF-OSC-WIDGET`，会干扰 BitBlt 抓屏验证——验证"视觉"必须以实机为准）
- 用户机原有"视频壁纸程序"（本会话期间未开）
- 重要：`grabWindow`/BitBlt 对 layered 窗口与 NVIDIA Overlay 区域抓取为黑/失真，**视觉验证只能靠用户实机**
