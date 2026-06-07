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
        self.provider = provider or get_provider(config.get("data_provider", "composite"))
        # 请求间隔，避免被限流（并发模式下使用较小值）
        self.min_sleep = float(config.get("rate_limit_min_sec", 0.5))
        self.max_sleep = float(config.get("rate_limit_max_sec", 1.5))
        self.history_days = int(config.get("kline_history_days", 500))
        self.max_workers = 8  # 并发线程数
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
            # 记录股票列表更新时间
            cur.execute(
                """
                INSERT OR REPLACE INTO app_config (key, value)
                VALUES ('stock_list_updated', ?)
                """,
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
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

    def get_stock_list_updated_time(self) -> Optional[str]:
        """获取股票列表最后更新时间。"""
        with db.cursor() as cur:
            cur.execute(
                "SELECT value FROM app_config WHERE key = 'stock_list_updated'"
            )
            row = cur.fetchone()
            return row[0] if row else None

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

    def get_all_last_dates(self, adjust: str = "qfq") -> dict:
        """批量查询所有股票的最后更新日期，用于快速判断哪些需要更新。"""
        with db.cursor() as cur:
            cur.execute(
                "SELECT code, MAX(trade_date) as d FROM kline_daily WHERE adjust = ? GROUP BY code",
                (adjust,),
            )
            rows = cur.fetchall()
        return {row["code"]: row["d"] for row in rows}

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

    def fetch_and_save_daily(self, code: str) -> pd.DataFrame:
        """在线拉取日线并保存到数据库，返回DataFrame。供行情中心使用。"""
        code = str(code).zfill(6)
        try:
            df = self.provider.get_daily(code)
            if not df.empty:
                self._save_daily(code, df)
                log.info("行情中心拉取并保存 %s 日线 %d 条", code, len(df))
            return df
        except Exception as e:
            log.warning("行情中心拉取 %s 日线失败: %s", code, e)
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "volume", "amount"]
            )

    def fetch_daily(self, code: str, force: bool = False,
                    progress: Optional[Callable[[str, int, int], None]] = None,
                    index_total: Tuple[int, int] = None) -> int:
        """拉取单只股票日线，返回新增/更新的条数。
        
        异常情况：
        - 网络错误时会抛出异常，调用者可以重试
        - 数据为空时返回 0（表示已是最新或无数据）
        """
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
        
        df = self.provider.get_daily(code, start=start_date)
        
        # 如果数据为空，可能是网络错误，需要检查
        if df.empty and start_date is None:
            # 第一次拉取就为空，可能是网络错误
            # 抛出异常让调用者重试
            raise Exception(f"获取 {code} 日线数据为空，可能是网络错误")
        
        n = self._save_daily(code, df)
        time.sleep(random.uniform(self.min_sleep, self.max_sleep))

        if progress and index_total:
            progress(code, index_total[0], index_total[1])
        return n

    # ---------------- 断点续传 ----------------
    def save_update_progress(self, last_code: str) -> None:
        """保存更新进度（用于断点续传）。"""
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO app_config (key, value)
                VALUES ('update_progress', ?)
                """,
                (last_code,),
            )

    def get_update_progress(self) -> Optional[dict]:
        """获取更新进度。"""
        with db.cursor() as cur:
            cur.execute(
                "SELECT value FROM app_config WHERE key = 'update_progress'"
            )
            row = cur.fetchone()
            if row:
                return {"last_code": row[0]}
        return None

    def clear_update_progress(self) -> None:
        """清除更新进度。"""
        with db.cursor() as cur:
            cur.execute(
                "DELETE FROM app_config WHERE key = 'update_progress'"
            )

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
