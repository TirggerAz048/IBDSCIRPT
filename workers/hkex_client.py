"""
港交所(HKEX)披露文件获取模块

从 HkChat/mian.py 提取的纯数据获取逻辑，不涉及浏览器/AI 操作。

核心流程（与原脚本完全一致）：
1. GET prefix.do → 获取 stockId（需传 name=stock_code 参数）
2. 按月分块
3. 每月：GET 搜索页 → 提取 ViewState → POST 设置日期 → GET JSON API 分页
4. _parse_record: 直接取 STOCK_CODE / STOCK_NAME 字段（不从DATE_TIME拆分）
"""

import re
import time
import json
import requests
from bs4 import BeautifulSoup
from calendar import monthrange
from datetime import datetime
from typing import List, Tuple

BASE        = "https://www1.hkexnews.hk"
SEARCH_PAGE = "https://www1.hkexnews.hk/search/titlesearch.xhtml"
API_URL     = "https://www1.hkexnews.hk/search/titleSearchServlet.do"
PREFIX_URL  = "https://www1.hkexnews.hk/search/prefix.do"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def create_session():
    """创建带 UA 的 requests Session"""
    session = requests.Session()
    session.headers["User-Agent"] = UA
    return session


# ──────────────────────────── stockId 解析 ────────────────────────────

def get_stock_id(session: requests.Session, stock_code: str) -> str:
    """通过 prefix.do 接口把股票代码转为港交所内部 stockId。

    与原脚本一致：必须传 name=stock_code 参数，API返回 stockInfo 列表，
    取第一项的 stockId。
    """
    ts = str(int(time.time() * 1000))
    try:
        resp = session.get(PREFIX_URL, params={
            "callback": "callback",
            "lang":     "EN",
            "type":     "A",
            "name":     stock_code,   # 关键：原脚本传 name 参数
            "market":   "SEHK",
            "_":        ts,
        }, timeout=30)
    except requests.RequestException as e:
        raise ValueError("连接港交所失败: {}".format(str(e)))

    if not resp.text or len(resp.text.strip()) < 5:
        raise ValueError("港交所返回空数据，请检查网络连接")

    # 去掉 JSONP 包裹 callback(...);
    inner = re.sub(r"^callback\s*\(", "", resp.text).rstrip().rstrip(");").rstrip(")")
    try:
        data = json.loads(inner)
    except json.JSONDecodeError:
        raise ValueError("港交所返回数据格式异常（非JSON），原始内容前200字符: {}".format(resp.text[:200]))

    items = data.get("stockInfo", [])
    if not items:
        raise ValueError("未找到股票 {} 的 stockId".format(stock_code))
    return str(items[0]["stockId"])


# ──────────────────────────── 月份分块 ────────────────────────────

def month_chunks(dt_from: datetime, dt_to: datetime) -> List[Tuple[datetime, datetime]]:
    """将日期范围按月分块，从晚到早返回（与原脚本一致）"""
    chunks = []
    c = datetime(dt_to.year, dt_to.month, 1)
    f = datetime(dt_from.year, dt_from.month, 1)
    while c >= f:
        _, ld = monthrange(c.year, c.month)
        s = max(c, dt_from)
        e = min(datetime(c.year, c.month, ld), dt_to)
        chunks.append((s, e))
        c = datetime(c.year - 1, 12, 1) if c.month == 1 else datetime(c.year, c.month - 1, 1)
    return chunks


# ──────────────────────────── 记录解析 ────────────────────────────

