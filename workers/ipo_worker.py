"""
中概股 IPO Worker 线程

工作流:
1. 从 NASDAQ API 获取指定月份的 IPO 日历
2. 遍历 priced/filed 公司 → 中概股过滤
3. SEC EDGAR 搜索招股书 URL
4. 下载招股书 HTML → 提取 3 个章节（财务/行业顾问/法律顾问）
5. 3 轮 AI 调用（通过 send_to_ai 信号 + wait_for_ai_response）
6. 失败重试（一轮）
7. 汇总报告 + Excel 导出

params 字段:
- SEC Cookie: SEC EDGAR 访问用的 Cookie
- IPO Cookie: NASDAQ IPO 日历访问用的 Cookie
- 开始日期 / 结束日期: "YYYY-MM-DD" 格式，范围上限30天
- 财务提示词: "..."
- 行业顾问提示词: "..."
- 法律顾问提示词: "..."
"""
import os
import re
from datetime import datetime, timedelta
from .base_worker import BaseWorker
from .ipo_client import (
    fetch_ipo_calendar, fetch_company_detail, search_sec_filing,
    parse_prospectus_chapters, parse_ai_response, classify_lawyers,
    build_nasdaq_headers, build_sec_headers, export_ipo_excel,
)


class IpoWorker(BaseWorker):
    """中概股 IPO Worker"""

    def run(self):
        try:
            self._do_work()
            if self._is_running:
                self.finished_ok.emit()
        except Exception as e:
            self.log.emit(f"[ERROR] {e}")
            self.finished_error.emit(str(e))

    def _do_work(self):
        sec_cookie = self.params.get("SEC Cookie", "")
        ipo_cookie = self.params.get("IPO Cookie", "")
        self._start_date_str = self.params.get("开始日期", "")
        self._end_date_str = self.params.get("结束日期", "")
        prompt_fin = self.params.get("财务提示词", "")
        prompt_ind = self.params.get("行业顾问提示词", "")
        prompt_law = self.params.get("法律顾问提示词", "")

        if not self._start_date_str or not self._end_date_str:
            # 兜底：默认当月1号 ~ 当月最后一天
            today = datetime.now()
            self._start_date_str = today.replace(day=1).strftime("%Y-%m-%d")
            import calendar
            _, last_day = calendar.monthrange(today.year, today.month)
            self._end_date_str = today.replace(day=last_day).strftime("%Y-%m-%d")

        dt_from = datetime.strptime(self._start_date_str, "%Y-%m-%d")
        dt_to = datetime.strptime(self._end_date_str, "%Y-%m-%d")

        nasdaq_headers = build_nasdaq_headers(ipo_cookie)
        sec_headers = build_sec_headers(sec_cookie)

        self.progress.emit(5)
        priced_list, filed_list = fetch_ipo_calendar(
            dt_from, dt_to, nasdaq_headers, log_fn=self.log.emit
        )

        if not self._is_running:
            return

        if not priced_list and not filed_list:
            self.log.emit("[WARN] 该日期范围内没有 IPO 数据")
            return

        self.log.emit("=" * 50)
        self.log.emit("开始第一轮: Priced(已上市)")
        self.log.emit("=" * 50)

        self.datalist = []
        self.failed_tasks = []
        self.ai_failures = []

        total_companies = len(priced_list) + len(filed_list)
        processed = 0

        for item in priced_list:
            if not self._is_running:
                break
            processed += 1
            if isinstance(item, dict) and item.get("dealID"):
                self._process_deal(
                    item["dealID"], "424B4", "已上市",
                    item.get("pricedDate", ""),
                    nasdaq_headers, sec_headers,
                    prompt_fin, prompt_ind, prompt_law,
                )
            self.progress.emit(int(10 + 70 * processed / max(total_companies, 1)))

        if self._is_running:
            self.log.emit("=" * 50)
            self.log.emit("开始第一轮: Filed(申请中)")
            self.log.emit("=" * 50)

        for item in filed_list:
            if not self._is_running:
                break
            processed += 1
            if isinstance(item, dict) and item.get("dealID"):
                self._process_deal(
                    item["dealID"], "F-1", "申请中",
                    item.get("filedDate", ""),
                    nasdaq_headers, sec_headers,
                    prompt_fin, prompt_ind, prompt_law,
                )
            self.progress.emit(int(10 + 70 * processed / max(total_companies, 1)))

        if self._is_running and self.failed_tasks:
            self.log.emit("")
            self.log.emit(f"[提示] 第一轮有 {len(self.failed_tasks)} 个任务失败，准备重试...")
            retry_queue = self.failed_tasks.copy()
            self.failed_tasks.clear()

            for task in retry_queue:
                if not self._is_running:
                    break
                self.log.emit(f"正在重试: {task['deal_id']}")
                self._process_deal(
                    task["deal_id"], task["filetype"], task["status"],
                    task["date"], nasdaq_headers, sec_headers,
                    prompt_fin, prompt_ind, prompt_law,
                )

        self.progress.emit(90)

        if self.datalist:
            results_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "results"
            )
            filepath = export_ipo_excel(self.datalist, results_dir, log_fn=self.log.emit)
            if filepath:
                self.output_filepath = filepath
        else:
            self.log.emit("[WARN] 未抓取到有效数据，Excel 未生成")

        self.progress.emit(95)
        self.log.emit("")
        self.log.emit("=" * 60)
        self.log.emit("IPO 获取任务最终汇总报告")
        self.log.emit("=" * 60)

        if self.failed_tasks:
            self.log.emit(f"[FAIL] 以下 {len(self.failed_tasks)} 家公司无法获取文件或基本信息:")
            for i, task in enumerate(self.failed_tasks, 1):
                self.log.emit(f"  {i}. [ID: {task['deal_id']}] 类型: {task['filetype']} | 日期: {task['date']}")
        else:
            self.log.emit("[OK] 网页抓取与基本信息获取: 全部成功")

        self.log.emit("-" * 60)

        if self.ai_failures:
            self.log.emit(f"[WARN] 以下 {len(self.ai_failures)} 处 AI 解析异常:")
            for i, err in enumerate(self.ai_failures, 1):
                self.log.emit(f"  {i}. {err}")
        else:
            self.log.emit("[OK] DeepSeek AI 数据解析: 全部成功")

        self.log.emit(f"成功: {len(self.datalist)} 家公司")
        self.log.emit("=" * 60)
        self.progress.emit(100)

    def _process_deal(self, deal_id, filetype, status, date_val,
                      nasdaq_headers, sec_headers,
                      prompt_fin, prompt_ind, prompt_law):
        try:
            base_data = fetch_company_detail(
                deal_id, nasdaq_headers, log_fn=self.log.emit
            )
            if not base_data:
                return

            base_data["status"] = status
            base_data["filetype"] = filetype
            base_data["IPODate"] = date_val if status == "已上市" else ""
            base_data["ApplicationDate"] = date_val if status != "已上市" else ""

            sec_startdt = self._start_date_str
            sec_enddt = self._end_date_str

            search_data = {
                "forms": filetype,
                "entityName": base_data["CompanyName"],
                "startdt": sec_startdt,
                "enddt": sec_enddt,
            }
            file_url = search_sec_filing(search_data, nasdaq_headers, log_fn=self.log.emit)

            if not file_url:
                self.log.emit(f"  [跳过] {base_data['CompanyName']} — 未找到招股书 URL")
                self.failed_tasks.append({
                    "deal_id": deal_id, "filetype": filetype,
                    "status": status, "date": date_val,
                })
                return

            base_data["baseurl"] = file_url
            company_name = base_data["CompanyName"]

            self.log.emit(f"[INFO] 正在提取 {company_name} 的招股书章节...")
            chapters = parse_prospectus_chapters(file_url, sec_headers, log_fn=self.log.emit)

            if not chapters:
                self.failed_tasks.append({
                    "deal_id": deal_id, "filetype": filetype,
                    "status": status, "date": date_val,
                })
                return

            self.log.emit(f"[INFO] 开始 AI 解析: {company_name}")

            if chapters["financial"]["text"]:
                self._ai_extract_financial(company_name, chapters, prompt_fin, base_data)
            else:
                self.ai_failures.append(f"[{company_name}] 财务章节为空")

            if chapters["industry"]["text"]:
                self._ai_extract_industry(company_name, chapters, prompt_ind, base_data)
            else:
                self.ai_failures.append(f"[{company_name}] 行业顾问章节为空")

            if chapters["legal"]["text"]:
                self._ai_extract_legal(company_name, chapters, prompt_law, base_data)
            else:
                self.ai_failures.append(f"[{company_name}] 法律事项章节为空")

            self.datalist.append(base_data)
            self.log.emit(f"[OK] {company_name} 处理完成")

        except Exception as e:
            self.log.emit(f"[ERROR] 处理 {deal_id} 异常: {e}")
            self.failed_tasks.append({
                "deal_id": deal_id, "filetype": filetype,
                "status": status, "date": date_val,
            })

    def _ai_extract_financial(self, company_name, chapters, prompt_fin, base_data):
        output_req = (
            "\n输出要求：\n"
            "1. 返回格式：[{'净收入':'xxx','净利润':'xxx'}]，数值保留原格式（含括号表示负数）\n"
            "注:返回的回答必须是json字符串。\n"
            "2. 如果没找到相关数据则返回[{'净收入':'xxx','净利润':'xxx'}]。\n"
            "注:返回的回答必须是json字符串。\n"
            "只输出纯JSON字符串，不要Markdown代码块。\n"
            "【输出要求】只输出纯JSON字符串，不要Markdown代码块（不要```json、```等），不要任何解释性文字。"
        )
        fin_text = re.sub(r'\n{3,}', '\n\n', chapters["financial"]["text"])
        prompt = f"{company_name} 财务数据\n" + prompt_fin + output_req + f"\n目标内容:{fin_text}"

        self.log.emit(f"  [AI] 正在提取财务数据...")
        self.send_to_ai.emit(prompt)
        response = self.wait_for_ai_response(timeout_ms=60000)

        if response:
            result = parse_ai_response(response)
            if result and isinstance(result, list) and len(result) > 0:
                base_data["Totalrevenues"] = result[0].get("净收入", "")
                base_data["Netincome"] = result[0].get("净利润", "")
                if chapters["financial"]["year_end"]:
                    base_data["YearEnd"] = chapters["financial"]["year_end"]
            else:
                self.ai_failures.append(f"[{company_name}] 财务提取失败 (AI未返回有效内容)")
        else:
            self.ai_failures.append(f"[{company_name}] 财务提取失败 (AI无响应)")

    def _ai_extract_industry(self, company_name, chapters, prompt_ind, base_data):
        output_req = (
            "\n输出要求：\n"
            "1. 可能有多个人名，返回格式为['名字1','名字2']。\n"
            "2. 如果没有任何名字，则返回['无']。\n"
            "3. 所有回答只返回JSON字符串，不要markdown格式。"
        )
        ind_text = re.sub(r'\n{3,}', '\n\n', chapters["industry"]["text"])
        prompt = f"{company_name} 行业顾问\n" + prompt_ind + output_req + f"\n目标内容:{ind_text}"

        self.log.emit(f"  [AI] 正在提取行业顾问...")
        self.send_to_ai.emit(prompt)
        response = self.wait_for_ai_response(timeout_ms=60000)

        if response:
            result = parse_ai_response(response)
            if isinstance(result, list):
                base_data["vocationalcounselor"].extend(result)
            else:
                self.ai_failures.append(f"[{company_name}] 行业顾问提取失败 (AI格式错误)")
        else:
            self.ai_failures.append(f"[{company_name}] 行业顾问提取失败 (AI无响应)")

    def _ai_extract_legal(self, company_name, chapters, prompt_law, base_data):
        output_req = (
            "\n输出要求：\n"
            "回答只返回 [{'name':'事务所名称','company':'地区'}]格式的JSON字符串 "
            "我不要markdown形式的回答 你只需要输出json字符串给我即可 "
            "一定要是json字符串格式的才行 "
            "如果文段内容有类似 [●]或[     ] 或者其他的明显的隐藏名字的字符则返回['无']，"
            "如果没有找到符合条件的字符也返回['无'] "
            "我的需求请你好好分析。"
        )
        law_text = re.sub(r'\n{3,}', '\n\n', chapters["legal"]["text"])
        prompt = f"{company_name} 法律顾问\n" + prompt_law + output_req + f"\n目标内容:{law_text}"

        self.log.emit(f"  [AI] 正在提取法律顾问...")
        self.send_to_ai.emit(prompt)
        response = self.wait_for_ai_response(timeout_ms=60000)

        if response:
            result = parse_ai_response(response)
            if isinstance(result, list):
                classify_lawyers(result, base_data)
            else:
                self.ai_failures.append(f"[{company_name}] 法律顾问提取失败 (AI格式错误)")
        else:
            self.ai_failures.append(f"[{company_name}] 法律顾问提取失败 (AI无响应)")
