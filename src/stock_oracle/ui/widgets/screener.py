"""选股中心 Tab。"""
from typing import Dict, Optional

import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFormLayout,
    QGroupBox, QDoubleSpinBox, QSpinBox, QCheckBox, QMessageBox, QFileDialog,
)
from PySide6.QtCore import QThread, Signal, Qt

from ...data.fetcher import DataFetcher
from ...indicators.technical import enrich
from ...screener.engine import RuleRegistry, run_rule, results_to_dataframe
from ...logger import log


class _ScreenThread(QThread):
    progress = Signal(int, int, str)   # (idx, total, code)
    finished_ok = Signal(object)       # List[RuleResult]
    failed = Signal(str)

    def __init__(self, fetcher: DataFetcher, rule_key: str,
                 params: dict, top_n: int = 50, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.rule_key = rule_key
        self.params = params
        self.top_n = top_n

    def run(self):
        try:
            # 取股票列表
            df_list = self.fetcher.get_local_stock_list()
            if df_list.empty:
                self.failed.emit("请先在『数据中心』更新股票列表")
                return

            codes = df_list["code"].tolist()
            names = dict(zip(df_list["code"], df_list["name"]))
            results = []
            total = len(codes)
            for i, code in enumerate(codes):
                kline = self.fetcher.get_local_daily(code)
                if kline.empty or len(kline) < 25:
                    continue
                enriched = enrich(kline)
                r = run_rule(self.rule_key, enriched, self.params,
                             code=code, name=names.get(code, ""))
                if r.hit:
                    results.append(r)
                if i % 100 == 0:
                    self.progress.emit(i + 1, total, code)

            results.sort(key=lambda x: x.score, reverse=True)
            self.progress.emit(total, total, "done")
            self.finished_ok.emit(results[: self.top_n])
        except Exception as e:
            self.failed.emit(str(e))


class ScreenerWidget(QWidget):
    """选股中心界面。"""

    code_clicked = Signal(str)  # 发射到行情中心

    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._thread: Optional[_ScreenThread] = None
        self._build_ui()

    # ==================== UI ====================
    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        # 左侧：规则 + 参数
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(6, 6, 6, 6)

        rule_box = QGroupBox("选股规则")
        rl = QVBoxLayout(rule_box)
        self.rule_combo = QComboBox()
        for k in RuleRegistry.all_keys():
            meta = RuleRegistry.get_meta(k)
            self.rule_combo.addItem(f"{k} — {meta.get('desc','')}", k)
        self.rule_combo.currentIndexChanged.connect(self._on_rule_changed)
        rl.addWidget(self.rule_combo)

        self.param_box = QGroupBox("参数")
        self.param_form = QFormLayout(self.param_box)
        rl.addWidget(self.param_box)

        self.top_spin = QSpinBox()
        self.top_spin.setRange(10, 500)
        self.top_spin.setValue(50)
        self.param_form.addRow("返回 Top N", self.top_spin)

        self.btn_run = QPushButton("▶ 运行选股")
        self.btn_run.clicked.connect(self._on_run)
        rl.addWidget(self.btn_run)

        self.btn_export = QPushButton("导出 CSV")
        self.btn_export.clicked.connect(self._on_export)
        rl.addWidget(self.btn_export)

        lv.addWidget(rule_box)
        lv.addStretch(1)

        splitter.addWidget(left)

        # 右侧：结果表
        right = QWidget()
        rv = QVBoxLayout(right)
        self.lbl_status = QLabel("就绪")
        rv.addWidget(self.lbl_status)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        rv.addWidget(self.table, stretch=1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        self._on_rule_changed(0)
        self._last_df = pd.DataFrame()

    def _on_rule_changed(self, _idx):
        # 动态生成参数输入控件
        while self.param_form.rowCount() > 1:
            self.param_form.removeRow(1)

        rule_key = self.rule_combo.currentData()
        meta = RuleRegistry.get_meta(rule_key)
        params = meta.get("params", {})

        self._param_inputs = {}
        for k, v in params.items():
            if isinstance(v, bool):
                cb = QCheckBox()
                cb.setChecked(v)
                self.param_form.addRow(k, cb)
                self._param_inputs[k] = cb
            elif isinstance(v, int):
                sp = QSpinBox()
                sp.setRange(-1000000, 1000000)
                sp.setValue(int(v))
                self.param_form.addRow(k, sp)
                self._param_inputs[k] = sp
            else:
                ds = QDoubleSpinBox()
                ds.setRange(-100000.0, 100000.0)
                ds.setDecimals(3)
                ds.setValue(float(v))
                self.param_form.addRow(k, ds)
                self._param_inputs[k] = ds

    def _collect_params(self) -> Dict:
        out = {}
        for k, w in self._param_inputs.items():
            if isinstance(w, QCheckBox):
                out[k] = w.isChecked()
            elif isinstance(w, QSpinBox):
                out[k] = w.value()
            elif isinstance(w, QDoubleSpinBox):
                out[k] = w.value()
        return out

    def _on_run(self):
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(self, "提示", "已有任务正在运行")
            return

        rule_key = self.rule_combo.currentData()
        params = self._collect_params()
        params["code"] = ""
        top_n = self.top_spin.value()

        self.btn_run.setEnabled(False)
        self.lbl_status.setText("运行中...")

        self._thread = _ScreenThread(self.fetcher, rule_key, params, top_n)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished_ok.connect(self._on_done)
        self._thread.failed.connect(self._on_failed)
        self._thread.finished.connect(lambda: self.btn_run.setEnabled(True))
        self._thread.start()

    def _on_progress(self, idx, total, code):
        pct = int((idx / total) * 100) if total > 0 else 0
        self.lbl_status.setText(f"运行中 {idx}/{total} ({pct}%) — {code}")

    def _on_done(self, results):
        df = results_to_dataframe(results) if results else pd.DataFrame()
        self._last_df = df
        self._render_table(df)
        self.lbl_status.setText(f"完成，命中 {len(df)} 只")

    def _on_failed(self, err: str):
        self.lbl_status.setText("失败")
        QMessageBox.critical(self, "错误", err)
        log.error("选股失败: %s", err)

    def _render_table(self, df: pd.DataFrame):
        self.table.clear()
        if df.empty:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        columns = list(df.columns)
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(df))
        for r in range(len(df)):
            for c, col in enumerate(columns):
                val = df.iloc[r][col]
                if isinstance(val, float):
                    text = f"{val:.2f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                if col == "code":
                    item.setData(Qt.UserRole, str(df.iloc[r][col]))
                self.table.setItem(r, c, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def _on_row_double_clicked(self, index):
        row = index.row()
        code_item = self.table.item(row, 0)
        if code_item is None:
            code_item = self.table.item(row, self.table.columnCount() - 1)
        # 查找 code 列
        code = None
        for c in range(self.table.columnCount()):
            item = self.table.item(row, c)
            header = self.table.horizontalHeaderItem(c)
            if header and header.text() == "code" and item:
                code = item.text()
                break
        if code is None and code_item is not None:
            code = code_item.text()
        if code:
            self.code_clicked.emit(str(code).zfill(6))

    def _on_export(self):
        if self._last_df.empty:
            QMessageBox.information(self, "提示", "没有可导出的数据")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV",
                                              f"screen_result.csv",
                                              "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            self._last_df.to_csv(path, index=False, encoding="utf-8-sig")
            QMessageBox.information(self, "成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "失败", str(e))
