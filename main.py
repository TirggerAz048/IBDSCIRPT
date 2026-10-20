import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView

app = QApplication(sys.argv)
app.setApplicationName("IBD Spider")
app.setApplicationVersion("2.0")
_ui_font = "Microsoft YaHei" if sys.platform == "win32" else "PingFang SC"
app.setFont(QFont(_ui_font, 10))
from qfluentwidgets import setTheme, Theme, setThemeColor
setTheme(Theme.DARK)
setThemeColor("#0078D7")
from gui.theme import DARK_THEME_STYLESHEET, apply_label_transparent_background
app.setStyleSheet(DARK_THEME_STYLESHEET)  
from gui.main_window import MainWindow
window = MainWindow()
window.resize(1200, 800)
window.setMinimumSize(1000, 650)
window.setWindowTitle("IBD Spider v2.0 - 金融数据集成工具")
window.show()
QTimer.singleShot(200, lambda: (apply_label_transparent_background(window),))
sys.exit(app.exec())
