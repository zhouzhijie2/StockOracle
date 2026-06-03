"""K线图组件（基于 pyqtgraph，深色主题，稳健渲染）。"""
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


RED = "#f85149"      # 涨
GREEN = "#3fb950"    # 跌
MA5_COLOR = "#ffa502"
MA10_COLOR = "#388bfd"
MA20_COLOR = "#a855f7"

# 自定义坐标轴：显示日期字符串
class DateAxis(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tick_labels = {}
        self.setPen(QColor("#8b949e"))
        self.setTextPen(QColor("#8b949e"))

    def set_date_labels(self, dates):
        self._tick_labels = {}
        if not dates:
            return
        step = max(1, len(dates) // 12)
        for i in range(0, len(dates), step):
            label = str(dates[i])[:10]
            self._tick_labels[float(i)] = label

    def tickStrings(self, values, scale, spacing):
        return [self._tick_labels.get(v, "") for v in values]


class KLineChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._price_plot = None
        self._macd_plot = None
        self._vol_plot = None

        if HAS_PYQTGRAPH:
            pg.setConfigOptions(
                background="#0d1117",
                foreground="#8b949e",
                antialias=True,
                imageAxisOrder="row-major",
            )
            self._chart_widget = pg.GraphicsLayoutWidget(self)
            self._chart_widget.setStyleSheet(
                "background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px;"
            )
            self._layout.addWidget(self._chart_widget, stretch=1)

            # 自定义 x 轴
            self._date_axis = DateAxis(orientation="bottom")

            # 上方 K线
            self._price_plot = self._chart_widget.addPlot(row=0, col=0)
            self._price_plot.setMinimumHeight(240)
            self._price_plot.showGrid(x=True, y=True, alpha=0.2)
            self._price_plot.setMouseEnabled(x=True, y=True)
            self._price_plot.hideAxis("bottom")
            self._price_plot.setLabel("left", "价格", **{"color": "#8b949e"})
            self._price_plot.getAxis("left").setPen("#8b949e")
            self._price_plot.getAxis("left").setTextPen("#8b949e")
            self._price_plot.addLegend(
                offset=(10, 10), labelTextSize="10pt",
                brush=QBrush(QColor("#161b22")),
                pen=QPen(QColor("#30363d")),
            )

            # 中间 MACD
            self._chart_widget.nextRow()
            self._macd_plot = self._chart_widget.addPlot(row=1, col=0, axisItems={"bottom": DateAxis(orientation="bottom")})
            self._macd_plot.setMinimumHeight(80)
            self._macd_plot.setMaximumHeight(120)
            self._macd_plot.showGrid(x=True, y=False, alpha=0.2)
            self._macd_plot.setXLink(self._price_plot)
            self._macd_plot.hideAxis("bottom")
            self._macd_plot.setLabel("left", "MACD", **{"color": "#8b949e"})
            self._macd_plot.getAxis("left").setPen("#8b949e")
            self._macd_plot.getAxis("left").setTextPen("#8b949e")

            # 下方 成交量
            self._chart_widget.nextRow()
            self._vol_plot = self._chart_widget.addPlot(row=2, col=0, axisItems={"bottom": self._date_axis})
            self._vol_plot.setMinimumHeight(70)
            self._vol_plot.setMaximumHeight(110)
            self._vol_plot.showGrid(x=True, y=True, alpha=0.2)
            self._vol_plot.setXLink(self._price_plot)
            self._vol_plot.setLabel("left", "成交量", **{"color": "#8b949e"})
            self._vol_plot.getAxis("left").setPen("#8b949e")
            self._vol_plot.getAxis("left").setTextPen("#8b949e")
        else:
            msg = QLabel(
                "未检测到 pyqtgraph，图表功能已禁用\n请执行: pip install pyqtgraph"
            )
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #8b949e; background: #161b22; padding: 40px;")
            self._layout.addWidget(msg)

    def _calc_macd(self, closes, nfast=12, nslow=26, nsignal=9):
        df = pd.Series(closes.astype(float))
        ema_fast = df.ewm(span=nfast, adjust=False).mean().to_numpy()
        ema_slow = df.ewm(span=nslow, adjust=False).mean().to_numpy()
        dif = ema_fast - ema_slow
        dea = pd.Series(dif).ewm(span=nsignal, adjust=False).mean().to_numpy()
        macd_hist = (dif - dea) * 2.0
        return dif, dea, macd_hist

    def plot(self, df: pd.DataFrame):
        """绘制 K 线图（蜡烛图 + MA + MACD + 成交量）。"""
        if self._price_plot is None or df is None or df.empty:
            self.clear()
            return

        d = df.copy()
        needed_cols = {"open", "high", "low", "close", "volume"}
        if not needed_cols.issubset(set(d.columns)):
            self.clear()
            return

        for col in needed_cols:
            d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=list(needed_cols)).tail(120).reset_index(drop=True)
        if d.empty:
            self.clear()
            return

        n = len(d)
        x = np.arange(n, dtype=float)
        opens = d["open"].to_numpy(dtype=float)
        highs = d["high"].to_numpy(dtype=float)
        lows = d["low"].to_numpy(dtype=float)
        closes = d["close"].to_numpy(dtype=float)
        volumes = d["volume"].to_numpy(dtype=float)
        dates = d["date"].astype(str).tolist() if "date" in d.columns else []

        # --- 清空并重建 ---
        self._price_plot.clear()
        self._macd_plot.clear()
        self._vol_plot.clear()

        # 重建图例
        self._price_plot.addLegend(
            offset=(10, 10), labelTextSize="10pt",
            brush=QBrush(QColor("#161b22")),
            pen=QPen(QColor("#30363d")),
        )

        # --- 蜡烛图: 绘制影线 + 实体 ---
        # 影线（最高价-最低价的垂直线）分涨/跌两类
        up_mask = closes >= opens
        down_mask = ~up_mask

        candle_width = 0.65

        # 影线 (wicks) - 使用 Qt graphics lines 更高效
        for i in range(n):
            color = RED if up_mask[i] else GREEN
            pen = QPen(QColor(color))
            pen.setWidth(1)
            line = pg.PlotCurveItem(
                [i, i], [lows[i], highs[i]],
                pen=pen,
            )
            self._price_plot.addItem(line)

        # 蜡烛实体（用 BarGraphItem 批量绘制）
        up_x = x[up_mask]
        up_y0 = np.minimum(opens[up_mask], closes[up_mask])
        up_heights = np.abs(closes[up_mask] - opens[up_mask])
        if len(up_x) > 0:
            up_bars = pg.BarGraphItem(
                x=up_x, height=up_heights, y0=up_y0,
                width=candle_width,
                brush=QBrush(QColor(RED)),
                pen=QPen(QColor(RED)),
            )
            self._price_plot.addItem(up_bars)

        down_x = x[down_mask]
        down_y0 = np.minimum(opens[down_mask], closes[down_mask])
        down_heights = np.abs(closes[down_mask] - opens[down_mask])
        if len(down_x) > 0:
            down_bars = pg.BarGraphItem(
                x=down_x, height=down_heights, y0=down_y0,
                width=candle_width,
                brush=QBrush(QColor(GREEN)),
                pen=QPen(QColor(GREEN)),
            )
            self._price_plot.addItem(down_bars)

        # --- MA 均线 ---
        closes_series = pd.Series(closes.astype(float))
        for ma_n, color in [(5, MA5_COLOR), (10, MA10_COLOR), (20, MA20_COLOR)]:
            if n >= ma_n:
                ma_vals = closes_series.rolling(ma_n).mean().to_numpy()
                self._price_plot.plot(
                    x[ma_n - 1:], ma_vals[ma_n - 1:],
                    pen=QPen(QColor(color), 1.5),
                    name=f"MA{ma_n}",
                )

        # --- MACD ---
        if n >= 26:
            dif, dea, macd_hist = self._calc_macd(closes)
            # DIF / DEA 线
            self._macd_plot.plot(x, dif, pen=QPen(QColor(MA5_COLOR), 1.2), name="DIF")
            self._macd_plot.plot(x, dea, pen=QPen(QColor(MA10_COLOR), 1.2), name="DEA")

            # MACD 柱
            macd_up = x[macd_hist >= 0]
            macd_up_h = np.abs(macd_hist[macd_hist >= 0])
            macd_up_y0 = np.zeros_like(macd_up_h)
            if len(macd_up) > 0:
                self._macd_plot.addItem(pg.BarGraphItem(
                    x=macd_up, height=macd_up_h, y0=macd_up_y0,
                    width=candle_width * 0.7,
                    brush=QBrush(QColor(RED)),
                    pen=QPen(QColor(RED)),
                ))

            macd_down = x[macd_hist < 0]
            macd_down_h = np.abs(macd_hist[macd_hist < 0])
            macd_down_y0 = -macd_down_h
            if len(macd_down) > 0:
                self._macd_plot.addItem(pg.BarGraphItem(
                    x=macd_down, height=macd_down_h, y0=macd_down_y0,
                    width=candle_width * 0.7,
                    brush=QBrush(QColor(GREEN)),
                    pen=QPen(QColor(GREEN)),
                ))

        # --- 成交量 ---
        vol_up_x = x[up_mask]
        vol_up_h = volumes[up_mask]
        if len(vol_up_x) > 0:
            self._vol_plot.addItem(pg.BarGraphItem(
                x=vol_up_x, height=vol_up_h,
                width=candle_width,
                brush=QBrush(QColor(RED)),
                pen=QPen(QColor(RED)),
            ))

        vol_down_x = x[down_mask]
        vol_down_h = volumes[down_mask]
        if len(vol_down_x) > 0:
            self._vol_plot.addItem(pg.BarGraphItem(
                x=vol_down_x, height=vol_down_h,
                width=candle_width,
                brush=QBrush(QColor(GREEN)),
                pen=QPen(QColor(GREEN)),
            ))

        # --- 设置 x 轴日期标签 ---
        if dates:
            self._date_axis.set_date_labels(dates)
            self._vol_plot.setXRange(-0.5, n - 0.5, padding=0)
        else:
            self._vol_plot.setXRange(-0.5, n - 0.5, padding=0)

    def clear(self):
        """清空图表。"""
        if self._price_plot:
            self._price_plot.clear()
        if self._macd_plot:
            self._macd_plot.clear()
        if self._vol_plot:
            self._vol_plot.clear()
