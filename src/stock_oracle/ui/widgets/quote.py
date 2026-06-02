"""行情中心 Tab。"""
from typing import Optional

import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFormLayout, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QMessageBox,
)
from PySide6.QtCore import Qt

from ...data.fetcher import DataFetcher
from ..charts.kline import KLineChart


class QuoteWidget(QWidget):
    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 搜索栏
        search = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入 6 位股票代码，回车查询")
        self.input.returnPressed.connect(self._on_search)
        search.addWidget(self.input, stretch=1)
        self.btn_search = QPushButton("查询")
        self.btn_search.clicked.connect(self._on_search)
        search.addWidget(self.btn_search)
        root.addLayout(search)

        # 上部：信息卡片 + K线
        splitter = QSplitter(Qt.Vertical)

        info_box = QGroupBox("股票信息")
        form = QFormLayout(info_box)
        self.lbl_name = QLabel("-")
        self.lbl_price = QLabel("-")
        self.lbl_change = QLabel("-")
        self.lbl_high = QLabel("-")
        self.lbl_low = QLabel("-")
        self.lbl_open = QLabel("-")
        self.lbl_vol = QLabel("-")
        self.lbl_amount = QLabel("-")
        self.lbl_turnover = QLabel("-")
        self.lbl_volratio = QLabel("-")
        form.addRow("名称", self.lbl_name)
        form.addRow("现价", self.lbl_price)
        form.addRow("涨跌幅%", self.lbl_change)
        form.addRow("今开/最高/最低", self._combine(self.lbl_open, self.lbl_high, self.lbl_low))
        form.addRow("成交量/成交额", self._combine(self.lbl_vol, self.lbl_amount))
        form.addRow("换手率% / 量比", self._combine(self.lbl_turnover, self.lbl_volratio))
        splitter.addWidget(info_box)

        # K线图
        self.chart = KLineChart()
        splitter.addWidget(self.chart)

        # 历史日线表
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["日期", "开盘", "最高", "最低", "收盘"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.table)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        root.addWidget(splitter, stretch=1)

    def _combine(self, *labels):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        for lbl in labels:
            layout.addWidget(lbl)
        layout.addStretch(1)
        return w

    # ==================== 搜索 ====================
    def show_code(self, code: str):
        self.input.setText(str(code).zfill(6))
        self._on_search()

    def _on_search(self):
        code = self.input.text().strip()
        if not (code.isdigit() and len(code) == 6):
            QMessageBox.warning(self, "提示", "请输入 6 位数字代码")
            return
        code = code.zfill(6)
        # 实时行情
        rt_df = self.fetcher.get_realtime([code])
        if rt_df is not None and not rt_df.empty:
            row = rt_df.iloc[0]
            self.lbl_name.setText(str(row.get("name", "-")))
            self.lbl_price.setText(f"{float(row.get('price') or 0):.2f}")
            self.lbl_change.setText(f"{float(row.get('change_pct') or 0):+.2f}%")
            self.lbl_open.setText(f"开: {float(row.get('open') or 0):.2f}")
            self.lbl_high.setText(f"高: {float(row.get('high') or 0):.2f}")
            self.lbl_low.setText(f"低: {float(row.get('low') or 0):.2f}")
            self.lbl_vol.setText(f"量: {float(row.get('volume') or 0):,.0f}")
            self.lbl_amount.setText(f"额: {float(row.get('amount') or 0):,.0f}")
            self.lbl_turnover.setText(f"换手率: {float(row.get('turnover_rate') or 0):.2f}%")
            self.lbl_volratio.setText(f"量比: {float(row.get('volume_ratio') or 0):.2f}")

        # 历史 K 线
        df = self.fetcher.get_local_daily(code)
        if df.empty:
            # 如果本地没有，则尝试在线拉
            df = self.fetcher.provider.get_daily(code)
            self.fetcher._save_daily(code, df)

        if df is not None and not df.empty:
            df = df.tail(120).reset_index(drop=True)
            self.chart.plot(df)

            self.table.setRowCount(len(df))
            for r in range(len(df) - 1, -1, -1):
                display_r = len(df) - 1 - r
                self.table.setItem(display_r, 0, QTableWidgetItem(str(df.iloc[r].get("date", ""))))
                self.table.setItem(display_r, 1, QTableWidgetItem(f"{float(df.iloc[r].get('open') or 0):.2f}"))
                self.table.setItem(display_r, 2, QTableWidgetItem(f"{float(df.iloc[r].get('high') or 0):.2f}"))
                self.table.setItem(display_r, 3, QTableWidgetItem(f"{float(df.iloc[r].get('low') or 0):.2f}"))
                self.table.setItem(display_r, 4, QTableWidgetItem(f"{float(df.iloc[r].get('close') or 0):.2f}"))
