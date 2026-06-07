"""选股中心。"""
from typing import Dict, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFormLayout,
    QGroupBox, QDoubleSpinBox, QSpinBox, QCheckBox, QMessageBox, QFileDialog,
    QLineEdit, QProgressBar, QTextEdit, QDialog,
)
from PySide6.QtCore import QThread, Signal, Qt

from ...data.fetcher import DataFetcher
from ...indicators.technical import enrich
from ...screener.engine import RuleRegistry, run_rule
from ...llm import LLMClient
from ... import config
from ...logger import log


class _ScreenThread(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(object)
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
            df_list = self.fetcher.get_local_stock_list()
            if df_list.empty:
                self.failed.emit("请先在『数据中心』更新股票列表和日线数据")
                return

            codes = df_list["code"].tolist()
            names = dict(zip(df_list["code"], df_list["name"]))
            results = []
            total = len(codes)

            for i, code in enumerate(codes):
                if self.isInterruptionRequested():
                    self.finished_ok.emit(results[:self.top_n])
                    return
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
            self.progress.emit(total, total, "完成")
            self.finished_ok.emit(results[:self.top_n])
        except Exception as e:
            self.failed.emit(str(e))


class _ExplainThread(QThread):
    """AI解释线程。"""
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, llm_client: LLMClient,
                 stock_name: str, stock_code: str,
                 rule_name: str, reasons: list,
                 extras: dict, kline_df, parent=None):
        super().__init__(parent)
        self.llm_client = llm_client
        self.stock_name = stock_name
        self.stock_code = stock_code
        self.rule_name = rule_name
        self.reasons = reasons
        self.extras = extras
        self.kline_df = kline_df

    def run(self):
        try:
            response = self.llm_client.explain_stock_selection(
                stock_name=self.stock_name,
                stock_code=self.stock_code,
                rule_name=self.rule_name,
                reasons=self.reasons,
                extras=self.extras,
                kline_df=self.kline_df
            )
            if response.success:
                self.finished_ok.emit(response.text)
            else:
                self.failed.emit(response.error or "未知错误")
        except Exception as e:
            self.failed.emit(str(e))


