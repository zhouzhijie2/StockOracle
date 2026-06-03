"""行情中心：股票信息卡片 + K 线图 + 分时图 + 日线数据。"""
from typing import Optional

import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QGridLayout,
)
from PySide6.QtCore import Qt, QThread, Signal

from ...data.fetcher import DataFetcher
from ..charts.kline import KLineChart
from ..charts.intraday import IntradayChart


class _QuoteDailyThread(QThread):
    """快速加载本地日线数据的线程（优先走本地，极快）。"""
    done = Signal(str, str, pd.DataFrame)  # code, name, daily_df

    def __init__(self, fetcher: DataFetcher, code: str, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.code = code

    def run(self):
        code = self.code.zfill(6)
        name = ""
        daily_df = pd.DataFrame()
        try:
            # 1) 快速查本地股票名称
            local = self.fetcher.get_local_stock_list()
            match = local[local["code"].astype(str) == code]
            if not match.empty:
                name = str(match.iloc[0].get("name", ""))
            # 2) 快速查本地日线数据（SQLite，毫秒级）
            daily_df = self.fetcher.get_local_daily(code)
        except Exception:
            pass
        self.done.emit(code, name, daily_df)


class _QuoteRealtimeThread(QThread):
    """后台获取实时行情的线程（较慢，不阻塞界面）。"""
    done = Signal(str, dict)  # code, quote_dict

    def __init__(self, fetcher: DataFetcher, code: str, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.code = code

    def run(self):
        code = self.code.zfill(6)
        quote_dict = {}
        try:
            df = self.fetcher.provider.get_realtime_quote([code])
            if df is not None and not df.empty:
                row = df.iloc[0]
                for col in df.columns:
                    quote_dict[str(col).lower()] = row[col]
        except Exception:
            pass
        self.done.emit(code, quote_dict)


class _QuotePullThread(QThread):
    """如果本地没有日线数据，在线拉取并保存到数据库的后台线程。"""
    done = Signal(str, pd.DataFrame)  # code, daily_df

    def __init__(self, fetcher: DataFetcher, code: str, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.code = code

    def run(self):
        code = self.code.zfill(6)
        daily_df = pd.DataFrame()
        try:
            daily_df = self.fetcher.fetch_and_save_daily(code)
        except Exception:
            pass
        self.done.emit(code, daily_df)


class _IntradayThread(QThread):
    """后台获取今日分时数据的线程。"""
    done = Signal(str, pd.DataFrame, object)  # code, intraday_df, preclose

    def __init__(self, fetcher: DataFetcher, code: str, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.code = code

    def run(self):
        code = self.code.zfill(6)
        intraday_df = pd.DataFrame()
        preclose = None
        try:
            intraday_df = self.fetcher.provider.get_intraday(code)
            # 尝试从实时行情获取昨收
            try:
                rq = self.fetcher.provider.get_realtime_quote([code])
                if rq is not None and not rq.empty:
                    preclose = rq.iloc[0].get("preclose")
            except Exception:
                pass
        except Exception:
            pass
        self.done.emit(code, intraday_df, preclose)


class QuoteWidget(QWidget):
    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._daily_thread: Optional[_QuoteDailyThread] = None
        self._realtime_thread: Optional[_QuoteRealtimeThread] = None
        self._pull_thread: Optional[_QuotePullThread] = None
        self._intraday_thread: Optional[_IntradayThread] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # ========== 搜索栏 ==========
        search_box = QWidget()
        search_layout = QHBoxLayout(search_box)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText("输入 6 位股票代码（例如：600519），回车查询")
        self.input.setFixedHeight(36)
        self.input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.input, stretch=1)

        self.btn_search = QPushButton("🔍 查询")
        self.btn_search.setObjectName("primaryButton")
        self.btn_search.setFixedHeight(36)
        self.btn_search.setMinimumWidth(100)
        self.btn_search.clicked.connect(self._on_search)
        search_layout.addWidget(self.btn_search)

        self.lbl_status = QLabel("请输入股票代码后查询")
        self.lbl_status.setObjectName("infoLabel")
        search_layout.addWidget(self.lbl_status, stretch=2)

        root.addWidget(search_box)

        # ========== 分隔器（上：信息 + 下：K线 + 表格）==========
        splitter = QSplitter(Qt.Vertical)

        # ===== 股票信息卡片 =====
        info_card = QGroupBox("股票信息")
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(16, 20, 16, 12)
        info_layout.setSpacing(24)

        # 左侧：名称 + 现价 + 涨跌幅
        left_info = QWidget()
        left_layout = QVBoxLayout(left_info)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.lbl_code = QLabel("-")
        self.lbl_code.setObjectName("cardTitle")
        left_layout.addWidget(self.lbl_code)

        self.lbl_name = QLabel("-")
        self.lbl_name.setObjectName("infoLabel")
        left_layout.addWidget(self.lbl_name)

        self.lbl_price = QLabel("-")
        self.lbl_price.setObjectName("priceLabel")
        self.lbl_price.setStyleSheet("font-size: 28px; font-weight: bold; color: #f0883e;")
        left_layout.addWidget(self.lbl_price)

        self.lbl_change = QLabel("-")
        self.lbl_change.setStyleSheet("font-size: 14px; font-weight: bold; color: #f85149;")
        left_layout.addWidget(self.lbl_change)

        left_layout.addStretch(1)
        info_layout.addWidget(left_info, stretch=1)

        # 右侧：详细信息网格
        right_info = QWidget()
        grid_layout = QGridLayout(right_info)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(32)
        grid_layout.setVerticalSpacing(8)

        self.lbl_open = _stat_cell("今开", "-")
        self.lbl_high = _stat_cell("最高", "-")
        self.lbl_low = _stat_cell("最低", "-")
        self.lbl_preclose = _stat_cell("昨收", "-")
        self.lbl_volume = _stat_cell("成交量", "-")
        self.lbl_amount = _stat_cell("成交额", "-")
        self.lbl_turnover = _stat_cell("换手率", "-")
        self.lbl_volratio = _stat_cell("量比", "-")

        grid_layout.addWidget(self.lbl_open["label"], 0, 0)
        grid_layout.addWidget(self.lbl_open["value"], 1, 0)
        grid_layout.addWidget(self.lbl_high["label"], 0, 1)
        grid_layout.addWidget(self.lbl_high["value"], 1, 1)
        grid_layout.addWidget(self.lbl_low["label"], 0, 2)
        grid_layout.addWidget(self.lbl_low["value"], 1, 2)
        grid_layout.addWidget(self.lbl_preclose["label"], 0, 3)
        grid_layout.addWidget(self.lbl_preclose["value"], 1, 3)

        grid_layout.addWidget(self.lbl_volume["label"], 2, 0)
        grid_layout.addWidget(self.lbl_volume["value"], 3, 0)
        grid_layout.addWidget(self.lbl_amount["label"], 2, 1)
        grid_layout.addWidget(self.lbl_amount["value"], 3, 1)
        grid_layout.addWidget(self.lbl_turnover["label"], 2, 2)
        grid_layout.addWidget(self.lbl_turnover["value"], 3, 2)
        grid_layout.addWidget(self.lbl_volratio["label"], 2, 3)
        grid_layout.addWidget(self.lbl_volratio["value"], 3, 3)

        info_layout.addWidget(right_info, stretch=2)

        splitter.addWidget(info_card)

        # ===== 今日分时图 =====
        self.intraday_card = QGroupBox("今日分时走势")
        intraday_layout = QVBoxLayout(self.intraday_card)
        intraday_layout.setContentsMargins(8, 20, 8, 8)

        self.intraday = IntradayChart()
        intraday_layout.addWidget(self.intraday)

        splitter.addWidget(self.intraday_card)

        # ===== K线图 =====
        self.chart_card = QGroupBox("K 线走势（最近 120 个交易日）")
        chart_layout = QVBoxLayout(self.chart_card)
        chart_layout.setContentsMargins(8, 20, 8, 8)

        self.chart = KLineChart()
        chart_layout.addWidget(self.chart)

        splitter.addWidget(self.chart_card)

        # ===== 日线表格 =====
        table_card = QGroupBox("历史日线数据")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(8, 20, 8, 8)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["日期", "开盘", "最高", "最低", "收盘"])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table)

        splitter.addWidget(table_card)

        splitter.setSizes([170, 220, 380, 220])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 3)
        splitter.setStretchFactor(3, 2)

        root.addWidget(splitter, stretch=1)

    def show_code(self, code: str):
        """从选股/盯盘中心跳转到行情中心。"""
        self.input.setText(str(code).zfill(6))
        self._on_search()

    def _on_search(self):
        code = self.input.text().strip()
        if not (code.isdigit() and len(code) == 6):
            self.lbl_status.setText("⚠ 请输入 6 位数字代码")
            self.lbl_status.setStyleSheet("color: #f85149; font-size: 13px;")
            return

        code = code.zfill(6)
        self.lbl_status.setText(f"⏳ 正在查询 {code} ...")
        self.lbl_status.setStyleSheet("color: #f0883e; font-size: 13px;")
        self.btn_search.setEnabled(False)

        # 清理旧线程
        self._stop_all_threads()

        # 阶段1：快速加载本地数据（SQLite，毫秒级）
        self._daily_thread = _QuoteDailyThread(self.fetcher, code)
        self._daily_thread.done.connect(self._on_daily_done)
        self._daily_thread.start()

    def _on_daily_done(self, code: str, name: str, daily_df: pd.DataFrame):
        """阶段1完成：展示本地日线数据。"""
        self.lbl_code.setText(code)
        self.lbl_name.setText(name or "—")

        if daily_df is not None and not daily_df.empty:
            self.chart.plot(daily_df)
            self._fill_table(daily_df)
            self.lbl_status.setText(f"✓ 已加载 {code} 本地数据 · {len(daily_df)} 条 · 正在获取实时行情和分时...")
            self.lbl_status.setStyleSheet("color: #f0883e; font-size: 13px;")

            # 阶段2：后台获取实时行情（慢，不阻塞）
            self._realtime_thread = _QuoteRealtimeThread(self.fetcher, code)
            self._realtime_thread.done.connect(self._on_realtime_done)
            self._realtime_thread.start()

            # 阶段3：后台获取分时数据（和实时行情并行）
            self._intraday_thread = _IntradayThread(self.fetcher, code)
            self._intraday_thread.done.connect(self._on_intraday_done)
            self._intraday_thread.start()

            # 从本地最后一条日线推算价格，让用户有即时反馈
            last_row = daily_df.iloc[-1]
            if "close" in daily_df.columns:
                price = float(last_row["close"])
                self.lbl_price.setText(f"{price:.2f}")
                self.lbl_change.setText("(本地最新)")
                self.lbl_change.setStyleSheet("font-size: 14px; font-weight: bold; color: #8b949e;")
        else:
            # 本地无数据 → 改为在线拉取日线
            self.lbl_status.setText(f"⏳ 本地无 {code} 数据 · 正在在线拉取...")
            self.lbl_status.setStyleSheet("color: #f0883e; font-size: 13px;")
            self._pull_thread = _QuotePullThread(self.fetcher, code)
            self._pull_thread.done.connect(self._on_pull_done)
            self._pull_thread.start()

    def _on_realtime_done(self, code: str, quote_dict: dict):
        """阶段2完成：更新实时行情价格。"""
        self.btn_search.setEnabled(True)

        price = quote_dict.get("price") or quote_dict.get("close")
        change_pct = quote_dict.get("change_pct")
        if change_pct is None:
            preclose = quote_dict.get("preclose")
            if price and preclose and float(preclose) > 0:
                try:
                    change_pct = (float(price) - float(preclose)) / float(preclose) * 100
                except Exception:
                    change_pct = None

        if price is not None:
            try:
                self.lbl_price.setText(f"{float(price):.2f}")
            except Exception:
                self.lbl_price.setText(str(price))

        if change_pct is not None:
            try:
                val = float(change_pct)
                color = "#f85149" if val > 0 else ("#3fb950" if val < 0 else "#8b949e")
                sign = "+" if val > 0 else ""
                self.lbl_change.setText(f"{sign}{val:.2f}%")
                self.lbl_change.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
            except Exception:
                self.lbl_change.setText(str(change_pct))

        # 更新详细信息
        def _get(*keys):
            for k in keys:
                if k in quote_dict and quote_dict[k] is not None:
                    return quote_dict[k]
            return None

        _set_stat(self.lbl_open, _get("open"))
        _set_stat(self.lbl_high, _get("high"))
        _set_stat(self.lbl_low, _get("low"))
        _set_stat(self.lbl_preclose, _get("preclose", "pre_close", "yclose"))
        _set_stat(self.lbl_volume, _get("volume"), fmt=lambda v: f"{float(v):,.0f}" if v else "—")
        _set_stat(self.lbl_amount, _get("amount"), fmt=lambda v: f"{float(v):,.0f}" if v else "—")
        _set_stat(self.lbl_turnover, _get("turnover_rate", "turnover"),
                  fmt=lambda v: f"{float(v):.2f}%" if v else "—")
        _set_stat(self.lbl_volratio, _get("volume_ratio", "volratio"),
                  fmt=lambda v: f"{float(v):.2f}" if v else "—")

        self.lbl_status.setText(f"✓ {code} 实时行情已更新")
        self.lbl_status.setStyleSheet("color: #3fb950; font-size: 13px;")

    def _on_pull_done(self, code: str, daily_df: pd.DataFrame):
        """在线拉取完成：展示 K 线。"""
        self.btn_search.setEnabled(True)
        if daily_df is not None and not daily_df.empty:
            self.chart.plot(daily_df)
            self._fill_table(daily_df)
            self.lbl_status.setText(f"✓ 已在线拉取 {code} · {len(daily_df)} 条数据，正在获取实时行情和分时...")
            self.lbl_status.setStyleSheet("color: #3fb950; font-size: 13px;")

            # 同步尝试获取实时行情 + 分时图
            self._realtime_thread = _QuoteRealtimeThread(self.fetcher, code)
            self._realtime_thread.done.connect(self._on_realtime_done)
            self._realtime_thread.start()

            self._intraday_thread = _IntradayThread(self.fetcher, code)
            self._intraday_thread.done.connect(self._on_intraday_done)
            self._intraday_thread.start()
        else:
            self.lbl_status.setText(f"⚠ 未能获取 {code} 的K线数据（网络或接口问题）")
            self.lbl_status.setStyleSheet("color: #f85149; font-size: 13px;")

    def _on_intraday_done(self, code: str, df: pd.DataFrame, preclose):
        """分时数据获取完成：绘制分时图。"""
        if df is not None and not df.empty:
            try:
                self.intraday.plot(df, preclose=preclose)
            except Exception:
                pass

    def _on_failed(self, err: str):
        self.btn_search.setEnabled(True)
        self.lbl_status.setText(f"✗ 查询失败: {err[:80]}")
        self.lbl_status.setStyleSheet("color: #f85149; font-size: 13px;")

    def _stop_all_threads(self):
        """安全停止所有后台线程。"""
        for t in (self._daily_thread, self._realtime_thread, self._pull_thread, self._intraday_thread):
            if t and t.isRunning():
                t.quit()
                t.wait(500)
        self._daily_thread = None
        self._realtime_thread = None
        self._pull_thread = None
        self._intraday_thread = None

    def _fill_table(self, df: pd.DataFrame):
        cols = [c for c in ["date", "open", "high", "low", "close"] if c in df.columns]
        df_sorted = df.sort_values("date", ascending=False).head(100).reset_index(drop=True)
        self.table.setRowCount(len(df_sorted))
        for r in range(len(df_sorted)):
            row = df_sorted.iloc[r]
            close_val = float(row.get("close", 0)) if "close" in cols else None
            open_val = float(row.get("open", 0)) if "open" in cols else None
            for c, col in enumerate(cols):
                val = row.get(col, "")
                if col == "date":
                    text = str(val)[:10]
                elif col in ["open", "high", "low", "close"]:
                    try:
                        text = f"{float(val):.2f}"
                    except Exception:
                        text = str(val)
                else:
                    text = str(val)

                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)


def _stat_cell(label: str, value: str) -> dict:
    """创建一个带标签的信息单元。"""
    lbl = QLabel(label)
    lbl.setObjectName("statLabel")
    lbl.setStyleSheet("color: #8b949e; font-size: 12px;")

    val = QLabel(value)
    val.setObjectName("priceLabel")
    val.setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold;")
    return {"label": lbl, "value": val}


def _set_stat(cell: dict, value, fmt=lambda v: f"{float(v):.2f}" if v is not None else "—"):
    """更新信息单元的数值。"""
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            cell["value"].setText("—")
            cell["value"].setStyleSheet("color: #8b949e; font-size: 16px; font-weight: bold;")
            return
        cell["value"].setText(fmt(value))
        cell["value"].setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold;")
    except Exception:
        cell["value"].setText("—")
