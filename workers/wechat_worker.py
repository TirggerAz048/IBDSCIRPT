"""
wechat_worker.py — 公众号数据导出 Worker 线程

工作流：
  Step1: 通过云服务器获取 access_token
  Step2: 按日期逐天获取文章统计数据
  Step3: 按标题匹配划线数据（来自 JS 提取）
  Step4: 合并数据，生成 Excel 到 results/ 目录
"""
import os
from datetime import datetime, timedelta
from .base_worker import BaseWorker
import time
from .wechat_client import fetch_access_token, fetch_articles, generate_excel, normalize_title, match_underline


class WechatWorker(BaseWorker):
    """公众号数据导出 Worker"""

    def __init__(self, params, parent=None):
        super().__init__(params, parent)
        self.output_filepath = ""

    def run(self):
        self.log.emit("[INFO] 公众号导出开始")

        appid = self.params.get("AppID", "")
        secret = self.params.get("AppSecret", "")
        start_date = self.params.get("开始日期", "")
        end_date = self.params.get("结束日期", "")
        underline_data = self.params.get("划线数据", [])

        # 构建划线数据的标准化标题映射：{normalize_title(标题): (原始标题, 划线数)}
        norm_map = {}
        if underline_data:
            for item in underline_data:
                title = item.get("title", "")
                underline = item.get("underline", "")
                if title:
                    norm_map[normalize_title(title)] = (title, underline)

        try:
            self.log.emit("正在获取 access_token（经云服务器）...")
            self.progress.emit(5)

            access_token, err = fetch_access_token(appid, secret)
            if err:
                self.log.emit("[ERROR] Token 获取失败: " + err)
                self.finished_error.emit(err)
                return

            self.log.emit("Token 获取成功")
            self.progress.emit(10)

            current = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            total_days = (end - current).days + 1
            day_count = 0

            all_articles = []
            matched_count = 0

            while current <= end:
                if not self._is_running:
                    self.log.emit("[INFO] 用户停止")
                    self.finished_error.emit("用户停止")
                    return

                date_str = current.strftime("%Y-%m-%d")
                day_count += 1
                self.progress.emit(10 + int(60 * day_count / total_days))

                self.log.emit("\n正在获取 " + date_str + " 的数据...")

                articles_list, err = fetch_articles(access_token, date_str, date_str)
                if err:
                    self.log.emit("  请求失败: " + err)
                    current += timedelta(days=1)
                    continue

                if articles_list:
                    self.log.emit("  找到 " + str(len(articles_list)) + " 篇文章")

                    for item in articles_list:
                        latest = item["detail_list"][-1]
                        title = item.get("title") or "(无标题)"

                        underline_count = ""
                        match_type = None
                        if norm_map:
                            underline_count, match_type = match_underline(title, norm_map)

                        if match_type == "exact":
                            self.log.emit("  【" + title[:25] + "】划线匹配 -> " + str(underline_count))
                        elif match_type == "fuzzy":
                            self.log.emit("  【" + title[:25] + "】划线模糊 -> " + str(underline_count))

                        if underline_count:
                            matched_count += 1

                        all_articles.append({
                            "文章发表日期": item["ref_date"],
                            "作者": "",
                            "文章标题": title,
                            "阅读人数": latest["read_user"],
                            "点赞人数": latest["like_user"],
                            "转发人数": latest["zaikan_user"],
                            "推荐人数": latest["share_user"],
                            "留言条数": latest["comment_count"],
                            "划线人数": underline_count,
                            "文章链接": item["content_url"],
                            "统计时间": latest["stat_date"]
                        })
                else:
                    self.log.emit("  该日无文章发布")

                time.sleep(0.5)
                current += timedelta(days=1)

            if not all_articles:
                self.log.emit("\n没有获取到任何数据！")
                self.finished_error.emit("无数据")
                return

            self.progress.emit(75)

            self.log.emit("\n正在生成 Excel，共 " + str(len(all_articles)) + " 条记录...")
            self.progress.emit(85)

            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "results"
            )
            filepath = generate_excel(all_articles, output_dir)
            self.output_filepath = filepath

            self.progress.emit(100)

            self.log.emit("\n" + "=" * 45)
            self.log.emit("Excel 已生成: " + filepath)
            self.log.emit("共 " + str(len(all_articles)) + " 条记录 | 划线匹配: " + str(matched_count) + "/" + str(len(all_articles)))
            self.log.emit("时间范围: " + start_date + " ~ " + end_date)

            self.finished_ok.emit()

        except Exception as e:
            self.log.emit("[ERROR] " + str(e))
            self.finished_error.emit(str(e))
