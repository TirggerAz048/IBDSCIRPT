from PyQt6.QtCore import QThread, pyqtSignal, QEventLoop


class BaseWorker(QThread):
    """Worker 线程基类

    所有子类 Worker 必须遵守的规则:
    1. 接收 params 字典（来自面板的 _collect_params）
    2. 通过信号与主线程通信，禁止直接操作 UI
    3. 通过 self._is_running 控制停止

    信号:
    - log(str)              → 写日志（追加一行）
    - progress(int)         → 更新进度条（0~100）
    - finished_ok()         → 任务正常完成
    - finished_error(str)   → 任务异常结束，附带错误信息
    - send_to_ai(str)       → 请求将文本注入到 WebEngine 发送给 AI
    - ai_response_received(str) → AI 回答已收到（由 main_window 通过信号回调）
    """

    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal()
    finished_error = pyqtSignal(str)
    send_to_ai = pyqtSignal(str)
    ai_response_received = pyqtSignal(str)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.params = params
        self._is_running = True
        self._current_ai_response = ""
        self._ai_response_event = None

    def run(self):
        raise NotImplementedError("子类必须覆写此方法")

    def stop(self):
        self._is_running = False

    @property
    def is_task_running(self):
        return self._is_running

    def wait_for_ai_response(self, timeout_ms=300000):
        """阻塞等待 AI 回答完成

        由子类在 emit(send_to_ai) 之后调用，会阻塞当前线程直到
        main_window 通过 ai_response_received 信号返回回答内容。

        Args:
            timeout_ms: 超时时间（毫秒），默认 5 分钟

        Returns:
            str: AI 的回答文本，超时或停止返回空字符串
        """
        # 先断开可能存在的旧连接，防止重复连接导致 _on_response 被多次调用
        try:
            self.ai_response_received.disconnect(self._on_response)
        except (TypeError, RuntimeError):
            pass

        loop = QEventLoop()
        self._ai_response_event = loop
        self.ai_response_received.connect(self._on_response)

        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(timeout_ms)

        loop.exec()

        timer.stop()
        self.ai_response_received.disconnect(self._on_response)
        return self._current_ai_response

    def _on_response(self, text):
        self._current_ai_response = text
        self._ai_response_event.quit()
