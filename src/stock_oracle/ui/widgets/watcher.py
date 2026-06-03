"""盯盘中心。"""
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QGroupBox,
    QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QInputDialog,
    QMessageBox, QSpinBox, QCheckBox,
)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QBrush, QColor

from ...data.fetcher import DataFetcher
from ...portfolio import manager as portfolio_mgr
from ...watcher import triggers as T
from ...watcher.monitor import Watcher


class _WatchThread(QThread):
    quote_received = Signal(dict)
    trigger_fired = Signal(dict, list)

    def __init__(self, fetcher: DataFetcher, codes: List[str],
                 triggers: List, interval_sec: int = 5, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.codes = codes
        self.triggers = triggers
        self.interval_sec = interval_sec
        self._running = True
        self._watcher: Optional[Watcher] = None

    def run(self):
        self._watcher = Watcher(
            fetcher=self.fetcher,
            interval_sec=self.interval_sec,
            codes=self.codes,
            triggers=self.triggers,
        )
        self._watcher.on_quote = lambda r: self.quote_received.emit(r)
        self._watcher.on_trigger = lambda r, t: self.trigger_fired.emit(r, t)
        self._watcher.start()
        while self._running and self._watcher.is_alive():
            self.msleep(500)

    def stop(self):
        self._running = False
        if self._watcher:
            self._watcher.stop()


class WatcherWidget(QWidget):
    code_clicked = Signal(str)

    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._watch_thread: Optional[_WatchThread] = None
        self._quote_cache: Dict[str, dict] = {}
        self._pending_logs: List[dict] = []
        self._build_ui()

        # UI刷新定时器
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._render_quotes)
        self._refresh_timer.start()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        # ========== 左侧：自选分组 + 股票列表 ==========
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)

        group_box = QGroupBox("自选分组")
        gl = QVBoxLayout(group_box)
        gl.setContentsMargins(12, 18, 12, 12)
        gl.setSpacing(8)

        group_row = QHBoxLayout()
        self.group_combo = QComboBox()
        self.group_combo.setFixedHeight(30)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        group_row.addWidget(self.group_combo, stretch=1)

        btn_new = QPushButton("+")
        btn_new.setFixedSize(34, 30)
        btn_new.clicked.connect(self._on_new_group)
        group_row.addWidget(btn_new)

        btn_del = QPushButton("-")
        btn_del.setFixedSize(34, 30)
        btn_del.clicked.connect(self._on_delete_group)
        group_row.addWidget(btn_del)

        gl.addLayout(group_row)

        self.stock_list = QListWidget()
        self.stock_list.itemDoubleClicked.connect(self._on_stock_double_clicked)
        gl.addWidget(self.stock_list, stretch=1)

        add_row = QHBoxLayout()
        self.add_edit = QLineEdit()
        self.add_edit.setPlaceholderText("输入6位代码")
        self.add_edit.setFixedHeight(30)
        self.add_edit.returnPressed.connect(self._on_add_stock)
        add_row.addWidget(self.add_edit, stretch=1)

        btn_add = QPushButton("添加")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._on_add_stock)
        add_row.addWidget(btn_add)

        btn_rm = QPushButton("删除")
        btn_rm.setFixedHeight(30)
        btn_rm.clicked.connect(self._on_remove_stock)
        add_row.addWidget(btn_rm)

        gl.addLayout(add_row)
        lv.addWidget(group_box)

        splitter.addWidget(left)

        # ========== 中间：控制 + 实时行情表 ==========
        mid = QWidget()
        mv = QVBoxLayout(mid)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(8)

        control_box = QGroupBox("盯盘控制")
        cf = QFormLayout(control_box)
        cf.setContentsMargins(12, 18, 12, 12)
        cf.setSpacing(8)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 600)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setFixedHeight(28)
        cf.addRow("刷新间隔", self.interval_spin)

        self.btn_start = QPushButton("▶ 开始盯盘")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setFixedHeight(36)
        self.btn_start.clicked.connect(self._toggle_watch)
        cf.addRow("控制", self.btn_start)

        # 触发条件
        cb_row = QHBoxLayout()
        self.trigger_pct_up = QCheckBox("涨幅 ≥ 3%")
        self.trigger_pct_up.setChecked(True)
        cb_row.addWidget(self.trigger_pct_up)
        self.trigger_pct_down = QCheckBox("跌幅 ≥ 3%")
        cb_row.addWidget(self.trigger_pct_down)
        mv2 = QWidget()
        cf.addRow("触发条件", _wrap_row(cb_row))

        cb_row2 = QHBoxLayout()
        self.trigger_vol = QCheckBox("量比 ≥ 2")
        cb_row2.addWidget(self.trigger_vol)
        self.trigger_turnover = QCheckBox("换手率 ≥ 5%")
        cb_row2.addWidget(self.trigger_turnover)
        cf.addRow("", _wrap_row(cb_row2))

        mv.addWidget(control_box)

        self.quote_table = QTableWidget(0, 6)
        self.quote_table.setHorizontalHeaderLabels(["代码", "名称", "现价", "涨跌幅", "量比", "换手%"])
        self.quote_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.quote_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.quote_table.setAlternatingRowColors(True)
        self.quote_table.verticalHeader().setVisible(False)
        self.quote_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.quote_table.doubleClicked.connect(self._on_quote_double_clicked)
        mv.addWidget(self.quote_table, stretch=1)

        splitter.addWidget(mid)

        # ========== 右侧：触发日志 ==========
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(8)

        log_box = QGroupBox("触发日志")
        ll = QVBoxLayout(log_box)
        ll.setContentsMargins(12, 18, 12, 12)

        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["时间", "代码", "触发规则", "详情"])
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.doubleClicked.connect(self._on_log_double_clicked)
        ll.addWidget(self.log_table, stretch=1)

        rv.addWidget(log_box)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)

        root.addWidget(splitter, stretch=1)

        # 初始化分组
        self._refresh_groups()

    # ============ 分组管理 ============
    def _refresh_groups(self):
        current = self.group_combo.currentText()
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        groups = portfolio_mgr.list_groups()
        if not groups:
            portfolio_mgr.create_group("默认", "默认自选股分组")
            groups = portfolio_mgr.list_groups()
        for g in groups:
            self.group_combo.addItem(g["name"], g["id"])
        idx = self.group_combo.findText(current)
        if idx >= 0:
            self.group_combo.setCurrentIndex(idx)
        self.group_combo.blockSignals(False)
        self._on_group_changed(self.group_combo.currentIndex())

    def _on_group_changed(self, _idx):
        name = self.group_combo.currentText()
        if not name:
            return
        # 停止当前 watcher
        self._stop_current_watcher()
        # 刷新股票列表
        codes = portfolio_mgr.list_codes(name)
        self.stock_list.clear()
        names = portfolio_mgr.get_code_names(codes)
        for c in codes:
            item = QListWidgetItem(f"{c}  {names.get(c, '')}")
            item.setData(Qt.UserRole, c)
            self.stock_list.addItem(item)
        # 如果盯盘正在运行，重新启动
        if self.btn_start.text().startswith("⏹"):
            self._start_watcher(codes)

    def _on_new_group(self):
        name, ok = QInputDialog.getText(self, "新建分组", "分组名称:")
        if ok and name.strip():
            portfolio_mgr.create_group(name.strip())
            self._refresh_groups()
            self.group_combo.setCurrentText(name.strip())

    def _on_delete_group(self):
        name = self.group_combo.currentText()
        if not name:
            return
        if QMessageBox.question(self, "确认", f"删除分组『{name}』?") == QMessageBox.Yes:
            portfolio_mgr.delete_group(name)
            self._refresh_groups()

    def _on_add_stock(self):
        code = self.add_edit.text().strip()
        if not (code.isdigit() and len(code) == 6):
            QMessageBox.warning(self, "提示", "请输入6位数字代码")
            return
        group = self.group_combo.currentText()
        portfolio_mgr.add_code(group, code)
        self.add_edit.clear()
        self._on_group_changed(0)

    def _on_remove_stock(self):
        group = self.group_combo.currentText()
        for item in self.stock_list.selectedItems():
            code = item.data(Qt.UserRole)
            portfolio_mgr.remove_code(group, code)
        self._on_group_changed(0)

    def _on_stock_double_clicked(self, item):
        code = item.data(Qt.UserRole)
        if code:
            self.code_clicked.emit(str(code))

    def _on_quote_double_clicked(self, index):
        code_item = self.quote_table.item(index.row(), 0)
        if code_item:
            self.code_clicked.emit(code_item.text())

    def _on_log_double_clicked(self, index):
        code_item = self.log_table.item(index.row(), 1)
        if code_item:
            self.code_clicked.emit(code_item.text())

    # ============ 盯盘控制 ============
    def _stop_current_watcher(self):
        if self._watch_thread is not None:
            try:
                self._watch_thread.stop()
                self._watch_thread.quit()
                self._watch_thread.wait(2000)
            except Exception:
                pass
        self._watch_thread = None

    def _collect_triggers(self) -> List:
        triggers = []
        if self.trigger_pct_up.isChecked():
            triggers.append(T.PctTrigger(
                key="pct_up", name="涨幅≥3%",
                params={"direction": "above", "threshold": 3.0}))
        if self.trigger_pct_down.isChecked():
            triggers.append(T.PctTrigger(
                key="pct_down", name="跌幅≥3%",
                params={"direction": "below", "threshold": -3.0}))
        if self.trigger_vol.isChecked():
            triggers.append(T.VolRatioTrigger(
                key="vol_up", name="量比≥2", params={"threshold": 2.0}))
        if self.trigger_turnover.isChecked():
            triggers.append(T.TurnoverTrigger(
                key="turnover_high", name="换手率≥5%", params={"threshold": 5.0}))
        return triggers

    def _toggle_watch(self):
        if self.btn_start.text().startswith("▶"):
            # 启动
            group = self.group_combo.currentText()
            codes = portfolio_mgr.list_codes(group)
            if not codes:
                QMessageBox.information(self, "提示", "当前分组没有股票，无法盯盘")
                return
            self._start_watcher(codes)
            self.btn_start.setText("⏹ 停止盯盘")
        else:
            self._stop_current_watcher()
            self.btn_start.setText("▶ 开始盯盘")

    def _start_watcher(self, codes: List[str]):
        triggers = self._collect_triggers()
        self._stop_current_watcher()
        self._watch_thread = _WatchThread(
            self.fetcher, codes, triggers, self.interval_spin.value())
        self._watch_thread.quote_received.connect(self._on_quote_received)
        self._watch_thread.trigger_fired.connect(self._on_trigger_received)
        self._watch_thread.start()

    def _on_quote_received(self, row: dict):
        self._quote_cache[str(row.get("code", ""))] = row

    def _on_trigger_received(self, row: dict, triggers: list):
        self._pending_logs.append({
            "time": row.get("timestamp", ""),
            "code": row.get("code", ""),
            "rule": "、".join(t.name for t in triggers),
            "note": f"{row.get('name','')} 现价 {row.get('price',0):.2f} ({row.get('change_pct',0):+.2f}%)",
        })

    # ============ UI 渲染 ============
    def _render_quotes(self):
        if not self._quote_cache:
            return

        codes = sorted(self._quote_cache.keys())
        self.quote_table.setRowCount(len(codes))

        for r, code in enumerate(codes):
            row = self._quote_cache[code]
            values = [
                str(code),
                str(row.get("name", "")),
                f"{float(row.get('price') or 0):.2f}",
                f"{float(row.get('change_pct') or 0):+.2f}%",
                f"{float(row.get('volume_ratio') or 0):.2f}",
                f"{float(row.get('turnover_rate') or 0):.2f}%",
            ]
            for c, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 3:  # 涨跌幅
                    pct = float(row.get("change_pct") or 0)
                    if pct > 0:
                        item.setForeground(QBrush(QColor("#f85149")))
                    elif pct < 0:
                        item.setForeground(QBrush(QColor("#3fb950")))
                self.quote_table.setItem(r, c, item)

        # 日志表
        if self._pending_logs:
            for entry in self._pending_logs:
                self.log_table.insertRow(0)
                for c, key in enumerate(["time", "code", "rule", "note"]):
                    item = QTableWidgetItem(str(entry.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    if c == 0:
                        item.setForeground(QBrush(QColor("#8b949e")))
                    elif c == 2:
                        item.setForeground(QBrush(QColor("#f0883e")))
                    self.log_table.setItem(0, c, item)
            self._pending_logs = []
            while self.log_table.rowCount() > 500:
                self.log_table.removeRow(self.log_table.rowCount() - 1)


def _wrap_row(layout: QHBoxLayout) -> QWidget:
    w = QWidget()
    w_layout = QVBoxLayout(w)
    w_layout.setContentsMargins(0, 0, 0, 0)
    w_layout.addLayout(layout)
    return w
