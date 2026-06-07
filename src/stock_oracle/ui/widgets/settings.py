"""设置中心。"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QCheckBox,
    QLineEdit, QPushButton, QGroupBox, QLabel, QMessageBox,
    QHBoxLayout, QFrame, QSizePolicy
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
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        provider_box = self._create_provider_group()
        root.addWidget(provider_box)

        watch_box = self._create_watch_group()
        root.addWidget(watch_box)

        proxy_box = self._create_proxy_group()
        root.addWidget(proxy_box)

        kline_box = self._create_kline_group()
        root.addWidget(kline_box)

        ai_box = self._create_ai_group()
        root.addWidget(ai_box)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setMaximumHeight(1)
        root.addWidget(separator)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_save = QPushButton("💾 保存设置")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setFixedSize(160, 40)
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)

        root.addLayout(btn_row)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #8b949e; font-size: 13px; padding: 8px;")
        root.addWidget(self.info_label)

        root.addStretch(1)

    def _create_provider_group(self):
        box = QGroupBox("数据源")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(12)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)
        
        label = QLabel("数据源")
        label.setFixedWidth(100)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("akshare (A股实时行情)", "akshare")
        self.provider_combo.addItem("efinance (备用)", "efinance")
        self.provider_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.provider_combo.setFixedHeight(32)
        
        row_layout.addWidget(label)
        row_layout.addWidget(self.provider_combo)
        
        layout.addLayout(row_layout)
        return box

    def _create_watch_group(self):
        box = QGroupBox("盯盘")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(12)
        label1 = QLabel("刷新间隔")
        label1.setFixedWidth(100)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 600)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.interval_spin.setFixedHeight(30)
        row1.addWidget(label1)
        row1.addWidget(self.interval_spin)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(12)
        label2 = QLabel("声音提示")
        label2.setFixedWidth(100)
        self.sound_cb = QCheckBox("启用声音提示")
        self.sound_cb.setChecked(False)
        row2.addWidget(label2)
        row2.addWidget(self.sound_cb)
        layout.addLayout(row2)

        return box

    def _create_proxy_group(self):
        box = QGroupBox("网络代理")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(12)
        label1 = QLabel("HTTP 代理")
        label1.setFixedWidth(100)
        self.http_proxy = QLineEdit()
        self.http_proxy.setPlaceholderText("例如 http://127.0.0.1:7890")
        self.http_proxy.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.http_proxy.setFixedHeight(32)
        row1.addWidget(label1)
        row1.addWidget(self.http_proxy)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(12)
        label2 = QLabel("HTTPS 代理")
        label2.setFixedWidth(100)
        self.https_proxy = QLineEdit()
        self.https_proxy.setPlaceholderText("例如 http://127.0.0.1:7890")
        self.https_proxy.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.https_proxy.setFixedHeight(32)
        row2.addWidget(label2)
        row2.addWidget(self.https_proxy)
        layout.addLayout(row2)

        return box

    def _create_kline_group(self):
        box = QGroupBox("K线数据")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(12)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)
        label = QLabel("历史天数")
        label.setFixedWidth(100)
        self.kline_days = QSpinBox()
        self.kline_days.setRange(30, 5000)
        self.kline_days.setSuffix(" 天")
        self.kline_days.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.kline_days.setFixedHeight(30)
        row_layout.addWidget(label)
        row_layout.addWidget(self.kline_days)
        layout.addLayout(row_layout)

        return box

    def _create_ai_group(self):
        box = QGroupBox("AI 助手（选股解释）")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(12)
        label1 = QLabel("AI 模型")
        label1.setFixedWidth(100)
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItem("阿里通义千问 (免费)", "qwen")
        self.ai_provider_combo.addItem("讯飞星火 (免费)", "spark")
        self.ai_provider_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ai_provider_combo.setFixedHeight(32)
        row1.addWidget(label1)
        row1.addWidget(self.ai_provider_combo)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(12)
        label2 = QLabel("API Key")
        label2.setFixedWidth(100)
        self.ai_api_key = QLineEdit()
        self.ai_api_key.setPlaceholderText("输入 API Key")
        self.ai_api_key.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ai_api_key.setFixedHeight(32)
        row2.addWidget(label2)
        row2.addWidget(self.ai_api_key)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(12)
        label3 = QLabel("API Secret")
        label3.setFixedWidth(100)
        self.ai_api_secret = QLineEdit()
        self.ai_api_secret.setPlaceholderText("API Secret（讯飞需要，其他留空）")
        self.ai_api_secret.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ai_api_secret.setFixedHeight(32)
        row3.addWidget(label3)
        row3.addWidget(self.ai_api_secret)
        layout.addLayout(row3)

        api_note = QLabel(
            "<small>💡 <b>获取API Key：</b><br>"
            "• 通义千问：https://dashscope.console.aliyun.com/apiKey（每天免费调用）<br>"
            "• 讯飞星火：https://console.xfyun.cn/services/bm35lite（有免费额度）</small>"
        )
        api_note.setWordWrap(True)
        api_note.setStyleSheet("color: #8b949e; padding-top: 12px;")
        api_note.setAlignment(Qt.AlignLeft)
        layout.addWidget(api_note)

        return box

    def _load(self):
        cfg = config.load_config()

        provider = cfg.get("data_provider", "akshare")
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        self.interval_spin.setValue(int(cfg.get("refresh_interval_sec", 5)))
        self.sound_cb.setChecked(bool(cfg.get("enable_sound", False)))

        self.http_proxy.setText(str(cfg.get("http_proxy", "")))
        self.https_proxy.setText(str(cfg.get("https_proxy", "")))

        self.kline_days.setValue(int(cfg.get("kline_history_days", 500)))

        ai_provider = cfg.get("ai_provider", "qwen")
        ai_idx = self.ai_provider_combo.findData(ai_provider)
        if ai_idx >= 0:
            self.ai_provider_combo.setCurrentIndex(ai_idx)
        self.ai_api_key.setText(str(cfg.get("ai_api_key", "")))
        self.ai_api_secret.setText(str(cfg.get("ai_api_secret", "")))

    def _on_save(self):
        cfg = {
            "data_provider": self.provider_combo.currentData(),
            "refresh_interval_sec": self.interval_spin.value(),
            "enable_sound": self.sound_cb.isChecked(),
            "sound_file": "",
            "http_proxy": self.http_proxy.text().strip(),
            "https_proxy": self.https_proxy.text().strip(),
            "kline_history_days": self.kline_days.value(),
            "ai_provider": self.ai_provider_combo.currentData(),
            "ai_api_key": self.ai_api_key.text().strip(),
            "ai_api_secret": self.ai_api_secret.text().strip(),
        }
        config.save_config(cfg)
        self.info_label.setText("✅ 设置已保存")
        self.info_label.setStyleSheet("color: #3fb950; font-size: 13px; padding: 8px; font-weight: bold;")
        QMessageBox.information(self, "成功", "设置已保存")
