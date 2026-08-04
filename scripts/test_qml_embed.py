"""QML/RHI 嵌入测试：创建可交互 QML 窗口，SetParent 到桌面层（Progman /
系统壁纸 WorkerW），验证 D3D 渲染在子窗口是否正常呈现 + 可交互。
用法: python test_qml_embed.py [progman|workerw] [x y]
退出: 按回车或 60 秒后自动关闭
"""
import ctypes
import os
import sys
import tempfile
import time
from ctypes import wintypes

# 子窗口嵌入后 D3D present 可能阻塞（等待 vsync → 窗口"忙"沙漏）：
# 1) 同步渲染循环（basic，主线程渲染）
# 2) 禁用 vsync（present 立即返回）
os.environ.setdefault("QSG_RENDER_LOOP", "basic")

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView, QQuickWindow

try:
    QQuickWindow.setSwapInterval(0)   # 部分 PySide6 版本无此 API，失败忽略
except Exception:
    pass

QML = """import QtQuick 2.15
Rectangle {
    width: 413; height: 480
    color: "#1e1e28"
    Text {
        text: "QML 可交互测试窗口"
        anchors.horizontalCenter: parent.horizontalCenter
        y: 30; color: "#ffffff"; font.pixelSize: 18
    }
    Text {
        id: status
        text: "未点击"
        anchors.horizontalCenter: parent.horizontalCenter
        y: 70; color: "#8ab4ff"; font.pixelSize: 13
    }
    Rectangle {
        width: 150; height: 46; radius: 10; color: "#4a9eff"
        anchors.centerIn: parent
        Text { text: "点击我（变色）"; anchors.centerIn: parent
               color: "white"; font.pixelSize: 15 }
        MouseArea {
            anchors.fill: parent
            onClicked: {
                parent.color = (parent.color === "#4a9eff") ? "#ff7a5c" : "#4a9eff"
                status.text = "已点击 " + (new Date().toLocaleTimeString())
                console.log("clicked!")
            }
        }
    }
}
"""


def embed(hwnd, target):
    u = ctypes.windll.user32
    style = u.GetWindowLongPtrW(hwnd, -16)
    if not style & 0x40000000:  # WS_CHILD
        u.SetWindowLongPtrW(hwnd, -16, style | 0x40000000)
    u.SetParent(hwnd, target)
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    x, y = r.left, r.top
    if target == 0:
        x, y = 1913, 65
    u.SetWindowPos(hwnd, wintypes.HWND(0), x, y,
                   r.right - r.left, r.bottom - r.top, 0x0010)
    u.ShowWindow(hwnd, 5)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "progman"
    app = QGuiApplication([])
    qml_path = os.path.join(tempfile.gettempdir(), "zhaxx_qml_test.qml")
    with open(qml_path, "w", encoding="utf-8") as f:
        f.write(QML)
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(qml_path))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(413, 480)
    view.setTitle("ZhaxxQMLTest")
    view.show()
    for _ in range(10):
        app.processEvents()

    u = ctypes.windll.user32
    if mode == "workerw":
        # 系统壁纸层 WorkerW
        progman = u.FindWindowW("Progman", None)
        out = ctypes.c_ulong()
        u.SendMessageTimeoutW(wintypes.HWND(progman), 0x052C, 0xD, 0x1,
                              2, 1000, ctypes.byref(out))
        ww = u.FindWindowExW(wintypes.HWND(progman), None, "WorkerW", None)
        target = wintypes.HWND(ww) if ww else wintypes.HWND(progman)
        print(f"嵌入目标: 系统 WorkerW hwnd={ww}")
    else:
        progman = u.FindWindowW("Progman", None)
        target = wintypes.HWND(progman)
        print(f"嵌入目标: Progman hwnd={progman}")

    hwnd = int(view.winId())
    print(f"QML 窗口 hwnd={hwnd} mode={mode}")
    embed(hwnd, target)
    app.processEvents()
    print("已嵌入。请验证：1) 窗口是否显示(深色面板+按钮) 2) 点击按钮是否变色")
    print("120 秒后自动退出...")
    import threading
    threading.Timer(120, lambda: os._exit(0)).start()
    time.sleep(125)


if __name__ == "__main__":
    main()
