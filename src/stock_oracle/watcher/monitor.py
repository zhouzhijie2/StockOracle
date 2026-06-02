"""盯盘引擎：实时刷新 + 触发评估 + 日志。"""
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

from ..data.fetcher import DataFetcher
from ..logger import log
from ..portfolio import manager as portfolio_mgr
from . import triggers as T
from . import notifier
from ..data import db


WatchCallback = Callable[[Dict[str, object]], None]  # 单只股票最新行情回调
TriggerCallback = Callable[[Dict[str, object], List[T.Trigger]], None]  # 触发回调


class Watcher:
    def __init__(self, fetcher: Optional[DataFetcher] = None,
                 interval_sec: int = 5,
                 codes: Optional[List[str]] = None,
                 triggers: Optional[List[T.Trigger]] = None):
        self.fetcher = fetcher or DataFetcher()
        self.interval_sec = max(1, int(interval_sec))
        self.codes: List[str] = list(codes) if codes else []
        self.triggers: List[T.Trigger] = list(triggers) if triggers else self._default_triggers()

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # 回调（在 GUI 中使用时可覆盖）
        self.on_quote: Optional[WatchCallback] = None
        self.on_trigger: Optional[TriggerCallback] = None
        self._recent_triggers: Dict[str, float] = {}  # code + rule -> last 触发时间戳
        self.cooldown_sec: float = 60.0  # 同一 (code, trigger) 冷却 60 秒

    # ===================== 默认触发配置 =====================
    def _default_triggers(self) -> List[T.Trigger]:
        return [
            T.PctTrigger(key="pct_up", name="涨幅≥3%",
                         params={"direction": "above", "threshold": 3.0}),
            T.PctTrigger(key="pct_down", name="跌幅≥3%",
                         params={"direction": "below", "threshold": -3.0}),
            T.VolRatioTrigger(key="vol_up", name="量比≥2",
                              params={"threshold": 2.0}),
            T.TurnoverTrigger(key="turnover_high", name="换手率≥5%",
                              params={"threshold": 5.0}),
        ]

    # ===================== 自选股管理 =====================
    def set_codes(self, codes: List[str]) -> None:
        with self._lock:
            self.codes = list(codes)

    def add_code(self, code: str) -> None:
        with self._lock:
            code = str(code).zfill(6)
            if code not in self.codes:
                self.codes.append(code)

    def load_from_group(self, group_name: str) -> None:
        codes = portfolio_mgr.list_codes(group_name)
        self.set_codes(codes)

    def set_triggers(self, triggers: List[T.Trigger]) -> None:
        self.triggers = list(triggers)

    # ===================== 运行控制 =====================
    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("盯盘引擎已启动（刷新 %ds, 股票 %d 只）",
                 self.interval_sec, len(self.codes))

    def stop(self) -> None:
        self._stop_event.set()
        log.info("盯盘引擎已停止")

    # ===================== 主循环 =====================
    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    codes = list(self.codes)

                if not codes:
                    time.sleep(2)
                    continue

                df = self.fetcher.get_realtime(codes)
                if df is None or df.empty:
                    time.sleep(self.interval_sec)
                    continue

                for _, row in df.iterrows():
                    row_dict = {
                        "code": str(row.get("code", "")).zfill(6),
                        "name": str(row.get("name", "")),
                        "price": float(row.get("price") or 0),
                        "change_pct": float(row.get("change_pct") or 0),
                        "open": float(row.get("open") or 0),
                        "high": float(row.get("high") or 0),
                        "low": float(row.get("low") or 0),
                        "preclose": float(row.get("preclose") or 0),
                        "volume": float(row.get("volume") or 0),
                        "amount": float(row.get("amount") or 0),
                        "turnover_rate": float(row.get("turnover_rate") or 0),
                        "volume_ratio": float(row.get("volume_ratio") or 0),
                        "timestamp": datetime.now().isoformat(),
                    }
                    if self.on_quote:
                        try:
                            self.on_quote(row_dict)
                        except Exception as e:
                            log.warning("on_quote 回调异常: %s", e)

                    # 触发检测
                    hit = T.evaluate_any(row_dict, self.triggers)
                    if hit:
                        self._handle_trigger(row_dict, hit)

            except Exception as e:
                log.warning("盯盘循环异常: %s", e)

            # 按间隔睡眠，可被 stop 唤醒
            for _ in range(self.interval_sec):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _handle_trigger(self, row: Dict[str, object],
                        triggers: List[T.Trigger]) -> None:
        code = str(row.get("code", ""))
        now = time.time()
        fired_triggers: List[T.Trigger] = []
        for t in triggers:
            k = f"{code}|{t.key}"
            last = self._recent_triggers.get(k, 0)
            if now - last < self.cooldown_sec:
                continue
            self._recent_triggers[k] = now
            fired_triggers.append(t)

        if not fired_triggers:
            return

        # 触发日志
        for t in fired_triggers:
            self._log_trigger(code, t.key,
                              float(row.get("price") or 0),
                              float(row.get("change_pct") or 0),
                              f"{row.get('name','')} {t.name}")

        # 通知
        names = "、".join(t.name for t in fired_triggers)
        title = f"[{row.get('name', code)}] {float(row.get('change_pct') or 0):.2f}%"
        msg = (f"现价 {float(row.get('price') or 0):.2f} | "
               f"触发: {names}")
        notifier.notify(title=title, message=msg)

        if self.on_trigger:
            try:
                self.on_trigger(row, fired_triggers)
            except Exception as e:
                log.warning("on_trigger 回调异常: %s", e)

    def _log_trigger(self, code: str, rule_key: str,
                     price: float, change_pct: float, note: str) -> None:
        try:
            with db.cursor() as cur:
                cur.execute(
                    """INSERT INTO watch_log
                    (code, rule_key, trigger_at, price, change_pct, note)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (code, rule_key, datetime.now().isoformat(timespec="seconds"),
                     price, change_pct, note),
                )
        except Exception as e:
            log.warning("写入 watch_log 失败: %s", e)

    def recent_logs(self, limit: int = 200) -> List[Dict[str, object]]:
        with db.cursor() as cur:
            cur.execute(
                """SELECT id, code, rule_key, trigger_at, price, change_pct, note
                   FROM watch_log ORDER BY id DESC LIMIT ?""",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]
