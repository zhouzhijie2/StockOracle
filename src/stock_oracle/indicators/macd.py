"""MACD 指标。"""
import pandas as pd
import numpy as np


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    返回 (dif, dea, hist)。"""
    c = pd.to_numeric(close, errors="coerce")
    ema_fast = c.ewm(span=fast, adjust=False).mean()
    ema_slow = c.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return dif, dea, hist


def macd_golden_cross(close: pd.Series) -> pd.Series:
    """DIF 上穿 DEA。"""
    dif, dea, _ = macd(close)
    return (dif > dea) & (dif.shift(1) <= dea.shift(1))


def macd_death_cross(close: pd.Series) -> pd.Series:
    dif, dea, _ = macd(close)
    return (dif < dea) & (dif.shift(1) >= dea.shift(1))
