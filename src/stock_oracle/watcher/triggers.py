"""触发条件评估。

Triggers 基于实时行情快照（单只股票的当前一行）来检测是否达到触发条件。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Trigger:
    key: str                    # 内部 key
    name: str                   # 显示名
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def evaluate(self, row: Dict[str, Any]) -> bool:
        return False


@dataclass
class PriceThresholdTrigger(Trigger):
    """价格突破阈值（上行 / 下行）。"""
    def evaluate(self, row: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        price = float(row.get("price") or 0)
        direction = str(self.params.get("direction", "above"))
        threshold = float(self.params.get("threshold") or 0)
        if direction == "above":
            return price >= threshold > 0
        if direction == "below":
            return 0 < price <= threshold
        return False


@dataclass
class PctTrigger(Trigger):
    """涨跌幅阈值。"""
    def evaluate(self, row: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        pct = float(row.get("change_pct") or 0)
        direction = str(self.params.get("direction", "above"))
        threshold = float(self.params.get("threshold") or 0)
        if direction == "above":
            return pct >= threshold
        if direction == "below":
            return pct <= threshold
        if direction == "abs":
            return abs(pct) >= threshold
        return False


@dataclass
class VolRatioTrigger(Trigger):
    """量比阈值。"""
    def evaluate(self, row: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        vr = float(row.get("volume_ratio") or 0)
        threshold = float(self.params.get("threshold") or 2.0)
        return vr >= threshold


@dataclass
class TurnoverTrigger(Trigger):
    """换手率阈值。"""
    def evaluate(self, row: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        to = float(row.get("turnover_rate") or 0)
        threshold = float(self.params.get("threshold") or 3.0)
        return to >= threshold


_TRIGGER_CLASSES = {
    "price": PriceThresholdTrigger,
    "pct": PctTrigger,
    "vol_ratio": VolRatioTrigger,
    "turnover": TurnoverTrigger,
}


def build_trigger(key: str, **params) -> Optional[Trigger]:
    cls = _TRIGGER_CLASSES.get(key)
    if not cls:
        return None
    return cls(key=key, name=params.pop("name", key), params=params)


def evaluate_any(row: Dict[str, Any], triggers: List[Trigger]) -> List[Trigger]:
    """返回所有被触发的 Trigger。"""
    return [t for t in triggers if t.evaluate(row)]
