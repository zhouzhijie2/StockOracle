"""新浪财经数据源。

直接调用新浪/东方财富原始 API，绕过 akshare/efinance 的封装层，更稳定可控。
"""
import time
import random
import json
from typing import List, Optional
import pandas as pd
import requests

from .base import DataProvider
from ...logger import log


# ===== 工具函数 =====
def _detect_market(code: str) -> str:
    """根据代码判断市场前缀。"""
    code = str(code).zfill(6)
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith(("0", "3")):
        return "sz"
    if code.startswith(("8", "4")):
        return "bj"
    return "sh"


def _sina_symbol(code: str) -> str:
    """新浪代码格式：sh600519 / sz000001。"""
    return f"{_detect_market(code)}{code}"


def _safe_request(url: str, headers: dict = None, params: dict = None,
                  max_retries: int = 3, timeout: int = 10) -> Optional[str]:
    """带重试和超时的请求。"""
    headers = headers or {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36",
    }
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, params=params,
                                timeout=timeout)
            if resp.status_code == 200 and resp.text.strip():
                return resp.text
            log.warning("新浪接口返回空或状态码 %s (第 %d 次)",
                        resp.status_code, attempt + 1)
        except Exception as e:
            log.warning("新浪接口请求异常: %s (第 %d 次)", e, attempt + 1)
        time.sleep(0.5 + random.random())
    return None


