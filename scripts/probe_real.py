import sys, os
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\Temp\opencode\ZhaxxxxxxQAQ-src")
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\Temp\opencode\ZhaxxxxxxQAQ-src\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import app.core as core
from app.main_window import FloatWindow

qapp = QApplication(sys.argv)
app = type("A", (), {})()
app.config = core.Config()
app.store = core.DataStore(r"D:\ZhaxxxxxxQAQ\data\data.json")
win = FloatWindow(app)   # 内部 apply_window_state(show) + refresh

def probe():
    print("=== real platform, shown ===")
    print("window:", win.width(), "x", win.height())
    print("content.sizeHint:", win.content.sizeHint().height())
    print("content_lay.sizeHint:", win.content_lay.sizeHint().height())
    print("content.isVisible:", win.content.isVisible())
    gh = win.content_lay.itemAt(0).widget() if win.content_lay.count() else None
    if gh:
        print("first:", gh.__class__.__name__, "sizeHint", gh.sizeHint().height(),
              "isVisible", gh.isVisible(), "isHidden", gh.isHidden())
    qapp.quit()

QTimer.singleShot(2500, probe)
sys.exit(qapp.exec())
