"""盯盘中心 Tab。"""
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QGroupBox,
    QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QInputDialog,
    QMessageBox, QSpinBox, QCheckBox,
)
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QBrush, QColor

from ...data.fetcher import DataFetcher
from ...portfolio import manager as portfolio_mgr
from ...watcher import triggers as T
from ...watcher.monitor import Watcher


class WatcherWidget(QWidget):
    code_clicked = Signal(str)

    def __init__(self, fetcher: DataFetcher, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self._watchers: Dict[str, Watcher] = {}

        self._build_ui()
        self._refresh_groups()

        # 定时刷新表格（非阻塞，避免在回调中直接操作 UI 出问题）
        self._quote_cache: Dict[str, dict] = {}
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1500)
        self._refresh_timer.timeout.connect(self._render_quotes)
        self._refresh_timer.start()

    # ==================== UI ====================
    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        # 左：分组 + 股票列表
        left = QWidget()
        lv = QVBoxLayout(left)

        group_box = QGroupBox("自选股分组")
        gl = QVBoxLayout(group_box)
        row = QHBoxLayout()
        self.group_combo = QComboBox()
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        row.addWidget(self.group_combo, stretch=1)
        btn_new = QPushButton("+")
        btn_new.setFixedWidth(30)
        btn_new.clicked.connect(self._on_new_group)
        row.addWidget(btn_new)
        btn_del = QPushButton("-")
        btn_del.setFixedWidth(30)
        btn_del.clicked.connect(self._on_delete_group)
        row.addWidget(btn_del)
        gl.addLayout(row)

        self.stock_list = QListWidget()
        self.stock_list.itemDoubleClicked.connect(self._on_stock_double_clicked)
        gl.addWidget(self.stock_list, stretch=1)

        row2 = QHBoxLayout()
        self.add_edit = QLineEdit()
        self.add_edit.setPlaceholderText("输入 6 位代码，回车添加")
        self.add_edit.returnPressed.connect(self._on_add_stock)
        row2.addWidget(self.add_edit, stretch=1)
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self._on_add_stock)
        row2.addWidget(btn_add)
        btn_rm = QPushButton("删除选中")
        btn_rm.clicked.connect(self._on_remove_stock)
        row2.addWidget(btn_rm)
        gl.addLayout(row2)

        lv.addWidget(group_box)
        splitter.addWidget(left)

        # 中：实时行情表
        mid = QWidget()
        mv = QVBoxLayout(mid)

        control_box = QGroupBox("盯盘控制")
        cf = QFormLayout(control_box)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 600)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" 秒")
        cf.addRow("刷新间隔", self.interval_spin)

        self.btn_start = QPushButton("▶ 开始盯盘")
        self.btn_start.clicked.connect(self._toggle_watch)
        cf.addRow("控制", self.btn_start)

        # 触发条件勾选
        self.trigger_pct_up = QCheckBox("涨幅 ≥ 3%")
        self.trigger_pct_up.setChecked(True)
        self.trigger_pct_down = QCheckBox("跌幅 ≥ 3%")
        self.trigger_vol = QCheckBox("量比 ≥ 2")
        self.trigger_turnover = QCheckBox("换手率 ≥ 5%")
        cf.addRow("触发条件", self.trigger_pct_up)
        cf.addRow("", self.trigger_pct_down)
        cf.addRow("", self.trigger_vol)
        cf.addRow("", self.trigger_turnover)

        mv.addWidget(control_box)

        self.quote_table = QTableWidget(0, 8)
        self.quote_table.setHorizontalHeaderLabels(
            ["代码", "名称", "现价", "涨跌幅%", "今开", "最高", "最低", "量比"]
        )
        self.quote_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.quote_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.quote_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.quote_table.doubleClicked.connect(self._on_quote_double_clicked)
        mv.addWidget(self.quote_table, stretch=1)

        splitter.addWidget(mid)

        # 右：触发日志
        right = QWidget()
        rv = QVBoxLayout(right)
        log_box = QGroupBox("触发日志")
        ll = QVBoxLayout(log_box)
        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["时间", "代码", "规则", "备注"])
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.log_table, stretch=1)
        rv.addWidget(log_box)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)

        root = QVBoxLayout(self)
        root.addWidget(splitter)

    # ==================== 分组 ====================
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
        # 恢复选择
        idx = self.group_combo.findText(current)
        if idx >= 0:
            self.group_combo.setCurrentIndex(idx)
        self.group_combo.blockSignals(False)
        self._on_group_changed(self.group_combo.currentIndex())

    def _on_group_changed(self, _idx):
        name = self.group_combo.currentText()
        if not name:
            return
        self._stop_current_watcher()
        codes = portfolio_mgr.list_codes(name)
        self.stock_list.clear()
        names = portfolio_mgr.get_code_names(codes)
        for c in codes:
            item = QListWidgetItem(f"{c}  {names.get(c, '')}")
            item.setData(Qt.UserRole, c)
            self.stock_list.addItem(item)
        # 立即启动新 watcher
        if self.btn_start.text().startswith("⏹"):
            self._start_watcher(name, codes)

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
        if not code.isdigit() or len(code) != 6:
            QMessageBox.warning(self, "提示", "请输入 6 位数字代码")
            return
        group = self.group_combo.currentText()
        if portfolio_mgr.add_code(group, code):
            self._on_group_changed(self.group_combo.currentIndex())
        self.add_edit.clear()

    def _on_remove_stock(self):
        group = self.group_combo.currentText()
        for item in self.stock_list.selectedItems():
            code = item.data(Qt.UserRole)
            portfolio_mgr.remove_code(group, code)
        self._on_group_changed(self.group_combo.currentIndex())

    def _on_stock_double_clicked(self, item):
        code = item.data(Qt.UserRole)
        if code:
            self.code_clicked.emit(str(code))

    def _on_quote_double_clicked(self, index):
        code_item = self.quote_table.item(index.row(), 0)
        if code_item:
            self.code_clicked.emit(code_item.text())

    # ==================== 盯盘控制 ====================
    def _stop_current_watcher(self):
        for w in self._watchers.values():
            w.stop()
        self._watchers.clear()

    def _collect_triggers(self) -> List[T.Trigger]:
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
            self._start_watcher(group, codes)
            self.btn_start.setText("⏹ 停止盯盘")
        else:
            self._stop_current_watcher()
            self.btn_start.setText("▶ 开始盯盘")

    def _start_watcher(self, group: str, codes: List[str]):
        triggers = self._collect_triggers()
        w = Watcher(fetcher=self.fetcher,
                    interval_sec=self.interval_spin.value(),
                    codes=codes, triggers=triggers)
        w.on_quote = self._on_quote_received
        w.on_trigger = self._on_trigger_received
        w.start()
        self._watchers[group] = w

    def _on_quote_received(self, row: dict):
        self._quote_cache[row["code"]] = row

    def _on_trigger_received(self, row: dict, triggers: list):
        # 触发日志追加到 UI
        code = row.get("code", "")
        names = "、".join(t.name for t in triggers)
        note = f"{row.get('name','')} 现价 {row.get('price',0):.2f} ({row.get('change_pct',0):+.2f}%)"
        # 用 QMetaObject 跨线程安全（这里简化：在 QTimer 渲染周期中合并）
        self._pending_logs = getattr(self, "_pending_logs", [])
        self._pending_logs.append({
            "time": row.get("timestamp", ""),
            "code": code,
            "rule": names,
            "note": note,
        })

    # ==================== UI 渲染 ====================
    def _render_quotes(self):
        # 行情表
        codes = [c for c in self._quote_cache.keys()]
        if not codes:
            return

        self.quote_table.setRowCount(len(codes))
        for r, code in enumerate(sorted(codes)):
            row = self._quote_cache[code]
            values = [
                str(code),
                str(row.get("name", "")),
                f"{float(row.get('price') or 0):.2f}",
                f"{float(row.get('change_pct') or 0):+.2f}",
                f"{float(row.get('open') or 0):.2f}",
                f"{float(row.get('high') or 0):.2f}",
                f"{float(row.get('low') or 0):.2f}",
                f"{float(row.get('volume_ratio') or 0):.2f}",
            ]
            for c, v in enumerate(values):
                item = QTableWidgetItem(v)
                # 涨跌幅着色
                if c == 3:
                    pct = float(row.get("change_pct") or 0)
                    if pct > 0:
                        item.setForeground(QBrush(QColor(220, 40, 40)))
                    elif pct < 0:
                        item.setForeground(QBrush(QColor(30, 140, 30)))
                self.quote_table.setItem(r, c, item)

        # 日志表
        pending = getattr(self, "_pending_logs", [])
        if pending:
            for entry in pending:
                self.log_table.insertRow(0)
                self.log_table.setItem(0, 0, QTableWidgetItem(str(entry.get("time", ""))))
                self.log_table.setItem(0, 1, QTableWidgetItem(str(entry.get("code", ""))))
                self.log_table.setItem(0, 2, QTableWidgetItem(str(entry.get("rule", ""))))
                self.log_table.setItem(0, 3, QTableWidgetItem(str(entry.get("note", ""))))
            self._pending_logs = []
            # 最多保留 500 行
            while self.log_table.rowCount() > 500:
                self.log_table.removeRow(self.log_table.rowCount() - 1)
