import sys, os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\Temp\opencode\ZhaxxxxxxQAQ-src")
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\Temp\opencode\ZhaxxxxxxQAQ-src\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import app.core as core
from app.main_window import FloatWindow

app = QApplication(sys.argv)
cfg = core.Config()
app.config = cfg
app.store = core.DataStore(r"D:\ZhaxxxxxxQAQ\data\data.json")
win = FloatWindow(app)

def probe():
    win.refresh()
    gh = win.content_lay.itemAt(0).widget()
    print("gh.sizeHint", gh.sizeHint().height(),
          "gh.layout().sizeHint", gh.layout().sizeHint().height(),
          "gh.minimumSizeHint", gh.minimumSizeHint().height(),
          "gh.layout().minimumSize", gh.layout().minimumSize().height(),
          "frameWidth", gh.frameWidth(),
          "isHidden", gh.isHidden(), "isVisible", gh.isVisible())
    app.quit()

QTimer.singleShot(200, probe)
sys.exit(app.exec())
