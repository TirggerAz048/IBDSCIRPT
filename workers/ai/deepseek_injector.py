"""
DeepSeek AI 注入器（港股 + 美股共用）

通过 JS 注入操作 chat.deepseek.com 页面：
- 找 textarea 输入框（placeholder 选择器 + contenteditable 备选）
- React 兼容填入文本（nativeInputValueSetter + dispatch InputEvent）
- 触发发送（找发送按钮或模拟 Enter）
- 轮询 .ds-message 消息容器[-1] 判断 AI 回答完成

用法:
    injector = DeepSeekInjector(web_view, status_label)
    injector.send(text, callback=on_complete)
"""
import json
from .base_injector import BaseInjector


class DeepSeekInjector(BaseInjector):
    """DeepSeek 注入器 — 继承通用轮询流程，只实现 JS 代码部分"""

    def _build_send_js(self, text):
        """构造 DeepSeek 发送 JS 代码

        流程：填入文本 → dispatch InputEvent 触发 React onChange →
        setTimeout 600ms 等待 React 更新状态（开启发送按钮）→ 点击发送
        模仿 Selenium 原版的 time.sleep(0.6) 延迟。
        """
        escaped = (
            text.replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", "")
        )

        return """
        (function() {
            // 找到 DeepSeek 输入框
            var textarea = document.querySelector('textarea[placeholder="给 DeepSeek 发送消息 "]');
            if (!textarea) {
                // 备选：contenteditable div
                textarea = document.querySelector('[contenteditable="true"][data-placeholder]');
            }
            if (!textarea) {
                return 'INPUT_NOT_FOUND';
            }

            // React 兼容：设置 value 并 dispatch InputEvent
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

            // dispatch InputEvent（React 16+ 使用 input 事件）
            var event = new InputEvent('input', {
                bubbles: true, cancelable: true, inputType: 'insertText', data: '""" + escaped + """'
            });
            textarea.dispatchEvent(event);
            textarea.focus();

            // 延迟 600ms 后触发发送（等待 React 状态更新，模仿 Selenium 原版 time.sleep(0.6)）
            setTimeout(function() {
                var sendBtn = document.querySelector('button[data-testid="send-button"]')
                           || document.querySelector('div[class*="send"]')
                           || document.querySelector('button[class*="send"]');
                // 如果按钮存在且未禁用（React 已更新状态），点击发送
                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                } else {
                    // 备选：直接在 textarea 上模拟 Enter 键
                    var enterEvent = new KeyboardEvent('keydown', {
                        key: 'Enter', code: 'Enter', keyCode: 13,
                        bubbles: true, cancelable: true
                    });
                    textarea.dispatchEvent(enterEvent);
                }
            }, 600);

            return 'OK';
        })();
        """

    def _build_poll_js(self):
        """构造轮询 AI 回答的 JS 代码

        策略：取所有 [class*="ds-message"] 消息容器，只读最后一项的 innerText。
        DeepSeek 使用 CSS Modules，实际 class 是 ds-message_a1b2c3（带 hash），
        必须用属性包含选择器 [class*="ds-message"] 而非类选择器 .ds-message。
        等价于 Selenium 原版的 find_elements(By.CSS_SELECTOR, '.ds-message[class*="_"]')[-1].text。
        多轮对话不会串联历史，干净准确。
        """
        return """
        (function() {
            // [class*="ds-message"] 匹配 CSS Modules 类名如 ds-message_a1b2c3
            var messages = document.querySelectorAll('[class*="ds-message"]');
            if (!messages || messages.length === 0) {
                return JSON.stringify({found: false, text: '', len: 0});
            }

            // 只取最后一条消息（当前这轮 AI 回答）
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
