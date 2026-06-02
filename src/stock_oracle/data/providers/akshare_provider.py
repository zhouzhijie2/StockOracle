"""AkShare 数据源实现。"""
from typing import List, Optional
import pandas as pd

from .base import DataProvider
from ...logger import log


def _detect_market(code: str) -> str:
    """根据 6 位股票代码判断市场。"""
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith(("0", "3")):
        return "sz"
    if code.startswith(("8", "4")):
        return "bj"
    return "sh"


def _to_symbol(code: str) -> str:
    return f"{_detect_market(code)}{code}"


class AkShareProvider(DataProvider):
    name = "akshare"

    def get_stock_list(self) -> pd.DataFrame:
        import akshare as ak
        log.info("拉取 A 股股票列表...")
        df = ak.stock_info_a_code_name()
        if df.empty:
            log.warning("股票列表为空")
            return pd.DataFrame(
                columns=["code", "name", "market", "symbol",
                         "industry", "list_date"]
            )

        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        # akshare 通常返回 [code, name] 两列
        if "code" not in df.columns and "symbol" in df.columns:
            df = df.rename(columns={"symbol": "code"})
        if "name" not in df.columns:
            for col in ("名称", "简称"):
                if col in df.columns:
                    df = df.rename(columns={col: "name"})
                    break

        df["code"] = df["code"].astype(str).str.zfill(6)
        df["market"] = df["code"].apply(_detect_market)
        df["symbol"] = df["code"].apply(_to_symbol)
        df["industry"] = ""
        df["list_date"] = ""
        return df[["code", "name", "market", "symbol", "industry", "list_date"]]

    def get_daily(
        self,
        code: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        import akshare as ak

        symbol = _to_symbol(code)
        log.info("拉取日线 %s (%s)", code, symbol)
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=(start or "").replace("-", ""),
                end_date=(end or "").replace("-", ""),
                adjust=adjust,
            )
        except Exception as e:
            log.warning("拉取 %s 日线失败: %s", code, e)
            return pd.DataFrame(
                columns=["date", "open", "high", "low",
                         "close", "volume", "amount"]
            )

        if df.empty:
            return pd.DataFrame(
                columns=["date", "open", "high", "low",
                         "close", "volume", "amount"]
            )

        # 归一化列名（akshare 返回中文）
        rename_map = {}
        for col in df.columns:
            if "日期" in str(col):
                rename_map[col] = "date"
            elif "开盘" in str(col):
                rename_map[col] = "open"
            elif "最高" in str(col):
                rename_map[col] = "high"
            elif "最低" in str(col):
                rename_map[col] = "low"
            elif "收盘" in str(col):
                rename_map[col] = "close"
            elif "成交量" in str(col):
                rename_map[col] = "volume"
            elif "成交额" in str(col):
                rename_map[col] = "amount"
        df = df.rename(columns=rename_map)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        for col in ["open", "high", "low", "close", "amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        return df[["date", "open", "high", "low", "close", "volume", "amount"]].copy()

    def get_minute(self, code: str, freq: str = "5", days: int = 30) -> pd.DataFrame:
        import akshare as ak

        symbol = _to_symbol(code)
        try:
            df = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                period=freq,
                adjust="qfq",
            )
        except Exception as e:
            log.warning("拉取 %s 分钟线失败: %s", code, e)
            return pd.DataFrame(
                columns=["datetime", "open", "high", "low", "close", "volume"]
            )

        if df.empty:
            return pd.DataFrame(
                columns=["datetime", "open", "high", "low", "close", "volume"]
            )

        rename_map = {}
        for col in df.columns:
            s = str(col)
            if "时间" in s:
                rename_map[col] = "datetime"
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
        df = df.rename(columns=rename_map)
        df["datetime"] = pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d %H:%M")
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        return df[["datetime", "open", "high", "low", "close", "volume"]].copy()

    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """
        使用 akshare 的全市场实时行情接口，然后根据 codes 过滤。
        """
        import akshare as ak
        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            log.warning("拉取实时行情失败: %s", e)
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