class ExplainDialog(QDialog):
    """AI解释对话框。"""

    def __init__(self, fetcher: DataFetcher, stock_result, rule_name: str, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.stock_result = stock_result
        self.rule_name = rule_name
        self.explain_thread: Optional[_ExplainThread] = None
        self._build_ui()
        self._start_explain()

    def _build_ui(self):
        self.setWindowTitle(f"🤖 AI 选股解释 - {self.stock_result.name}({self.stock_result.code})")
        self.resize(600, 450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 股票信息
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>股票：</b>{self.stock_result.name} ({self.stock_result.code})"))
        info_layout.addWidget(QLabel(f"<b>规则：</b>{self.rule_name}"))
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # 原因列表
        reasons_label = QLabel("<b>命中原因：</b>")
        layout.addWidget(reasons_label)
        reasons_text = "\n".join([f"  • {r}" for r in self.stock_result.reasons])
        reasons_edit = QTextEdit(reasons_text)
        reasons_edit.setReadOnly(True)
        reasons_edit.setMaximumHeight(100)
        layout.addWidget(reasons_edit)

        # AI解释
        layout.addWidget(QLabel("<b>AI 分析：</b>"))
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("正在调用AI分析，请稍候...")
        layout.addWidget(self.result_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("关闭")
        self.close_btn.setFixedHeight(36)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def _start_explain(self):
        try:
            cfg = config.load_config()
            provider = cfg.get("ai_provider", "qwen")
            api_key = cfg.get("ai_api_key", "")
            api_secret = cfg.get("ai_api_secret", "")

            if not api_key:
                self.result_edit.setText(
                    "⚠️ 请先在「设置中心」配置 AI API Key\n\n"
                    "📖 获取方式：\n"
                    "• 通义千问：https://dashscope.console.aliyun.com/apiKey\n"
                    "• 讯飞星火：https://console.xfyun.cn/services/bm35lite"
                )
                return

            # 准备代理
            proxy = None
            http_proxy = cfg.get("http_proxy", "")
            https_proxy = cfg.get("https_proxy", "")
            if http_proxy or https_proxy:
                proxy = {
                    "http": http_proxy,
                    "https": https_proxy
                }

            llm_client = LLMClient(
                provider=provider,
                api_key=api_key,
                api_secret=api_secret,
                proxy=proxy
            )

            # 获取K线数据
            kline_df = self.fetcher.get_local_daily(self.stock_result.code)

            self.explain_thread = _ExplainThread(
                llm_client=llm_client,
                stock_name=self.stock_result.name,
                stock_code=self.stock_result.code,
                rule_name=self.rule_name,
                reasons=self.stock_result.reasons,
                extras=getattr(self.stock_result, "extras", {}),
                kline_df=kline_df
            )
            self.explain_thread.finished_ok.connect(self._on_explain_ok)
            self.explain_thread.failed.connect(self._on_explain_failed)
            self.explain_thread.start()
        except Exception as e:
            self.result_edit.setText(f"❌ 初始化失败：{str(e)}")

    def _on_explain_ok(self, text: str):
        self.result_edit.setText(text)

    def _on_explain_failed(self, error: str):
        self.result_edit.setText(f"❌ AI分析失败：{error}\n\n💡 请检查网络和API Key配置")


class ScreenerWidget(QWidget):
    code_clicked = Signal(str)

    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._thread: Optional[_ScreenThread] = None
        self._last_results = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)

        # ========== 左侧：规则与参数 ==========
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)

        # 规则选择
        rule_box = QGroupBox("选股规则")
        rl = QVBoxLayout(rule_box)
        rl.setContentsMargins(12, 18, 12, 12)
        rl.setSpacing(8)

        self.rule_combo = QComboBox()
        self.rule_combo.setFixedHeight(32)
        rule_name_map = {
            "consolidation_breakout": "核心策略",
            "ma_cross": "均线金叉",
            "macd_golden": "MACD金叉",
            "new_high_breakout": "新高突破",
            "limit_up": "涨停检测",
        }
        for k in RuleRegistry.all_keys():
            meta = RuleRegistry.get_meta(k)
            name = rule_name_map.get(k, k)
            self.rule_combo.addItem(f"{name}  —  {meta.get('desc', '')}", k)
        self.rule_combo.currentIndexChanged.connect(self._on_rule_changed)
        rl.addWidget(self.rule_combo)
        lv.addWidget(rule_box)

        # 参数
        param_box = QGroupBox("参数")
        pl = QVBoxLayout(param_box)
        pl.setContentsMargins(12, 18, 12, 12)
        pl.setSpacing(6)

        self.param_form = QFormLayout()
        self.param_form.setSpacing(8)
        self.top_spin = QSpinBox()
        self.top_spin.setRange(10, 500)
        self.top_spin.setValue(50)
        self.top_spin.setFixedHeight(30)
        self.param_form.addRow("返回数量", self.top_spin)
        pl.addLayout(self.param_form)
        lv.addWidget(param_box)

        # 运行按钮
        self.btn_run = QPushButton("▶ 运行选股")
        self.btn_run.setObjectName("primaryButton")
        self.btn_run.setFixedHeight(44)
        self.btn_run.clicked.connect(self._on_run)
        lv.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("⏹ 取消")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        lv.addWidget(self.btn_cancel)

        self.btn_export = QPushButton("📤 导出 CSV")
        self.btn_export.setFixedHeight(36)
        self.btn_export.clicked.connect(self._on_export)
        lv.addWidget(self.btn_export)

        lv.addStretch(1)
        splitter.addWidget(left)

        # ========== 右侧：结果 ==========
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(8)

        self.lbl_result_status = QLabel("请选择规则后点击「运行选股」")
        self.lbl_result_status.setStyleSheet("color: #8b949e; font-weight: bold; padding: 4px;")
        rv.addWidget(self.lbl_result_status)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setFormat("就绪")
        rv.addWidget(self.progress_bar)

        # 结果表
        result_box = QGroupBox("选股结果")
        rbox_layout = QVBoxLayout(result_box)
        rbox_layout.setContentsMargins(8, 18, 8, 8)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        rbox_layout.addWidget(self.table)

        rv.addWidget(result_box, stretch=1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        root.addWidget(splitter, stretch=1)
        self._on_rule_changed(0)

    def _on_rule_changed(self, _idx):
        # 清除旧参数行
        while self.param_form.rowCount() > 1:
            self.param_form.removeRow(1)

        rule_key = self.rule_combo.currentData()
        meta = RuleRegistry.get_meta(rule_key)
        params = meta.get("params", {})
        param_names = {
            "consolidation_days": "横盘天数",
            "consolidation_range_pct": "横盘振幅(%)",
            "shrink_vol_ratio": "缩量比",
            "today_min_pct": "最小涨幅(%)",
            "today_max_pct": "最大涨幅(%)",
            "vol_expansion_ratio": "量能放大倍数",
            "price_above_ma20": "价格站上MA20",
            "short": "短期均线",
            "long": "长期均线",
            "n_days": "突破天数",
            "vol_ratio": "量比阈值",
        }

        self._param_inputs = {}
        for k, v in params.items():
            label = param_names.get(k, k)
            if isinstance(v, bool):
                cb = QCheckBox()
                cb.setChecked(v)
                self.param_form.addRow(label, cb)
                self._param_inputs[k] = cb
            elif isinstance(v, int):
                sp = QSpinBox()
                sp.setRange(-10000, 10000)
                sp.setValue(int(v))
                sp.setFixedHeight(28)
                self.param_form.addRow(label, sp)
                self._param_inputs[k] = sp
            else:
                ds = QDoubleSpinBox()
                ds.setRange(-10000.0, 10000.0)
                ds.setDecimals(3)
                ds.setValue(float(v))
                ds.setFixedHeight(28)
                self.param_form.addRow(label, ds)
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
            return

        rule_key = self.rule_combo.currentData()
        params = self._collect_params()
        top_n = self.top_spin.value()

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("启动中...")
        self.lbl_result_status.setText(f"⏳ 正在运行: {rule_key}")
        self.lbl_result_status.setStyleSheet("color: #f0883e; font-weight: bold; padding: 4px;")

        self._thread = _ScreenThread(self.fetcher, rule_key, params, top_n)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished_ok.connect(self._on_done)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _on_cancel(self):
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self.btn_cancel.setEnabled(False)
            self.lbl_result_status.setText("⏹ 正在取消...")

    def _on_progress(self, idx, total, code):
        if total > 0:
            pct = int(idx / total * 100)
            self.progress_bar.setValue(pct)
            self.progress_bar.setFormat(f"{idx}/{total} ({pct}%) - {code}")
            self.lbl_result_status.setText(f"⏳ 扫描中: {idx}/{total} - {code}")

    def _on_done(self, results):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self._last_results = results

        if not results:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("完成")
            self.lbl_result_status.setText("⚠️ 没有符合条件的股票")
            self.lbl_result_status.setStyleSheet("color: #d29922; font-weight: bold; padding: 4px;")
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("完成")
        self.lbl_result_status.setText(f"✅ 命中 {len(results)} 只股票，按评分降序")
        self.lbl_result_status.setStyleSheet("color: #3fb950; font-weight: bold; padding: 4px;")

        columns = ["代码", "名称", "评分", "原因", "价格", "涨幅%", "AI分析"]
        self.table.clear()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(results))

        # 获取当前规则名称
        current_rule_key = self.rule_combo.currentData()
        rule_name_map = {
            "consolidation_breakout": "底部横盘缩量 + 今日放量上涨",
            "ma_cross": "均线金叉",
            "macd_golden": "MACD金叉",
            "new_high_breakout": "突破新高",
            "limit_up": "涨停板",
        }
        rule_name = rule_name_map.get(current_rule_key, current_rule_key)

        for r, res in enumerate(results):
            item_code = QTableWidgetItem(str(getattr(res, "code", "")))
            item_name = QTableWidgetItem(str(getattr(res, "name", "")))
            item_score = QTableWidgetItem(f"{getattr(res, 'score', 0):.2f}")
            item_reason = QTableWidgetItem(", ".join(getattr(res, "reasons", [])[:3]))
            price = getattr(res, "extra", {}).get("price")
            pct = getattr(res, "extra", {}).get("change_pct")
            item_price = QTableWidgetItem(f"{float(price):.2f}" if price else "-")
            item_pct = QTableWidgetItem(f"{float(pct):+.2f}%" if pct is not None else "-")

            for item in [item_code, item_name, item_score, item_reason, item_price, item_pct]:
                item.setTextAlignment(Qt.AlignCenter)

            # 涨跌幅颜色
            if pct is not None and float(pct) > 0:
                item_pct.setForeground(Qt.GlobalColor.red)

            self.table.setItem(r, 0, item_code)
            self.table.setItem(r, 1, item_name)
            self.table.setItem(r, 2, item_score)
            self.table.setItem(r, 3, item_reason)
            self.table.setItem(r, 4, item_price)
            self.table.setItem(r, 5, item_pct)

            # AI分析按钮
            btn = QPushButton("🤖 AI分析")
            btn.setFixedHeight(26)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: #333;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            btn.clicked.connect(lambda checked, idx=r, result=res, rn=rule_name: self._on_ai_explain(idx, result, rn))
            self.table.setCellWidget(r, 6, btn)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def _on_ai_explain(self, row: int, result, rule_name: str):
        """打开AI解释对话框。"""
        dialog = ExplainDialog(self.fetcher, result, rule_name, self)
        dialog.exec()

    def _on_failed(self, err: str):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_result_status.setText(f"❌ 失败: {err[:60]}")
        self.lbl_result_status.setStyleSheet("color: #f85149; font-weight: bold; padding: 4px;")
        log.error("选股失败: %s", err)
        QMessageBox.critical(self, "失败", err)

    def _on_row_double_clicked(self, index):
        row = index.row()
        code_item = self.table.item(row, 0)
        if code_item:
            self.code_clicked.emit(str(code_item.text()))

    def _on_export(self):
        if not self._last_results:
            QMessageBox.information(self, "提示", "没有可导出的数据")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "screen_result.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            rows = []
            for r in self._last_results:
                rows.append({
                    "code": getattr(r, "code", ""),
                    "name": getattr(r, "name", ""),
                    "score": getattr(r, "score", 0),
                    "reasons": ", ".join(getattr(r, "reasons", [])),
                })
            pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
            QMessageBox.information(self, "成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "失败", str(e))
