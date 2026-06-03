"""数据中心 Tab（含智能增量更新 + 断点续传 + 数据预览）。"""
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar,
    QTextEdit, QGroupBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import QThread, Signal, Qt

from ...data.fetcher import DataFetcher
from ...logger import log


class _DataThread(QThread):
    """数据更新线程（支持断点续传 + 智能增量）。"""
    progress = Signal(int, int, str, int, int, int)  # (current, total, code, updated, skipped, failed)
    log = Signal(str)
    finished_ok = Signal(int, int, int, int, str)  # (total, updated, skipped, failed, last_code)
    failed = Signal(str)

    def __init__(self, fetcher: DataFetcher, action: str = "incremental", parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.action = action

    def run(self):
        try:
            if self.action == "list":
                self.log.emit("📥 正在获取股票列表...")
                n = self.fetcher.update_stock_list()
                self.log.emit(f"✅ 股票列表更新完成，共 {n} 只")
                self.finished_ok.emit(n, 0, 0, 0, "")
                return

            # 日线更新
            self.log.emit("📥 正在同步股票列表...")
            self.fetcher.update_stock_list()
            df = self.fetcher.get_local_stock_list()
            codes = df["code"].tolist() if not df.empty else []
            if not codes:
                self.log.emit("⚠️ 没有股票代码，请先更新股票列表")
                self.finished_ok.emit(0, 0, 0, 0, "")
                return

            total = len(codes)
            updated = 0
            skipped = 0
            failed = 0
            action_name = "全量" if self.action == "full" else "增量"

            # 读取断点
            start_idx = 0
            if self.action == "incremental":
                saved = self.fetcher.get_update_progress()
                if saved and saved.get("last_code"):
                    last_code = saved["last_code"]
                    if last_code in codes:
                        start_idx = codes.index(last_code) + 1
                        self.log.emit(f"🔄 断点续传：从第 {start_idx + 1} 只开始（上次中断于 {last_code}）")
                    else:
                        self.log.emit("💡 未找到上次进度，从头开始")

            self.log.emit(f"🚀 开始{action_name}更新 {total} 只股票的日线")
            self.log.emit("💡 已更新到最新日期的会自动跳过，不重复拉取")

            last_code = ""
            for i in range(start_idx, len(codes)):
                code = codes[i]

                if self.isInterruptionRequested():
                    self.fetcher.save_update_progress(last_code)
                    self.log.emit(f"⏹️ 已暂停。进度已保存：{code}（{i+1}/{total}）")
                    self.log.emit(f"   下次继续时会从这里开始，无需重新处理")
                    self.finished_ok.emit(i - start_idx, updated, skipped, failed, code)
                    return

                try:
                    n_rows = self.fetcher.fetch_daily(
                        code,
                        force=(self.action == "full"),
                        index_total=(i + 1, total)
                    )
                    if n_rows > 0:
                        updated += 1
                        status = f"新增 {n_rows} 条"
                    else:
                        skipped += 1
                        status = "已是最新"
                except Exception as e:
                    failed += 1
                    status = f"失败({str(e)[:20]})"

                last_code = code

                if (i + 1) % 20 == 0 or i == total - 1 or status.startswith("失败"):
                    self.progress.emit(i + 1, total, code, updated, skipped, failed)

                if (i + 1) % 50 == 0:
                    self.fetcher.save_update_progress(code)

                self.log.emit(f"  {i+1:4d}/{total}  {code}  →  {status}")

            self.fetcher.clear_update_progress()

            self.log.emit(f"")
            self.log.emit(f"✅ {action_name}更新完成！")
            self.log.emit(f"   📊 总计：{total} 只（本次处理 {total - start_idx} 只）")
            self.log.emit(f"   🆕 新增数据：{updated} 只")
            self.log.emit(f"   ⏭️ 已是最新：{skipped} 只")
            self.log.emit(f"   ❌ 失败：{failed} 只")
            self.finished_ok.emit(total, updated, skipped, failed, "")

        except Exception as e:
            self.failed.emit(str(e))


class DataCenterWidget(QWidget):
    data_updated = Signal()

    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._thread: Optional[_DataThread] = None
        self._build_ui()
        self._refresh_summary()
        self._refresh_preview()
        self._check_stock_list_updated()
        self._check_resume()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # ========== 操作区 ==========
        ops_box = QGroupBox("数据操作")
        ops_layout = QHBoxLayout(ops_box)
        ops_layout.setContentsMargins(16, 20, 16, 16)
        ops_layout.setSpacing(12)

        self.btn_list = QPushButton("📥 更新股票列表")
        self.btn_list.setFixedHeight(40)
        self.btn_list.clicked.connect(lambda: self._start("list"))
        ops_layout.addWidget(self.btn_list)

        self.btn_incr = QPushButton("⬆️ 增量更新日线")
        self.btn_incr.setObjectName("primaryButton")
        self.btn_incr.setFixedHeight(40)
        self.btn_incr.clicked.connect(lambda: self._start("incremental"))
        ops_layout.addWidget(self.btn_incr)

        self.btn_full = QPushButton("🔄 全量更新日线")
        self.btn_full.setFixedHeight(40)
        self.btn_full.clicked.connect(lambda: self._start("full"))
        ops_layout.addWidget(self.btn_full)

        self.btn_cancel = QPushButton("⏹ 暂停")
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)
        ops_layout.addWidget(self.btn_cancel)

        ops_layout.addStretch(1)
        root.addWidget(ops_box)

        # ========== 进度区 ==========
        progress_box = QGroupBox("更新进度")
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setContentsMargins(16, 20, 16, 16)
        progress_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 10000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setFormat("%v/%m  %p%")
        progress_layout.addWidget(self.progress_bar)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.lbl_updated = self._make_stat("🆕 新增", "0", "#3fb950")
        self.lbl_skipped = self._make_stat("⏭️ 跳过", "0", "#388bfd")
        self.lbl_failed = self._make_stat("❌ 失败", "0", "#f85149")
        self.lbl_status = self._make_stat("📊 状态", "就绪", "#8b949e")

        for w in [self.lbl_updated, self.lbl_skipped, self.lbl_failed, self.lbl_status]:
            stats_layout.addWidget(w)
        stats_layout.addStretch(1)
        progress_layout.addLayout(stats_layout)

        root.addWidget(progress_box)

        # ========== 摘要 + 数据预览（上下布局）==========
        bottom_splitter = QFrame()
        bottom_layout = QVBoxLayout(bottom_splitter)
        bottom_layout.setSpacing(10)

        # 摘要区
        summary_box = QGroupBox("本地数据摘要")
        summary_layout = QHBoxLayout(summary_box)
        summary_layout.setContentsMargins(16, 20, 16, 16)
        summary_layout.setSpacing(12)

        self._n_stocks = self._make_stat("📈 股票", "—", "#f0883e")
        self._n_daily = self._make_stat("📊 日线", "—", "#ffa502")
        self._n_latest = self._make_stat("🕐 最新日期", "—", "#8b949e")
        self._n_range = self._make_stat("📅 日期范围", "—", "#388bfd")

        for w in [self._n_stocks, self._n_daily, self._n_latest, self._n_range]:
            summary_layout.addWidget(w)
        summary_layout.addStretch(1)

        bottom_layout.addWidget(summary_box)

        # 数据预览
        preview_box = QGroupBox("📋 数据预览（最近更新 10 条）")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(16, 20, 16, 16)

        self.preview_table = QTableWidget(0, 6)
        self.preview_table.setHorizontalHeaderLabels(["代码", "名称", "日期", "开盘", "最高", "收盘"])
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_layout.addWidget(self.preview_table)

        bottom_layout.addWidget(preview_box, stretch=1)

        root.addWidget(bottom_splitter, stretch=2)

        # ========== 日志区 ==========
        log_box = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(16, 20, 16, 16)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d; "
            "border-radius: 6px; font-family: 'Menlo', 'Monaco', monospace; font-size: 12px; "
            "padding: 8px;"
        )
        log_layout.addWidget(self.log_view)

        root.addWidget(log_box, stretch=1)

        self._log("✅ 系统就绪。点击上方按钮开始更新数据。")
        self._log("💡 增量更新日线只会拉取缺少的日期，已有的数据会自动跳过。")

    def _check_stock_list_updated(self):
        """检查股票列表是否已更新过，如果是则更新按钮文字。"""
        updated_time = self.fetcher.get_stock_list_updated_time()
        if updated_time:
            self.btn_list.setText(f"✅ 股票列表已更新")
            self.btn_list.setEnabled(False)
            self._log(f"📌 股票列表已于 {updated_time} 更新，跳过重复更新")

    def _check_resume(self):
        """检查是否有未完成的更新进度"""
        saved = self.fetcher.get_update_progress()
        if saved and saved.get("last_code"):
            self._log(f"")
            self._log(f"📌 检测到未完成的更新任务")
            self._log(f"   上次中断于：{saved['last_code']}")
            self._log(f"   下次运行增量更新时会自动从断点继续")

    def _make_stat(self, label: str, value: str, color: str) -> QWidget:
        """制作一个统计标签卡片。"""
        card = QWidget()
        card.setStyleSheet(
            "QWidget { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("statValue")
        val_lbl.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        val_lbl.setAlignment(Qt.AlignCenter)

        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        lbl_lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(val_lbl)
        layout.addWidget(lbl_lbl)
        card.setMinimumWidth(90)
        return card

    def _refresh_summary(self):
        """刷新本地数据摘要。"""
        try:
            import sqlite3
            conn = sqlite3.connect("data/oracle.db")
            cur = conn.cursor()

            # 股票数量
            cur.execute("SELECT COUNT(*) FROM stock_list")
            n = cur.fetchone()[0]
            self._n_stocks.findChild(QLabel, "statValue").setText(str(n) if n else "—")

            # 日线条数
            cur.execute("SELECT COUNT(*) FROM kline_daily")
            n = cur.fetchone()[0]
            self._n_daily.findChild(QLabel, "statValue").setText(f"{n:,}" if n else "0")

            # 日期范围
            cur.execute("SELECT MIN(trade_date), MAX(trade_date) FROM kline_daily")
            row = cur.fetchone()
            if row and row[0] and row[1]:
                self._n_latest.findChild(QLabel, "statValue").setText(str(row[1])[:10])
                self._n_range.findChild(QLabel, "statValue").setText(f"{str(row[0])[:10]} ~ {str(row[1])[:10]}")
            else:
                self._n_latest.findChild(QLabel, "statValue").setText("—")
                self._n_range.findChild(QLabel, "statValue").setText("—")

            cur.close()
            conn.close()
        except Exception as e:
            log.warning("刷新摘要失败: %s", e)

    def _refresh_preview(self):
        """刷新数据预览表格。"""
        try:
            import sqlite3
            conn = sqlite3.connect("data/oracle.db")
            cur = conn.cursor()

            cur.execute("""
                SELECT k.code, s.name, k.trade_date, k.open, k.high, k.close
                FROM kline_daily k
                LEFT JOIN stock_list s ON k.code = s.code
                ORDER BY k.trade_date DESC, k.code ASC
                LIMIT 15
            """)
            rows = cur.fetchall()

            self.preview_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    if c in (3, 4, 5) and val is not None:
                        text = f"{float(val):.2f}"
                    else:
                        text = str(val) if val else "-"
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    # 涨跌颜色
                    if c == 5 and len(row) > 3:
                        try:
                            open_p = float(row[3]) if row[3] else 0
                            close_p = float(val) if val else 0
                            if close_p > open_p > 0:
                                item.setForeground(Qt.GlobalColor.red)
                            elif close_p < open_p > 0:
                                item.setForeground(Qt.GlobalColor.darkGreen)
                        except:
                            pass
                    self.preview_table.setItem(r, c, item)

            cur.close()
            conn.close()
        except Exception as e:
            log.warning("刷新预览失败: %s", e)

    def _log(self, text: str):
        self.log_view.append(text)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def _start(self, action: str):
        if self._thread is not None and self._thread.isRunning():
            self._log("⚠️ 已有任务在运行")
            return

        self._update_stat(self.lbl_updated, "0")
        self._update_stat(self.lbl_skipped, "0")
        self._update_stat(self.lbl_failed, "0")
        self._set_buttons_enabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self._update_stat(self.lbl_status, "运行中...")

        self._thread = _DataThread(self.fetcher, action)
        self._thread.progress.connect(self._on_progress)
        self._thread.log.connect(self._on_log)
        self._thread.finished_ok.connect(self._on_done)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _cancel(self):
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self.btn_cancel.setEnabled(False)
            self._update_stat(self.lbl_status, "暂停中...")

    def _set_buttons_enabled(self, enabled: bool):
        self.btn_list.setEnabled(enabled)
        self.btn_incr.setEnabled(enabled)
        self.btn_full.setEnabled(enabled)

    def _update_stat(self, card: QWidget, value: str):
        val_lbl = card.findChild(QLabel, "statValue")
        if val_lbl:
            val_lbl.setText(value)

    def _on_progress(self, current: int, total: int, code: str, updated: int, skipped: int, failed: int):
        pct = int(current / total * 10000) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self._update_stat(self.lbl_updated, str(updated))
        self._update_stat(self.lbl_skipped, str(skipped))
        self._update_stat(self.lbl_failed, str(failed))
        self._update_stat(self.lbl_status, f"{current}/{total}")

    def _on_log(self, text: str):
        self._log(text)

    def _on_done(self, total: int, updated: int, skipped: int, failed: int, last_code: str):
        self._set_buttons_enabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(10000)
        self._update_stat(self.lbl_updated, str(updated))
        self._update_stat(self.lbl_skipped, str(skipped))
        self._update_stat(self.lbl_failed, str(failed))

        if last_code:
            self._update_stat(self.lbl_status, f"⏹ {last_code}")
        elif failed > 0:
            self._update_stat(self.lbl_status, f"⚠️ {failed}个失败")
        else:
            self._update_stat(self.lbl_status, "✅ 完成")

        self._refresh_summary()
        self._refresh_preview()
        self.data_updated.emit()

    def _on_failed(self, err: str):
        self._set_buttons_enabled(True)
        self.btn_cancel.setEnabled(False)
        self._update_stat(self.lbl_status, "❌ 失败")
        self._log(f"❌ 错误: {err}")
        log.error("数据中心任务失败: %s", err)
