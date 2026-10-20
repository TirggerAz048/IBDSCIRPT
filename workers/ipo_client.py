"""
IPO 业务逻辑模块

从 SecPythonWebCrawler/mian.py 的 SecSpiderCore 拆分，纯数据获取+解析，
不含 GUI 和 AI 调用。

功能：
- NASDAQ IPO 日历 API
- 公司详情 + 中概股过滤
- SEC EDGAR 招股书搜索
- 招股书 HTML 章节提取
- AI 响应 JSON 解析
- 律师事务所分类
- Excel 导出
"""
import os
import re
import ast
import json
import requests
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup, Tag, NavigableString

from .ipo_utils import (
    SEC_UA, BROWSER_UA,
    safe_get_json, safe_get_html, get_nested_value,
    is_chinese_company, getended,
)


URL_NASDAQ_CALENDAR = "https://api.nasdaq.com/api/ipo/calendar?date="
URL_NASDAQ_OVERVIEW = "https://api.nasdaq.com/api/ipo/overview/?dealId="
URL_NASDAQ_EXPERTS = "https://api.nasdaq.com/api/ipo/experts/?dealId="
URL_SEC_SEARCH = "https://efts.sec.gov/LATEST/search-index"


def _generate_month_strings(dt_from, dt_to):
    """生成 dt_from ~ dt_to 之间所有 YYYY-MM 月份字符串

    Example:
        dt_from=date(2026,6,15), dt_to=date(2026,7,15) → ["2026-06", "2026-07"]
        dt_from=date(2026,5,18), dt_to=date(2026,6,18) → ["2026-05", "2026-06"]
        dt_from=date(2026,1,1),  dt_to=date(2026,1,31)  → ["2026-01"]
        dt_from=date(2025,12,20),dt_to=date(2026,1,10)  → ["2025-12", "2026-01"]
    """
    months = []
    cur = date(dt_from.year, dt_from.month, 1) if isinstance(dt_from, datetime) else dt_from.replace(day=1)
    end = date(dt_to.year, dt_to.month, 1) if isinstance(dt_to, datetime) else dt_to.replace(day=1)
    while cur <= end:
        months.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months


def _parse_nasdaq_date(date_str):
    """解析 NASDAQ API 返回的日期字符串

    支持格式:
    - "MM/DD/YYYY"     (最常见)
    - "YYYY-MM-DD"      (ISO)
    - "MM/DD/YY"        (2位年份 → 2000+)
    - "Mon DD, YYYY"    (英文缩写月)
    - "Month DD, YYYY"  (英文全称月)

    Returns:
        date 对象，解析失败返回 None
    """
    if not date_str or not isinstance(date_str, str) or not date_str.strip():
        return None

    date_str = date_str.strip()

    formats = [
        ("%m/%d/%Y", None),
        ("%Y-%m-%d", None),
        ("%m/%d/%y", lambda d: d.replace(year=2000 + d.year % 100)),
        ("%b %d, %Y", None),
        ("%B %d, %Y", None),
    ]

    for fmt, adjust_fn in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            d = dt.date()
            if adjust_fn:
                d = adjust_fn(d)
            return d
        except ValueError:
            continue

    return None


