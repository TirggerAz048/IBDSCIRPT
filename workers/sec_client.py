"""
SEC EDGAR 文件获取模块

从 SecChat/gui.py 提取的纯数据获取逻辑，不涉及浏览器/AI 操作。
API 文档: https://data.sec.gov/submissions/CIK{cik_padded}.json
"""

import re
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

UA = "IBDspider/1.0 contact@example.com"

NESTED_FORM_TYPES = ["6-K", "8-K"]


def fetch_sec_filings(cik, start_date, end_date=None, allowed_forms=None, log_fn=None, progress_fn=None, should_stop_fn=None):
    """从 SEC EDGAR 获取指定 CIK 的披露文件列表

    Args:
        cik: SEC CIK 号码（如 "0001905956"，会自动补零到10位）
        start_date: 开始日期（datetime）
        end_date: 结束日期（datetime，None 则不限结束）
        allowed_forms: 允许的表单类型白名单（如 ["10-K", "10-Q", "8-K"]），None 表示不过滤
        log_fn: 日志回调 log_fn(str)
        progress_fn: 进度回调 progress_fn(int 0~50)（数据获取阶段占 0~50%）
        should_stop_fn: 停止检查 should_stop_fn() -> bool

    Returns:
        文件列表 [{"id": int, "date": "YYYY-MM-DD", "url": str}, ...]
        已按 date 升序排列（从早到晚），由上层 Worker 按用户选择的顺序再处理
    """
    cik_padded = cik.strip().zfill(10)
    url = "https://data.sec.gov/submissions/CIK{}.json".format(cik_padded)
    headers = {"User-Agent": UA}

    if log_fn:
        log_fn("正在请求 SEC API: CIK{}...".format(cik_padded))

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    filings_data = data.get("filings", {})
    recent = filings_data.get("recent", {})

    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    forms = recent.get("form", [])
    primary_docs = recent.get("primaryDocument", [])

    if not accession_numbers:
        raise RuntimeError("CIK{} 没有找到任何文件记录".format(cik))

    filings = []
    total = len(accession_numbers)

    for i in range(total):
        filing_date_str = filing_dates[i]
        form_type = forms[i].upper()
        accession_no = accession_numbers[i].replace("-", "")
        primary_doc = primary_docs[i] if i < len(primary_docs) else ""

        try:
            filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
        except Exception:
            continue

        if filing_date < start_date:
            continue
        if end_date and filing_date > end_date:
            continue

        if allowed_forms and form_type not in allowed_forms:
            continue

        file_url = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}".format(
            str(int(cik)), accession_no, primary_doc
        )

        filings.append({
            "id": i,
            "date": filing_date_str,
            "form": form_type,
            "url": file_url,
        })

    filings.sort(key=lambda x: x["date"])

    if log_fn:
        log_fn("[OK] 获取到 {} 条原始记录，正在过滤...".format(total))
        log_fn("[OK] 过滤后共 {} 个文件".format(len(filings)))

    if progress_fn:
        progress_fn(50)

    return filings


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


