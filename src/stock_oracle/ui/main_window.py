"""主窗口：集成 5 个 Tab。"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QStatusBar,
    QMessageBox,
)
from PySide6.QtCore import Qt

from .. import __version__
from ..data.fetcher import DataFetcher
from ..data import db as _db
from .widgets.data_center import DataCenterWidget
from .widgets.screener import ScreenerWidget
from .widgets.watcher import WatcherWidget
from .widgets.quote import QuoteWidget
from .widgets.settings import SettingsWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"StockOracle - 智能选股工具 v{__version__}")
        self.resize(1280, 800)

        # 数据层
        _db.init_db()
        self.fetcher = DataFetcher()

        # 中央窗口
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        self.setCentralWidget(central)

        # 标签页
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        self.data_center = DataCenterWidget(self.fetcher)
        self.screener = ScreenerWidget(self.fetcher)
        self.watcher = WatcherWidget(self.fetcher)
        self.quote = QuoteWidget(self.fetcher)
        self.settings = SettingsWidget()

        self.tabs.addTab(self.data_center, "📊 数据中心")
        self.tabs.addTab(self.screener, "🎯 选股中心")
        self.tabs.addTab(self.watcher, "👁 盯盘中心")
        self.tabs.addTab(self.quote, "📈 行情中心")
        self.tabs.addTab(self.settings, "⚙ 设置")

        # 跨 Tab 信号：选股/盯盘双击 → 行情中心
        self.screener.code_clicked.connect(self._on_code_clicked)
        self.watcher.code_clicked.connect(self._on_code_clicked)

        # 状态栏
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage(f"StockOracle v{__version__}  |  数据源: akshare  |  "
                       f"本地数据: {self.fetcher.get_local_stock_list().shape[0]} 只股票")

    def _on_code_clicked(self, code: str):
        self.tabs.setCurrentWidget(self.quote)
        self.quote.show_code(code)

    def closeEvent(self, event):
        # 优雅关闭
        try:
            self.watcher._stop_current_watcher()
        except Exception:
            pass
        event.accept()
