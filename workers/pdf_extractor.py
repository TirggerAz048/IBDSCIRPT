"""
PDF 文本提取通用模块

使用 PyMuPDF (fitz) 从 URL 下载 PDF 并提取纯文本。
适用于港股 HKEX 披露文件和美股 SEC 文件中的 PDF 类型。

用法:
    from workers.pdf_extractor import download_and_extract_pdf

    text = download_and_extract_pdf("https://www1.hkexnews.hk/.../xxx.pdf")
    if text:
        print(text)  # 提取到的纯文本（最多 MAX_CHARS 字符）
"""

import os
import time
import hashlib
import requests
import fitz

MAX_CHARS = 120000
MAX_RETRIES = 5
RETRY_INTERVAL = 1
UA = "IBDspider/1.0 contact@example.com"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache", "pdf_text")
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(url):
    """根据 URL 生成缓存文件路径"""
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, "{}.txt".format(url_hash))


def download_and_extract_pdf(url, max_chars=MAX_CHARS, use_cache=False, timeout=60):
    """从 URL 下载 PDF 并提取纯文本

    Args:
        url: PDF 文件的 URL
        max_chars: 最多提取的字符数，默认 8000
        use_cache: 是否使用缓存，默认 True
        timeout: 下载超时秒数，默认 60

    Returns:
        str: 提取到的纯文本；失败返回空字符串
    """
    cache_path = _get_cache_path(url)

    if use_cache and os.path.exists(cache_path):
        with open(cache_path, mode="r", encoding="utf-8") as f:
            text = f.read()
            return text

    last_error = ""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "").lower()

            if "pdf" not in content_type and len(resp.content) < 1000:
                last_error = "[下载内容不是PDF或内容过小]"
                continue

            doc = fitz.open(stream=resp.content, filetype="pdf")
            full_text = ""
            for page in doc:
                page_text = page.get_text("text")
                full_text += page_text + "\n"
            doc.close()

            full_text = full_text.strip()
            if not full_text:
                return "[PDF内容为空（可能是扫描件）]"

            if len(full_text) > max_chars:
                full_text = full_text[:max_chars] + "\n\n[... 文档过长，已截取前 {} 字符（共 {} 字符）]".format(max_chars, len(full_text))

            with open(cache_path, mode="w", encoding="utf-8") as f:
                f.write(full_text)
            return full_text

        except Exception as e:
            last_error = "[PDF下载失败(重试{}次): {}]".format(attempt + 1, str(e))
            time.sleep(RETRY_INTERVAL)

    return ""


def is_pdf_url(url):
    """判断 URL 是否指向 PDF 文件

    Args:
        url: 文件 URL

    Returns:
        bool: True 表示是 PDF
    """
    url_lower = url.lower().split("?")[0]
    return url_lower.endswith(".pdf")
