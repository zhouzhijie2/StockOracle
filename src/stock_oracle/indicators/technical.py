"""技术指标统一入口。

提供在 pandas DataFrame 上一次性计算常用指标的函数。
"""
from typing import Optional
import pandas as pd

from .ma import sma, ema, above_ma
from .macd import macd, macd_golden_cross, macd_death_cross
from .volume import (
    volume_sma, volume_ratio, volume_breakout,
    shrink_volume, price_change_pct, range_high_low, new_high, new_low,
)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """在日线 DataFrame 上一次性计算常用指标并返回扩展后的 DataFrame。"""
    if df is None or df.empty:
        return df
    d = df.copy()
    d["open"] = pd.to_numeric(d["open"], errors="coerce")
    d["high"] = pd.to_numeric(d["high"], errors="coerce")
    d["low"] = pd.to_numeric(d["low"], errors="coerce")
    d["close"] = pd.to_numeric(d["close"], errors="coerce")
    d["volume"] = pd.to_numeric(d["volume"], errors="coerce")

    # 均线
    for n in (5, 10, 20, 60):
        d[f"ma{n}"] = sma(d["close"], n)
    for n in (5, 10, 20):
        d[f"ema{n}"] = ema(d["close"], n)

    # 均线金叉
    d["golden_cross_5_10"] = (d["ma5"] > d["ma10"]) & (d["ma5"].shift(1) <= d["ma10"].shift(1))
    d["golden_cross_5_20"] = (d["ma5"] > d["ma20"]) & (d["ma5"].shift(1) <= d["ma20"].shift(1))

    # MACD
    dif, dea, hist = macd(d["close"])
    d["dif"] = dif
    d["dea"] = dea
    d["macd_hist"] = hist
    d["macd_golden"] = macd_golden_cross(d["close"])
    d["macd_death"] = macd_death_cross(d["close"])

    # 量能
    for n in (5, 10, 20):
        d[f"vol_ma{n}"] = volume_sma(d["volume"], n)

    d["vol_ratio"] = volume_ratio(d["volume"], 20)

    # 涨跌幅
    d["pct"] = price_change_pct(d["close"])

    # 新高 / 新低
    d["new_high_20"] = new_high(d["close"], 20)
    d["new_high_60"] = new_high(d["close"], 60)

    # 振幅
    d["hl_range_20"] = range_high_low(d["high"], d["low"], 20)

    # 是否 > MA20
    d["above_ma20"] = above_ma(d["close"], 20)

    return d


__all__ = [
    "sma", "ema", "above_ma",
    "macd", "macd_golden_cross", "macd_death_cross",
    "volume_sma", "volume_ratio", "volume_breakout",
    "shrink_volume", "price_change_pct", "range_high_low",
    "new_high", "new_low",
    "enrich",
]