def fetch_ipo_calendar(dt_from, dt_to, nasdaq_headers, log_fn=None):
    """获取指定日期范围内的 IPO 日历

    Args:
        dt_from: 开始日期 (datetime 或 date)
        dt_to:   结束日期 (datetime 或 date)
        nasdaq_headers: NASDAQ 请求头（含 IPOS Cookie）
        log_fn: 日志回调

    Returns:
        (priced_list, filed_list): 过滤到 [dt_from, dt_to] 范围内的 rows 列表
    """
    # 统一转为 date 类型比较
    from_d = dt_from.date() if isinstance(dt_from, datetime) else dt_from
    to_d = dt_to.date() if isinstance(dt_to, datetime) else dt_to

    month_strings = _generate_month_strings(from_d, to_d)
    if log_fn:
        log_fn("日期范围: {} ~ {}，涉及 {} 个月份: {}".format(
            from_d, to_d, len(month_strings), month_strings
        ))

    all_priced = {}
    all_filed = {}

    for month_str in month_strings:
        if log_fn:
            log_fn("正在获取 IPO 日历: " + month_str)

        url = URL_NASDAQ_CALENDAR + month_str
        ipodata = safe_get_json(url, headers=nasdaq_headers)

        if not ipodata or not isinstance(ipodata, dict):
            if log_fn:
                log_fn("  [WARN] 月份 {} 未获取到 IPO 日历数据".format(month_str))
            continue

        data_section = ipodata.get("data") or {}
        month_priced = (data_section.get("priced") or {}).get("rows") or []
        month_filed = (data_section.get("filed") or {}).get("rows") or []

        # 按 dealID 去重合并
        for item in month_priced:
            deal_id = item.get("dealID")
            if deal_id and deal_id not in all_priced:
                all_priced[deal_id] = item

        for item in month_filed:
            deal_id = item.get("dealID")
            if deal_id and deal_id not in all_filed:
                all_filed[deal_id] = item

    # 按具体日期范围过滤
    priced_list = []
    for item in all_priced.values():
        date_str = item.get("pricedDate", "")
        item_date = _parse_nasdaq_date(date_str)
        if item_date is None:
            # 无法解析日期则保留（避免丢数据）
            priced_list.append(item)
        elif from_d <= item_date <= to_d:
            priced_list.append(item)

    filed_list = []
    for item in all_filed.values():
        date_str = item.get("filedDate", "")
        item_date = _parse_nasdaq_date(date_str)
        if item_date is None:
            filed_list.append(item)
        elif from_d <= item_date <= to_d:
            filed_list.append(item)

    if log_fn:
        log_fn("[OK] 获取到 Priced(已上市) {} 家，Filed(申请中) {} 家（已按日期过滤）".format(
            len(priced_list), len(filed_list)
        ))

    return priced_list, filed_list


def fetch_company_detail(deal_id, nasdaq_headers, log_fn=None):
    """获取公司详情并判断是否为中概股

    Args:
        deal_id: NASDAQ deal ID
        nasdaq_headers: NASDAQ 请求头
        log_fn: 日志回调

    Returns:
        dict: 公司基本信息字典，非中概股返回 None
    """
    overview = safe_get_json(URL_NASDAQ_OVERVIEW + deal_id, headers=nasdaq_headers)
    experts = safe_get_json(URL_NASDAQ_EXPERTS + deal_id, headers=nasdaq_headers)

    if not is_chinese_company(overview):
        if log_fn:
            company_name = get_nested_value(
                overview, ["data", "poOverview", "CompanyName", "value"], "未知"
            )
            log_fn("  [跳过] " + company_name + " — 非中概股")
        return None

    company_name = get_nested_value(overview, ["data", "poOverview", "CompanyName", "value"], "")

    data_dict = {
        "ProposedSymbol": get_nested_value(overview, ["data", "poOverview", "Symbol", "value"], ""),
        "CompanyName": company_name,
        "Exchange": get_nested_value(overview, ["data", "poOverview", "Exchange", "value"], ""),
        "SharePrice": get_nested_value(overview, ["data", "poOverview", "ProposedSharePrice", "value"], ""),
        "SharesOffered": get_nested_value(overview, ["data", "poOverview", "SharesOffered", "value"], ""),
        "Offeramount": get_nested_value(overview, ["data", "poOverview", "DollarValueOfSharesOffered", "value"], ""),
        "Auditor": "", "CompanyCounsel": "", "Underwriter": "", "LeadUnderwriter": "",
        "UnderwriterCounsel": "",
        "vocationalcounselor": [], "CaymanorBvi": [], "Otherlawyers": [],
        "Totalrevenues": "", "Netincome": "", "HongKonglawyers": [], "Chineselawyers": [],
        "YearEnd": "", "baseurl": "",
        "companyurl": URL_NASDAQ_OVERVIEW + deal_id,
        "status": "", "filetype": "",
        "IPODate": "", "ApplicationDate": "",
    }

    rows = get_nested_value(experts, ["data", "tableModel", "rows"], [])
    for row in rows:
        role = row.get("role", "")
        name = row.get("expertName", "")
        if role == "Auditor":
            data_dict["Auditor"] = name
        elif role == "CompanyCounsel":
            data_dict["CompanyCounsel"] = name
        elif role == "LeadUnderwriter":
            data_dict["LeadUnderwriter"] = name
        elif role == "Underwriter":
            data_dict["Underwriter"] = name
        elif role == "UnderwriterCounsel":
            data_dict["UnderwriterCounsel"] = name

    if log_fn:
        log_fn("  [中概股] " + company_name)

    return data_dict


