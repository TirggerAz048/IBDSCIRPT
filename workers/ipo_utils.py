"""
IPO 工具函数模块

从 SecPythonWebCrawler/utiles.py 迁移，包含：
- 华人姓氏、中国地区数据集
- 中概股四重识别函数
- HTTP 安全请求工具
- 财务段落识别
"""
import re
import json
import random
import time
import requests

SEC_UA = "IBDspider/1.0 contact@example.com"

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CHINESE_SURNAMES = {
    "Li", "Wang", "Zhang", "Liu", "Chen", "Yang", "Zhao", "Huang", "Zhou", "Wu",
    "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "He", "Gao", "Lin", "Luo",
    "Tang", "Xue", "Cai", "Liang", "Han", "Shen", "Zheng", "Yuan", "Pan", "Deng",
    "Zeng", "Yue", "Yu", "Yao", "Ye", "Yan", "Xie", "Xiao", "Xia", "Wen",
    "Wei", "Wan", "Song", "Shao", "Qian", "Qin", "Qi", "Peng", "Ou", "Niu",
    "Nie", "Lu", "Lei", "Kang", "Jiang", "Ji", "Hong", "Gong", "Fu", "Fan",
    "Fang", "Cao", "Cheng", "Chai", "Bian", "Bi", "Bai", "An", "Ai", "Zou",
    "Zhen", "Zhan", "Jin", "Qiu", "Hou", "Meng", "Yuwen", "Ouyang", "Sima",
    "Shangguan", "Huangfu", "Ouyang",
}

