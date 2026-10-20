import sys
import os
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QFrame, QToolButton, QStackedWidget, QSizePolicy)
from PyQt6.QtCore import (Qt, QSize, QPropertyAnimation, QEasingCurve,
                          pyqtProperty, pyqtSignal)
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor
from qfluentwidgets import (Pivot, NavigationItemPosition, FluentIcon,
                             TitleLabel, PushButton, PrimaryPushButton,
                             ToolButton, TextEdit, LineEdit, ComboBox,
                             ProgressBar, BodyLabel, CardWidget,
                             StrongBodyLabel, CaptionLabel, InfoBar,
                             InfoBarPosition, TransparentToolButton)
from gui.panels.hk_panel import HKPanel
from gui.panels.us_panel import USPanel
from gui.panels.ipo_panel import IpoPanel
from gui.panels.wechat_panel import WechatPanel
from gui.panels.settings_panel import SettingsPanel

TAB_INDEX = {"hk": 0, "us": 1, "ipo": 2, "wechat": 3, "settings": 4}


class CollapsibleSideBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._min_width = 0
        self._max_width = 340
        self._expanded = True
        self._width_value = self._max_width
        self._animation = None
        self.setFixedWidth(self._max_width)
        self.setMinimumHeight(0)
        self._inner_layout = QVBoxLayout(self)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)
        self._inner_widget = None

    def set_inner_widget(self, widget):
        self._inner_widget = widget
        self._inner_layout.addWidget(widget, 1)

    def get_width(self):
        return self._width_value

    def set_width(self, w):
        self._width_value = w
        self.setFixedWidth(w)
        if w <= 0 and self._inner_widget:
            self._inner_widget.hide()
        else:
            if self._inner_widget:
                self._inner_widget.show()

    width_prop = pyqtProperty(int, get_width, set_width)

    def toggle(self):
        if self._expanded:
            self._collapse()
        else:
            self._expand()

    def _collapse(self):
        self._expanded = False
        self._animate_to(self._min_width)

    def _expand(self):
        self._expanded = True
        if self._inner_widget:
            self._inner_widget.show()
        self._animate_to(self._max_width)

    def _animate_to(self, target_width):
        if self._animation and self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()
        self._animation = QPropertyAnimation(self, b"width_prop")
        self._animation.setDuration(250)
        self._animation.setStartValue(int(self.width_prop))
        self._animation.setEndValue(target_width)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.start()

    def is_expanded(self):
        return self._expanded