def search_sec_filing(data, nasdaq_headers, log_fn=None):
    """通过 SEC EDGAR 搜索接口查找招股书 URL

    注意：原脚本 getfileurl() 用 hearders（浏览器UA + IPO cookie）发起搜索，
    不是用 SEC UA，这里传入 nasdaq_headers 以保持一致。

    Args:
        data: {"forms": "424B4"/"F-1", "entityName": "公司名", "startdt": "...", "enddt": "..."}
        nasdaq_headers: NASDAQ 请求头（含 IPOS Cookie），与原脚本保持一致
        log_fn: 日志回调

    Returns:
        str: 招股书 URL，未找到返回 None
    """
    ipo_data = safe_get_json(URL_SEC_SEARCH, headers=nasdaq_headers, params=data)
    if ipo_data:
        for hit in ipo_data.get("hits", {}).get("hits", []):
            hit_id = hit.get("_id", "")
            if ":" in hit_id:
                adsh_no_hyphen = hit.get("_source", {}).get("adsh", "").replace("-", "")
                ciks = hit.get("_source", {}).get("ciks", [])
                if ciks:
                    return "https://www.sec.gov/Archives/edgar/data/" + str(ciks[0]) + "/" + adsh_no_hyphen + "/" + hit_id.split(":")[1]
    if log_fn:
        log_fn("    [WARN] 未找到招股书: " + data.get("entityName", "") + " (" + data.get("forms", "") + ")")
    return None


def parse_prospectus_chapters(file_url, sec_headers, log_fn=None):
    """下载招股书 HTML，提取 3 个章节文本

    Returns:
        dict: {"financial": {"text": "...", "year_end": "..."}, "industry": {"text": "..."}, "legal": {"text": "..."}}
        下载失败返回 None
    """
    try:
        text = safe_get_html(file_url, headers=sec_headers)
    except Exception:
        text = None

    if not text:
        if log_fn:
            log_fn("    [FAIL] 招股书 HTML 获取为空")
        return None

    soup = BeautifulSoup(text, "html.parser")
    alist = soup.find_all("a")

    result = {
        "financial": {"text": "", "year_end": ""},
        "industry": {"text": ""},
        "legal": {"text": ""},
    }

    financial_done = False
    industry_done = False
    legal_done = False

    for item in alist:
        if item.text == "Table of Contents":
            continue

        parent = item.parent
        clean_text = (parent.text if parent else item.text).replace("\n", " ").replace("\r", " ")
        clean_text = re.sub(r'\s+', ' ', clean_text).strip().lower()

        if getended(clean_text) and not financial_done:
            target_idx = clean_text.find("ended")
            year_end = clean_text[target_idx + len("ended"):].strip()
            result["financial"]["year_end"] = year_end
            toc_tag = (parent.find("a") if parent else None) or item
            content = get_content_by_index_logic(toc_tag, alist, soup)
            if content:
                result["financial"]["text"] = content.get_text()
                financial_done = True

        elif clean_text == "industry overview" and not industry_done:
            content = get_content_by_index_logic(item, alist, soup)
            if content:
                result["industry"]["text"] = content.get_text()
                industry_done = True

        elif clean_text == "legal matters" and not legal_done:
            content = get_content_by_index_logic(item, alist, soup)
            if content:
                result["legal"]["text"] = content.get_text()
                legal_done = True

    return result


def get_content_by_index_logic(target_anchor, alist, soup):
    """根据锚点提取章节内容（HTML锚点定位）"""
    try:
        start_href = target_anchor.get("href")
        if not start_href:
            return None
        start_id = start_href.replace("#", "")
        real_start_node = soup.find(id=start_id) or soup.find(attrs={"name": start_id})
        if not real_start_node:
            return None

        next_id = None
        try:
            start_idx = alist.index(target_anchor)
        except ValueError:
            start_idx = -1

        if start_idx >= 0:
            for i in range(start_idx + 1, len(alist)):
                curr_href = alist[i].get("href")
                if curr_href and curr_href != start_href:
                    next_id = curr_href.replace("#", "")
                    break

        real_end_node = (
            (soup.find(id=next_id) or soup.find(attrs={"name": next_id}))
            if next_id else None
        )

        collected = []
        curr = real_start_node.next_element
        while curr and curr != real_end_node:
            if isinstance(curr, NavigableString):
                collected.append(str(curr))
            elif isinstance(curr, Tag) and not (real_end_node and real_end_node in curr.descendants):
                collected.append(curr.get_text())
            curr = curr.next_element

        return BeautifulSoup("<div>" + " ".join(collected) + "</div>", "html.parser")
    except Exception:
        return None


