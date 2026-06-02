"""自选股分组管理（基于 SQLite）。"""
from typing import List, Dict, Optional

import pandas as pd

from ..data import db


def list_groups() -> List[Dict[str, str]]:
    """返回所有分组列表。"""
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, name, description, created_at FROM portfolio ORDER BY id ASC"
        )
        return [dict(r) for r in cur.fetchall()]


def create_group(name: str, description: str = "") -> int:
    """创建分组，如果已存在则返回其 id。"""
    with db.cursor() as cur:
        cur.execute("SELECT id FROM portfolio WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            "INSERT INTO portfolio (name, description) VALUES (?, ?)",
            (name, description),
        )
        return cur.lastrowid


def delete_group(name: str) -> None:
    with db.cursor() as cur:
        cur.execute("SELECT id FROM portfolio WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            return
        pid = row["id"]
        cur.execute("DELETE FROM portfolio_item WHERE portfolio_id = ?", (pid,))
        cur.execute("DELETE FROM portfolio WHERE id = ?", (pid,))


def list_codes(group_name: str) -> List[str]:
    with db.cursor() as cur:
        cur.execute("SELECT id FROM portfolio WHERE name = ?", (group_name,))
        row = cur.fetchone()
        if not row:
            return []
        cur.execute(
            "SELECT code FROM portfolio_item WHERE portfolio_id = ? ORDER BY added_at DESC",
            (row["id"],),
        )
        return [r["code"] for r in cur.fetchall()]


def add_code(group_name: str, code: str) -> bool:
    """添加代码到分组，返回 True 表示新增成功。"""
    code = str(code).zfill(6)
    with db.cursor() as cur:
        cur.execute("SELECT id FROM portfolio WHERE name = ?", (group_name,))
        row = cur.fetchone()
        if not row:
            pid = create_group(group_name)
        else:
            pid = row["id"]
        cur.execute(
            "SELECT 1 FROM portfolio_item WHERE portfolio_id = ? AND code = ?",
            (pid, code),
        )
        if cur.fetchone():
            return False
        cur.execute(
            "INSERT INTO portfolio_item (portfolio_id, code) VALUES (?, ?)",
            (pid, code),
        )
        return True


def remove_code(group_name: str, code: str) -> bool:
    code = str(code).zfill(6)
    with db.cursor() as cur:
        cur.execute("SELECT id FROM portfolio WHERE name = ?", (group_name,))
        row = cur.fetchone()
        if not row:
            return False
        cur.execute(
            "DELETE FROM portfolio_item WHERE portfolio_id = ? AND code = ?",
            (row["id"], code),
        )
        return cur.rowcount > 0


def get_code_names(codes: List[str]) -> Dict[str, str]:
    """根据 code 查名称。"""
    if not codes:
        return {}
    placeholders = ",".join(["?"] * len(codes))
    with db.cursor() as cur:
        cur.execute(
            f"SELECT code, name FROM stock_list WHERE code IN ({placeholders})",
            [str(c).zfill(6) for c in codes],
        )
        return {r["code"]: r["name"] for r in cur.fetchall()}
