"""数据拉取与缓存。

DataFetcher 负责:
- 从 DataProvider 拉取
- 写入 SQLite 本地缓存
- 限速与重试
"""
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Tuple

import pandas as pd

from . import db
from .providers import DataProvider, get_provider
from .. import config
from ..logger import log


class DataFetcher:
    def __init__(self, provider: Optional[DataProvider] = None):
        self.provider = provider or get_provider(config.get("data_provider", "akshare"))
        self.min_sleep = float(config.get("rate_limit_min_sec", 0.3))
        self.max_sleep = float(config.get("rate_limit_max_sec", 1.0))
        self.history_days = int(config.get("kline_history_days", 500))
        self.max_workers = 4
        self._cancel_flag = False

    # ---------------- 取消 ----------------
    def cancel(self):
        self._cancel_flag = True

    # ---------------- 股票列表 ----------------
    def update_stock_list(self) -> int:
        df = self.provider.get_stock_list()
        if df.empty:
            log.warning("股票列表为空，不更新")
            return 0

        with db.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute(
                    """
                    INSERT INTO stock_list (code, symbol, name, market, industry, list_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        symbol=excluded.symbol,
                        name=excluded.name,
                        market=excluded.market,
                        industry=excluded.industry,
                        list_date=excluded.list_date,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        str(row.get("code", "")).zfill(6),
                        str(row.get("symbol", "")),
                        str(row.get("name", "")),
                        str(row.get("market", "")),
                        str(row.get("industry", "")),
                        str(row.get("list_date", "")),
                    ),
                )
        log.info("股票列表已更新: %d 只", len(df))
        return len(df)

    def get_local_stock_list(self) -> pd.DataFrame:
        with db.cursor() as cur:
            cur.execute("SELECT code, name, market, symbol, industry, list_date FROM stock_list")
            rows = cur.fetchall()
        if not rows:
            return pd.DataFrame(
                columns=["code", "name", "market", "symbol", "industry", "list_date"]
            )
        return pd.DataFrame([dict(r) for r in rows])

    # ---------------- 日线 ----------------
    def get_local_daily(self, code: str, adjust: str = "qfq") -> pd.DataFrame:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT trade_date as date, open, high, low, close, volume, amount
                FROM kline_daily
                WHERE code = ? AND adjust = ?
                ORDER BY trade_date ASC
                """,
                (str(code).zfill(6), adjust),
            )
            rows = cur.fetchall()
        if not rows:
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "volume", "amount"]
            )
        return pd.DataFrame([dict(r) for r in rows])

    def _last_local_date(self, code: str, adjust: str = "qfq") -> Optional[str]:
        with db.cursor() as cur:
            cur.execute(
                "SELECT MAX(trade_date) as d FROM kline_daily WHERE code = ? AND adjust = ?",
                (str(code).zfill(6), adjust),
            )
            row = cur.fetchone()
        return row["d"] if row and row["d"] else None

    def _save_daily(self, code: str, df: pd.DataFrame, adjust: str = "qfq") -> int:
        if df.empty:
            return 0
        code = str(code).zfill(6)
        rows = []
        for _, r in df.iterrows():
            try:
                rows.append((
                    code,
                    str(r["date"]),
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    int(r["volume"] or 0),
                    float(r["amount"] or 0.0),
                    adjust,
                ))
            except (ValueError, TypeError):
                continue
        if not rows:
            return 0
        with db.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO kline_daily (code, trade_date, open, high, low, close, volume, amount, adjust)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code, trade_date, adjust) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume, amount=excluded.amount
                """,
                rows,
            )
        return len(rows)

    def fetch_daily(self, code: str, force: bool = False,
                    progress: Optional[Callable[[str, int, int], None]] = None,
                    index_total: Tuple[int, int] = None) -> int:
        """拉取单只股票日线，返回新增/更新的条数。"""
        if self._cancel_flag:
            return 0

        code = str(code).zfill(6)

        # 增量：如果本地有数据，只拉取最近缺少的部分
        start_date = None
        if not force:
            last = self._last_local_date(code)
            if last:
                try:
                    last_dt = datetime.strptime(last, "%Y-%m-%d")
                    start_dt = last_dt + timedelta(days=1)
                    start_date = start_dt.strftime("%Y%m%d")
                    # 如果今天就是上次更新日期，跳过
                    if start_dt.date() > datetime.now().date():
                        if progress and index_total:
                            progress(code, index_total[0], index_total[1])
                        return 0
                except Exception:
                    start_date = None
        try:
            df = self.provider.get_daily(code, start=start_date)
        except Exception as e:
            log.warning("拉取 %s 日线失败: %s", code, e)
            return 0

        n = self._save_daily(code, df)
        time.sleep(random.uniform(self.min_sleep, self.max_sleep))

        if progress and index_total:
            progress(code, index_total[0], index_total[1])
        return n

    def update_all_daily(self, codes: Optional[List[str]] = None,
                         force: bool = False,
                         progress: Optional[Callable[[str, int, int], None]] = None,
                         only_incremental: bool = True) -> int:
        self._cancel_flag = False
        if codes is None:
            df = self.get_local_stock_list()
            if df.empty:
                self.update_stock_list()
                df = self.get_local_stock_list()
            codes = df["code"].tolist()

        total = len(codes)
        log.info("开始更新 %d 只股票日线...", total)
        count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {}
            for idx, code in enumerate(codes):
                futures[ex.submit(
                    self.fetch_daily,
                    code,
                    force if not only_incremental else False,
                    progress,
                    (idx + 1, total),
                )] = code

            for fut in as_completed(futures):
                if self._cancel_flag:
                    break
                try:
                    count += fut.result() or 0
                except Exception as e:
                    log.warning("更新失败: %s", e)
        log.info("日线更新完成，共写入 %d 条记录", count)
        return count

    # ---------------- 实时行情 ----------------
    def get_realtime(self, codes: List[str]) -> pd.DataFrame:
        if not codes:
            return pd.DataFrame()
        try:
            return self.provider.get_realtime_quote(codes)
        except Exception as e:
            log.warning("实时行情失败: %s", e)
            return pd.DataFrame()

    # ---------------- 分钟线 ----------------
    def fetch_minute(self, code: str, freq: str = "5", days: int = 30) -> int:
        try:
            df = self.provider.get_minute(code, freq=freq, days=days)
        except Exception as e:
            log.warning("拉取 %s 分钟线失败: %s", code, e)
            return 0
        if df.empty:
            return 0
        code = str(code).zfill(6)
        rows = []
        for _, r in df.iterrows():
            try:
                rows.append((
                    code,
                    str(r["datetime"]),
                    freq,
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    int(r["volume"] or 0),
                ))
            except (ValueError, TypeError):
                continue
        with db.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO kline_minute (code, ts, freq, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code, ts, freq) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume
                """,
                rows,
            )
        return len(rows)
