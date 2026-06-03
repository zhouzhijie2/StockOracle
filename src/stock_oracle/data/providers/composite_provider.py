"""组合数据源 Provider：优先使用新浪财经，失败自动降级。

数据源优先级：新浪 > akshare > efinance
"""
import time
from typing import List, Optional
import pandas as pd

from .base import DataProvider
from .sina_provider import SinaProvider
from .akshare_provider import AkShareProvider
from .efinance_provider import EFinanceProvider
from ...logger import log


class CompositeProvider(DataProvider):
    name = "composite"

    def __init__(self):
        # 优先级: 新浪 > akshare > efinance
        self._providers = [
            SinaProvider(),
            AkShareProvider(),
            EFinanceProvider(),
        ]
        # 全市场实时行情缓存
        self._realtime_cache: Optional[pd.DataFrame] = None
        self._realtime_cache_time: float = 0
        self._realtime_cache_ttl: int = 60  # 缓存 60 秒
        # 股票列表缓存（极慢变化）
        self._stock_list_cache: Optional[pd.DataFrame] = None
        self._stock_list_cache_time: float = 0
        self._stock_list_cache_ttl: int = 86400  # 缓存 24 小时

    # ---------- 通用降级工具 ----------
    def _try_methods(self, method_name: str, *args, **kwargs) -> pd.DataFrame:
        """依次尝试所有 provider，返回第一个成功的非空结果。"""
        for provider in self._providers:
            try:
                result = getattr(provider, method_name)(*args, **kwargs)
                if result is not None and not result.empty:
                    return result
                log.info("%s.%s 返回空，尝试下一个数据源",
                         provider.name, method_name)
            except Exception as e:
                log.warning("%s.%s 异常: %s，尝试下一个数据源",
                            provider.name, method_name, e)
        # 全部失败，返回空 DataFrame
        log.error("所有数据源获取 %s 失败", method_name)
        return pd.DataFrame()

    # ---------- 股票列表 ----------
    def get_stock_list(self) -> pd.DataFrame:
        now = time.time()
        if (self._stock_list_cache is not None and
                now - self._stock_list_cache_time < self._stock_list_cache_ttl and
                not self._stock_list_cache.empty):
            log.info("使用缓存的股票列表（%d 只）", len(self._stock_list_cache))
            return self._stock_list_cache.copy()

        df = self._try_methods("get_stock_list")
        if not df.empty:
            self._stock_list_cache = df.copy()
            self._stock_list_cache_time = now
        return df

    # ---------- 日线 ----------
    def get_daily(self, code: str, start: Optional[str] = None,
                  end: Optional[str] = None, adjust: str = "qfq") -> pd.DataFrame:
        return self._try_methods("get_daily", code, start=start, end=end, adjust=adjust)

    # ---------- 分钟线 ----------
    def get_minute(self, code: str, freq: str = "5", days: int = 30) -> pd.DataFrame:
        return self._try_methods("get_minute", code, freq=freq, days=days)

    # ---------- 实时行情（直接查询指定股票，不拉全市场） ----------
    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """批量获取实时行情，直接查询指定股票。"""
        if not codes:
            return pd.DataFrame(
                columns=["code", "name", "price", "change_pct", "open",
                         "high", "low", "preclose", "volume", "amount",
                         "turnover_rate", "volume_ratio"]
            )

        # 检查缓存（仅当缓存包含所有请求的 codes 时使用）
        now = time.time()
        codes_set = set(str(c).zfill(6) for c in codes)
        if (self._realtime_cache is not None and
                not self._realtime_cache.empty and
                now - self._realtime_cache_time < self._realtime_cache_ttl):
            cached_codes = set(self._realtime_cache["code"].astype(str).str.zfill(6))
            if codes_set.issubset(cached_codes):
                log.info("使用缓存的实时行情（%d 秒前）", int(now - self._realtime_cache_time))
                df = self._realtime_cache
                df = df[df["code"].astype(str).str.zfill(6).isin(codes_set)].copy()
                return df.reset_index(drop=True)

        # 直接查询指定股票（带降级）
        df = self._try_methods("get_realtime_quote", codes)
        if not df.empty:
            # 更新缓存
            if self._realtime_cache is not None and not self._realtime_cache.empty:
                # 合并新旧缓存
                old_codes = set(self._realtime_cache["code"].astype(str).str.zfill(6))
                new_codes = set(df["code"].astype(str).str.zfill(6))
                if not new_codes.issubset(old_codes):
                    self._realtime_cache = pd.concat([self._realtime_cache, df], ignore_index=True)
                    self._realtime_cache_time = now
            else:
                self._realtime_cache = df.copy()
                self._realtime_cache_time = now

        return df

    def get_intraday(self, code: str) -> pd.DataFrame:
        """获取今日分时数据（新浪优先）。"""
        return self._try_methods("get_intraday", code)

    def clear_cache(self):
        """手动清空缓存，用于测试。"""
        self._realtime_cache = None
        self._stock_list_cache = None
