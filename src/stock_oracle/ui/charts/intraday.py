"""今日分时图组件（基于 pyqtgraph）。

展示：价格走势（带昨收参考线）、成交量柱状图。"""
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

RED = "#f85149"
GREEN = "#3fb950"


class IntradayChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._price_plot = None
        self._vol_plot = None

        if HAS_PYQTGRAPH:
            pg.setConfigOptions(
                background="#0d1117",
                foreground="#8b949e",
                antialias=True,
            )
            self._chart_widget = pg.GraphicsLayoutWidget(self)
            self._chart_widget.setStyleSheet(
                "background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px;"
            )
            self._layout.addWidget(self._chart_widget, stretch=1)

            self._price_plot = self._chart_widget.addPlot(row=0, col=0)
            self._price_plot.setMinimumHeight(200)
            self._price_plot.showGrid(x=True, y=True, alpha=0.2)
            self._price_plot.setMouseEnabled(x=True, y=True)
            self._price_plot.hideAxis("bottom")
            self._price_plot.setLabel("left", "价格", **{"color": "#8b949e"})
            self._price_plot.getAxis("left").setPen("#8b949e")
            self._price_plot.getAxis("left").setTextPen("#8b949e")

            self._chart_widget.nextRow()
            self._vol_plot = self._chart_widget.addPlot(row=1, col=0)
            self._vol_plot.setMinimumHeight(80)
            self._vol_plot.setMaximumHeight(120)
            self._vol_plot.showGrid(x=True, y=True, alpha=0.2)
            self._vol_plot.setXLink(self._price_plot)
            self._vol_plot.setLabel("left", "成交量", **{"color": "#8b949e"})
            self._vol_plot.getAxis("left").setPen("#8b949e")
            self._vol_plot.getAxis("left").setTextPen("#8b949e")
            self._vol_plot.getAxis("bottom").setPen("#8b949e")
            self._vol_plot.getAxis("bottom").setTextPen("#8b949e")
        else:
            msg = QLabel(
                "未检测到 pyqtgraph，图表功能已禁用\n请执行: pip install pyqtgraph"
            )
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #8b949e; background: #161b22; padding: 40px;")
            self._layout.addWidget(msg)

    def plot(self, df: pd.DataFrame, preclose=None):
        """绘制分时图。"""
        if self._price_plot is None or df is None or df.empty:
            self.clear()
            return

        data = df.copy()
        for col in ["price", "volume"]:
            if col not in data.columns:
                self.clear()
                return
            data[col] = pd.to_numeric(data[col], errors="coerce")

        data = data.dropna(subset=["price", "volume"])
        if data.empty:
            self.clear()
            return

        n = len(data)
        x = np.arange(n, dtype=float)
        prices = data["price"].to_numpy(dtype=float)
        volumes = data["volume"].to_numpy(dtype=float)

        # 时间标签
        times = []
        if "datetime" in data.columns:
            times = [str(t) for t in data["datetime"].tolist()]
        elif "time" in data.columns:
            times = [str(t) for t in data["time"].tolist()]
        else:
            times = [str(i) for i in x]

        self._price_plot.clear()
        self._vol_plot.clear()

        # 昨收参考线
        if preclose and float(preclose) > 0:
            self._price_plot.addLine(
                y=float(preclose),
                pen=QPen(QColor("#8b949e"), 1, Qt.DashLine),
            )

        # 价格曲线：按相对昨收涨跌分段着色
        if preclose and float(preclose) > 0:
            # 分段绘制
            ref = float(preclose)
            # 用颜色数组：每一段的颜色
            colors = [RED if prices[i] >= ref else GREEN for i in range(n)]
            # 用多个短线段（相邻两点之间）
            for i in range(n - 1):
                c = RED if prices[i + 1] >= prices[i] else GREEN
                pen = QPen(QColor(c), 1.5)
                self._price_plot.plot(
                    [i, i + 1], [prices[i], prices[i + 1]], pen=pen,
                )
        else:
            # 简单折线
            self._price_plot.plot(x, prices, pen=QPen(QColor("#f0883e"), 2))

        # 成交量柱（涨红跌绿）
        bar_width = 0.7
        vol_up_x = []
        vol_up_h = []
        vol_down_x = []
        vol_down_h = []
        for i in range(n):
            ref = float(preclose) if preclose else (prices[i - 1] if i > 0 else prices[0])
            if prices[i] >= ref:
                vol_up_x.append(i)
                vol_up_h.append(volumes[i])
            else:
                vol_down_x.append(i)
                vol_down_h.append(volumes[i])

        if vol_up_x:
            self._vol_plot.addItem(pg.BarGraphItem(
                x=np.array(vol_up_x, dtype=float),
                height=np.array(vol_up_h, dtype=float),
                width=bar_width,
                brush=QBrush(QColor(RED)),
                pen=QPen(QColor(RED)),
            ))
        if vol_down_x:
            self._vol_plot.addItem(pg.BarGraphItem(
                x=np.array(vol_down_x, dtype=float),
                height=np.array(vol_down_h, dtype=float),
                width=bar_width,
                brush=QBrush(QColor(GREEN)),
                pen=QPen(QColor(GREEN)),
            ))

        # 设置 x 轴
        self._vol_plot.setXRange(-0.5, n - 0.5, padding=0)

    def clear(self):
        if self._price_plot:
            self._price_plot.clear()
        if self._vol_plot:
            self._vol_plot.clear()
