"""数据中心 Tab。"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar,
    QTextEdit, QSpinBox, QComboBox, QGroupBox, QFormLayout,
)
from PySide6.QtCore import QThread, Signal, Qt

from ...data.fetcher import DataFetcher
from ...logger import log


class _UpdateThread(QThread):
    progress = Signal(str, int, int)  # (code, idx, total)
    finished_ok = Signal(int, int)   # (stocks, rows)
    failed = Signal(str)

    def __init__(self, fetcher: DataFetcher, action: str = "all",
                 codes=None, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.action = action
        self.codes = codes or []

    def run(self):
        try:
            if self.action == "list":
                n = self.fetcher.update_stock_list()
                self.finished_ok.emit(n, 0)
            elif self.action == "incremental":
                self.fetcher.update_stock_list()
                df = self.fetcher.get_local_stock_list()
                codes = df["code"].tolist() if not df.empty else []
                rows = 0
                total = len(codes)
                for i, code in enumerate(codes):
                    if i % 200 == 0:
                        self.progress.emit(code, i + 1, total)
                    rows += self.fetcher.fetch_daily(code)
                self.finished_ok.emit(total, rows)
            elif self.action == "full":
                # 全量：force=True
                self.fetcher.update_stock_list()
                df = self.fetcher.get_local_stock_list()
                codes = df["code"].tolist() if not df.empty else []
                rows = 0
                total = len(codes)
                for i, code in enumerate(codes):
                    if i % 200 == 0:
                        self.progress.emit(code, i + 1, total)
                    rows += self.fetcher.fetch_daily(code, force=True)
                self.finished_ok.emit(total, rows)
        except Exception as e:
            self.failed.emit(str(e))


class DataCenterWidget(QWidget):
    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._thread: _UpdateThread | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 操作区
        op_box = QGroupBox("数据更新")
        op_form = QFormLayout(op_box)

        self.btn_list = QPushButton("更新股票列表")
        self.btn_list.clicked.connect(self._on_update_list)

        self.btn_incr = QPushButton("增量更新日线（推荐）")
        self.btn_incr.setToolTip("从上次最后一个交易日增量拉取")
        self.btn_incr.clicked.connect(self._on_incremental)

        self.btn_full = QPushButton("全量更新日线")
        self.btn_full.setToolTip("强制重新拉取全部股票最近的数据")
        self.btn_full.clicked.connect(self._on_full)

        self.provider_box = QComboBox()
        self.provider_box.addItems(["akshare", "efinance"])
        self.provider_box.setCurrentText("akshare")

        op_form.addRow("数据源", self.provider_box)
        row = QHBoxLayout()
        row.addWidget(self.btn_list)
        row.addWidget(self.btn_incr)
        row.addWidget(self.btn_full)
        row.addStretch(1)
        op_form.addRow("操作", self._wrap(row))

        root.addWidget(op_box)

        # 进度区
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.lbl_status = QLabel("就绪")
        root.addWidget(self.lbl_status)

        # 日志
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        root.addWidget(self.log_view, stretch=1)

    def _wrap(self, layout):
        w = QWidget()
        w.setLayout(layout)
        return w

    def _log(self, text: str):
        self.log_view.append(text)

    def _on_update_list(self):
        self._start_thread("list")

    def _on_incremental(self):
        self._start_thread("incremental")

    def _on_full(self):
        self._start_thread("full")

    def _start_thread(self, action: str):
        if self._thread is not None and self._thread.isRunning():
            self._log("已有任务在运行，请等待...")
            return
        self._log(f"启动任务: {action}")
        self.btn_list.setEnabled(False)
        self.btn_incr.setEnabled(False)
        self.btn_full.setEnabled(False)

        self._thread = _UpdateThread(self.fetcher, action=action)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished_ok.connect(self._on_done)
        self._thread.failed.connect(self._on_failed)
        self._thread.finished.connect(lambda: self._enable_buttons())
        self._thread.start()

    def _enable_buttons(self):
        self.btn_list.setEnabled(True)
        self.btn_incr.setEnabled(True)
        self.btn_full.setEnabled(True)

    def _on_progress(self, code: str, idx: int, total: int):
        pct = int((idx / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"更新中: {idx}/{total} - {code}")

    def _on_done(self, stocks: int, rows: int):
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"完成：股票 {stocks} 只, K线 {rows} 行")
        self._log(f"✅ 完成：stocks={stocks}, kline_rows={rows}")

    def _on_failed(self, err: str):
        self.lbl_status.setText("失败")
        self._log(f"❌ 失败: {err}")
        log.error("数据更新失败: %s", err)
