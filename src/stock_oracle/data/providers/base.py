"""数据源抽象基类。"""
from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd


class DataProvider(ABC):
    name: str = "base"

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """返回全市场 A 股列表 [code, name, market, industry, list_date]"""
        ...

    @abstractmethod
    def get_daily(
        self,
        code: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """
        返回前复权日线 DataFrame，列:
        [date, open, high, low, close, volume, amount]
        date 格式: 'YYYY-MM-DD'
        """
        ...

    @abstractmethod
    def get_minute(
        self,
        code: str,
        freq: str = "5",
        days: int = 30,
    ) -> pd.DataFrame:
        """
        返回分钟线 DataFrame，列:
        [datetime, open, high, low, close, volume]
        """
        ...

    @abstractmethod
    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """
        批量拉取实时行情。返回列:
        [code, name, price, change_pct, open, high, low, preclose,
         volume, amount, turnover_rate, volume_ratio]
        """
        ...

    def health_check(self) -> bool:
        try:
            df = self.get_stock_list()
            return not df.empty
        except Exception:
            return False
