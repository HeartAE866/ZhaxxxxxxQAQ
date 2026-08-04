"""QML Window 根 + swapInterval:0 测试：验证嵌入 Progman 后是否不阻塞(hung)。
用法: python test_qml_window.py [保持秒数]
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

os.environ.setdefault("QSG_RENDER_LOOP", "basic")

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QByteArray, QUrl
from PySide6.QtQml import QQmlApplicationEngine

QML = """import QtQuick
Window {
    width: 413; height: 480
    swapInterval: 0
    color: "#1e1e28"
    Text { text: "QML Window 测试(swapInterval 0)"
           anchors.horizontalCenter: parent.horizontalCenter
           y: 30; color: "white"; font.pixelSize: 18 }
    Text { id: st; text: "未点击"
           anchors.horizontalCenter: parent.horizontalCenter
           y: 70; color: "#8ab4ff"; font.pixelSize: 13 }
    Rectangle { width: 150; height: 46; radius: 10; color: "#4a9eff"
        anchors.centerIn: parent
        Text { text: "点击我(变色)"; anchors.centerIn: parent; color: "white" }
        MouseArea { anchors.fill: parent
            onClicked: { parent.color = "#ff7a5c"; st.text = "已点击" } }
    }
}
"""


def main():
    keep = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    app = QGuiApplication([])
    engine = QQmlApplicationEngine()
    errs = []
    engine.warnings.connect(lambda msgs: errs.extend(msgs))
    engine.loadData(QByteArray(QML.encode("utf-8")), QUrl("zhaxx_window.qml"))
    for w in errs:
        print("QML warning:", str(w))
    objs = engine.rootObjects()
    if not objs:
        print("FAIL: QML 加载失败")
        return 1
    win = objs[0]
    win.show()
    for _ in range(10):
        app.processEvents()
    hwnd = int(win.winId())
    print(f"winId={hwnd} swapInterval={win.property('swapInterval')}")
    u = ctypes.windll.user32
    progman = u.FindWindowW("Progman", None)
    style = u.GetWindowLongPtrW(wintypes.HWND(hwnd), -16)
    u.SetWindowLongPtrW(wintypes.HWND(hwnd), -16, style | 0x40000000)
    u.SetParent(wintypes.HWND(hwnd), wintypes.HWND(progman))
    u.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(0),
                   1065, 425, 413, 480, 0x0010)
    app.processEvents()
    print(f"已嵌入 Progman。保持 {keep}s。hung 采样：")
    for i in range(min(keep // 2, 30)):
        time.sleep(2)
        print(f"  t+{(i + 1) * 2}s hung={bool(u.IsHungAppWindow(wintypes.HWND(hwnd)))}"
              f" vis={bool(u.IsWindowVisible(wintypes.HWND(hwnd)))}", flush=True)


if __name__ == "__main__":
    main()