def parse_ai_response(response):
    """解析 AI 返回的 JSON/列表

    支持格式：
    - JSON 数组 [{"key": "value"}, ...]
    - JSON 对象 {"key": "value"}
    - Python 字面量（ast.literal_eval 兜底）

    Returns:
        解析后的对象（list/dict），失败返回 None
    """
    try:
        match = re.search(r'\[.*?\]', response, re.DOTALL) or re.search(r'\{.*?\}', response, re.DOTALL)
        if match:
            json_str = match.group(0).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                cleaned = re.sub(r'\bnull\b', 'None', json_str)
                cleaned = re.sub(r'\btrue\b', 'True', cleaned)
                cleaned = re.sub(r'\bfalse\b', 'False', cleaned)
                return ast.literal_eval(cleaned)
        return None
    except Exception:
        return None


def classify_lawyers(res_list, current_data):
    """将法律顾问解析结果按地区分类到 data_dict

    Args:
        res_list: parse_ai_response 返回的列表
        current_data: 公司数据字典（会原地修改）
    """
    if not res_list:
        return

    for r in res_list:
        if not isinstance(r, dict) or not r.get("name"):
            continue
        comp = r.get("company", "")
        name = r.get("name")
        if comp == "中国地区":
            current_data["Chineselawyers"].append(name)
        elif comp == "香港地区":
            current_data["HongKonglawyers"].append(name)
        elif "开曼" in comp or "BVI" in comp:
            current_data["CaymanorBvi"].append(name)
        else:
            current_data["Otherlawyers"].append(name)


def build_nasdaq_headers(ipo_cookie):
    """构建 NASDAQ API 请求头"""
    return {
        "User-Agent": BROWSER_UA,
        "cookie": ipo_cookie,
    }


def build_sec_headers(sec_cookie):
    """构建 SEC EDGAR 请求头"""
    return {
        "User-Agent": SEC_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
        "cookie": sec_cookie,
    }


def export_ipo_excel(data_list, output_dir, log_fn=None):
    """导出 IPO 数据到 Excel（22列）

    Args:
        data_list: 公司数据字典列表
        output_dir: 输出目录
        log_fn: 日志回调

    Returns:
        str: 生成的文件路径，失败返回 None
    """
    try:
        import openpyxl
    except ImportError:
        if log_fn:
            log_fn("[ERROR] openpyxl 未安装，无法导出 Excel")
        return None

    os.makedirs(output_dir, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IPO Data"

    headers = [
        "上市状态", "公司全称", "股票代码", "上市日期",
        "申请日期", "募资额（美元）", "发行量（股）", "发行价", "交易所",
        "总营收", "总利润", "审计机构", "承销商", "美国律师", "中国律师",
        "香港律师", "其他律师", "行业顾问", "年结日", "公司链接", "招股书链接", "文件类型",
    ]
    ws.append(headers)

    for item in data_list:
        ws.append([
            item.get("status"),
            item.get("CompanyName"),
            item.get("ProposedSymbol"),
            item.get("IPODate"),
            item.get("ApplicationDate"),
            item.get("Offeramount"),
            item.get("SharesOffered"),
            item.get("SharePrice"),
            item.get("Exchange"),
            item.get("Totalrevenues"),
            item.get("Netincome"),
            item.get("Auditor"),
            item.get("LeadUnderwriter"),
            item.get("CompanyCounsel"),
            ", ".join(item.get("Chineselawyers", [])),
            ", ".join(item.get("HongKonglawyers", [])),
            ", ".join(item.get("Otherlawyers", [])),
            ", ".join(item.get("vocationalcounselor", [])),
            item.get("YearEnd"),
            item.get("companyurl"),
            item.get("baseurl"),
            item.get("filetype"),
        ])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, "IPO数据_" + ts + ".xlsx")
    wb.save(file_path)

    if log_fn:
        log_fn("[OK] Excel 已导出: " + file_path)

    return file_path
