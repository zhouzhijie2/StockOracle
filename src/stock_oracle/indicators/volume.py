"""成交量 / 量能相关指标。"""
import pandas as pd
import numpy as np


def volume_sma(volume: pd.Series, n: int = 20) -> pd.Series:
    v = pd.to_numeric(volume, errors="coerce")
    return v.rolling(n).mean()


def volume_ratio(volume: pd.Series, n: int = 20) -> pd.Series:
    """当日成交量 / 最近 N 日均量。"""
    return volume / volume_sma(volume, n)


def volume_breakout(volume: pd.Series, n: int = 20, ratio: float = 2.0) -> pd.Series:
    """放量突破。"""
    return volume / volume_sma(volume, n) >= ratio


def shrink_volume(volume: pd.Series, n: int = 5, ratio: float = 0.7) -> pd.Series:
    """最近 N 日均量 / 前 N 日均量 <= ratio。"""
    v = pd.to_numeric(volume, errors="coerce")
    recent = v.rolling(n).mean()
    previous = v.shift(n).rolling(n).mean()
    return (recent / previous.replace(0, np.nan)) <= ratio


def price_change_pct(close: pd.Series) -> pd.Series:
    """当日涨跌幅 %。"""
    return (close / close.shift(1) - 1) * 100


def range_high_low(high: pd.Series, low: pd.Series, n: int = 20) -> pd.Series:
    """最近 N 日最高价 / 最低价。"""
    return high.rolling(n).max() / low.rolling(n).min()


def new_high(close: pd.Series, n: int = 20) -> pd.Series:
    """今日收盘创最近 N 日新高。"""
    return close >= close.rolling(n).max()


def new_low(close: pd.Series, n: int = 20) -> pd.Series:
    return close <= close.rolling(n).min()
