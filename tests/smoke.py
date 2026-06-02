"""简单自测试脚本（不依赖 pytest）。"""
import os
import sys

sys.path.insert(0, "src")
os.environ.setdefault("STOCK_ORACLE_TEST", "1")

import pandas as pd
import numpy as np

# ---- indicators ----
from stock_oracle.indicators.ma import sma, ma_cross
from stock_oracle.indicators.macd import macd, macd_golden_cross
from stock_oracle.indicators.volume import volume_sma, price_change_pct

print("✓ indicators import ok")

close = pd.Series(100 + np.cumsum(np.random.randn(60) * 2))
assert not sma(close, 5).isna().iloc[-1]
assert len(ma_cross(close, 5, 20)) == 60
dif, dea, hist = macd(close)
assert len(dif) == 60
print("✓ indicators calculation ok")

# ---- data layer ----
from stock_oracle.data import db as _db

# 用临时数据库测试
import sqlite3, tempfile
_db._connection = sqlite3.connect(":memory:")
_db.init_db()

from stock_oracle.data.fetcher import DataFetcher

# 测试 save_daily / get_local_daily round trip
f = DataFetcher()
test_df = pd.DataFrame({
    "date": ["2024-01-02", "2024-01-03"],
    "open": [100.0, 101.0],
    "high": [101.0, 102.0],
    "low": [99.0, 100.0],
    "close": [100.5, 101.5],
    "volume": [1_000_000, 2_000_000],
    "amount": [100_000_000, 200_000_000],
})
n = f._save_daily("000001", test_df)
assert n == 2
got = f.get_local_daily("000001")
assert len(got) == 2, f"expected 2, got {len(got)}"
print("✓ data layer roundtrip ok")

# ---- screener ----
from stock_oracle.screener.engine import RuleRegistry, run_rule
print("✓ screener import ok, rules:", RuleRegistry.all_keys())

from stock_oracle.indicators.technical import enrich
df_full = pd.DataFrame({
    "date": pd.date_range("2024-01-01", periods=60, freq="B").strftime("%Y-%m-%d"),
    "open": list(close.shift(1).fillna(close.iloc[0])),
    "high": list(close + 1),
    "low": list(close - 1),
    "close": list(close),
    "volume": list(np.random.randint(1_000_000, 5_000_000, 60)),
    "amount": list(np.random.randint(1_000_000, 5_000_000, 60)),
})
enriched = enrich(df_full)
assert "ma5" in enriched.columns
assert "macd_hist" in enriched.columns
print("✓ indicators enrich ok")

r = run_rule("ma_cross", enriched, {"short": 5, "long": 20}, code="000001", name="test")
assert r is not None
print(f"✓ ma_cross rule evaluated: hit={r.hit}, score={r.score:.2f}")

# ---- watcher triggers ----
from stock_oracle.watcher.triggers import PctTrigger, VolRatioTrigger
t = PctTrigger(key="t1", name="test", params={"direction": "above", "threshold": 3.0})
assert t.evaluate({"change_pct": 5.0})
assert not t.evaluate({"change_pct": 2.0})
print("✓ watcher triggers ok")

# ---- portfolio ----
from stock_oracle.portfolio import manager as pm
groups = pm.list_groups()
print("✓ portfolio manager ok, groups:", len(groups))

print("\n=== ALL TESTS PASSED ===")
