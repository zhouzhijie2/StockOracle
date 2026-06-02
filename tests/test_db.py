"""SQLite 数据库层基础测试。"""
import os
import tempfile
import sqlite3

import pytest

from stock_oracle.data import db as _db
from stock_oracle.data.fetcher import DataFetcher
from stock_oracle.data.providers.base import DataProvider


def _reset_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _db._connection = None
    # 用 monkeypatch 改变 db_path
    con = sqlite3.connect(str(db_path))
    _db._connection = con
    _db.init_db()


def test_db_init(tmp_path, monkeypatch):
    # 手动覆盖 db 连接
    _db._connection = sqlite3.connect(str(tmp_path / "t.db"))
    _db.init_db()
    # 检查表是否存在
    cur = _db._connection.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r["name"] for r in cur.fetchall()]
    for expected in ["stock_list", "kline_daily", "portfolio",
                     "portfolio_item", "watch_log", "app_config"]:
        assert expected in tables, f"缺失表: {expected}"


def test_kline_roundtrip(tmp_path, monkeypatch):
    _db._connection = sqlite3.connect(str(tmp_path / "t2.db"))
    _db.init_db()

    f = DataFetcher(provider=None)
    import pandas as pd
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

    df2 = f.get_local_daily("000001")
    assert len(df2) == 2
    assert abs(float(df2.iloc[-1]["close"]) - 101.5) < 1e-6
