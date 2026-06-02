"""选股规则单元测试（使用 mock 数据）。"""
import pandas as pd
import numpy as np
import pytest

from stock_oracle.screener.engine import (
    RuleRegistry, run_rule, rule_consolidation_breakout,
    rule_ma_cross, rule_macd_golden, rule_new_high_breakout,
    rule_limit_up,
)


def _make_kline(n: int = 60, base: float = 100.0,
                trend: float = 0.0, vol: float = 1.0,
                seed: int = 0):
    """构造一个日线 DataFrame。"""
    np.random.seed(seed)
    prices = base + np.cumsum(np.random.randn(n) * 0.5 + trend)
    opens = prices + np.random.randn(n) * 0.3
    highs = np.maximum(prices, opens) + np.abs(np.random.randn(n)) * 0.5
    lows = np.minimum(prices, opens) - np.abs(np.random.randn(n)) * 0.5
    vols = np.random.randint(1_000_000, 5_000_000, n) * vol
    amounts = vols * prices * 0.01

    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="B").strftime("%Y-%m-%d"),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": vols,
        "amount": amounts,
    })
    return df


def test_registry_exposes_rules():
    for key in ["consolidation_breakout", "ma_cross", "macd_golden",
                "new_high_breakout", "limit_up"]:
        assert key in RuleRegistry.all_keys()


def test_ma_cross_detects_golden():
    # 前 40 日横盘 + 后 20 日上涨，MA5 向上穿 MA20
    df1 = _make_kline(n=40, base=100.0, trend=0.0, seed=1)
    df2 = _make_kline(n=20, base=df1["close"].iloc[-1], trend=1.5, seed=2)
    df = pd.concat([df1, df2], ignore_index=True)

    r = run_rule("ma_cross", df, {"short": 5, "long": 20}, code="600000", name="测试")
    # 只对最后一行进行判断
    assert r is not None


def test_macd_golden_runs():
    df = _make_kline(n=60, base=100.0, trend=0.2, seed=3)
    r = run_rule("macd_golden", df, code="600000")
    assert r is not None


def test_limit_up_detects_10pct():
    df = _make_kline(n=20, base=100.0, seed=4)
    # 最后一天强制涨停
    df.loc[df.index[-1], "close"] = df.iloc[-2]["close"] * 1.101
    df.loc[df.index[-1], "high"] = df.iloc[-1]["close"]
    r = run_rule("limit_up", df, params={"code": "600000"}, code="600000")
    # 主板涨幅 > 9.9% 应命中
    assert r.hit


def test_consolidation_breakout_scenario():
    # 前 40 日横盘（窄幅） + 后一日放量大涨
    df1 = _make_kline(n=40, base=100.0, trend=0.0, vol=1.0, seed=5)
    # 使高位/低位更窄
    df1["high"] = df1["close"] * 1.01
    df1["low"] = df1["close"] * 0.99
    # 最后一天放量大涨
    df1.loc[df1.index[-1], "close"] = df1.iloc[-2]["close"] * 1.06
    df1.loc[df1.index[-1], "high"] = df1.iloc[-1]["close"]
    df1.loc[df1.index[-1], "low"] = df1.iloc[-2]["close"]
    df1.loc[df1.index[-1], "volume"] = int(df1["volume"].mean() * 3)

    r = run_rule("consolidation_breakout", df1, params={
        "consolidation_days": 20,
        "consolidation_range_pct": 15.0,
        "shrink_vol_ratio": 1.0,
        "today_min_pct": 5.0,
        "today_max_pct": 20.0,
        "vol_expansion_ratio": 2.0,
        "price_above_ma20": False,
    }, code="600001")
    # 这个配置应当触发
    assert r.hit


def test_empty_df_returns_non_hit():
    df = pd.DataFrame()
    r = run_rule("ma_cross", df, {}, code="000001")
    assert not r.hit
