"""
wechat_extract.py — 微信公众号划线数据 JS 提取模块

通过 QWebEngine 的 runJavaScript() 在内嵌浏览器中执行 JS，
从微信公众号后台「内容管理→已发布」页面提取文章标题和划线人数。

等价于原脚本 playmain.py 中 BeautifulSoup 的 extract_with_bs4() 逻辑。

DOM 结构：
  div.publish_hover_content
    └── div.weui-desktop-mass-appmsg__bd
        ├── a 标签 → 文章标题
        └── div.weui-desktop-mass-media__data-list
            └── 多个 div.weui-desktop-tooltip__wrp
                └── 倒数第3个 → span.weui-desktop-link → 划线人数
"""


def extract_underline_js():
    """返回提取划线数据的 JS 代码

    执行后返回 JSON 字符串：
    [{"title": "文章标题", "underline": "划线人数"}, ...]
    """
    return """
    (function() {
        var containers = document.querySelectorAll('div.publish_hover_content');
        var results = [];

        for (var i = 0; i < containers.length; i++) {
            var container = containers[i];
            try {
                var bd = container.querySelector('div.weui-desktop-mass-appmsg__bd');
                if (!bd) continue;

                var aTag = bd.querySelector('a');
                var title = aTag ? aTag.textContent.trim() : '(无标题)';

                var dataList = container.querySelector('div.weui-desktop-mass-media__data-list');
                if (!dataList) {
                    results.push({title: title, underline: ''});
                    continue;
                }

                var tooltips = dataList.querySelectorAll('div.weui-desktop-tooltip__wrp');
                var underline = '';

                if (tooltips.length >= 3) {
                    var target = tooltips[tooltips.length - 3];
                    var linkSpan = target.querySelector('span.weui-desktop-link');
                    underline = linkSpan ? linkSpan.textContent.trim() : '';
                }

                results.push({title: title, underline: underline});
            } catch (e) {
                results.push({title: '(解析异常)', underline: ''});
            }
        }

        return JSON.stringify(results);
    })();
    """
