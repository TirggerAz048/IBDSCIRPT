from .base_panel import BasePanel
from qfluentwidgets import BodyLabel


class SettingsPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title("设置")
        card, layout = self.add_card()
        layout.addWidget(BodyLabel("（设置选项待添加）"))
