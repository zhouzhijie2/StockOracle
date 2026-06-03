"""选股规则引擎 + 预置规则 R1-R4。

使用示例:
    from stock_oracle.screener.engine import run_rule, RuleRegistry
    # 使用字符串 key 调用
    result = run_rule("consolidation_breakout", df_kline, params=None)

    # 或者批量运行（见 run_all）
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# ==================== RuleResult ====================
@dataclass
class RuleResult:
    code: str
    name: str = ""
    hit: bool = False
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)


# ==================== Rule Registry ====================
RuleFn = Callable[[pd.DataFrame, Dict[str, Any]], RuleResult]

class RuleRegistry:
    _rules: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, key: str, fn: RuleFn,
                 default_params: Dict[str, Any],
                 description: str = ""):
        cls._rules[key] = {
            "fn": fn,
            "params": default_params,
            "desc": description,
        }

    @classmethod
    def all_keys(cls) -> List[str]:
        return list(cls._rules.keys())

    @classmethod
    def get_meta(cls, key: str) -> Dict[str, Any]:
        return cls._rules.get(key, {})

    @classmethod
    def run(cls, key: str, df: pd.DataFrame,
            params: Optional[Dict[str, Any]] = None,
            code: str = "", name: str = "") -> RuleResult:
        entry = cls._rules.get(key)
        if not entry:
            raise ValueError(f"未知规则: {key}")
        merged = {**entry["params"], **(params or {})}
        result = entry["fn"](df, merged)
        result.code = code or result.code
        result.name = name or result.name
        return result


def run_rule(key: str, df: pd.DataFrame,
             params: Optional[Dict[str, Any]] = None,
             code: str = "", name: str = "") -> RuleResult:
    return RuleRegistry.run(key, df, params, code, name)


# ==================== 预置规则 ====================

def _ensure_valid(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    required = {"close", "high", "low", "volume"}
    return required.issubset(set(df.columns))


def rule_consolidation_breakout(df: pd.DataFrame, params: Dict[str, Any]) -> RuleResult:
    """R1: 底部横盘缩量 + 今日放量上涨。"""
    r = RuleResult(code="", hit=False, score=0.0, reasons=[])
    if not _ensure_valid(df):
        return r

    consolidation_days = int(params.get("横盘天数", params.get("consolidation_days", 20)))
    range_pct = float(params.get("横盘振幅(%)", params.get("consolidation_range_pct", 15.0))) / 100.0
    shrink_ratio = float(params.get("缩量比", params.get("shrink_vol_ratio", 0.7)))
    today_min = float(params.get("最小涨幅(%)", params.get("today_min_pct", 5.0)))
    today_max = float(params.get("最大涨幅(%)", params.get("today_max_pct", 7.0)))
    vol_expansion = float(params.get("量能放大倍数", params.get("vol_expansion_ratio", 2.0)))
    need_above_ma20 = bool(params.get("价格站上MA20", params.get("price_above_ma20", True)))

    if len(df) < consolidation_days + 5:
        return r

    d = df.iloc[-(consolidation_days + 1):].copy()
    # 观察窗口不含今日
    win = d.iloc[:-1].copy()
    today = d.iloc[-1]
    yesterday = d.iloc[-2]

    if float(yesterday["close"]) <= 0:
        return r

    # 1) 横盘振幅检测
    hh = float(win["high"].max())
    ll = float(win["low"].min())
    if ll <= 0 or hh / ll - 1 > range_pct:
        return r

    # 2) 缩量：后 5 日量 / 前 (consolidation_days - 5) 日量 <= shrink_ratio
    shrink_window = int(params.get("缩量窗口天数", params.get("shrink_window", 5)))
    recent_vol = float(win.tail(shrink_window)["volume"].mean())
    prev_vol = float(win.head(len(win) - shrink_window)["volume"].mean())
    if prev_vol <= 0 or recent_vol / prev_vol > shrink_ratio:
        return r

    # 3) 今日涨幅
    pct_today = (float(today["close"]) / float(yesterday["close"]) - 1) * 100
    if pct_today < today_min or pct_today > today_max:
        # 放宽：如果用户想抓所有放量突破（非严格区间），today_max 可设为 100
        if today_max > 50:
            if pct_today < today_min:
                return r
        else:
            return r

    # 4) 今日放量
    vol_ma = float(win["volume"].mean())
    if vol_ma <= 0 or float(today["volume"]) / vol_ma < vol_expansion:
        return r

    # 5) 价格 > MA20
    if need_above_ma20:
        ma20 = float(df["close"].tail(20).mean())
        if float(today["close"]) <= ma20:
            return r

    # ---- 命中 ----
    r.hit = True
    # 打分：涨幅偏离 5% 中线 + 放量放大倍数 + 横盘越紧得分越高
    ideal_pct = (today_min + today_max) / 2
    r.score += max(0.0, 5.0 - abs(pct_today - ideal_pct))
    r.score += min(float(today["volume"]) / vol_ma - 1, 5.0) * 2
    r.score += max(0.0, (1 - (hh / ll - 1) / range_pct)) * 3

    r.reasons = [
        f"横盘振幅 {round((hh/ll-1)*100, 2)}% (≤{range_pct*100}%)",
        f"缩量比 {round(recent_vol/prev_vol, 2) if prev_vol>0 else 0} (≤{shrink_ratio})",
        f"今日涨幅 {round(pct_today, 2)}%",
        f"量能放大 {round(float(today['volume'])/vol_ma, 2) if vol_ma>0 else 0} 倍",
    ]
    r.extras = {
        "今日涨幅": round(pct_today, 2),
        "量比": round(float(today["volume"]) / vol_ma, 2) if vol_ma > 0 else 0,
        "振幅": round((hh / ll - 1) * 100, 2) if ll > 0 else 0,
    }
    return r


def rule_ma_cross(df: pd.DataFrame, params: Dict[str, Any]) -> RuleResult:
    """R2: MA5 上穿 MA10 / MA20。"""
    r = RuleResult(code="", hit=False, score=0.0, reasons=[])
    if not _ensure_valid(df) or len(df) < 25:
        return r

    short = int(params.get("短期均线", params.get("short", 5)))
    long = int(params.get("长期均线", params.get("long", 20)))
    n = len(df)
    close = df["close"].astype(float)
    ma_s = close.rolling(short).mean()
    ma_l = close.rolling(long).mean()

    if ma_s.iloc[-1] <= ma_l.iloc[-1] or ma_s.iloc[-2] > ma_l.iloc[-2]:
        return r

    r.hit = True
    # 打分：短长均线差值越大得分越高，加上今日涨幅
    diff_pct = (ma_s.iloc[-1] / ma_l.iloc[-1] - 1) * 100
    pct_today = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if n > 1 else 0
    r.score = max(0.0, diff_pct) * 5 + max(0.0, pct_today)
    r.reasons = [f"MA{short} 上穿 MA{long}", f"短长均线差 {round(diff_pct, 2)}%"]
    r.extras = {"今日涨幅": round(pct_today, 2)}
    return r


def rule_macd_golden(df: pd.DataFrame, params: Dict[str, Any]) -> RuleResult:
    """R3: MACD 日线金叉。"""
    r = RuleResult(code="", hit=False, score=0.0, reasons=[])
    if not _ensure_valid(df) or len(df) < 35:
        return r

    close = df["close"].astype(float)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()

    if not (dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]):
        return r

    r.hit = True
    hist = (dif.iloc[-1] - dea.iloc[-1]) * 2
    pct_today = (close.iloc[-1] / close.iloc[-2] - 1) * 100
    # 零轴上方金叉打分更高
    bonus = 2.0 if dif.iloc[-1] > 0 else 0
    r.score = min(abs(hist) * 10, 5.0) + max(0.0, pct_today) + bonus
    r.reasons = [
        f"MACD 金叉 (DIF={round(dif.iloc[-1], 3)}, DEA={round(dea.iloc[-1], 3)})",
        ("零轴上方" if dif.iloc[-1] > 0 else "零轴下方"),
    ]
    r.extras = {"DIF": round(dif.iloc[-1], 3), "DEA": round(dea.iloc[-1], 3)}
    return r


def rule_new_high_breakout(df: pd.DataFrame, params: Dict[str, Any]) -> RuleResult:
    """R4: 放量突破 N 日新高。"""
    r = RuleResult(code="", hit=False, score=0.0, reasons=[])
    if not _ensure_valid(df):
        return r

    n = int(params.get("突破天数", params.get("n_days", 20)))
    vol_ratio = float(params.get("量比阈值", params.get("vol_ratio", 1.5)))
    if len(df) < n + 1:
        return r

    close = df["close"].astype(float)
    vol = df["volume"].astype(float)

    today = close.iloc[-1]
    prev_high = close.iloc[:-1].tail(n).max()
    if today <= prev_high or prev_high <= 0:
        return r

    avg_vol = vol.iloc[:-1].tail(n).mean()
    if avg_vol <= 0 or vol.iloc[-1] / avg_vol < vol_ratio:
        return r

    r.hit = True
    pct_today = (close.iloc[-1] / close.iloc[-2] - 1) * 100
    vr = vol.iloc[-1] / avg_vol
    r.score = max(0.0, pct_today) + min(vr, 5.0)
    r.reasons = [
        f"突破 {n} 日新高（前高 {round(prev_high, 2)}，今日 {round(today, 2)}）",
        f"量能放大 {round(vr, 2)} 倍",
    ]
    r.extras = {"今日涨幅": round(pct_today, 2), "量比": round(vr, 2)}
    return r


def rule_limit_up(df: pd.DataFrame, params: Dict[str, Any]) -> RuleResult:
    """R5: 涨停板检测（主板 10% / 创业板 / 北交所 30%，自动识别代码类型）。"""
    r = RuleResult(code="", hit=False, score=0.0, reasons=[])
    if not _ensure_valid(df) or len(df) < 2:
        return r

    code = params.get("code", "")
    close = df["close"].astype(float)
    today = close.iloc[-1]
    yday = close.iloc[-2]
    if yday <= 0:
        return r

    pct = (today / yday - 1) * 100

    # 识别涨跌幅限制
    if code and code.startswith(("688", "689")):
        limit = 19.9  # 科创板 ±20%
    elif code and code.startswith(("300", "301")):
        limit = 19.9
    elif code and code.startswith(("8", "4", "920")):
        limit = 29.9
    else:
        limit = 9.9  # 主板 ±10%

    if pct < limit:
        return r

    r.hit = True
    r.score = 5.0 + min(pct - limit, 5.0)
    r.reasons = [f"涨停（涨 {round(pct, 2)}%, limit≈{limit}%）"]
    r.extras = {"涨幅": round(pct, 2)}
    return r


# ==================== 注册 ====================
RuleRegistry.register(
    "consolidation_breakout",
    rule_consolidation_breakout,
    {
        "横盘天数": 20,
        "横盘振幅(%)": 15.0,
        "缩量比": 0.7,
        "最小涨幅(%)": 5.0,
        "最大涨幅(%)": 11.0,
        "量能放大倍数": 2.0,
        "价格站上MA20": True,
    },
    "底部横盘缩量 + 今日放量上涨",
)
RuleRegistry.register(
    "ma_cross",
    rule_ma_cross,
    {"短期均线": 5, "长期均线": 20},
    "MA5 上穿 MA20",
)
RuleRegistry.register(
    "macd_golden",
    rule_macd_golden,
    {},
    "MACD 日线金叉",
)
RuleRegistry.register(
    "new_high_breakout",
    rule_new_high_breakout,
    {"突破天数": 20, "量比阈值": 1.5},
    "放量突破 20 日新高",
)
RuleRegistry.register(
    "limit_up",
    rule_limit_up,
    {},
    "涨停板",
)


# ==================== 批量筛选接口 ====================
def run_all(klines: Dict[str, pd.DataFrame],
            rule_key: str,
            params: Optional[Dict[str, Any]] = None,
            top_n: int = 50) -> List[RuleResult]:
    """对 {code: kline_df} 批量跑一个规则，返回所有命中结果按分数排序。"""
    results: List[RuleResult] = []
    for code, df in klines.items():
        r = run_rule(rule_key, df, params, code=code, name="")
        if r.hit:
            results.append(r)
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_n]


def results_to_dataframe(results: List[RuleResult]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame(columns=["代码", "名称", "评分", "理由"])
    rows = []
    for r in results:
        rows.append({
            "代码": r.code,
            "名称": r.name,
            "评分": round(r.score, 2),
            "理由": " | ".join(r.reasons),
            **{k: v for k, v in (r.extras or {}).items()},
        })
    return pd.DataFrame(rows)


__all__ = [
    "RuleResult", "RuleRegistry", "run_rule", "run_all",
    "results_to_dataframe",
    "rule_consolidation_breakout", "rule_ma_cross",
    "rule_macd_golden", "rule_new_high_breakout", "rule_limit_up",
]
