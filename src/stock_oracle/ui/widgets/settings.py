"""设置 Tab。"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QCheckBox,
    QLineEdit, QPushButton, QGroupBox, QLabel, QMessageBox, QFileDialog,
)
from ... import config
from ...logger import log


class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)

        box = QGroupBox("应用设置")
        form = QFormLayout(box)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["akshare", "efinance"])
        form.addRow("数据源", self.provider_combo)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 600)
        form.addRow("盯盘刷新间隔 (秒)", self.interval_spin)

        self.sound_cb = QCheckBox("启用提示音")
        form.addRow("通知", self.sound_cb)

        self.sound_file = QLineEdit()
        self.sound_file.setPlaceholderText("（可选）自定义提示音路径")
        row = QFileDialogPushRow(self.sound_file, "选择音频文件", "音频 (*.wav *.mp3)")
        form.addRow("提示音文件", row.widget())

        self.http_proxy = QLineEdit()
        self.http_proxy.setPlaceholderText("例如 http://127.0.0.1:7890 （可留空）")
        form.addRow("HTTP 代理", self.http_proxy)

        self.https_proxy = QLineEdit()
        self.https_proxy.setPlaceholderText("例如 http://127.0.0.1:7890 （可留空）")
        form.addRow("HTTPS 代理", self.https_proxy)

        self.kline_days = QSpinBox()
        self.kline_days.setRange(30, 5000)
        self.kline_days.setValue(500)
        form.addRow("K线历史天数（默认 500）", self.kline_days)

        root.addWidget(box)

        self.btn_save = QPushButton("💾 保存设置")
        self.btn_save.clicked.connect(self._on_save)
        root.addWidget(self.btn_save)

        self.info = QLabel("设置保存后将立即生效。")
        root.addWidget(self.info)
        root.addStretch(1)

    def _load(self):
        cfg = config.load_config()
        idx = self.provider_combo.findText(cfg.get("data_provider", "akshare"))
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.interval_spin.setValue(int(cfg.get("refresh_interval_sec", 5)))
        self.sound_cb.setChecked(bool(cfg.get("enable_sound", False)))
        self.sound_file.setText(str(cfg.get("sound_file", "")))
        self.http_proxy.setText(str(cfg.get("http_proxy", "")))
        self.https_proxy.setText(str(cfg.get("https_proxy", "")))
        self.kline_days.setValue(int(cfg.get("kline_history_days", 500)))

    def _on_save(self):
        cfg = {
            "data_provider": self.provider_combo.currentText(),
            "refresh_interval_sec": self.interval_spin.value(),
            "enable_sound": self.sound_cb.isChecked(),
            "sound_file": self.sound_file.text().strip(),
            "http_proxy": self.http_proxy.text().strip(),
            "https_proxy": self.https_proxy.text().strip(),
            "kline_history_days": self.kline_days.value(),
        }
        config.save_config(cfg)
        self.info.setText("✅ 设置已保存。")
        log.info("设置已保存")
        QMessageBox.information(self, "成功", "设置已保存")


class QFileDialogPushRow:
    """简单的 QLineEdit + 按钮组合，用于选择文件路径。"""
    def __init__(self, line_edit: QLineEdit, btn_text: str, file_filter: str):
        self._line_edit = line_edit
        self._filter = file_filter
        self._container = QWidget()
        from PySide6.QtWidgets import QHBoxLayout, QPushButton
        layout = QHBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, stretch=1)
        btn = QPushButton(btn_text)
        btn.clicked.connect(self._pick)
        layout.addWidget(btn)

    def widget(self) -> QWidget:
        return self._container

    def _pick(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self._container, "选择文件", "", self._filter)
        if path:
            self._line_edit.setText(path)
