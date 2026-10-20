"""
美股获取 Worker 线程

工作流:
1. 从 SEC EDGAR API 获取 CIK 对应的披露文件列表
2. 按用户选择的顺序排列
3. 逐条通过 send_to_ai 信号将文本发送给 WebEngine 内的 DeepSeek AI
4. 同步等待 AI 回答完成，保存到 results/

params 字段:
- CIK: "0001905956"（SEC CIK，最多10位数字）
- 开始日期: "2025-01-01"
- 结束日期: "2025-12-31"
- AI提示词: "总结这份 SEC 披露文件的主要内容"
- 发送顺序: "从晚到早" / "从早到晚"
"""

import os
from datetime import datetime
from .base_worker import BaseWorker
from .sec_client import fetch_sec_filings, format_date_cn, expand_filings_with_nested, export_us_excel
from .pdf_extractor import download_and_extract_pdf, is_pdf_url


class USWorker(BaseWorker):
    """美股获取 Worker"""

    def run(self):
        try:
            self._do_work()
            if self._is_running:
                self.finished_ok.emit()
        except Exception as e:
            self.log.emit("[ERROR] {}".format(str(e)))
            self.finished_error.emit(str(e))

    def _do_work(self):
        cik = self.params["CIK"].strip()
        dt_from = datetime.strptime(self.params["开始日期"], "%Y-%m-%d")
        dt_to = datetime.strptime(self.params["结束日期"], "%Y-%m-%d")
        prompt = self.params.get("AI提示词", "总结这份 SEC 披露文件的主要内容")
        order = self.params.get("发送顺序", "")

        self.log.emit("正在从 SEC EDGAR 获取 CIK {} 的文件...".format(cik))

        filings = fetch_sec_filings(
            cik,
            start_date=dt_from,
            end_date=dt_to,
            log_fn=lambda msg: self.log.emit(msg),
            progress_fn=lambda v: self.progress.emit(v),
            should_stop_fn=lambda: not self._is_running,
        )
        total = len(filings)
        if total == 0:
            self.log.emit("[WARN] 该时间段内没有找到符合条件的文件")
            return

        filings = expand_filings_with_nested(
            filings,
            log_fn=lambda msg: self.log.emit(msg),
            should_stop_fn=lambda: not self._is_running,
        )

        if order == "从晚到早":
            filings_list = list(filings)
            self.log.emit("发送顺序: 从晚到早（较早文件优先）")
        else:
            filings_list = list(reversed(filings))
            self.log.emit("发送顺序: 从早到晚（较新文件优先）")

        self.log.emit("=" * 50)
        self.log.emit("数据获取完毕，开始逐条发送给 AI 分析...")

        success_count = 0
        fail_count = 0
        self._result_list = []

        for idx, item in enumerate(filings_list):
            if not self._is_running:
                self.log.emit("[INFO] 已手动停止")
                break
            pct = int((idx + 1) / total * 50) + 50
            self.progress.emit(pct)

            date_cn = format_date_cn(item.get("date", ""))
            form_type = item.get("form", "")
            file_url = item.get("url", "")

            self.log.emit("\n[{}/{}] {}{} | {}".format(
                idx + 1, total, item.get("date", ""), form_type or "", file_url
            ))

            self.log.emit("[INFO] 正在下载并提取 PDF 内容...")
            # 构建完整上下文头部（与原脚本一致：日期+CIK+文件类型+URL）
            context_header = "日期：{}，CIK：{}，文件类型：{}".format(
                date_cn, cik, form_type
            )
            if is_pdf_url(file_url):
                pdf_text = download_and_extract_pdf(file_url)
                if pdf_text and pdf_text.strip():
                    self.log.emit("[OK] PDF 提取成功，{} 字符".format(len(pdf_text)))
                    ai_text = "{}\n提示词：{}\n内容：\n{}".format(
                        context_header, prompt, pdf_text
                    )
                else:
                    self.log.emit("[WARN] PDF 提取失败，降级发送原始链接")
                    ai_text = "{}\n提示词：{}\n链接：{}".format(
                        context_header, prompt, file_url
                    )
            else:
                self.log.emit("[INFO] HTML 文件，发送链接+上下文")
                ai_text = "{}\n提示词：{}\n链接：{}".format(
                    context_header, prompt, file_url
                )

            self.log.emit("[INFO] 正在发送给 AI...")
            self.send_to_ai.emit(ai_text)

            self.log.emit("[INFO] 等待 AI 回答...")
            ai_response = self.wait_for_ai_response(timeout_ms=300000)

            if ai_response:
                self.log.emit("[OK] 第 {} 条已完成，回答 {}".format(idx + 1, ai_response[:50]))
                success_count += 1
                self._result_list.append({
                    "日期": item.get("date", ""),
                    "CIK": cik,
                    "文件类型": item.get("form", ""),
                    "文件链接": item.get("url", ""),
                    "AI分析结果": ai_response,
                })
            else:
                self.log.emit("[FAIL] 第 {} 条失败，AI 未返回有效回答".format(idx + 1))
                fail_count += 1

        self.log.emit("全部完成: 成功 {}，失败 {}".format(success_count, fail_count))

        if self._result_list:
            self.log.emit("\n正在生成 Excel，共 {} 条记录...".format(len(self._result_list)))
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "results"
            )
            export_us_excel(self._result_list, output_dir, log_fn=lambda msg: self.log.emit(msg))
        else:
            self.log.emit("[WARN] 未获取到有效数据，Excel 未生成")

