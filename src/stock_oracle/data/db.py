"""SQLite 数据库管理。"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .. import config
from ..logger import log

_SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS stock_list (
        code TEXT PRIMARY KEY,
        symbol TEXT UNIQUE,
        name TEXT NOT NULL,
        market TEXT,
        industry TEXT,
        list_date TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS kline_daily (
        code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        amount REAL,
        adjust TEXT DEFAULT 'qfq',
        PRIMARY KEY (code, trade_date, adjust)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_kline_daily_code ON kline_daily(code)",
    "CREATE INDEX IF NOT EXISTS idx_kline_daily_date ON kline_daily(trade_date)",
    """
    CREATE TABLE IF NOT EXISTS kline_minute (
        code TEXT NOT NULL,
        ts TEXT NOT NULL,
        freq TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        PRIMARY KEY (code, ts, freq)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio_item (
        portfolio_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (portfolio_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watch_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        rule_key TEXT NOT NULL,
        trigger_at TEXT NOT NULL,
        price REAL,
        change_pct REAL,
        note TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """,
]


def _db_path() -> Path:
    return config.get_db_path()


_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        path = _db_path()
        _connection = sqlite3.connect(str(path), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
    return _connection


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    for sql in _SCHEMA_SQL:
        cur.execute(sql)
    conn.commit()
    log.info("数据库初始化完成: %s", _db_path())


@contextmanager
def cursor() -> Iterator[sqlite3.Cursor]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def close() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def vacuum() -> None:
    with cursor() as cur:
        cur.execute("VACUUM")