def _parse_record(r: dict) -> dict:
    """解析单条披露文件记录（与原脚本 parse_record 完全一致）

    原脚本直接取 STOCK_CODE / STOCK_NAME 字段，不从 DATE_TIME 拆分。
    旧版集成脚本错误地从 DATE_TIME 拆分 code/name，导致字段取错。
    """
    date_raw = r.get("DATE_TIME", "").split(" ")[0]
    # HKEX API 返回 DD/MM/YYYY 格式，需转为 YYYY-MM-DD
    try:
        date = datetime.strptime(date_raw, "%d/%m/%Y").strftime("%Y-%m-%d") if date_raw else ""
    except ValueError:
        date = date_raw  # 解析失败则保留原始格式
    code  = r.get("STOCK_CODE", "").split("<br/>")[0].strip()
    name  = r.get("STOCK_NAME", "").split("<br/>")[0].strip()
    title = r.get("TITLE", "").replace("&#x3b;", ";").replace("&amp;", "&")
    link  = r.get("FILE_LINK", "")
    if link.startswith("/"):
        link = BASE + link
    elif link and not link.startswith("http"):
        link = BASE + "/" + link
    ftype = r.get("FILE_TYPE", "")
    cat   = r.get("LONG_TEXT", "")
    return {"date": date, "stockCode": code, "stockName": name,
            "title": title, "link": link, "fileType": ftype, "category": cat}


# ──────────────────────────── 获取单月数据 ────────────────────────────

def _fetch_month(session: requests.Session, from_d: str, to_d: str, stock_id: str,
                 log_fn=None, should_stop_fn=None) -> List[dict]:
    """获取单个月的披露文件（与原脚本 fetch_month 完全一致）

    流程：
    1. GET 搜索页 → 提取 ViewState + form action
    2. POST 设置日期范围到服务端 Session
    3. 循环 GET JSON API 分页
    """
    # Step 1: GET 搜索页，提取 ViewState
    page = session.get(SEARCH_PAGE, params={
        "sortDir": "0", "sortByRecordDate": "on", "searchType": "0",
        "category": "0", "t1code": "-2", "t2Gcode": "-2", "t2code": "-2",
        "documentType": "-1", "rowRange": "0", "lang": "EN",
    }, timeout=30)

    soup = BeautifulSoup(page.text, "html.parser")
    vs = soup.find("input", {"name": "javax.faces.ViewState"})
    view_state = vs["value"] if vs else ""
    form = soup.find("form")
    action = form.get("action", "") if form else ""
    submit_url = (BASE + action) if action.startswith("/") else (BASE + SEARCH_PAGE)

    # Step 2: POST 设置日期范围到服务端 Session
    session.post(submit_url, data={
        "j_idt10": "j_idt10",
        "j_idt10:loadMoreRange": "100",
        "javax.faces.ViewState": view_state,
        "from": from_d,
        "to":   to_d,
    }, timeout=30)

    # Step 3: 循环 GET JSON API 分页
    results = []
    fetched = 0

    while True:
        if should_stop_fn and should_stop_fn():
            break

        row_range = fetched + 5000
        try:
            resp = session.get(API_URL, params={
                "sortDir":        "0",
                "sortByOptions":  "DateTime",
                "category":       "0",
                "market":         "SEHK",
                "stockId":        stock_id,
                "documentType":   "-1",
                "fromDate":       from_d,
                "toDate":         to_d,
                "title":          "",
                "searchType":     "0",
                "t1code":         "-2",
                "t2Gcode":        "-2",
                "t2code":         "-2",
                "rowRange":       str(row_range),
                "lang":           "E",
            }, headers={
                "Accept":           "application/json, text/javascript, */*; q=0.01",
                "Referer":          SEARCH_PAGE,
                "X-Requested-With": "XMLHttpRequest",
            }, timeout=120)
        except Exception as e:
            if log_fn:
                log_fn("[ERROR] 获取 API 数据失败: {}".format(str(e)))
            break

        data = resp.json()
        raw = data.get("result", "null")
        if not raw or raw == "null":
            break

        records = json.loads(raw) if isinstance(raw, str) else raw
        for rec in records[fetched:]:
            results.append(_parse_record(rec))
        fetched = len(records)

        if not data.get("hasNextRow", False):
            break

    return results


# ──────────────────────────── 主入口 ────────────────────────────

