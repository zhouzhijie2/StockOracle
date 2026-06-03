"""设置中心。"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QCheckBox,
    QLineEdit, QPushButton, QGroupBox, QLabel, QMessageBox, QFileDialog,
    QHBoxLayout,
)
from PySide6.QtCore import Qt

from ... import config


class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        # ============ 数据源 ============
        provider_box = QGroupBox("数据源")
        pf = QFormLayout(provider_box)
        pf.setContentsMargins(16, 20, 16, 16)
        pf.setSpacing(10)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("akshare (A股实时行情)", "akshare")
        self.provider_combo.addItem("efinance (备用)", "efinance")
        self.provider_combo.setFixedHeight(30)
        pf.addRow("数据源", self.provider_combo)

        root.addWidget(provider_box)

        # ============ 盯盘设置 ============
        watch_box = QGroupBox("盯盘")
        wf = QFormLayout(watch_box)
        wf.setContentsMargins(16, 20, 16, 16)
        wf.setSpacing(10)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 600)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setFixedHeight(28)
        wf.addRow("刷新间隔", self.interval_spin)

        self.sound_cb = QCheckBox("启用声音提示")
        self.sound_cb.setChecked(False)
        wf.addRow("声音提示", self.sound_cb)

        root.addWidget(watch_box)

        # ============ 代理设置 ============
        proxy_box = QGroupBox("网络代理")
        proxyf = QFormLayout(proxy_box)
        proxyf.setContentsMargins(16, 20, 16, 16)
        proxyf.setSpacing(10)

        self.http_proxy = QLineEdit()
        self.http_proxy.setPlaceholderText("例如 http://127.0.0.1:7890 (可留空)")
        self.http_proxy.setFixedHeight(30)
        proxyf.addRow("HTTP 代理", self.http_proxy)

        self.https_proxy = QLineEdit()
        self.https_proxy.setPlaceholderText("例如 http://127.0.0.1:7890 (可留空)")
        self.https_proxy.setFixedHeight(30)
        proxyf.addRow("HTTPS 代理", self.https_proxy)

        root.addWidget(proxy_box)

        # ============ K线数据 ============
        kline_box = QGroupBox("K线数据")
        kf = QFormLayout(kline_box)
        kf.setContentsMargins(16, 20, 16, 16)
        kf.setSpacing(10)

        self.kline_days = QSpinBox()
        self.kline_days.setRange(30, 5000)
        self.kline_days.setSuffix(" 天")
        self.kline_days.setFixedHeight(28)
        kf.addRow("历史天数", self.kline_days)

        root.addWidget(kline_box)

        # ============ 保存按钮 ============
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_save = QPushButton("💾 保存设置")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setFixedHeight(40)
        self.btn_save.setMinimumWidth(140)
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)

        root.addLayout(btn_row)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #8b949e; font-size: 13px; padding: 8px;")
        root.addWidget(self.info_label)

        root.addStretch(1)

    def _load(self):
        """加载配置。"""
        cfg = config.load_config()

        # 数据源
        provider = cfg.get("data_provider", "akshare")
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        # 盯盘
        self.interval_spin.setValue(int(cfg.get("refresh_interval_sec", 5)))
        self.sound_cb.setChecked(bool(cfg.get("enable_sound", False)))

        # 代理
        self.http_proxy.setText(str(cfg.get("http_proxy", "")))
        self.https_proxy.setText(str(cfg.get("https_proxy", "")))

        # K线
        self.kline_days.setValue(int(cfg.get("kline_history_days", 500)))

    def _on_save(self):
        """保存设置。"""
        cfg = {
            "data_provider": self.provider_combo.currentData(),
            "refresh_interval_sec": self.interval_spin.value(),
            "enable_sound": self.sound_cb.isChecked(),
            "sound_file": "",
            "http_proxy": self.http_proxy.text().strip(),
            "https_proxy": self.https_proxy.text().strip(),
            "kline_history_days": self.kline_days.value(),
        }
        config.save_config(cfg)
        self.info_label.setText("✅ 设置已保存")
        self.info_label.setStyleSheet("color: #3fb950; font-size: 13px; padding: 8px; font-weight: bold;")
        QMessageBox.information(self, "成功", "设置已保存")
