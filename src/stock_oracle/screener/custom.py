"""自定义规则的表达式解析。

支持的简单表达式：
- 数字：直接写数字
- 指标列：pct, vol_ratio, ma5, ma10, ma20, close, volume, hl_range_20, new_high_20 等
- 比较：<, <=, ==, !=, >=, >
- 逻辑：and, or, not
- 括号

示例：
  "pct > 5 and vol_ratio > 2 and ma5 > ma20"
  "new_high_20 and pct > 3"
"""
import ast
from typing import Dict, Any

import pandas as pd


# 允许访问的指标（白名单）
ALLOWED_COLUMNS = {
    "pct", "vol_ratio", "ma5", "ma10", "ma20", "ma60", "ema5", "ema10", "ema20",
    "close", "open", "high", "low", "volume", "amount",
    "new_high_20", "new_high_60", "hl_range_20",
    "above_ma20", "dif", "dea", "macd_hist", "macd_golden", "macd_death",
    "golden_cross_5_10", "golden_cross_5_20",
}


class RuleSyntaxError(ValueError):
    pass


def _safe_eval(node, row: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, row)
    if isinstance(node, ast.BoolOp):
        values = [_safe_eval(v, row) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, row)
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, row)
        for op, comparator in zip(node.ops, node.comparators):
            right = _safe_eval(comparator, row)
            if isinstance(op, ast.Lt) and not (left < right):
                return False
            if isinstance(op, ast.LtE) and not (left <= right):
                return False
            if isinstance(node, ast.Gt):
                pass
            if isinstance(op, ast.Gt) and not (left > right):
                return False
            if isinstance(op, ast.GtE) and not (left >= right):
                return False
            if isinstance(op, ast.Eq) and not (left == right):
                return False
            if isinstance(op, ast.NotEq) and not (left != right):
                return False
        return True
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Num):  # 兼容旧版本
        return node.n
    if isinstance(node, ast.Name):
        if node.id in row:
            return row[node.id]
        if node.id.lower() in ("true", "false"):
            return node.id.lower() == "true"
        raise RuleSyntaxError(f"未知变量: {node.id}")
    if isinstance(node, ast.BinOp):
        a = _safe_eval(node.left, row)
        b = _safe_eval(node.right, row)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            return a / b if b else 0
    raise RuleSyntaxError(f"不支持的表达式节点: {type(node).__name__}")


def eval_expression(expr: str, row: Dict[str, Any]) -> bool:
    """对单行数据计算布尔表达式。"""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
        return bool(_safe_eval(tree, row))
    except RuleSyntaxError:
        raise
    except Exception as e:
        raise RuleSyntaxError(f"表达式解析错误: {e}")


def filter_by_expression(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    """对 DataFrame 按表达式过滤。"""
    if df.empty:
        return df
    # 取最后一行（今日）来过滤每只股票
    last_row = df.iloc[-1].to_dict()
    # 统一转为小写，便于列名匹配
    lower = {k.lower(): v for k, v in last_row.items()}
    ok = eval_expression(expr, lower)
    if ok:
        return df
    return pd.DataFrame()