def fetch_hkex_filings(session, stock_id, dt_from, dt_to,
                       log_fn=None, progress_fn=None, should_stop_fn=None):
    """按月分块获取港交所披露文件

    Args:
        session: requests Session
        stock_id: 港交所内部 stockId
        dt_from: 开始日期 (datetime)
        dt_to: 结束日期 (datetime)
        log_fn: 日志回调 log_fn(str)
        progress_fn: 进度回调 progress_fn(current, total) 用于更新进度条百分比
        should_stop_fn: 停止检查 should_stop_fn() -> bool

    Returns:
        披露文件列表 [dict, ...]
    """
    chunks = month_chunks(dt_from, dt_to)
    total_chunks = len(chunks)
    all_results = []

    for idx, (chunk_from, chunk_to) in enumerate(chunks):
        f_str = chunk_from.strftime("%Y%m%d")
        t_str = chunk_to.strftime("%Y%m%d")
        month_label = chunk_from.strftime("%Y-%m")

        if log_fn:
            log_fn("[{}/{}] 正在获取 {} 的数据...".format(idx + 1, total_chunks, month_label))

        results = _fetch_month(session, f_str, t_str, stock_id,
                               log_fn=log_fn, should_stop_fn=should_stop_fn)
        all_results.extend(results)

        if log_fn:
            log_fn("[OK] {}: {} 条记录".format(month_label, len(results)))

        if progress_fn:
            progress_fn(int((idx + 1) / total_chunks * 50))

        if should_stop_fn and should_stop_fn():
            break

    return all_results


def format_date_cn(date_str):
    """把 'YYYY-MM-DD' 或 'YYYYMMDD' 格式化成 'YYYY年MM月DD日'"""
    s = date_str.strip()
    if "-" in s and len(s) == 10:
        d = datetime.strptime(s, "%Y-%m-%d")
    elif len(s) == 8 and s.isdigit():
        d = datetime.strptime(s, "%Y%m%d")
    else:
        return date_str
    return d.strftime("%Y年%m月%d日")


def export_hk_excel(results, output_dir, log_fn=None):
    """导出港股披露文件数据到 Excel

    Args:
        results: 结果列表，每项为 dict，含 date/stockCode/stockName/title/link/ai_response
        output_dir: 输出目录
        log_fn: 日志回调

    Returns:
        str: 生成的文件路径，失败返回 None
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        if log_fn:
            log_fn("[ERROR] openpyxl 未安装，无法导出 Excel")
        return None

    if not results:
        if log_fn:
            log_fn("[WARN] 无数据可导出，Excel 未生成")
        return None

    os.makedirs(output_dir, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "港交所披露文件"

    headers = [
        "日期", "股票代码", "公司名称", "文件标题",
        "文件链接", "AI分析结果"
    ]

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)

    for row_idx, item in enumerate(results, 2):
        ws.cell(row=row_idx, column=1).value = item.get("日期", "")
        ws.cell(row=row_idx, column=2).value = item.get("股票代码", "")
        ws.cell(row=row_idx, column=3).value = item.get("公司名称", "")
        ws.cell(row=row_idx, column=4).value = item.get("标题", "")
        ws.cell(row=row_idx, column=5).value = item.get("链接", "")
        ws.cell(row=row_idx, column=6).value = item.get("AI分析结果", "")

    col_widths = [15, 10, 18, 45, 60, 80]
    for i, width in enumerate(col_widths, 1):
        col_letter = chr(64 + i) if i <= 26 else "A" + chr(64 + i - 26)
        ws.column_dimensions[col_letter].width = width

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    code = results[0].get("股票代码", "unknown") if results else "unknown"
    filepath = os.path.join(output_dir, "港交所数据_{}_{}.xlsx".format(code, ts))
    wb.save(filepath)

    if log_fn:
        log_fn("[OK] Excel 已导出: " + filepath)

    return filepath
