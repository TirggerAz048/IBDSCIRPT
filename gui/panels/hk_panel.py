from gui.panels.base_panel import BasePanel
from qfluentwidgets import (BodyLabel, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, InfoBar, InfoBarPosition)
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from workers.hk_worker import HKWorker


class HKPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title("港股获取")
        card, layout = self.add_card()
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("股票代码:"))
        code_edit = LineEdit()
        self.code_edit = code_edit
        code_edit.setPlaceholderText("如 00700")
        code_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,5}$")))
        row.addStretch()
        row.addWidget(code_edit, 1)
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
        self.code_edit.setText("01011")
        self.start_edit.setText("2026-04-25")
        self.end_edit.setText("2026-05-25")
        self.prompt_edit.setText("请查看这份文档 并总结的主要内容")

    def _get_task_name(self):
        return "港股获取"

    def _get_worker_class(self):
        return HKWorker

    def _collect_params(self):
        print("[INFO] 获取参数")
        code = self.code_edit.text().strip()
        if len(code) != 5:
            InfoBar.error(
                title="错误",
                content="请输入5位股票代码",
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
            "股票代码": code,
            "开始日期": start,
            "结束日期": end,
            "AI提示词": prompt,
            "发送顺序": order
        }
