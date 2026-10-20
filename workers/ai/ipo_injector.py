"""
DeepSeek AI 注入器（IPO 专用）

与港股/美股共用的 DeepSeekInjector 的差异：
- 没有最小响应长度阈值（MIN_RESPONSE_LEN = 0）
  → IPO 的 AI 回复可能是短 JSON（如 ["无"]），不适用 400 字符门槛
- 轮询间隔 500ms，与原脚本 SecPythonWebCrawler time.sleep(0.5) 完全一致
- 稳定判断 5 次，与原脚本 unchanged_count >= 5 完全一致
- 不做两阶段间隔切换（原脚本始终 0.5s）
- 超时 30 秒，与原脚本 60次×0.5秒=30s 完全一致

JS 注入代码与 DeepSeekInjector 完全一致，仅轮询判定策略不同。
"""
import json
from .base_injector import BaseInjector


class IpoInjector(BaseInjector):
    """IPO 专用注入器 — 无最小长度阈值，快速稳定判定"""

    POLL_INTERVAL_MS = 500
    POLL_INTERVAL_MS_AFTER = 500
    STABLE_THRESHOLD = 5
    MIN_RESPONSE_LEN = 0
    DEFAULT_TIMEOUT_MS = 30000

    def _build_send_js(self, text):
        """构造 DeepSeek 发送 JS 代码（与 DeepSeekInjector 完全一致）

        流程：填入文本 → dispatch InputEvent 触发 React onChange →
        setTimeout 600ms → 点击发送
        """
        escaped = (
            text.replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", "")
        )

        return """
        (function() {
            var textarea = document.querySelector('textarea[placeholder="给 DeepSeek 发送消息 "]');
            if (!textarea) {
                textarea = document.querySelector('[contenteditable="true"][data-placeholder]');
            }
            if (!textarea) {
                return 'INPUT_NOT_FOUND';
            }

            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            )?.set || Object.getOwnPropertyDescriptor(
                window.HTMLDivElement.prototype, 'innerText'
            )?.set;

            if (nativeInputValueSetter) {
                nativeInputValueSetter.call(textarea, '""" + escaped + """');
            } else {
                textarea.value = '""" + escaped + """';
            }

            var event = new InputEvent('input', {
                bubbles: true, cancelable: true, inputType: 'insertText', data: '""" + escaped + """'
            });
            textarea.dispatchEvent(event);
            textarea.focus();

            // 延迟 600ms 后触发发送（等待 React 状态更新）
            setTimeout(function() {
                var sendBtn = document.querySelector('button[data-testid="send-button"]')
                           || document.querySelector('div[class*="send"]')
                           || document.querySelector('button[class*="send"]');
                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                } else {
                    var enterEvent = new KeyboardEvent('keydown', {
                        key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true
                    });
                    textarea.dispatchEvent(enterEvent);
                }
            }, 600);

            return 'OK';
        })();
        """

    def _build_poll_js(self):
        """构造轮询 AI 回答的 JS 代码（与 DeepSeekInjector 完全一致）"""
        return """
        (function() {
            // [class*="ds-message"] 匹配 CSS Modules 类名如 ds-message_a1b2c3
            var messages = document.querySelectorAll('[class*="ds-message"]');
            if (!messages || messages.length === 0) {
                return JSON.stringify({found: false, text: '', len: 0});
            }
            var last = messages[messages.length - 1];
            var text = last.innerText || last.textContent || '';
            return JSON.stringify({found: true, text: text, len: text.length});
        })();
        """

    def _parse_poll_result(self, raw):
        """解析轮询 JS 的返回值"""
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            return (False, "")
        return (
            data.get("found", False),
            data.get("text", ""),
        )