CHINA_REGIONS = {
    "Beijing", "beijing", "Bei Jing", "bei jing", "BEIJING", "BEI JING",
    "Shanghai", "shanghai", "Shang Hai", "shang hai", "SHANGHAI", "SHANG HAI",
    "Tianjin", "tianjin", "Tian Jin", "tian jin", "TIANJIN", "TIAN JIN",
    "Chongqing", "chongqing", "Chong Qing", "chong qing", "CHONGQING", "CHONG QING",
    "Guangdong", "guangdong", "Guang Dong", "guang dong", "GUANGDONG", "GUANG DONG",
    "Guangzhou", "guangzhou", "Guang Zhou", "guang zhou", "GUANGZHOU", "GUANG ZHOU",
    "Shenzhen", "shenzhen", "Shen Zhen", "shen zhen", "SHENZHEN", "SHEN ZHEN",
    "Zhejiang", "zhejiang", "Zhe Jiang", "zhe jiang", "ZHEJIANG", "ZHE JIANG",
    "Hangzhou", "hangzhou", "Hang Zhou", "hang zhou", "HANGZHOU", "HANG ZHOU",
    "Jiangsu", "jiangsu", "Jiang Su", "jiang su", "JIANGSU", "JIANG SU",
    "Nanjing", "nanjing", "Nan Jing", "nan jing", "NANJING", "NAN JING",
    "Suzhou", "suzhou", "Su Zhou", "su zhou", "SUZHOU", "SU ZHOU",
    "Sichuan", "sichuan", "Si Chuan", "si chuan", "SICHUAN", "SI CHUAN",
    "Chengdu", "chengdu", "Cheng Du", "cheng du", "CHENGDU", "CHENG DU",
    "Hubei", "hubei", "Hu Bei", "hu bei", "HUBEI", "HU BEI",
    "Wuhan", "wuhan", "Wu Han", "wu han", "WUHAN", "WU HAN",
    "Hunan", "hunan", "Hu Nan", "hu nan", "HUNAN", "HU NAN",
    "Changsha", "changsha", "Chang Sha", "chang sha", "CHANGSHA", "CHANG SHA",
    "Fujian", "fujian", "Fu Jian", "fu jian", "FUJIAN", "FU JIAN",
    "Xiamen", "xiamen", "Xia Men", "xia men", "XIAMEN", "XIA MEN",
    "Quanzhou", "quanzhou", "Quan Zhou", "quan zhou", "QUANZHOU", "QUAN ZHOU",
    "Shandong", "shandong", "Shan Dong", "shan dong", "SHANDONG", "SHAN DONG",
    "Jinan", "jinan", "Ji Nan", "ji nan", "JINAN", "JI NAN",
    "Qingdao", "qingdao", "Qing Dao", "qing dao", "QINGDAO", "QING DAO",
    "Henan", "henan", "He Nan", "he nan", "HENAN", "HE NAN",
    "Zhengzhou", "zhengzhou", "Zheng Zhou", "zheng zhou", "ZHENGZHOU", "ZHENG ZHOU",
    "Hebei", "hebei", "He Bei", "he bei", "HEBEI", "HE BEI",
    "Shijiazhuang", "shijiazhuang", "Shi Jia Zhuang", "shi jia zhuang", "SHIJIAZHUANG", "SHI JIA ZHUANG",
    "Liaoning", "liaoning", "Liao Ning", "liao ning", "LIAONING", "LIAO NING",
    "Shenyang", "shenyang", "Shen Yang", "shen yang", "SHENYANG", "SHEN YANG",
    "Dalian", "dalian", "Da Lian", "da lian", "DALIAN", "DA LIAN",
    "Heilongjiang", "heilongjiang", "Hei Long Jiang", "hei long jiang", "HEILONGJIANG", "HEI LONG JIANG",
    "Harbin", "harbin", "Ha Er Bin", "ha er bin", "HARBIN", "HA ER BIN",
    "Jilin", "jilin", "Ji Lin", "ji lin", "JILIN", "JI LIN",
    "Changchun", "changchun", "Chang Chun", "chang chun", "CHANGCHUN", "CHANG CHUN",
    "Anhui", "anhui", "An Hui", "an hui", "ANHUI", "AN HUI",
    "Hefei", "hefei", "He Fei", "he fei", "HEFEI", "HE FEI",
    "Jiangxi", "jiangxi", "Jiang Xi", "jiang xi", "JIANGXI", "JIANG XI",
    "Nanchang", "nanchang", "Nan Chang", "nan chang", "NANCHANG", "NAN CHANG",
    "Guangxi", "guangxi", "Guang Xi", "guang xi", "GUANGXI", "GUANG XI",
    "Nanning", "nanning", "Nan Ning", "nan ning", "NANNING", "NAN NING",
    "Yunnan", "yunnan", "Yun Nan", "yun nan", "YUNNAN", "YUN NAN",
    "Kunming", "kunming", "Kun Ming", "kun ming", "KUNMING", "KUN MING",
    "Guizhou", "guizhou", "Gui Zhou", "gui zhou", "GUIZHOU", "GUI ZHOU",
    "Guiyang", "guiyang", "Gui Yang", "gui yang", "GUIYANG", "GUI YANG",
    "Shanxi", "shanxi", "Shan Xi", "shan xi", "SHANXI", "SHAN XI",
    "Taiyuan", "taiyuan", "Tai Yuan", "tai yuan", "TAIYUAN", "TAI YUAN",
    "Shaanxi", "shaanxi", "Shaan Xi", "shaan xi", "SHAANXI", "SHAAN XI",
    "Xian", "xian", "Xi An", "xi an", "XIAN", "XI AN",
    "Gansu", "gansu", "Gan Su", "gan su", "GANSU", "GAN SU",
    "Lanzhou", "lanzhou", "Lan Zhou", "lan zhou", "LANZHOU", "LAN ZHOU",
    "Inner Mongolia", "inner mongolia", "INNER MONGOLIA",
    "Neimenggu", "neimenggu", "Nei Meng Gu", "nei meng gu", "NEIMENGGU", "NEI MENG GU",
    "Ningxia", "ningxia", "Ning Xia", "ning xia", "NINGXIA", "NING XIA",
    "Xinjiang", "xinjiang", "Xin Jiang", "xin jiang", "XINJIANG", "XIN JIANG",
    "Xinjiang Uygur", "xinjiang uygur", "XINJIANG UYGHUR",
    "Tibet", "tibet", "Xi Zang", "xi zang", "TIBET", "XI ZANG",
    "Hong Kong", "hong kong", "Hongkong", "hongkong", "HK", "hk", "HONG KONG", "HONGKONG", "HK", "HK",
    "Macau", "macau", "Macao", "macao", "MACAU", "MACAO",
    "Taiwan", "taiwan", "Tai Wan", "tai wan", "TAIWAN", "TAI WAN",
    "Taipei", "taipei", "Tai Pei", "tai pei", "TAIPEI", "TAI PEI",
    "Taitung", "taitung", "Tai Tung", "tai tung", "TAITUNG", "TAI TUNG",
    "Kaohsiung", "kaohsiung", "Kao Hsiung", "kao hsiung", "KAOHSIUNG", "KAO HSIUNG",
    "Tainan", "tainan", "Tai Nan", "tai nan", "TAINAN", "TAI NAN",
    "Taichung", "taichung", "Tai Chung", "tai chung", "TAICHUNG", "TAI CHUNG",
    "Taoyuan", "taoyuan", "Tao Yuan", "tao yuan", "TAOYUAN", "TAO YUAN",
    "Hsinchu", "hsinchu", "Hsin Chu", "hsin chu", "HSINCHU", "HSIN CHU",
    "Miaoli", "miaoli", "Miao Li", "miao li", "MIAOLI", "MIAO LI",
    "Changhua", "changhua", "Chang Hua", "chang hua", "CHANGHUA", "CHANG HUA",
    "Nantou", "nantou", "Nan Tou", "nan tou", "NANTOU", "NAN TOU",
    "Yunlin", "yunlin", "Yun Lin", "yun lin", "YUNLIN", "YUN LIN",
    "Chiayi", "chiayi", "Cha Yi", "cha yi", "CHIAYI", "CHA YI",
    "Pingtung", "pingtung", "Ping Tung", "ping tung", "PINGTUNG", "PING TUNG",
    "Hualien", "hualien", "Hua Lien", "hua lien", "HUALIEN", "HUA LIEN",
    "Penghu", "penghu", "Peng Hu", "peng hu", "PENGHU", "PENG HU",
    "Kinmen", "kinmen", "Jin Men", "jin men", "KINMEN", "JIN MEN",
    "Matsu", "matsu", "Ma Zu", "ma zu", "MATSU", "MA ZU",
}