class MainWindow(QWidget):
    ai_response_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("IBD Spider")
        _icon_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        self.setWindowIcon(QIcon(os.path.join(_icon_dir, "mian.ico")))
        self._setup_ui()
        self._set_dark_title_bar()
        self._injector = None
        self._ipo_injector = None
        self._current_worker = None
        self._worker_running = False
        self._status_text = ""

    def _update_status(self, text):
        self._status_text = text
        self.status_label.setText(text)
        self.setWindowTitle("IBD Spider — " + text)

    def _set_dark_title_bar(self):
        if sys.platform == "win32":
            try:
                ctypes = __import__('ctypes')
                hwnd = int(self.winId())
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        # 顶部导航栏
        nav_bar = QWidget()
        nav_bar.setObjectName("topNavBar")
        nav_bar.setFixedHeight(44)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 0, 12, 0)
        nav_layout.setSpacing(6)
        toggle_btn = TransparentToolButton(FluentIcon.MENU)
        toggle_btn.setFixedSize(36, 36)
        toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        toggle_btn.setStyleSheet(
            "TransparentToolButton{background:transparent;border:none;color:white;}"
            "TransparentToolButton:hover{background:rgba(255,255,255,0.08);}"
        )
        toggle_btn.clicked.connect(self._toggle_sidebar)
        self.toggle_btn = toggle_btn
        nav_layout.addWidget(toggle_btn)
        self.pivot = Pivot(parent=nav_bar)
        self.pivot.setObjectName("navPivot")
        self._build_tabs()
        nav_layout.addWidget(self.pivot, 1)
        root_layout.addWidget(nav_bar)
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        sidebar = CollapsibleSideBar()
        self.sidebar = sidebar
        sidebar.setObjectName("sideBar")
        sidebar_inner = QWidget()
        sidebar_inner.setObjectName("sideBarInner")
        left_layout = QVBoxLayout(sidebar_inner)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        sidebar.set_inner_widget(sidebar_inner)
        self.left_layout = left_layout
        left_panel = self._build_left_panel()
        right_panel, right_layout = self._build_right_panel()
        content_layout.addWidget(sidebar)
        content_layout.addLayout(right_layout)
        root_layout.addWidget(content_area, 1)
        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(8, 0, 12, 0)
        status_label = CaptionLabel("就绪")
        self.status_label = status_label
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        root_layout.addWidget(status_bar)

    def _toggle_sidebar(self):
        self.sidebar.toggle()
        expanded = self.sidebar.is_expanded()
        try:
            if expanded:
                self.toggle_btn.setIcon(FluentIcon.MENU)
                self.toggle_btn.setToolTip("收起侧边栏")
            else:
                self.toggle_btn.setIcon(FluentIcon.CANCEL)
                self.toggle_btn.setToolTip("展开侧边栏")
        except Exception:
            self.toggle_btn.setText("☰" if expanded else "✕")

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def _build_left_panel(self):
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(0)
        panel_title = StrongBodyLabel("控制面板")
        panel_title.setStyleSheet("font-size: 14px; padding: 4px 0;")
        title_row.addWidget(panel_title)
        title_row.addStretch()
        self.left_layout.addLayout(title_row)
        panel_stack = QStackedWidget()
        self.panel_stack = panel_stack
        panel_stack.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)
        self.left_layout.addWidget(panel_stack)
        panel_stack.addWidget(HKPanel())
        panel_stack.addWidget(USPanel())
        panel_stack.addWidget(IpoPanel())
        panel_stack.addWidget(WechatPanel())
        panel_stack.addWidget(SettingsPanel())
        return panel_stack

    def _build_right_panel(self):
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
        from PyQt6.QtCore import QUrl, QStandardPaths
        import os as _os

        profile_path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        profile = QWebEngineProfile("deepseek_profile")
        profile.setPersistentStoragePath(os.path.join(profile_path, "webengine"))
        self._web_profile = profile
        web_view = QWebEngineView()
        self.web_view = web_view
        web_view.setObjectName("webView")

        def create_window(type_hint):
            import webbrowser
            url = self.web_view.url().toString()
            self._update_status("已在新窗口打开: " + url)
            webbrowser.open(url)
            return None

        page = QWebEnginePage(profile, web_view)
        self._web_page = page
        page.createWindow = create_window
        web_view.setPage(page)
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        page.setDevToolsPage(None)
        web_view.page().runJavaScript("", 0)
        web_view.installEventFilter(self)
        self._devtools_opened = False
        web_view.setUrl(QUrl("https://chat.deepseek.com/"))
        web_view.loadProgress.connect(lambda p: self._update_status(f"页面加载中... {p}%"))
        web_view.loadFinished.connect(lambda ok: self._update_status("就绪" if ok else "页面加载失败"))
        profile.downloadRequested.connect(self._on_download_requested)
        web_view.page().featurePermissionRequested.connect(self._on_feature_permission)
        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(web_view)
        return web_view, right_layout

    def get_web_view(self):
        return self.web_view

    def get_injector(self, injector_type):
        if injector_type == "wechat":
            # 微信公众号不需要 AI 注入器
            return None
        if hasattr(self, '_ipo_injector') and injector_type == "ipo":
            from workers.ai.ipo_injector import IpoInjector
            if self._ipo_injector is None:
                self._ipo_injector = IpoInjector(self.web_view, self.status_label)
            return self._ipo_injector
        if self._injector is None:
            from workers.ai.deepseek_injector import DeepSeekInjector
            self._injector = DeepSeekInjector(self.web_view, self.status_label, parent=self)
        return self._injector

    def on_send_to_ai(self, text):
        """发送文本到内嵌浏览器的 DeepSeek AI

        流程:
        1. 验证浏览器当前是否在 chat.deepseek.com，不在则自动导航
        2. 等待页面加载完成（最多 15 秒）
        3. 通过注入器发送文本并启动轮询
        """
        from PyQt6.QtCore import QUrl, QEventLoop, QTimer

        # ── 步骤 1: 验证浏览器 URL ──
        current_url = self.web_view.url().toString()
        if "deepseek.com" not in current_url:
            self._update_status("浏览器不在 DeepSeek，正在自动导航...")
            self.web_view.setUrl(QUrl("https://chat.deepseek.com/"))

            # 等待页面加载完成
            loop = QEventLoop()
            def _on_load_finished(ok):
                loop.quit()
            self.web_view.loadFinished.connect(_on_load_finished)
            QTimer.singleShot(15000, loop.quit)  # 15 秒超时
            loop.exec()
            # 断开信号避免重复连接
            try:
                self.web_view.loadFinished.disconnect(_on_load_finished)
            except (TypeError, RuntimeError):
                pass
            self._update_status("DeepSeek 页面已就绪")

        # ── 步骤 2: 选择注入器并发送 ──
        worker = getattr(self, '_current_worker', None)
        worker_type = type(worker).__name__ if worker else ""
        if worker_type == "IpoWorker":
            injector = self.get_injector("ipo")
        else:
            injector = self.get_injector("deepseek")
        injector.send(text, callback=lambda response: self._on_ai_complete(worker, response))

    def _on_ai_complete(self, worker, response):
        self.ai_response_received.emit(response)

    def stop_injector(self):
        if self._injector:
            self._injector.stop()
        if hasattr(self, '_ipo_injector'):
            self._ipo_injector.stop()

    def run_js(self, script, callback=None):
        self.web_view.page().runJavaScript(script, 0, callback)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if hasattr(self, 'web_view') and self.web_view and obj is self.web_view and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
            shift = modifiers & Qt.KeyboardModifier.ShiftModifier
            if ctrl and shift:
                if key == Qt.Key.Key_I or key == Qt.Key.Key_J or key == Qt.Key.Key_C:
                    self._toggle_devtools()
                    return True
                if key == Qt.Key.Key_F12:
                    self._toggle_devtools()
                    return True
        return super().eventFilter(obj, event)

    def _toggle_devtools(self):
        page = self.web_view.page()
        if self._devtools_opened:
            page.setDevToolsPage(None)
            self._update_status("DevTools 已关闭")
            self._devtools_opened = False
        else:
            from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
            profile = QWebEngineProfile.defaultProfile()
            devtools_page = QWebEnginePage(profile, self.web_view)
            page.setDevToolsPage(devtools_page)
            devtools_page.setFocus()
            self._update_status("DevTools 已打开 (Ctrl+Shift+I 关闭)")
            self._devtools_opened = True

    def _on_download_requested(self, download):
        import webbrowser
        url = download.url().toString()
        self._update_status("正在外部浏览器打开: " + url)
        download.cancel()
        webbrowser.open(url)

    def _on_feature_permission(self, url, feature, granted):
        from PyQt6.QtWebEngineCore import QWebEnginePage
        page = self.web_view.page()
        page.setFeaturePermission(
            url, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
        )

    def _build_tabs(self):
        self.pivot.addItem(
            routeKey="hk",
            text="港股获取",
            onClick=lambda: self._switch_tab("hk"),
        )
        self.pivot.addItem(
            routeKey="us",
            text="美股获取",
            onClick=lambda: self._switch_tab("us"),
        )
        self.pivot.addItem(
            routeKey="ipo",
            text="中概股 IPO",
            onClick=lambda: self._switch_tab("ipo"),
        )
        self.pivot.addItem(
            routeKey="wechat",
            text="公众号",
            onClick=lambda: self._switch_tab("wechat"),
        )
        self.pivot.setCurrentItem("hk")

    def lock_all_panels(self, running_panel):
        self._worker_running = True
        self._running_tab_index = self.panel_stack.indexOf(running_panel) if running_panel else 0
        for i in range(self.panel_stack.count()):
            panel = self.panel_stack.widget(i)
            if hasattr(panel, 'lock_controls'):
                panel.lock_controls(keep_stop_enabled=(panel is running_panel))

    def unlock_all_panels(self):
        self._worker_running = False
        self._running_tab_index = None
        for i in range(self.panel_stack.count()):
            panel = self.panel_stack.widget(i)
            if hasattr(panel, 'unlock_controls'):
                panel.unlock_controls()

    def _switch_tab(self, key):
        index = TAB_INDEX.get(key, 0)
        tab_names = {
            "hk": "港股获取",
            "us": "美股获取",
            "ipo": "中概股 IPO",
            "wechat": "公众号",
            "settings": "设置"
        }
        # 工作流运行期间：禁止切换面板和浏览器跳转，保护 AI 注入器的页面上下文
        if self._worker_running:
            running_idx = getattr(self, '_running_tab_index', None) or 0
            running_key = list(TAB_INDEX.keys())[running_idx] if running_idx < len(TAB_INDEX) else "hk"
            if hasattr(self, 'pivot'):
                self.pivot.setCurrentItem(running_key)
            self._update_status("当前任务运行中 — 请等待任务完成后再切换")
            InfoBar.warning(
                title="任务运行中",
                content="工作流正在执行，请等待任务完成后再切换页面",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
            return
        self.panel_stack.setCurrentIndex(index)
        if hasattr(self, 'pivot'):
            self.pivot.setCurrentItem(key)
        self._update_status(tab_names.get(key, ""))
        from PyQt6.QtCore import QUrl
        if key == "wechat":
            self.web_view.load(QUrl("https://mp.weixin.qq.com/"))
        elif key == "settings":
            self.web_view.load(QUrl("https://chat.deepseek.com/"))
        else:
            # HK/US/IPO tab: 每次切换都重新加载 DeepSeek
            self.web_view.load(QUrl("https://chat.deepseek.com/"))
