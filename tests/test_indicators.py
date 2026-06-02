"""技术指标单元测试。"""
import numpy as np
import pandas as pd
import pytest

from stock_oracle.indicators.ma import sma, ma_cross, above_ma
from stock_oracle.indicators.macd import macd, macd_golden_cross
from stock_oracle.indicators.volume import volume_sma, price_change_pct, new_high


@pytest.fixture
def sample_close():
    np.random.seed(42)
    series = pd.Series(100 + np.cumsum(np.random.randn(60) * 2))
    return series


def test_sma(sample_close):
    s = sma(sample_close, 5)
    assert s.isna().sum() == 4
    assert abs(s.iloc[-1] - sample_close.iloc[-5:].mean()) < 1e-6


def test_ma_cross(sample_close):
    s = ma_cross(sample_close, short=5, long=20)
    assert len(s) == len(sample_close)
    # 至少有 0 到几次金叉
    assert s.sum() >= 0


def test_above_ma(sample_close):
    s = above_ma(sample_close, 20)
    assert s.sum() >= 0


def test_macd(sample_close):
    dif, dea, hist = macd(sample_close)
    assert len(dif) == len(sample_close)
    assert len(dea) == len(sample_close)
    # MACD 的最开始 NaN 数量
    assert dea.iloc[:20].isna().sum() > 0


def test_macd_golden_cross(sample_close):
    r = macd_golden_cross(sample_close)
    assert len(r) == len(sample_close)


def test_volume_sma():
    vol = pd.Series(np.random.randint(100, 1000, 30))
    s = volume_sma(vol, 5)
    assert s.isna().sum() == 4


def test_price_change_pct(sample_close):
    pct = price_change_pct(sample_close)
    assert pd.isna(pct.iloc[0])
    assert abs(pct.iloc[-1] - (sample_close.iloc[-1] / sample_close.iloc[-2] - 1) * 100) < 1e-6


def test_new_high(sample_close):
    r = new_high(sample_close, 20)
    # 最后一天如果是最近 20 日新高，为 True
    last = sample_close.iloc[-1]
    tail20_max = sample_close.tail(20).max()
    assert r.iloc[-1] == (last >= tail20_max)
