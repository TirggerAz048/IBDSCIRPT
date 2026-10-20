from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QSizePolicy
from qfluentwidgets import (StrongBodyLabel, ProgressBar, PushButton,
                            PrimaryPushButton, TextEdit, CardWidget,
                            CaptionLabel, SmoothScrollArea)


class BasePanel(QWidget):
    ai_response_received = None

    def __init__(self, parent=None):
        super().__init__(parent)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        _scroll_area = SmoothScrollArea()
        self._scroll_area = _scroll_area
        _scroll_area.setWidgetResizable(True)
        _scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        _scroll_content = QWidget()
        self._scroll_content = _scroll_content
        _form_layout = QVBoxLayout(_scroll_content)
        self._form_layout = _form_layout
        _scroll_area.setWidget(_scroll_content)
        root_layout.addWidget(_scroll_area)
        _log_container = CardWidget()
        self._log_container = _log_container
        _log_layout = QVBoxLayout(_log_container)
        self._log_layout = _log_layout
        root_layout.addWidget(_log_container, 1)

    def _collect_params(self):
        return None

    def _get_task_name(self):
        return "任务"

    def _get_worker_class(self):
        raise NotImplementedError

    def add_title(self, text):
        title = StrongBodyLabel(text)
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px 0;")
        self._form_layout.addWidget(title)
        return title

    def add_card(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        self._form_layout.addWidget(card)
        return card, layout

    def add_progress_bar(self):
        bar = ProgressBar()
        self._form_layout.addWidget(bar)
        return bar

    def add_action_buttons(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        start_btn = PrimaryPushButton("开始")
        start_btn.setFixedHeight(40)
        start_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stop_btn = PushButton("停止")
        stop_btn.setFixedHeight(40)
        stop_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stop_btn.setEnabled(False)
        right_spacer = QWidget()
        right_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(left_spacer, 1)
        row.addWidget(start_btn, 4)
        row.addWidget(stop_btn, 4)
        row.addWidget(right_spacer, 1)
        self._form_layout.addLayout(row)
        start_btn.clicked.connect(self._on_start)
        stop_btn.clicked.connect(self._on_stop)
        return start_btn, stop_btn

    def add_log_card(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 6, 12, 8)
        layout.setSpacing(4)
        log_title = StrongBodyLabel("日志")
        log_title.setStyleSheet("font-size: 13px;")
        layout.addWidget(log_title)
        log_edit = TextEdit()
        log_edit.setReadOnly(True)
        log_edit.setFixedHeight(240)
        log_edit.setStyleSheet("font-size: 12px; font-family: Consolas, 'Courier New', monospace;background: #1e1e1e; color: #d4d4d4; border: none;")
        layout.addWidget(log_edit)
        self._log_layout.addWidget(card)
        return card, log_edit

    def end_of_form(self):
        self._form_layout.addStretch()

    def _on_start(self):
        self.log_edit.clear()
        self.progress.setValue(0)
        params = self._collect_params()
        if params is None:
            return
        task_name = self._get_task_name()
        self.log_edit.append(f"[INFO] {task_name} 开始执行")
        for key, value in params.items():
            self.log_edit.append(f"  {key}: {value}")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        worker_class = self._get_worker_class()
        if worker_class is None:
            self.log_edit.append("[WARN] 该任务暂未配置 Worker")
            self.reset_buttons()
            return
        self._worker = worker_class(params)
        main_win = self.window()
        self._worker.log.connect(lambda msg: self.log_edit.append(msg))
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished_ok.connect(self._on_worker_finished)
        self._worker.finished_error.connect(self._on_worker_error)
        if hasattr(self._worker, 'send_to_ai') and hasattr(main_win, 'on_send_to_ai'):
            self._worker.send_to_ai.connect(main_win.on_send_to_ai)
        if hasattr(main_win, '_current_worker'):
            main_win._current_worker = self._worker
        if hasattr(self._worker, 'ai_response_received') and hasattr(main_win, 'ai_response_received'):
            try:
                main_win.ai_response_received.connect(self._worker.ai_response_received)
            except Exception:
                pass
        try:
            self._worker.start()
            if hasattr(main_win, 'lock_all_panels'):
                main_win.lock_all_panels(self)
            self.log_edit.append("[INFO] Worker 线程已启动")
        except Exception:
            pass

    def _on_stop(self):
        self.log_edit.append("[INFO] 正在停止...")
        main_win = self.window()
        if hasattr(main_win, 'stop_injector'):
            try:
                main_win.stop_injector()
            except Exception:
                pass
        if hasattr(self, '_worker') and self._worker.isRunning():
            self._worker.stop()
            self._worker.ai_response_received.emit("")
            self._worker.quit()
            self._worker.wait(3000)
        self.reset_buttons()
        if hasattr(main_win, 'unlock_all_panels'):
            main_win.unlock_all_panels()
        self.log_edit.append("[INFO] 已停止")

    def _on_worker_finished(self):
        self._cleanup_injector()
        self.progress.setValue(100)
        self.log_edit.append("[INFO] 任务完成")
        self.reset_buttons()
        main_win = self.window()
        if hasattr(main_win, 'unlock_all_panels'):
            try:
                main_win.unlock_all_panels()
            except Exception:
                pass

    def _on_worker_error(self, msg):
        self._cleanup_injector()
        self.log_edit.append(f"[ERROR] 任务异常: {msg}")
        self.reset_buttons()
        main_win = self.window()
        if hasattr(main_win, 'unlock_all_panels'):
            try:
                main_win.unlock_all_panels()
            except Exception:
                pass

    def _cleanup_injector(self):
        main_win = self.window()
        if hasattr(main_win, 'stop_injector'):
            try:
                main_win.stop_injector()
            except Exception:
                pass

    def lock_controls(self, keep_stop_enabled=False):
        for widget in self._scroll_content.findChildren(QWidget):
            widget.setEnabled(False)
        if keep_stop_enabled and hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(True)

    def unlock_controls(self):
        for widget in self._scroll_content.findChildren(QWidget):
            widget.setEnabled(True)
        self.reset_buttons()

    def reset_buttons(self):
        if hasattr(self, 'start_btn'):
            self.start_btn.setEnabled(True)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(False)
