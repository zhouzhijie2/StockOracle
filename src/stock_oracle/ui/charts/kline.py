"""K线图组件（基于 pyqtgraph）。"""
from typing import List

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class KLineChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._title = QLabel("K线（日线）")
        self._title.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._title)
        self._chart_widget = None
        self._init_chart()

    def _init_chart(self):
        try:
            import pyqtgraph as pg  # type: ignore
            pg.setConfigOption("background", "w")
            pg.setConfigOption("foreground", "k")
            self._chart_widget = pg.GraphicsLayoutWidget(self)
            self._layout.addWidget(self._chart_widget)
            self._price_plot = self._chart_widget.addPlot(row=0, col=0)
            self._price_plot.setLabel("left", "价格")
            self._price_plot.showGrid(x=True, y=True, alpha=0.3)
            self._price_plot.addLegend()

            self._chart_widget.nextRow()
            self._vol_plot = self._chart_widget.addPlot(row=1, col=0)
            self._vol_plot.setLabel("left", "成交量")
            self._vol_plot.setXLink(self._price_plot)
            self._vol_plot.showGrid(x=True, y=True, alpha=0.3)

            self._ma5_item = pg.PlotItem()
        except Exception:
            # pyqtgraph 不可用，降级为简单的文本展示
            self._fallback_label = QLabel("未检测到 pyqtgraph，图表功能已禁用\n请执行: pip install pyqtgraph")
            self._fallback_label.setAlignment(Qt.AlignCenter)
            self._layout.addWidget(self._fallback_label)
            self._chart_widget = None

    def plot(self, df: pd.DataFrame):
        if self._chart_widget is None:
            return
        if df is None or df.empty:
            self._title.setText("K线（日线） - 无数据")
            return

        d = df.copy()
        for col in ("open", "high", "low", "close", "volume"):
            if col not in d.columns:
                return
            d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=["open", "high", "low", "close", "volume"]).tail(120)
        if d.empty:
            return

        self._price_plot.clear()
        self._vol_plot.clear()

        import pyqtgraph as pg  # type: ignore

        x = np.arange(len(d))
        opens = d["open"].to_numpy(dtype=float)
        highs = d["high"].to_numpy(dtype=float)
        lows = d["low"].to_numpy(dtype=float)
        closes = d["close"].to_numpy(dtype=float)
        volumes = d["volume"].to_numpy(dtype=float)

        # 蜡烛图：用竖线表示 high-low，用矩形表示 open-close
        for i in range(len(x)):
            col = (200, 30, 30) if closes[i] >= opens[i] else (30, 140, 30)
            # 影线
            line = pg.PlotDataItem([x[i], x[i]], [lows[i], highs[i]],
                                   pen=pg.mkPen(col, width=1))
            self._price_plot.addItem(line)
            # 实体
            rect = pg.BarGraphItem(x=[x[i]], height=[abs(closes[i] - opens[i])],
                                   width=0.7,
                                   y0=min(opens[i], closes[i]),
                                   brush=pg.mkBrush(col))
            self._price_plot.addItem(rect)

        # MA5 / MA10 / MA20
        for n, color in [(5, (255, 165, 0)), (10, (0, 100, 200)), (20, (180, 0, 200))]:
            if len(closes) >= n:
                ma = pd.Series(closes).rolling(n).mean().to_numpy()
                self._price_plot.plot(x, ma, pen=pg.mkPen(color, width=1.5),
                                      name=f"MA{n}")

        # 成交量：根据涨跌颜色
        colors = []
        for i in range(len(x)):
            colors.append(
                pg.mkBrush(200, 30, 30) if closes[i] >= opens[i]
                else pg.mkBrush(30, 140, 30)
            )
        vol_bars = pg.BarGraphItem(x=x, height=volumes, width=0.7,
                                   brushes=colors)
        self._vol_plot.addItem(vol_bars)

        # 日期轴（简化）
        tick_dates = d["date"].to_list() if "date" in d.columns else [str(i) for i in x]
        ax = self._price_plot.getAxis("bottom")
        ticks_per = max(1, len(tick_dates) // 10)
        ticks = [(i, str(tick_dates[i])[:10]) for i in range(0, len(tick_dates), ticks_per)]
        ax.setTicks([ticks])

        self._title.setText(f"K线（最近 {len(d)} 日）")