# ===== 主 Provider =====
class SinaProvider(DataProvider):
    name = "sina"

    # ----- 股票列表（使用 akshare 的东方财富接口，最稳定）-----
    def get_stock_list(self) -> pd.DataFrame:
        """拉取全市场 A 股列表。优先使用 akshare（已验证稳定）。"""
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            if df.empty:
                return pd.DataFrame(
                    columns=["code", "name", "market", "symbol",
                             "industry", "list_date"]
                )
            df = df.copy()
            df["code"] = df["code"].astype(str).str.zfill(6)
            df["market"] = df["code"].apply(_detect_market)
            df["symbol"] = df["code"].apply(_sina_symbol)
            df["industry"] = ""
            df["list_date"] = ""
            return df[["code", "name", "market", "symbol", "industry", "list_date"]]
        except Exception as e:
            log.warning("akshare 股票列表失败，尝试东方财富直连: %s", e)

        # 备用方案：直连东方财富
        all_stocks = []
        markets = [
            ("m:0+t:6,m:0+t:13,m:0+t:80", "sz"),
            ("m:1+t:2,m:1+t:23,m:1+t:90", "sh"),
        ]
        for market_filter, _ in markets:
            page = 1
            page_size = 1000
            while True:
                url = "https://push2.eastmoney.com/api/qt/clist/get"
                params = {
                    "pn": page, "pz": page_size, "po": "1", "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": "2", "invt": "2", "fid": "f3",
                    "fs": market_filter, "fields": "f12,f14",
                    "_": str(int(time.time() * 1000)),
                }
                text = _safe_request(url, params=params)
                if not text:
                    break
                try:
                    data = json.loads(text)
                    diff = data.get("data", {}).get("diff") or []
                    if not diff:
                        break
                    for item in diff:
                        code = str(item.get("f12", "")).zfill(6)
                        name = str(item.get("f14", ""))
                        if code.isdigit() and len(code) == 6:
                            all_stocks.append({
                                "code": code, "name": name,
                                "market": _detect_market(code),
                                "symbol": _sina_symbol(code),
                                "industry": "", "list_date": "",
                            })
                    if len(diff) < page_size:
                        break
                    page += 1
                    time.sleep(0.2)
                except Exception:
                    break

        if not all_stocks:
            return pd.DataFrame(
                columns=["code", "name", "market", "symbol",
                         "industry", "list_date"]
            )
        return pd.DataFrame(all_stocks)

    # ----- 日线 K线（新浪接口）-----
    def get_daily(self, code: str, start: Optional[str] = None,
                  end: Optional[str] = None,
                  adjust: str = "qfq") -> pd.DataFrame:
        """拉取单只股票日线。"""
        code = str(code).zfill(6)
        symbol = _sina_symbol(code)

        # 新浪 K线接口：前复权
        # adjust=qfq => fq_factor_=000001,1 (前复权)
        fq_param = "000001,1" if adjust == "qfq" else ""

        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            "symbol": symbol,
            "scale": "240",  # 240 分钟 = 日线
            "ma": "no",
            "datalen": "2000",  # 最多 2000 根
        }
        if fq_param:
            params["fq_factor_"] = fq_param

        text = _safe_request(url, params=params)
        if not text:
            return pd.DataFrame(
                columns=["date", "open", "high", "low",
                         "close", "volume", "amount"]
            )

        try:
            # 新浪返回的是 JSON 数组字符串（非标准但可 json.loads）
            data = json.loads(text)
        except Exception as e:
            log.warning("解析新浪 K线 JSON 失败 %s: %s", code, e)
            # 尝试手动解析
            try:
                data = eval(text, {"__builtins__": {}}, {})
            except Exception:
                return pd.DataFrame(
                    columns=["date", "open", "high", "low",
                             "close", "volume", "amount"]
                )

        if not data:
            return pd.DataFrame(
                columns=["date", "open", "high", "low",
                         "close", "volume", "amount"]
            )

        rows = []
        for item in data:
            try:
                # 新浪返回字段: day, open, high, low, close, volume, ma_price5, ...
                row = {
                    "date": str(item.get("day", "")).replace("/", "-")[:10],
                    "open": float(item.get("open", 0) or 0),
                    "high": float(item.get("high", 0) or 0),
                    "low": float(item.get("low", 0) or 0),
                    "close": float(item.get("close", 0) or 0),
                    "volume": int(float(item.get("volume", 0) or 0)),
                    "amount": 0.0,  # 新浪 K线不提供成交额
                }
                if not row["date"] or row["close"] <= 0:
                    continue
                rows.append(row)
            except (ValueError, TypeError):
                continue

        # 日期过滤
        if start or end:
            filtered = []
            start_str = start.replace("-", "") if start else None
            end_str = end.replace("-", "") if end else None
            for r in rows:
                d = r["date"].replace("-", "")
                if start_str and d < start_str:
                    continue
                if end_str and d > end_str:
                    continue
                filtered.append(r)
            rows = filtered

        if not rows:
            return pd.DataFrame(
                columns=["date", "open", "high", "low",
                         "close", "volume", "amount"]
            )
        return pd.DataFrame(rows)

    # ----- 分钟线（新浪接口）-----
    def get_minute(self, code: str, freq: str = "5",
                   days: int = 30) -> pd.DataFrame:
        """拉取分钟线。scale 参数单位为分钟。"""
        code = str(code).zfill(6)
        symbol = _sina_symbol(code)

        try:
            scale = int(freq)
        except (ValueError, TypeError):
            scale = 5

        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            "symbol": symbol,
            "scale": str(scale),
            "ma": "no",
            "datalen": str(max(100, days * 50)),
        }

        text = _safe_request(url, params=params)
        if not text:
            return pd.DataFrame(
                columns=["datetime", "open", "high", "low", "close", "volume"]
            )

        try:
            data = json.loads(text)
        except Exception:
            try:
                data = eval(text, {"__builtins__": {}}, {})
            except Exception:
                return pd.DataFrame(
                    columns=["datetime", "open", "high", "low", "close", "volume"]
                )

        if not data:
            return pd.DataFrame(
                columns=["datetime", "open", "high", "low", "close", "volume"]
            )

        rows = []
        for item in data:
            try:
                rows.append({
                    "datetime": str(item.get("day", "")).replace("/", "-")[:16],
                    "open": float(item.get("open", 0) or 0),
                    "high": float(item.get("high", 0) or 0),
                    "low": float(item.get("low", 0) or 0),
                    "close": float(item.get("close", 0) or 0),
                    "volume": int(float(item.get("volume", 0) or 0)),
                })
            except (ValueError, TypeError):
                continue
        return pd.DataFrame(rows)

    # ----- 今日分时行情 -----
    def get_intraday(self, code: str) -> pd.DataFrame:
        """获取今日分时数据（1分钟K线）。

        返回 columns: [datetime, price, volume]
        """
        code = str(code).zfill(6)
        symbol = _sina_symbol(code)

        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            "symbol": symbol,
            "scale": "1",  # 1分钟
            "ma": "no",
            "datalen": "240",  # 最多240分钟
        }

        text = _safe_request(url, params=params)
        if not text:
            return pd.DataFrame(columns=["datetime", "price", "volume"])

        try:
            data = json.loads(text)
        except Exception:
            try:
                data = eval(text, {"__builtins__": {}}, {})
            except Exception:
                return pd.DataFrame(columns=["datetime", "price", "volume"])

        if not data:
            return pd.DataFrame(columns=["datetime", "price", "volume"])

        rows = []
        for item in data:
            try:
                day = str(item.get("day", "")).strip().replace("/", "-")
                price = float(item.get("close", 0) or 0)
                volume = int(float(item.get("volume", 0) or 0))
                if price <= 0 or not day:
                    continue
                rows.append({"datetime": day, "price": price, "volume": volume})
            except (ValueError, TypeError):
                continue
        return pd.DataFrame(rows)

    # ----- 实时行情（新浪批量接口 + 东方财富补充字段）-----
    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """批量拉取实时行情，包含换手率和量比。"""
        if not codes:
            return pd.DataFrame(
                columns=["code", "name", "price", "change_pct", "open",
                         "high", "low", "preclose", "volume", "amount",
                         "turnover_rate", "volume_ratio"]
            )

        # 先从新浪获取基础行情数据
        symbols = [_sina_symbol(str(c).zfill(6)) for c in codes]
        batch_size = 500
        all_rows = {}

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            url = "https://hq.sinajs.cn/list=" + ",".join(batch)
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn",
            }
            text = _safe_request(url, headers=headers)
            if not text:
                continue

            for line in text.split("\n"):
                line = line.strip()
                if not line or "=" not in line:
                    continue
                try:
                    eq_pos = line.index("=")
                    var_part = line[:eq_pos].strip()
                    val_part = line[eq_pos + 1:].strip().strip('";')
                    if not val_part:
                        continue
                    sym = var_part.replace("var hq_str_", "").strip()
                    code = sym[2:].zfill(6) if len(sym) > 2 else ""
                    if not code:
                        continue

                    fields = val_part.split(",")
                    if len(fields) < 10:
                        continue

                    name = fields[0]
                    open_p = float(fields[1]) if fields[1] else 0.0
                    preclose = float(fields[2]) if fields[2] else 0.0
                    price = float(fields[3]) if fields[3] else 0.0
                    high = float(fields[4]) if fields[4] else 0.0
                    low = float(fields[5]) if fields[5] else 0.0
                    volume = int(float(fields[8])) if fields[8] else 0
                    amount = float(fields[9]) if fields[9] else 0.0

                    change_pct = 0.0
                    if preclose > 0:
                        change_pct = (price - preclose) / preclose * 100

                    all_rows[code] = {
                        "code": code,
                        "name": name,
                        "price": price,
                        "change_pct": round(change_pct, 2),
                        "open": open_p,
                        "high": high,
                        "low": low,
                        "preclose": preclose,
                        "volume": volume,
                        "amount": amount,
                        "turnover_rate": None,
                        "volume_ratio": None,
                    }
                except (ValueError, IndexError, TypeError):
                    continue

        # 从东方财富补充换手率和量比
        if all_rows:
            codes_to_enrich = list(all_rows.keys())
            for code in codes_to_enrich:
                market_prefix = _detect_market(code)  # 'sh' or 'sz'
                em_prefix = "1" if market_prefix == "sh" else "0"
                em_url = (
                    f"https://push2.eastmoney.com/api/qt/stock/get"
                    f"?secid={em_prefix}.{code}&fields=f58,f59,f84,f85"
                )
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://quote.eastmoney.com/",
                }
                try:
                    resp = requests.get(em_url, headers=headers, timeout=5)
                    if resp.status_code == 200:
                        jdata = json.loads(resp.text)
                        d = jdata.get("data") or {}
                        # f84 = 换手率, f85 = 量比, f58 = 最新价(校验), f59 = 涨跌额
                        turnover = d.get("f84")
                        volratio = d.get("f85")
                        if code in all_rows:
                            if turnover and str(turnover).replace(".", "").isdigit():
                                try:
                                    all_rows[code]["turnover_rate"] = round(float(turnover), 2)
                                except (ValueError, TypeError):
                                    pass
                            if volratio and str(volratio).replace(".", "").isdigit():
                                try:
                                    all_rows[code]["volume_ratio"] = round(float(volratio), 2)
                                except (ValueError, TypeError):
                                    pass
                except Exception:
                    pass

        if not all_rows:
            return pd.DataFrame(
                columns=["code", "name", "price", "change_pct", "open",
                         "high", "low", "preclose", "volume", "amount",
                         "turnover_rate", "volume_ratio"]
            )
        return pd.DataFrame(list(all_rows.values()))
