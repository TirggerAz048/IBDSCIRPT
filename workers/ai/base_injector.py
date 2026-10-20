"""
AI 注入器基类

封装通用的「注入 → 轮询 → 稳定判断 → 回传」流程。
所有具体的注入器（DeepSeek、IPO 等）继承此类，只需实现：
- _build_send_js(text) → 返回注入发送的 JS 代码字符串
- _build_poll_js()    → 返回轮询 AI 回答的 JS 代码字符串
- _parse_poll_result(raw) → 解析轮询 JS 返回值，返回 (found, text) 元组
"""
import json
from PyQt6.QtCore import QObject, QTimer


class BaseInjector(QObject):
    """AI 注入器基类

    通用职责:
    - 管理 QTimer 轮询定时器
    - 快照对比 + 稳定计数
    - 判定 AI 回答完成后通过回调通知外部
    - 状态栏文本更新

    子类职责:
    - 提供 JS 注入代码
    - 解析轮询返回值
    """

    POLL_INTERVAL_MS = 1000
    POLL_INTERVAL_MS_AFTER = 1500
    STABLE_THRESHOLD = 5
    MIN_RESPONSE_LEN = 400
    DEFAULT_TIMEOUT_MS = 300000

    def __init__(self, web_view, status_label=None, parent=None):
        super().__init__(parent)
        self.web_view = web_view
        self.status_label = status_label

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._on_poll_tick)

        self._polling = False
        self._poll_stable_count = 0
        self._poll_last_snapshot = ""
        self._poll_total_count = 0        # 总轮询次数（诊断用）
        self._callback = None

    def send(self, text, callback):
        """发送文本给 AI 并启动轮询

        Args:
            text: 要发送的文本
            callback: 完成回调 callback(response_text: str)
        """
        self._callback = callback
        self._poll_stable_count = 0
        self._poll_last_snapshot = ""
        self._poll_total_count = 0
        self._poll_timer.setInterval(self.POLL_INTERVAL_MS)

        js_code = self._build_send_js(text)
        self.web_view.page().runJavaScript(js_code, 0, self._on_send_result)

    def stop(self):
        """停止轮询（用户点停止时调用）"""
        self._polling = False
        self._poll_timer.stop()
        self._poll_total_count = 0
        self._notify_complete("")

    def _build_send_js(self, text):
        """构造注入发送的 JS 代码

        子类必须实现。返回的 JS 代码应:
        - 找到输入框并填入 text
        - 触发发送
        - return 'OK' 表示成功，或 return 'INPUT_NOT_FOUND' 等错误标记

        Args:
            text: 已转义的文本（子类按需再次转义）

        Returns:
            str: 可执行的 JS 代码字符串
        """
        raise NotImplementedError

    def _build_poll_js(self):
        """构造轮询 AI 回答的 JS 代码

        子类必须实现。返回的 JS 代码应:
        - 获取最后一个 AI 回答的文本
        - return JSON.stringify({found: bool, text: str, len: int})
        - 注意：DeepSeek 使用 CSS Modules，需用属性选择器 [class*="key"] 而非 .class 选择器

        Returns:
            str: 可执行的 JS 代码字符串
        """
        raise NotImplementedError

    def _parse_poll_result(self, raw):
        """解析轮询 JS 的返回值

        Args:
            raw: runJavaScript 的回调参数

        Returns:
            (found: bool, text: str) 元组
        """
        raise NotImplementedError

    def _on_send_result(self, result):
        """JS 注入发送结果回调"""
        if result == "INPUT_NOT_FOUND":
            self._set_status("❌ 未找到输入框 — 请确认 DeepSeek 页面已加载并已登录")
            self._notify_complete("")
        elif result == "OK":
            self._set_status("已发送，等待 AI 回答...")
            self._poll_stable_count = 0
            self._poll_last_snapshot = ""
            self._poll_total_count = 0
            self._polling = True
            self._poll_timer.setInterval(self.POLL_INTERVAL_MS)
            self._poll_timer.start()
        elif result is None:
            # runJavaScript 回调返回 None 通常表示 JS 执行异常或页面未就绪
            self._set_status("❌ JS 注入失败 (None) — 页面可能未完全加载")
            self._notify_complete("")
        else:
            self._set_status("❌ JS 注入异常: " + str(result))
            self._notify_complete("")

    def _on_poll_tick(self):
        """QTimer 定时回调：执行轮询 JS"""
        if not self._polling:
            return
        js_code = self._build_poll_js()
        self.web_view.page().runJavaScript(js_code, 0, self._on_poll_result)

    def _on_poll_result(self, raw):
        """轮询 JS 返回值处理

        两阶段策略:
        - 长度 < MIN_RESPONSE_LEN: 只更新快照，不做稳定判断（AI 还在写开头）
        - 长度 >= MIN_RESPONSE_LEN: 切换到慢速间隔，连续 STABLE_THRESHOLD 次不变 → 完成
        """
        self._poll_total_count += 1

        if not raw:
            # 每 20 次空轮询才报一次状态（避免刷屏）
            if self._poll_total_count % 20 == 0:
                self._set_status(
                    "等待 AI 回答... (已轮询 " + str(self._poll_total_count) +
                    " 次，未找到消息元素 — 确认 DeepSeek 页面是否正常)"
                )
            return

        found, text = self._parse_poll_result(raw)
        length = len(text)

        if not found or length == 0:
            self._poll_stable_count = 0
            self._poll_last_snapshot = ""
            if self._poll_total_count % 10 == 0:
                self._set_status(
                    "等待 AI 回答... (已轮询 " + str(self._poll_total_count) +
                    " 次，消息为空)"
                )
            return

        # 首次找到有效内容
        if self._poll_total_count <= 2:
            self._set_status("检测到 AI 回复开始生成 (" + str(length) + " 字符)...")

        if length < self.MIN_RESPONSE_LEN:
            self._poll_stable_count = 0
            self._poll_last_snapshot = text
            self._set_status("AI 正在生成... (" + str(length) + "/" + str(self.MIN_RESPONSE_LEN) + " 字符, 轮询 #" + str(self._poll_total_count) + ")")
            return

        if self._poll_timer.interval() < self.POLL_INTERVAL_MS_AFTER:
            self._poll_timer.setInterval(self.POLL_INTERVAL_MS_AFTER)

        if text == self._poll_last_snapshot:
            self._poll_stable_count += 1
            self._set_status(
                "AI 回答中... 稳定 " + str(self._poll_stable_count) + "/" + str(self.STABLE_THRESHOLD) + "次 ("
                + str(length) + " 字符, 轮询 #" + str(self._poll_total_count) + ")"
            )
            if self._poll_stable_count >= self.STABLE_THRESHOLD:
                self._polling = False
                self._poll_timer.stop()
                self._set_status("✅ AI 回答完成 (" + str(length) + " 字符, 共轮询 " + str(self._poll_total_count) + " 次)")
                self._notify_complete(text)
        else:
            self._poll_stable_count = 0
            self._poll_last_snapshot = text
            self._set_status("AI 正在生成... (" + str(length) + " 字符, 轮询 #" + str(self._poll_total_count) + ")")

    def _notify_complete(self, text):
        """通知外部 AI 回答完成"""
        if self._callback:
            self._callback(text)
            self._callback = None

    def _set_status(self, text):
        """更新状态栏"""
        if self.status_label:
            self.status_label.setText(text)