def check_phone_number(res):
    """检查电话是否以 86 或 852 开头"""
    try:
        phone = res.get("data", {}).get("poOverview", {}).get("PhoneNumber", {}).get("value", "")
        return phone.strip().startswith(("86", "852"))
    except Exception:
        return False


def check_address(res):
    """检查地址是否包含中国/香港地区关键词"""
    try:
        address = res.get("data", {}).get("poOverview", {}).get("Address", {}).get("value", "").lower()
        if "hongkong" in address or "hk" in address or "hong kong" in address:
            return True
        for region in [r.lower() for r in CHINA_REGIONS]:
            if region in address:
                return True
    except Exception:
        pass
    return False


def check_company_info_china(res):
    """检查公司描述中是否含 china/prc（排除否定句）"""
    try:
        info = res.get("data", {}).get("companyInformation", {}).get("companyDescription", "").lower()
        if "china" in info or "prc" in info:
            negations = ["not", "no", "never", "without", "except", "excluding"]
            for neg in negations:
                if neg in info:
                    neg_pos = info.find(neg)
                    china_pos = min(
                        [p for p in [info.find("china"), info.find("prc")] if p != -1] or [-1]
                    )
                    if neg_pos != -1 and china_pos != -1 and china_pos - neg_pos < 100:
                        return False
            return True
    except Exception:
        pass
    return False


def check_company_info_address(res):
    """检查公司描述中是否含中国地区关键词"""
    try:
        info = res.get("data", {}).get("companyInformation", {}).get("companyDescription", "").lower()
        if "hongkong" in info or "hk" in info or "hong kong" in info:
            return True
        for region in [r.lower() for r in CHINA_REGIONS]:
            if region in info:
                return True
    except Exception:
        pass
    return False


def is_chinese_company(res):
    """四重判断是否为中概股"""
    if check_phone_number(res):
        print("电话符合中概股特征")
        return True
    if check_address(res):
        print("地址符合中概股特征")
        return True
    if check_company_info_china(res):
        print("介绍含PRC符合中概股特征")
        return True
    if check_company_info_address(res):
        print("文字内地址符合中概股特征")
        return True
    return False


def safe_request(url, headers=None, params=None, timeout=30, max_retries=5, expected_type="auto"):
    """带重试的 HTTP GET 请求"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            if expected_type == "json" or (
                "application/json" in response.headers.get("Content-Type", "")
                and expected_type == "auto"
            ):
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return None
            else:
                return response.text
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
            else:
                return None


def safe_get_json(url, headers=None, params=None, timeout=30, max_retries=5):
    """安全获取 JSON"""
    return safe_request(
        url, headers=headers, params=params,
        timeout=timeout, max_retries=max_retries, expected_type="json"
    )


def safe_get_html(url, headers=None, params=None, timeout=30, max_retries=5):
    """安全获取 HTML 文本"""
    return safe_request(
        url, headers=headers, params=params,
        timeout=timeout, max_retries=max_retries, expected_type="html"
    )


def get_nested_value(data, keys, default=""):
    """嵌套字典安全取值"""
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return default
        if result is None:
            return default
    return result


def getended(text):
    """识别财务报表段落关键词

    检查文本是否包含合并利润表标题关键词，
    用于定位招股书中财务数据章节。
    """
    list_keys = [
        "consolidated statements of income and comprehensive income for the years ended",
        "tatements of income and comprehensive income for the years ended",
        "statements of income for the years ended",
    ]
    for item in list_keys:
        if item in text:
            return item
    if "comprehensive" in text and "income" in text:
        return text
    return None
