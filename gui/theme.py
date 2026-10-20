from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QLabel, QWidget


DARK_THEME_STYLESHEET = """
/* === 全局 === */
QWidget {
    background-color: #1a1a1a;
    color: #ffffff;
}

QStackedWidget {
    background-color: #1a1a1a;
    border: none;
}
QStackedWidget > QWidget {
    background-color: #1a1a1a;
}

/* === 页面容器 === */
QScrollArea {
    background-color: #1a1a1a;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #1a1a1a;
}
QScrollArea > QWidget#qt_scrollarea_viewport {
    background-color: #1a1a1a;
}
SingleDirectionScrollArea, SmoothScrollArea {
    background-color: #1a1a1a;
    border: none;
}
SingleDirectionScrollArea > QWidget, SmoothScrollArea > QWidget {
    background-color: #1a1a1a;
}

/* === 卡片 === */
CardWidget {
    background-color: #2d2d2d;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
}
CardWidget:hover {
    background-color: #363636;
    border: 1px solid rgba(0, 120, 215, 0.3);
}

/* === 输入框 === */
QLineEdit, LineEdit {
    background-color: #2d2d2d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
}
QLineEdit:focus, LineEdit:focus {
    border: 1px solid #0078D7;
    background-color: #363636;
}

/* === 下拉框 === */
QComboBox, ComboBox {
    background-color: #2d2d2d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 6px 12px;
    color: #ffffff;
}
QComboBox:hover, ComboBox:hover {
    border: 1px solid rgba(0, 120, 215, 0.5);
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    selection-background-color: #0078D7;
    color: #ffffff;
}

/* === 文本编辑 === */
QTextEdit, QPlainTextEdit, TextEdit, PlainTextEdit {
    background-color: #2d2d2d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #ffffff;
    padding: 8px;
}
QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #0078D7;
}

/* === 表格 === */
QTableWidget, QTableView, TableWidget {
    background-color: #2d2d2d;
    alternate-background-color: #252525;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.05);
    color: #ffffff;
}
QTableWidget::item, QTableView::item {
    padding: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: rgba(0, 120, 215, 0.3);
}
QHeaderView::section {
    background-color: #363636;
    color: #ffffff;
    padding: 10px;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    font-weight: bold;
}

/* === 按钮 === */
QPushButton, PushButton {
    background-color: #363636;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 8px 16px;
    color: #ffffff;
}
QPushButton:hover, PushButton:hover {
    background-color: #404040;
    border: 1px solid rgba(0, 120, 215, 0.5);
}
PrimaryPushButton {
    background-color: #0078D7;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    color: #ffffff;
}
PrimaryPushButton:hover {
    background-color: #006CBE;
}

/* === 标签 === */
QLabel {
    background-color: transparent;
    background: transparent;
    color: #ffffff;
}
TitleLabel {
    background-color: transparent;
    color: #ffffff;
    font-weight: bold;
}
BodyLabel {
    background-color: transparent;
    color: #e0e0e0;
}
SubtitleLabel {
    background-color: transparent;
    color: #ffffff;
    font-weight: 600;
}
CaptionLabel {
    background-color: transparent;
    color: #b0b0b0;
}
StrongBodyLabel {
    background-color: transparent;
    color: #ffffff;
    font-weight: bold;
}
LargeTitleLabel {
    background-color: transparent;
    color: #ffffff;
    font-weight: bold;
}
QWidget QLabel {
    background: transparent;
    background-color: transparent;
}

/* === 进度条 === */
QProgressBar {
    background-color: #2d2d2d;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
}
QProgressBar::chunk {
    background-color: #0078D7;
    border-radius: 4px;
}

/* === 滚动条 === */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: rgba(0, 120, 215, 0.5);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: rgba(0, 120, 215, 0.5);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === CheckBox / RadioButton === */
QCheckBox, CheckBox {
    background-color: transparent;
    background: transparent;
    color: #ffffff;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px; height: 18px;
    border-radius: 4px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    background-color: transparent;
}
QCheckBox::indicator:checked {
    background-color: #0078D7;
    border-color: #0078D7;
}
QCheckBox::indicator:hover {
    border-color: #0078D7;
}
QRadioButton, RadioButton {
    background-color: transparent;
    background: transparent;
    color: #ffffff;
}

/* === GroupBox === */
QGroupBox {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}
QGroupBox::title {
    background-color: transparent;
    color: #ffffff;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

/* === SpinBox === */
QSpinBox, SpinBox {
    background-color: #2d2d2d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 6px 12px;
    color: #ffffff;
}
QSpinBox:focus, SpinBox:focus {
    border: 1px solid #0078D7;
}

/* === 菜单 === */
QMenu {
    background-color: #2d2d2d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 20px;
    border-radius: 4px;
    color: #ffffff;
}
QMenu::item:selected {
    background-color: rgba(0, 120, 215, 0.3);
}

/* === ToolTip === */
QToolTip {
    background-color: #363636;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    padding: 6px 10px;
    color: #ffffff;
}

/* === 分隔线 === */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    background-color: rgba(255, 255, 255, 0.08);
}

/* === InfoBar === */
InfoBar {
    background-color: #2d2d2d;
}

/* === Pivot 顶部导航 === */
Pivot {
    background-color: #1a1a1a;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
PivotItem {
    background-color: transparent;
    color: #b0b0b0;
    padding: 10px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}
PivotItem:hover {
    color: #ffffff;
    background-color: transparent;
}
PivotItem:selected {
    color: #ffffff;
    border-bottom: 2px solid #0078D7;
}

/* === 透明工具按钮 === */
TransparentToolButton {
    background-color: transparent;
    border: none;
    color: #ffffff;
    padding: 0px;
    margin: 0px;
}
TransparentToolButton:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border: none;
}
TransparentToolButton:pressed {
    background-color: rgba(255, 255, 255, 0.12);
    border: none;
}

/* === ToolButton === */
ToolButton {
    background-color: transparent;
    border: none;
    color: #ffffff;
}
ToolButton:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border: none;
}

/* === QSplitter 分割线 === */
QSplitter::handle {
    background-color: rgba(255, 255, 255, 0.08);
}
QSplitter::handle:hover {
    background-color: rgba(0, 120, 215, 0.3);
}

/* === 侧边栏 === */
#sideBar {
    background-color: #1f1f1f;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
#topNavBar {
    background-color: #1a1a1a;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

/* === 状态栏 === */
#statusBar {
    background-color: #252525;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}

/* === 全局选中色 === */
* {
    selection-background-color: rgba(0, 120, 215, 0.4);
    selection-color: #ffffff;
}
"""


def apply_label_transparent_background(widget):
    label_class_names = {
        'BodyLabel', 'TitleLabel', 'SubtitleLabel', 'CaptionLabel',
        'StrongBodyLabel', 'LargeTitleLabel', 'DisplayLabel',
        'FluentLabelBase', 'PixmapLabel'
    }

    def make_transparent(w):
        w.setAutoFillBackground(False)
        w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        w.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        palette = w.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        w.setPalette(palette)
        current_style = w.styleSheet()
        if 'transparent' not in current_style.lower():
            w.setStyleSheet(current_style + " background: transparent; background-color: transparent;")

    for child in widget.findChildren(QLabel):
        make_transparent(child)
    for child in widget.findChildren(QWidget):
        if child.__class__.__name__ in label_class_names:
            make_transparent(child)
