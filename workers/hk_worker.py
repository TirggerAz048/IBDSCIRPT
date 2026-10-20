"""
港股获取 Worker 线程

工作流:
1. 获取 stockId（通过 HKEX API）
2. 按月分块抓取披露文件列表
3. 按用户选择的顺序排列
4. 逐条通过 send_to_ai 信号将文本发送给 WebEngine 内的 DeepSeek AI

params 字段:
- 股票代码: "00700"
- 开始日期: "2025-01-01"
- 结束日期: "2025-06-01"
- AI提示词: "总结这份港交所披露文件的主要内容"
- 发送顺序: "从晚到早" / "从早到晚"
"""

import os
from datetime import datetime
from .base_worker import BaseWorker
from .hkex_client import create_session, get_stock_id, fetch_hkex_filings, format_date_cn, export_hk_excel
from .pdf_extractor import download_and_extract_pdf


class HKWorker(BaseWorker):
    """港股获取 Worker"""

    def run(self):
        try:
            self._do_work()
            if self._is_running:
                self.finished_ok.emit()
        except Exception as e:
            self.log.emit("[ERROR] {}".format(str(e)))
            self.finished_error.emit(str(e))

    def _do_work(self):
        code = self.params["股票代码"]
        dt_from = datetime.strptime(self.params["开始日期"], "%Y-%m-%d")
        dt_to = datetime.strptime(self.params["结束日期"], "%Y-%m-%d")
        prompt = self.params.get("AI提示词", "总结这份港交所披露文件的主要内容")
        order = self.params.get("发送顺序", "")

        self.log.emit("正在从港交所获取股票 {} 的 stockId...".format(code))
        session = create_session()
        stock_id = get_stock_id(session, code)
        self.log.emit("[OK] stockId = {}，开始获取披露文件...".format(stock_id))

        filings = fetch_hkex_filings(
            session, stock_id, dt_from, dt_to,
            log_fn=lambda msg: self.log.emit(msg),
            progress_fn=lambda v: self.progress.emit(v),
            should_stop_fn=lambda: not self._is_running,
        )
        total = len(filings)
        if total == 0:
            self.log.emit("[WARN] 该时间段内没有找到披露文件")
            return

        if order == "从晚到早":
            filings_list = list(reversed(filings))
            self.log.emit("发送顺序: 从晚到早（较老文件优先）")
        else:
            filings_list = list(filings)
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

            date_cn = format_date_cn(item["date"])
            self.log.emit("\n[{}/{}] {} | {}{} {}  {}".format(
                idx + 1, total, item.get("date", ""), item.get("stockCode", ""),
                " ", item.get("stockName", ""),
                "  ", item.get("title", "")
            ))

            self.log.emit("[INFO] 正在下载并提取 PDF 内容...")
            pdf_text = download_and_extract_pdf(item["link"])
            # 构建完整上下文的 AI 文本（与原脚本一致：日期+公司+代码+标题+内容）
            context_header = "日期：{}，公司：{}，股票代码：{}，标题：{}".format(
                date_cn, item.get("stockName", ""), item.get("stockCode", ""),
                item.get("title", "")
            )
            if not pdf_text or not pdf_text.strip():
                self.log.emit("[WARN] PDF 提取失败，降级发送原始链接")
                ai_text = "{}\n提示词：{}\n链接：{}".format(
                    context_header, prompt, item.get("link", "")
                )
            else:
                self.log.emit("[OK] PDF 提取成功，{} 字符".format(len(pdf_text)))
                ai_text = "{}\n提示词：{}\n内容：\n{}".format(
                    context_header, prompt, pdf_text
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
                    "股票代码": item.get("stockCode", ""),
                    "公司名称": item.get("stockName", ""),
                    "标题": item.get("title", ""),
                    "链接": item.get("link", ""),
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
            export_hk_excel(self._result_list, output_dir, log_fn=lambda msg: self.log.emit(msg))
        else:
            self.log.emit("[WARN] 未获取到有效数据，Excel 未生成")

