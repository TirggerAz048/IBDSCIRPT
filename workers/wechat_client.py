"""
wechat_client.py — 微信公众号 API 客户端

通过云服务器（8.129.133.177:5000）转发微信 API 请求：
- 获取 access_token
- 获取文章统计数据（阅读量、点赞等）
- 生成 Excel 导出文件

云服务器的作用：微信 API 要求 IP 白名单，云服务器固定 IP 只需加一次白名单。
"""
import os
import re
import time
import requests
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font

PROXY_BASE = "http://8.129.133.177:5000"


def normalize_title(title):
    """归一化标题中的空白字符"""
    if not title:
        return ""
    title = title.replace('\xa0', ' ').replace('\u3000', ' ')
    return re.sub(r'\s+', ' ', title).strip()


def match_underline(title, norm_map):
    """用归一化标题匹配划线数据，返回 (划线人数, 匹配类型)"""
    tn = normalize_title(title)
    if tn in norm_map:
        return norm_map[tn][1], "exact"
    for nk, (_, val) in norm_map.items():
        if nk in tn or tn in nk:
            return val, "fuzzy"
    return "", None


def fetch_access_token(appid, secret):
    """通过云服务器获取 access_token

    Returns:
        access_token 字符串，失败返回 None
    """
    try:
        res = requests.get(
            PROXY_BASE + "/api/token",
            params={"appid": appid, "appsecret": secret},
            timeout=30
        )
        token_data = res.json()
        if "access_token" not in token_data:
            return None, token_data.get("errmsg", "未知错误")
        return token_data["access_token"], None
    except Exception as e:
        return None, str(e)


def fetch_articles(access_token, begin_date, end_date):
    """获取指定日期范围的文章统计数据

    Returns:
        list: 文章列表，每项为微信 API 返回的原始 dict
        str: 错误信息，成功为 None
    """
    try:
        res = requests.post(
            PROXY_BASE + "/api/articles",
            json={
                "access_token": access_token,
                "begin_date": begin_date,
                "end_date": end_date,
            },
            timeout=30
        )
        data = res.json()
        if "list" not in data:
            return [], data.get("errmsg", "未知错误")
        return data["list"], None
    except Exception as e:
        return [], str(e)


def generate_excel(all_articles, output_dir):
    """生成 Excel 文件

    Args:
        all_articles: 合并后的文章数据列表，每项为 dict（含中文字段名）
        output_dir: 输出目录路径

    Returns:
        str: 生成的 Excel 文件绝对路径
    """
    os.makedirs(output_dir, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "公众号文章数据"

    headers = [
        "文章发表日期", "作者", "文章标题",
        "阅读人数", "点赞人数", "转发人数",
        "推荐人数", "留言条数", "划线人数",
        "文章链接", "统计时间"
    ]

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)

    for row_idx, article in enumerate(all_articles, 2):
        ws.cell(row=row_idx, column=1, value=article.get("文章发表日期", ""))
        ws.cell(row=row_idx, column=2, value=article.get("作者", ""))
        ws.cell(row=row_idx, column=3, value=article.get("文章标题", ""))
        ws.cell(row=row_idx, column=4, value=article.get("阅读人数", ""))
        ws.cell(row=row_idx, column=5, value=article.get("点赞人数", ""))
        ws.cell(row=row_idx, column=6, value=article.get("转发人数", ""))
        ws.cell(row=row_idx, column=7, value=article.get("推荐人数", ""))
        ws.cell(row=row_idx, column=8, value=article.get("留言条数", ""))
        ws.cell(row=row_idx, column=9, value=article.get("划线人数", ""))
        ws.cell(row=row_idx, column=10, value=article.get("文章链接", ""))
        ws.cell(row=row_idx, column=11, value=article.get("统计时间", ""))

    col_widths = [15, 8, 45, 12, 12, 12, 12, 12, 10, 55, 18]
    for i, width in enumerate(col_widths, 1):
        col_letter = chr(64 + i) if i <= 26 else "A" + chr(64 + i - 26)
        ws.column_dimensions[col_letter].width = width

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "公众号文章数据_" + timestamp + ".xlsx"
    filepath = os.path.join(output_dir, filename)
    wb.save(filepath)

    return os.path.abspath(filepath)
