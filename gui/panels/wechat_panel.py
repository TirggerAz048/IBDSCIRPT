"""wechat_panel.py — 公众号数据导出面板

与港股/美股面板的差异：
  1. 不需要 AI 提示词，不连接 send_to_ai 信号
  2. 点击"开始"时先通过 JS 提取内嵌浏览器的划线数据，再启动 Worker
  3. 输出为 Excel 文件而非文本
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from .base_panel import BasePanel
from qfluentwidgets import (BodyLabel, StrongBodyLabel, LineEdit,
                            PasswordLineEdit, InfoBar, InfoBarPosition)
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from workers.wechat_worker import WechatWorker
from workers.wechat_extract import extract_underline_js


class WechatPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title("公众号获取")
        card, layout = self.add_card()
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("AppID:"))
        appid_edit = LineEdit()
        self.appid_edit = appid_edit
        appid_edit.setPlaceholderText("公众号 AppID")
        row.addStretch()
        row.addWidget(appid_edit, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("AppSecret:"))
        secret_edit = PasswordLineEdit()
        self.secret_edit = secret_edit
        secret_edit.setPlaceholderText("公众号 AppSecret")
        row.addStretch()
        row.addWidget(secret_edit, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("开始日期:"))
        start_edit = LineEdit()
        self.start_edit = start_edit
        start_edit.setPlaceholderText("YYYY-MM-DD")
        date_regex = QRegularExpression(r"^\d{0,4}(-\d{0,2}(-\d{0,2})?)?$")
        start_edit.setValidator(QRegularExpressionValidator(date_regex))
        row.addStretch()
        row.addWidget(start_edit, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(BodyLabel("结束日期:"))
        end_edit = LineEdit()
        self.end_edit = end_edit
        end_edit.setPlaceholderText("YYYY-MM-DD")
        end_edit.setValidator(QRegularExpressionValidator(date_regex))
        row.addStretch()
        row.addWidget(end_edit, 1)
        layout.addLayout(row)
        self._underline_data = None
        self.start_btn, self.stop_btn = self.add_action_buttons()
        self.progress = self.add_progress_bar()
        self.end_of_form()
        self.log_card, self.log_edit = self.add_log_card()
        self.appid_edit.setText("wxfb76ae29a47595f8")
        self.secret_edit.setText("b0448f69cb4d9b4d5e0127b10be6b113")
        # 默认日期：开始=7天前，结束=今天
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        self.start_edit.setText(seven_days_ago)
        self.end_edit.setText(today)

    def _get_task_name(self):
        return "公众号导出"

    def _get_worker_class(self):
        return WechatWorker

    def _collect_params(self):
        appid = self.appid_edit.text().strip()
        if not appid:
            InfoBar.error(
                title="错误",
                content="请输入 AppID",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None
        secret = self.secret_edit.text().strip()
        if not secret:
            InfoBar.error(
                title="错误",
                content="请输入 AppSecret",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return None
        start = self.start_edit.text().strip()
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
        end = self.end_edit.text().strip()
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
            "AppID": appid,
            "AppSecret": secret,
            "开始日期": start,
            "结束日期": end,
            "划线数据": self._underline_data
        }

    def _on_start(self):
        self.log_edit.clear()
        self.progress.setValue(0)
        appid = self.appid_edit.text().strip()
        secret = self.secret_edit.text().strip()
        start = self.start_edit.text().strip()
        end = self.end_edit.text().strip()
        if not all([appid, secret, start, end]):
            InfoBar.error(
                title="错误",
                content="请填写完整所有参数",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_edit.append("[INFO] 正在提取划线数据...")
        main_win = self.window()
        if hasattr(main_win, '_underline_data'):
            self._underline_data = main_win._underline_data
            self._start_worker()
        elif hasattr(main_win, 'run_js'):
            try:
                main_win.run_js(extract_underline_js(), self._on_underline_extracted)
            except Exception as e:
                self.log_edit.append(f"[WARN] 划线提取异常: {e}，跳过")
                self._start_worker()
        else:
            self.log_edit.append("[WARN] 无法提取划线数据，跳过")
            self._start_worker()

    def _on_underline_extracted(self, result):
        try:
            if isinstance(result, str):
                data = json.loads(result)
                if isinstance(data, list):
                    self._underline_data = data
                    self.log_edit.append(f"[OK] 划线数据提取成功，{len(data)} 条")
                else:
                    self.log_edit.append("[WARN] 划线数据格式异常，跳过")
            else:
                self.log_edit.append("[INFO] 未提取到划线数据（可能未在已发布页面）")
        except (json.JSONDecodeError, TypeError) as e:
            self.log_edit.append(f"[WARN] 划线数据解析失败: {e}，跳过")
        self._start_worker()

    def _start_worker(self):
        params = self._collect_params()
        if params is None:
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        task_name = self._get_task_name()
        self.log_edit.append(f"[INFO] {task_name} 开始执行")
        self.log_edit.append(f"  AppID: {params.get('AppID', '')}")
        self.log_edit.append(f"  日期: {params.get('开始日期', '')} ~ {params.get('结束日期', '')}")
        self.log_edit.append(f"  划线数据: {len(params.get('划线数据') or [])} 条")
        worker_class = self._get_worker_class()
        if worker_class is None:
            self.log_edit.append("[WARN] 该任务暂未配置 Worker")
            return
        self._worker = worker_class(params)
        self._worker.log.connect(lambda msg: self.log_edit.append(msg))
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished_ok.connect(self._on_worker_finished)
        self._worker.finished_error.connect(self._on_worker_error)
        main_win = self.window()
        if hasattr(self._worker, 'send_to_ai') and hasattr(main_win, 'on_send_to_ai'):
            self._worker.send_to_ai.connect(main_win.on_send_to_ai)
        if hasattr(main_win, '_current_worker'):
            main_win._current_worker = self._worker
        try:
            self._worker.start()
            main_win = self.window()
            if hasattr(main_win, 'lock_all_panels'):
                main_win.lock_all_panels(self)
            self.log_edit.append("[INFO] Worker 线程已启动")
        except Exception:
            pass

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
