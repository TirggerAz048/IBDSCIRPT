from .base_panel import BasePanel
from qfluentwidgets import (BodyLabel, StrongBodyLabel, LineEdit,
                            TextEdit, InfoBar, InfoBarPosition)
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtCore import Qt, QRegularExpression
import os
import sys
import subprocess
import calendar
from datetime import datetime, date, timedelta
from PyQt6.QtGui import QRegularExpressionValidator
from workers.ipo_worker import IpoWorker


class IpoPanel(BasePanel):
    """中概股 IPO - 侧边栏面板

    表单字段:
    - SEC Cookie: SEC EDGAR 访问用的 Cookie
    - IPO Cookie: NASDAQ IPO 日历访问用的 Cookie
    - 开始日期 / 结束日期: "YYYY-MM-DD"，默认当月，范围上限30天
    - 财务提示词 / 行业顾问提示词 / 法律顾问提示词
    """

    DEFAULT_PROMPT_FIN = '请从以下文本表格中提取财务数据：\n1. 找到“净收入”对应的行（可能标识为“REVENUE”、“Total revenue”、“Revenue”等也可能是其他字符），提取该行中最新年份（即表格中列出的最右侧年份列）的数值。\n2. 找到“净利润”对应的行（可能标识为“NET INCOME”、“NET (LOSS) INCOME”、“Net income”等也可能是其他字符），提取该行中最新年份的数值。\n3. 最新年份的判断依据：表格顶部有年份列头（如2025、2024），取最右侧（或数值最大的）年份作为最新年份。\n4. 如果获取到数据那么需要区分数据金额的币种货币符号，如$、¥、€、¥、CNY 等其他国家符号.'

    DEFAULT_PROMPT_IND = '请从以下文本中提取行业顾问的名字。\n1. 优先查找“prepared by”后面的内容，通常紧跟着人名或机构名（如“prepared by XXX”），提取XXX作为行业顾问。\n2. 如果没有找到“prepared by”，则寻找类似行业顾问的名称，例如出现在“industry consultant”、“advisor”、“prepared by”变体（如“prepared by:”、“Prepared By”等）后面的名字。\n'

    DEFAULT_PROMPT_LAW = '请分析以下法律文本并进行翻译翻译过后获取事务所名字 在对比原版文段后并提取原版文段其中的律师事务所信息对地区与事务所尽量准确些，事务所主要分为 开曼地区 BVI地区 香港地区 中国地区 其他地区 地区必须要中文。'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title("中概股 IPO")
        card, layout = self.add_card()
        layout.addWidget(StrongBodyLabel("网络配置"))
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("SEC Cookie:"))
        sec_cookie_edit = LineEdit()
        self.sec_cookie_edit = sec_cookie_edit
        sec_cookie_edit.setPlaceholderText("用于获取招股书")
        row.addStretch()
        row.addWidget(sec_cookie_edit, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("IPO Cookie:"))
        ipo_cookie_edit = LineEdit()
        self.ipo_cookie_edit = ipo_cookie_edit
        ipo_cookie_edit.setPlaceholderText("用于获取 IPO 日历")
        row.addStretch()
        row.addWidget(ipo_cookie_edit, 1)
        layout.addLayout(row)
        # 开始日期
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("开始日期:"))
        start_edit = LineEdit()
        self.start_edit = start_edit
        start_edit.setPlaceholderText("YYYY-MM-DD")
        start_edit.setMaxLength(10)
        date_regex = QRegularExpression(r"^\d{0,4}(-\d{0,2}(-\d{0,2})?)?$")
        start_edit.setValidator(QRegularExpressionValidator(date_regex))
        row.addStretch()
        row.addWidget(start_edit, 1)
        layout.addLayout(row)
        # 结束日期
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("结束日期:"))
        end_edit = LineEdit()
        self.end_edit = end_edit
        end_edit.setPlaceholderText("YYYY-MM-DD")
        end_edit.setMaxLength(10)
        end_edit.setValidator(QRegularExpressionValidator(date_regex))
        row.addStretch()
        row.addWidget(end_edit, 1)
        layout.addLayout(row)
        layout.addWidget(StrongBodyLabel("财务提示词"))
        prompt_fin_edit = TextEdit()
        self.prompt_fin_edit = prompt_fin_edit
        prompt_fin_edit.setFixedHeight(120)
        prompt_fin_edit.setText(self.DEFAULT_PROMPT_FIN)
        layout.addWidget(prompt_fin_edit)
        layout.addWidget(StrongBodyLabel("行业顾问提示词"))
        prompt_ind_edit = TextEdit()
        self.prompt_ind_edit = prompt_ind_edit
        prompt_ind_edit.setFixedHeight(100)
        prompt_ind_edit.setText(self.DEFAULT_PROMPT_IND)
        layout.addWidget(prompt_ind_edit)
        layout.addWidget(StrongBodyLabel("法律顾问提示词"))
        prompt_law_edit = TextEdit()
        self.prompt_law_edit = prompt_law_edit
        prompt_law_edit.setFixedHeight(80)
        prompt_law_edit.setText(self.DEFAULT_PROMPT_LAW)
        layout.addWidget(prompt_law_edit)
        self.start_btn, self.stop_btn = self.add_action_buttons()
        self.progress = self.add_progress_bar()
        self.end_of_form()
        self.log_card, self.log_edit = self.add_log_card()
        # 默认开始日期：当月1号，结束日期留空（非必填）
        today = date.today()
        self.start_edit.setText(today.replace(day=1).strftime("%Y-%m-%d"))

    def _get_task_name(self):
        return "中概股 IPO"

    def _get_worker_class(self):
        return IpoWorker

    def _collect_params(self):
        start_text = self.start_edit.text().strip()
        end_text = self.end_edit.text().strip()

        # ── 验证开始日期（必填） ──
        if len(start_text) != 10:
            InfoBar.error(
                title="开始日期",
                content="请填写开始日期 (YYYY-MM-DD)",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None

        try:
            dt_start = datetime.strptime(start_text, "%Y-%m-%d")
        except ValueError:
            InfoBar.error(
                title="开始日期",
                content="开始日期格式无效，请输入正确的年月日",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None

        # ── 处理结束日期（非必填） ──
        if not end_text or len(end_text) != 10:
            # 未填结束日期 → 自动补全为该月1号 ~ 最后一天
            _, last_day = calendar.monthrange(dt_start.year, dt_start.month)
            dt_start = dt_start.replace(day=1)
            dt_end = dt_start.replace(day=last_day)
            self.start_edit.setText(dt_start.strftime("%Y-%m-%d"))
            self.end_edit.setText(dt_end.strftime("%Y-%m-%d"))
        else:
            try:
                dt_end = datetime.strptime(end_text, "%Y-%m-%d")
            except ValueError:
                InfoBar.error(
                    title="结束日期",
                    content="结束日期格式无效，请输入 YYYY-MM-DD 或留空",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return None

        # ── 开始 ≤ 结束 ──
        if dt_start > dt_end:
            InfoBar.error(
                title="日期范围",
                content="开始日期不能晚于结束日期，请重新输入",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None

        # ── 超出1个月自动截断 ──
        if (dt_end - dt_start).days > 30:
            dt_end = dt_start + timedelta(days=30)
            self.end_edit.setText(dt_end.strftime("%Y-%m-%d"))
            InfoBar.warning(
                title="日期范围",
                content="日期范围超过30天，已自动调整为1个月",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            # 不 return，继续执行

        return {
            "SEC Cookie": self.sec_cookie_edit.text().strip(),
            "IPO Cookie": self.ipo_cookie_edit.text().strip(),
            "开始日期": dt_start.strftime("%Y-%m-%d"),
            "结束日期": dt_end.strftime("%Y-%m-%d"),
            "财务提示词": self.prompt_fin_edit.toPlainText(),
            "行业顾问提示词": self.prompt_ind_edit.toPlainText(),
            "法律顾问提示词": self.prompt_law_edit.toPlainText()
        }

    def _on_worker_finished(self):
        super()._on_worker_finished()
        if hasattr(self, '_worker') and hasattr(self._worker, 'output_filepath'):
            filepath = getattr(self._worker, 'output_filepath', '')
            if filepath and os.path.exists(filepath):
                folder = os.path.dirname(filepath)
                self.log_edit.append(f"[INFO] 正在打开文件夹: {folder}")
                try:
                    if sys.platform == "win32":
                        subprocess.run(["explorer", "/select,", filepath], check=False)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", "-R", filepath], check=False)
                    else:
                        subprocess.run(["xdg-open", folder], check=False)
                except Exception as e:
                    self.log_edit.append(f"[WARN] 打开文件夹失败: {e}")
