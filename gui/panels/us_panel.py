from .base_panel import BasePanel
from qfluentwidgets import (BodyLabel, LineEdit, ComboBox,
                            TextEdit, InfoBar, InfoBarPosition)
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from workers.us_worker import USWorker


class USPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title("美股获取")
        card, layout = self.add_card()
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("CIK:"))
        cik_edit = LineEdit()
        self.cik_edit = cik_edit
        cik_edit.setPlaceholderText("如 0001318605")
        cik_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,10}$")))
        row.addStretch()
        row.addWidget(cik_edit, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("开始日期:"))
        start_edit = LineEdit()
        self.start_edit = start_edit
        start_edit.setPlaceholderText("YYYY-MM-DD")
        start_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}(-\d{0,2}(-\d{0,2})?)?$")))
        row.addStretch()
        row.addWidget(start_edit, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("结束日期:"))
        end_edit = LineEdit()
        self.end_edit = end_edit
        end_edit.setPlaceholderText("YYYY-MM-DD")
        end_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}(-\d{0,2}(-\d{0,2})?)?$")))
        row.addStretch()
        row.addWidget(end_edit, 1)
        layout.addLayout(row)
        layout.addWidget(BodyLabel("AI 提示词:"))
        prompt_edit = TextEdit()
        self.prompt_edit = prompt_edit
        prompt_edit.setFixedHeight(100)
        prompt_edit.setPlaceholderText("输入提示词，{title} {date} 等为占位符")
        layout.addWidget(prompt_edit)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("发送顺序:"))
        order_combo = ComboBox()
        self.order_combo = order_combo
        order_combo.addItems(["从晚到早", "从早到晚"])
        row.addStretch()
        row.addWidget(order_combo, 1)
        layout.addLayout(row)
        self.start_btn, self.stop_btn = self.add_action_buttons()
        self.progress = self.add_progress_bar()
        self.end_of_form()
        self.log_card, self.log_edit = self.add_log_card()
        self.cik_edit.setText("0002066836")
        self.start_edit.setText("2026-04-25")
        self.end_edit.setText("2026-05-25")
        self.prompt_edit.setText("总结这份纳斯达克披露文件的主要内容")

    def _get_task_name(self):
        return "美股获取"

    def _get_worker_class(self):
        return USWorker

    def _collect_params(self):
        cik = self.cik_edit.text().strip()
        if not cik:
            InfoBar.error(
                title="错误",
                content="请输入 CIK",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None
        start = self.start_edit.text().strip()
        end = self.end_edit.text().strip()
        prompt = self.prompt_edit.toPlainText()
        order = self.order_combo.currentText()
        if len(start) != 10:
            InfoBar.error(
                title="错误",
                content="请输入正确的开始日期（YYYY-MM-DD）",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None
        if len(end) != 10:
            InfoBar.error(
                title="错误",
                content="请输入正确的结束日期（YYYY-MM-DD）",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None
        return {
            "CIK": cik,
            "开始日期": start,
            "结束日期": end,
            "AI提示词": prompt,
            "发送顺序": order
        }
