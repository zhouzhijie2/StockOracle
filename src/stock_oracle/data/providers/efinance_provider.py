"""efinance 备用数据源。"""
from typing import List, Optional
import pandas as pd

from .base import DataProvider
from .akshare_provider import _detect_market, _to_symbol
from ...logger import log


class EFinanceProvider(DataProvider):
    name = "efinance"

    def get_stock_list(self) -> pd.DataFrame:
        try:
            import efinance as ef
            df = ef.stock.get_realtime_quotes()
        except Exception as e:
            log.warning("efinance 拉取股票列表失败: %s", e)
            return pd.DataFrame()
        if df.empty:
            return pd.DataFrame()
        df = df.copy()
        code_col = None
        name_col = None
        for col in df.columns:
            if "代码" in str(col):
                code_col = col
            elif "名称" in str(col):
                name_col = col
        if code_col is None or name_col is None:
            return pd.DataFrame()
        out = pd.DataFrame()
        out["code"] = df[code_col].astype(str).str.zfill(6)
        out["name"] = df[name_col].astype(str)
        out = out[out["code"].str.match(r"^\d{6}$")].copy()
        out["market"] = out["code"].apply(_detect_market)
        out["symbol"] = out["code"].apply(_to_symbol)
        out["industry"] = ""
        out["list_date"] = ""
        return out

    def get_daily(
        self,
        code: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        try:
            import efinance as ef
            df = ef.stock.get_quote_history(
                stock_codes=code,
                beg=start.replace("-", "") if start else "",
                end=end.replace("-", "") if end else "",
                adjust=adjust,
            )
        except Exception as e:
            log.warning("efinance 拉取 %s 日线失败: %s", code, e)
            return pd.DataFrame(
                columns=["date", "open", "high", "low",
                         "close", "volume", "amount"]
            )

        if df.empty:
            return pd.DataFrame(
                columns=["date", "open", "high", "low",
                         "close", "volume", "amount"]
            )

        rename_map = {}
        for col in df.columns:
            s = str(col)
            if "日期" in s:
                rename_map[col] = "date"
            elif "开盘" in s:
                rename_map[col] = "open"
            elif "最高" in s:
                rename_map[col] = "high"
            elif "最低" in s:
                rename_map[col] = "low"
            elif "收盘" in s:
                rename_map[col] = "close"
            elif "成交量" in s:
                rename_map[col] = "volume"
            elif "成交额" in s:
                rename_map[col] = "amount"
        df = df.rename(columns=rename_map)
        if "date" not in df.columns:
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        for col in ["open", "high", "low", "close", "amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
        return df[["date", "open", "high", "low", "close", "volume", "amount"]].copy()

    def get_minute(self, code: str, freq: str = "5", days: int = 30) -> pd.DataFrame:
        return pd.DataFrame(
            columns=["datetime", "open", "high", "low", "close", "volume"]
        )

    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        try:
            import efinance as ef
            df = ef.stock.get_realtime_quotes()
        except Exception as e:
            log.warning("efinance 实时行情失败: %s", e)
            return pd.DataFrame()
        if df.empty:
            return pd.DataFrame()

        rename_map = {}
        for col in df.columns:
            s = str(col)
            if "代码" in s:
                rename_map[col] = "code"
            elif "名称" in s:
                rename_map[col] = "name"
            elif "最新价" in s:
                rename_map[col] = "price"
            elif "涨跌幅" in s:
                rename_map[col] = "change_pct"
            elif "今开" in s:
                rename_map[col] = "open"
            elif "最高" in s:
                rename_map[col] = "high"
            elif "最低" in s:
                rename_map[col] = "low"
            elif "昨收" in s:
                rename_map[col] = "preclose"
            elif "成交量" in s and "成交额" not in s:
                rename_map[col] = "volume"
            elif "成交额" in s:
                rename_map[col] = "amount"
            elif "换手率" in s:
                rename_map[col] = "turnover_rate"
            elif "量比" in s:
                rename_map[col] = "volume_ratio"
        df = df.rename(columns=rename_map)
        if "code" not in df.columns:
            return pd.DataFrame()
        df["code"] = df["code"].astype(str).str.zfill(6)

        if codes:
            codes_set = set(str(c).zfill(6) for c in codes)
            df = df[df["code"].isin(codes_set)].copy()

        for col in ["price", "change_pct", "open", "high", "low", "preclose",
                    "amount", "turnover_rate", "volume_ratio"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)

        needed = ["code", "name", "price", "change_pct", "open", "high",
                  "low", "preclose", "volume", "amount",
                  "turnover_rate", "volume_ratio"]
        for col in needed:
            if col not in df.columns:
                df[col] = None
        return df[needed].reset_index(drop=True).copy()

    def get_intraday(self, code: str) -> pd.DataFrame:
        """获取今日分时数据（efinance 分钟线接口）。"""
        return self.get_minute(code, freq="1", days=1)
