from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from qfluentwidgets import ScrollArea, TitleLabel, BodyLabel, CardWidget


def _card_layout(card, margin=16, spacing=10):
    lay = QVBoxLayout(card)
    lay.setContentsMargins(margin, margin, margin, margin)
    lay.setSpacing(spacing)
    return lay


class ShowDeepseek(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ShowDeepseek")
        self._setup_ui()

    def _setup_ui(self):
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(28, 20, 28, 20)
        self.layout.setSpacing(16)

        title_card = CardWidget(self)
        vBox = _card_layout(title_card, margin=24, spacing=8)

        title = TitleLabel("IBD Spider v2.0")
        title.setStyleSheet("font-size: 24px;")
        vBox.addWidget(title)

        subtitle = BodyLabel("金融数据集成工具 — 网页版 AI 可视化交互")
        subtitle.setStyleSheet("color: #909090;")
        vBox.addWidget(subtitle)

        self.layout.addWidget(title_card)

        desc_card = CardWidget(self)
        vBox = _card_layout(desc_card)

        features = [
            ("港股获取", "HKEX 披露文件抓取 + DeepSeek AI 分析"),
            ("美股获取", "SEC EDGAR 公告抓取 + DeepSeek AI 分析"),
            ("中概股 IPO", "NASDAQ IPO 数据采集"),
            ("公众号获取", "微信公众号文章采集"),
        ]
        for name, desc in features:
            label = BodyLabel(f"<b>{name}</b> — {desc}")
            label.setWordWrap(True)
            label.setStyleSheet("padding: 4px 0;")
            vBox.addWidget(label)

        self.layout.addWidget(desc_card)

        placeholder_card = CardWidget(self)
        vBox = _card_layout(placeholder_card)
        hint = BodyLabel("这里将嵌入 DeepSeek WebEngine 浏览器")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #606060; font-size: 13px; padding: 40px;")
        vBox.addWidget(hint)
        self.layout.addWidget(placeholder_card)

        self.layout.addStretch()
        self.setWidget(self.container)

        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.container.setStyleSheet("QWidget { background: transparent; }")
