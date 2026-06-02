"""均线指标。"""
import pandas as pd
import numpy as np


def sma(series: pd.Series, n: int) -> pd.Series:
    """简单移动平均。"""
    s = pd.to_numeric(series, errors="coerce")
    return s.rolling(n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    """指数移动平均。"""
    s = pd.to_numeric(series, errors="coerce")
    return s.ewm(span=n, adjust=False).mean()


def ma_cross(close: pd.Series, short: int = 5, long: int = 10) -> pd.Series:
    """短均线上穿长均线时为 True。"""
    s = sma(close, short)
    l = sma(close, long)
    return (s > l) & (s.shift(1) <= l.shift(1))


def ma_cross_death(close: pd.Series, short: int = 5, long: int = 10) -> pd.Series:
    """短均线下穿长均线时为 True。"""
    s = sma(close, short)
    l = sma(close, long)
    return (s < l) & (s.shift(1) >= l.shift(1))


def above_ma(close: pd.Series, n: int = 20) -> pd.Series:
    """收盘价高于 N 日均线。"""
    return close > sma(close, n)


def below_ma(close: pd.Series, n: int = 20) -> pd.Series:
    return close < sma(close, n)