def extract_nested_links(filings, log_fn=None, should_stop_fn=None):
    """从 6-K / 8-K 文件中提取嵌套的附件链接

    6-K 和 8-K 的主 HTML 文件中经常包含对附件的引用
    （如 Exhibits、Press Release 等），这些附件通常是 .htm/.pdf 文件。
    本函数访问这些主文件，提取其中的附件链接，返回追加条目列表。

    Args:
        filings: fetch_sec_filings 返回的文件列表
        log_fn: 日志回调
        should_stop_fn: 停止检查

    Returns:
        需要追加的附件条目列表（与 filings 格式一致），
        不修改原始 filings 列表。
    """
    from urllib.parse import urlparse, urljoin

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        if log_fn:
            log_fn("[WARN] BeautifulSoup 未安装，跳过 6-K/8-K 嵌套链接提取")
        return []

    TARGET_SUFFIXES = (".htm", ".html", ".pdf", ".xml")

    extra_items = []
    target_forms = set(NESTED_FORM_TYPES)
    seen_urls = set()

    for item in filings:
        form = item.get("form", "").upper()
        if form not in target_forms:
            continue

        file_url = item.get("url", "")
        parsed = urlparse(file_url)
        base_url = "{}://{}".format(parsed.scheme, parsed.netloc)

        try:
            resp = requests.get(file_url, headers={"User-Agent": UA}, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            if log_fn:
                log_fn("    [跳过] 请求失败: {}".format(str(e)))
            continue

        a_tags = soup.find_all("a")
        found_count = 0

        for a in a_tags:
            href = a.get("href", "")
            if not href:
                continue

            href_lower = href.lower()
            has_suffix = any(href_lower.endswith(s) for s in TARGET_SUFFIXES)
            has_url_param = bool(re.search(r"url=([^&\"\s]+)", href, re.IGNORECASE))

            if not (has_suffix or has_url_param):
                continue

            actual_url = re.search(r"url=([^&\"\s]+)", href, re.IGNORECASE)
            if actual_url:
                full_url = actual_url.group(1)
                if not full_url.startswith("http"):
                    full_url = urljoin(base_url, full_url)
            else:
                full_url = urljoin(base_url, href)
                if not full_url.startswith("http"):
                    full_url = "https://www.sec.gov" + full_url if full_url.startswith("/") else "https://www.sec.gov/" + full_url

            full_url_lower = full_url.lower()

            if full_url_lower.endswith(".pdf"):
                attachment_form = "PDF附件"
            else:
                attachment_form = "HTML附件"

            if full_url in seen_urls:
                continue

            seen_urls.add(full_url)

            extra_items.append({
                "id": item["id"],
                "date": item["date"],  # 保留原始日期格式，与父 filing 一致
                "form": attachment_form,
                "url": full_url,
                "_parent_form": form,
                "_parent_url": file_url,
            })
            found_count += 1

            if log_fn and found_count <= 3:
                log_fn("    [发现] {} → {}".format(form, full_url.rsplit("/", 1)[-1] if "/" in full_url else full_url))

        if found_count > 0 and log_fn:
            log_fn("    [发现] {} 个嵌套附件".format(found_count))

    if log_fn and extra_items:
        log_fn("[OK] 6-K/8-K 嵌套提取完成，共发现 {} 个附件".format(len(extra_items)))

    return extra_items


def expand_filings_with_nested(filings, log_fn=None, should_stop_fn=None):
    """展开 filings 列表：对 6-K/8-K 提取嵌套附件并合并

    原始条目保留不变，附件追加到列表末尾，然后按日期排序重新编号。

    Args:
        filings: fetch_sec_filings 返回的文件列表
        log_fn: 日志回调
        should_stop_fn: 停止检查

    Returns:
        合并后的完整文件列表
    """
    if log_fn:
        log_fn("[INFO] 正在扫描 6-K/8-K 文件的嵌套附件...")

    extra = extract_nested_links(filings, log_fn=log_fn, should_stop_fn=should_stop_fn)
    merged = list(filings) + extra
    merged.sort(key=lambda x: x["date"])

    for idx, item in enumerate(merged):
        item["id"] = idx + 1

    if log_fn:
        log_fn("[OK] 展开后共 {} 个文件（原始 {} + 附件 {}）".format(len(merged), len(filings), len(extra)))

    return merged


def export_us_excel(results, output_dir, log_fn=None):
    """导出美股 SEC 披露文件数据到 Excel

    Args:
        results: 结果列表，每项为 dict，含 date/cik/form/url/ai_response
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
    ws.title = "SEC披露文件"

    headers = [
        "日期", "CIK", "文件类型", "文件链接", "AI分析结果"
    ]

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)

    for row_idx, item in enumerate(results, 2):
        ws.cell(row=row_idx, column=1).value = item.get("日期", "")
        ws.cell(row=row_idx, column=2).value = item.get("CIK", "")
        ws.cell(row=row_idx, column=3).value = item.get("文件类型", "")
        ws.cell(row=row_idx, column=4).value = item.get("文件链接", "")
        ws.cell(row=row_idx, column=5).value = item.get("AI分析结果", "")

    col_widths = [15, 15, 12, 60, 80]
    for i, width in enumerate(col_widths, 1):
        col_letter = chr(64 + i) if i <= 26 else "A" + chr(64 + i - 26)
        ws.column_dimensions[col_letter].width = width

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cik = results[0].get("CIK", "unknown") if results else "unknown"
    filepath = os.path.join(output_dir, "SEC数据_{}_{}.xlsx".format(cik, ts))
    wb.save(filepath)

    if log_fn:
        log_fn("[OK] Excel 已导出: " + filepath)

    return filepath
