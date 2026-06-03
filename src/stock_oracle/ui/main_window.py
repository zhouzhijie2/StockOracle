"""主窗口：现代化风格，集成4个标签页（移除行情中心）。"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QStatusBar, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from .. import __version__
from ..data import db as _db
from ..data.fetcher import DataFetcher
from .widgets.data_center import DataCenterWidget
from .widgets.screener import ScreenerWidget
from .widgets.watcher import WatcherWidget
from .widgets.settings import SettingsWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"StockOracle · 智能选股工具 v{__version__}")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        # 数据层
        _db.init_db()
        self.fetcher = DataFetcher()

        # 中央容器
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 8)
        root_layout.setSpacing(12)
        self.setCentralWidget(central)

        # ========== 顶部标题栏 ==========
        header = QWidget()
        header.setFixedHeight(70)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(16)

        # 左侧：应用信息
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        title = QLabel("📈 StockOracle")
        title.setObjectName("appTitle")
        left_layout.addWidget(title)

        subtitle = QLabel("智能选股 · 行情监控 · 数据分析")
        subtitle.setObjectName("appSubtitle")
        left_layout.addWidget(subtitle)

        header_layout.addWidget(left)
        header_layout.addStretch(1)

        # 右侧：状态卡片
        self._build_stats(header_layout)

        root_layout.addWidget(header)

        # 分隔线
        hline = QFrame()
        hline.setObjectName("hLine")
        hline.setFrameShape(QFrame.HLine)
        root_layout.addWidget(hline)

        # ========== 标签页区域 ==========
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(True)

        self.data_center = DataCenterWidget(self.fetcher)
        self.screener = ScreenerWidget(self.fetcher)
        self.watcher = WatcherWidget(self.fetcher)
        self.settings = SettingsWidget()

        self.tabs.addTab(self.data_center, "  💾  数据中心  ")
        self.tabs.addTab(self.screener, "  🎯  选股中心  ")
        self.tabs.addTab(self.watcher, "  👁  盯盘中心  ")
        self.tabs.addTab(self.settings, "  ⚙  设置  ")

        root_layout.addWidget(self.tabs, stretch=1)

        # 状态栏
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.setStatusBar(sb)
        self._update_status_bar()

        # 跨 Tab 信号
        self.screener.code_clicked.connect(self._on_code_clicked)
        self.watcher.code_clicked.connect(self._on_code_clicked)
        self.data_center.data_updated.connect(self._update_status_bar)

    def _build_stats(self, parent_layout):
        """构建顶部的状态统计卡片。"""
        # 股票数量
        self.stat_stocks = QLabel("0")
        self.stat_stocks.setObjectName("statValue")
        self.stat_stocks.setAlignment(Qt.AlignCenter)
        label1 = QLabel("已缓存股票")
        label1.setObjectName("statLabel")
        label1.setAlignment(Qt.AlignCenter)
        card1 = self._make_stat_card(self.stat_stocks, label1)

        # 日线数据量
        self.stat_daily = QLabel("0")
        self.stat_daily.setObjectName("statValue")
        self.stat_daily.setAlignment(Qt.AlignCenter)
        label2 = QLabel("K 线数据")
        label2.setObjectName("statLabel")
        label2.setAlignment(Qt.AlignCenter)
        card2 = self._make_stat_card(self.stat_daily, label2)

        # 自选分组
        self.stat_watch = QLabel("0")
        self.stat_watch.setObjectName("statValue")
        self.stat_watch.setAlignment(Qt.AlignCenter)
        label3 = QLabel("自选分组")
        label3.setObjectName("statLabel")
        label3.setAlignment(Qt.AlignCenter)
        card3 = self._make_stat_card(self.stat_watch, label3)

        parent_layout.addWidget(card1)
        parent_layout.addWidget(card2)
        parent_layout.addWidget(card3)

    def _make_stat_card(self, value: QLabel, label: QLabel) -> QWidget:
        """制作一个带卡片背景的统计信息块。"""
        card = QWidget()
        card.setFixedSize(130, 60)
        # 使用样式表设置卡片背景
        card.setStyleSheet(
            "QWidget { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        layout.addWidget(value)
        layout.addWidget(label)
        return card

    def _update_status_bar(self):
        """更新状态栏和顶部统计信息。"""
        try:
            conn = _db._get_conn()
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM stocks")
            stock_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM kline_daily")
            daily_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM watchlist_groups")
            watch_count = cur.fetchone()[0]

            cur.close()

            self.stat_stocks.setText(str(stock_count))
            self.stat_daily.setText(f"{daily_count:,}")
            self.stat_watch.setText(str(watch_count))

            self.statusBar().showMessage(
                f"  ✓ 数据源: composite   |   本地数据: {stock_count} 只股票 / {daily_count:,} 条 K 线"
            )
        except Exception:
            self.statusBar().showMessage("  ✓ 数据源: composite")

    def _on_code_clicked(self, code: str):
        """选股/盯盘点击代码时的处理（移除行情中心跳转）。"""
        pass

    def closeEvent(self, event):
        """优雅关闭。"""
        try:
            self.watcher._stop_current_watcher()
        except Exception:
            pass
        event.accept()
