"""现代化金融风格主题 - 同花顺/富途风格深色主题。"""

# ============ 配色方案 ============
COLORS = {
    # 背景层级（从深到浅）
    "bg_base": "#0d1117",        # 最深背景（应用主背景）
    "bg_card": "#161b22",         # 卡片背景
    "bg_panel": "#21262d",        # 面板/次级卡片
    "bg_hover": "#2d333b",        # 悬停状态背景
    "bg_active": "#384047",       # 激活/选中状态背景

    # 边框
    "border": "#30363d",          # 常规边框
    "border_light": "#3d444d",     # 浅边框
    "border_accent": "#f0883e",    # 强调色边框

    # 主色调（金融红涨绿跌风格）
    "up": "#f85149",              # 上涨（红）
    "up_light": "#ff7b72",         # 上涨（浅红）
    "down": "#3fb950",            # 下跌（绿）
    "down_light": "#56d364",       # 下跌（浅绿）
    "accent": "#f0883e",           # 主强调色（橙色-富途风格）
    "accent_hover": "#ff9a52",     # 悬停强调色
    "accent_press": "#d97330",     # 按下强调色
    "info_blue": "#388bfd",        # 信息蓝
    "gold": "#ffd700",             # 金色

    # 文字
    "text_primary": "#e6edf3",     # 主文字（最亮）
    "text_secondary": "#8b949e",   # 次级文字
    "text_tertiary": "#6e7681",     # 第三级文字
    "text_inactive": "#484f58",     # 不可用文字
    "text_on_accent": "#ffffff",    # 强调色上的文字

    # 状态
    "success": "#3fb950",           # 成功绿
    "warning": "#d29922",           # 警告黄
    "danger": "#f85149",            # 危险红
    "info": "#388bfd",              # 信息蓝

    # 图表
    "grid_line": "#21262d",
    "chart_grid": "#30363d",
    "chart_bg": "#0d1117",

    # 进度条
    "progress_chunk": "#f0883e",
    "progress_bg": "#21262d",

    # 标签页
    "tab_bg": "#161b22",
    "tab_active": "#0d1117",
    "tab_border_active": "#f0883e",
}

# ============ 字号规格 ============
FONTS = {
    "size_small": "11px",
    "size_normal": "13px",
    "size_medium": "15px",
    "size_large": "18px",
    "size_xlarge": "24px",
}


def get_qss() -> str:
    """生成完整的 QSS 样式表。"""
    c = COLORS
    f = FONTS

    return f"""
    /* ============ 全局 ============ */
    QWidget {{
        background-color: {c['bg_base']};
        color: {c['text_primary']};
        font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
        font-size: {f['size_normal']};
    }}

    /* ============ 主窗口 ============ */
    QMainWindow {{
        background-color: {c['bg_base']};
    }}

    /* ============ 标签文字 ============ */
    QLabel {{
        color: {c['text_primary']};
        background: transparent;
    }}
    QLabel#appTitle {{
        color: {c['accent']};
        font-size: {f['size_large']};
        font-weight: bold;
        letter-spacing: 1px;
    }}
    QLabel#appSubtitle {{
        color: {c['text_secondary']};
        font-size: {f['size_small']};
    }}
    QLabel#cardTitle {{
        color: {c['accent']};
        font-size: {f['size_medium']};
        font-weight: bold;
    }}
    QLabel#cardSubtitle {{
        color: {c['text_secondary']};
        font-size: {f['size_small']};
    }}
    QLabel#priceLabel {{
        color: {c['text_primary']};
        font-size: {f['size_medium']};
        font-weight: bold;
    }}
    QLabel#upLabel {{
        color: {c['up']};
        font-weight: bold;
    }}
    QLabel#downLabel {{
        color: {c['down']};
        font-weight: bold;
    }}
    QLabel#infoLabel {{
        color: {c['text_secondary']};
        font-size: {f['size_small']};
    }}
    QLabel#statusReady {{
        color: {c['success']};
        font-weight: bold;
    }}
    QLabel#statusRunning {{
        color: {c['accent']};
        font-weight: bold;
    }}
    QLabel#statusError {{
        color: {c['danger']};
        font-weight: bold;
    }}
    QLabel#statValue {{
        color: {c['accent']};
        font-size: {f['size_large']};
        font-weight: bold;
    }}
    QLabel#statLabel {{
        color: {c['text_tertiary']};
        font-size: {f['size_small']};
    }}

    /* ============ 按钮 ============ */
    QPushButton {{
        background-color: {c['bg_panel']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 18px;
        min-height: 32px;
        font-size: {f['size_normal']};
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['accent']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_active']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_card']};
        color: {c['text_inactive']};
        border-color: {c['border']};
    }}

    /* 主要操作按钮（橙色强调） */
    QPushButton#primaryButton, QPushButton#runButton {{
        background-color: {c['accent']};
        color: {c['text_on_accent']};
        font-weight: bold;
        border: 1px solid {c['accent']};
    }}
    QPushButton#primaryButton:hover, QPushButton#runButton:hover {{
        background-color: {c['accent_hover']};
        border-color: {c['accent_hover']};
    }}
    QPushButton#primaryButton:pressed, QPushButton#runButton:pressed {{
        background-color: {c['accent_press']};
        border-color: {c['accent_press']};
    }}
    QPushButton#primaryButton:disabled, QPushButton#runButton:disabled {{
        background-color: {c['bg_panel']};
        color: {c['text_inactive']};
        border-color: {c['border']};
    }}

    /* 危险按钮 */
    QPushButton#dangerButton {{
        background-color: {c['bg_panel']};
        color: {c['up']};
        border: 1px solid {c['up']};
    }}
    QPushButton#dangerButton:hover {{
        background-color: {c['up']};
        color: {c['text_on_accent']};
    }}

    /* 小按钮 */
    QPushButton#smallButton {{
        padding: 4px 10px;
        min-height: 24px;
        background-color: transparent;
        border: 1px solid {c['border']};
    }}
    QPushButton#smallButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['accent']};
    }}

    /* ============ 输入框 ============ */
    QLineEdit {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 10px;
        min-height: 24px;
        selection-background-color: {c['accent']};
        selection-color: {c['text_on_accent']};
    }}
    QLineEdit:focus {{
        border: 1px solid {c['accent']};
    }}

    QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px 10px;
        min-height: 24px;
        selection-background-color: {c['accent']};
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {c['accent']};
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        width: 16px;
        background-color: {c['bg_panel']};
        border-top-right-radius: 5px;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
        background-color: {c['accent']};
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        width: 16px;
        background-color: {c['bg_panel']};
        border-bottom-right-radius: 5px;
    }}
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {c['accent']};
    }}

    QComboBox {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px 30px 4px 10px;
        min-height: 24px;
    }}
    QComboBox:hover {{
        border-color: {c['accent']};
    }}
    QComboBox:focus {{
        border-color: {c['accent']};
    }}
    QComboBox::drop-down {{
        width: 24px;
        border: none;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {c['text_secondary']};
        margin-right: 8px;
    }}
    QComboBox::down-arrow:hover {{
        border-top-color: {c['accent']};
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        selection-background-color: {c['bg_hover']};
        selection-color: {c['accent']};
        outline: 0;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 6px 10px;
    }}

    /* ============ 复选框 ============ */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {c['border']};
        border-radius: 4px;
        background-color: {c['bg_card']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['accent']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent']};
        border-color: {c['accent']};
    }}

    /* ============ 单选按钮 ============ */
    QRadioButton {{
        color: {c['text_primary']};
        spacing: 8px;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {c['border']};
        border-radius: 9px;
        background-color: {c['bg_card']};
    }}
    QRadioButton::indicator:hover {{
        border-color: {c['accent']};
    }}
    QRadioButton::indicator:checked {{
        border-color: {c['accent']};
        background-color: {c['accent']};
    }}

    /* ============ 分组框 ============ */
    QGroupBox {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 18px;
        padding: 16px 12px 12px 12px;
        font-weight: bold;
        color: {c['accent']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        padding: 0 8px;
        color: {c['accent']};
        background-color: {c['bg_card']};
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}

    /* 卡片式分组框（无边框，只保留卡片背景） */
    QGroupBox#cardBox {{
        border: 1px solid {c['border']};
    }}

    /* ============ 标签页 ============ */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background-color: {c['bg_card']};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {c['bg_base']};
        color: {c['text_secondary']};
        padding: 10px 24px;
        border: 1px solid transparent;
        border-bottom: 2px solid transparent;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 2px;
        font-size: {f['size_normal']};
        min-width: 80px;
    }}
    QTabBar::tab:selected {{
        background-color: {c['bg_card']};
        color: {c['accent']};
        font-weight: bold;
        border: 1px solid {c['border']};
        border-bottom: 2px solid {c['accent']};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
    }}

    /* ============ 表格 ============ */
    QTableWidget, QTableView {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        gridline-color: {c['border']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        selection-background-color: {c['bg_hover']};
        selection-color: {c['accent']};
        alternate-background-color: {c['bg_base']};
    }}
    QTableWidget::item, QTableView::item {{
        padding: 6px 8px;
        border: none;
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background-color: {c['bg_active']};
        color: {c['accent']};
    }}

    /* 表头 */
    QHeaderView::section {{
        background-color: {c['bg_panel']};
        color: {c['accent']};
        padding: 8px 10px;
        border: none;
        border-bottom: 2px solid {c['accent']};
        border-right: 1px solid {c['border']};
        font-weight: bold;
    }}
    QHeaderView::section:last {{
        border-right: none;
    }}
    QHeaderView::section:hover {{
        background-color: {c['bg_hover']};
    }}

    /* 垂直表头（行号） */
    QHeaderView::section:vertical {{
        color: {c['text_secondary']};
        background-color: {c['bg_panel']};
        border-right: 1px solid {c['border']};
        border-bottom: 1px solid {c['border']};
        padding: 4px 8px;
    }}

    /* ============ 列表 ============ */
    QListWidget {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 6px 10px;
        border-radius: 4px;
    }}
    QListWidget::item:selected {{
        background-color: {c['bg_hover']};
        color: {c['accent']};
    }}
    QListWidget::item:hover {{
        background-color: {c['bg_panel']};
    }}

    /* ============ 滚动条 ============ */
    QScrollBar:vertical {{
        background-color: {c['bg_card']};
        width: 10px;
        border: none;
        margin: 2px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {c['border_light']};
        border-radius: 5px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {c['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background-color: {c['bg_card']};
        height: 10px;
        border: none;
        margin: 2px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {c['border_light']};
        border-radius: 5px;
        min-width: 40px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {c['accent']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        border: none;
    }}

    /* ============ 进度条 ============ */
    QProgressBar {{
        background-color: {c['progress_bg']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        text-align: center;
        color: {c['text_primary']};
        height: 18px;
        font-size: {f['size_small']};
    }}
    QProgressBar::chunk {{
        background-color: {c['progress_chunk']};
        border-radius: 7px;
    }}

    /* ============ 分隔器 ============ */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    QSplitter::handle:hover {{
        background-color: {c['accent']};
    }}

    /* ============ 菜单栏 ============ */
    QMenuBar {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border-bottom: 1px solid {c['border']};
        padding: 0 4px;
    }}
    QMenuBar::item {{
        padding: 8px 16px;
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {c['bg_hover']};
        color: {c['accent']};
    }}

    QMenu {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 24px 6px 16px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {c['bg_hover']};
        color: {c['accent']};
    }}

    /* ============ 状态栏 ============ */
    QStatusBar {{
        background-color: {c['bg_card']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border']};
        padding: 2px 12px;
    }}
    QStatusBar QLabel {{
        color: {c['text_secondary']};
    }}

    /* ============ 文本编辑区 ============ */
    QTextEdit {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
    }}
    QTextEdit:focus {{
        border-color: {c['accent']};
    }}

    QPlainTextEdit {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
    }}

    /* ============ 工具提示 ============ */
    QToolTip {{
        background-color: {c['bg_panel']};
        color: {c['text_primary']};
        border: 1px solid {c['accent']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: {f['size_small']};
    }}

    /* ============ 消息框 ============ */
    QMessageBox {{
        background-color: {c['bg_card']};
    }}
    QMessageBox QLabel {{
        color: {c['text_primary']};
        background-color: {c['bg_card']};
    }}
    QMessageBox QPushButton {{
        min-width: 80px;
    }}

    /* ============ 框架线 ============ */
    QFrame#hLine {{
        background-color: {c['border']};
        max-height: 1px;
        min-height: 1px;
    }}
    QFrame#vLine {{
        background-color: {c['border']};
        max-width: 1px;
        min-width: 1px;
    }}

    /* ============ 滑动条 ============ */
    QSlider::groove:horizontal {{
        height: 6px;
        background: {c['bg_panel']};
        border-radius: 3px;
    }}
    QSlider::sub-page:horizontal {{
        background: {c['accent']};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
        background: {c['accent']};
    }}
    QSlider::handle:horizontal:hover {{
        background: {c['accent_hover']};
    }}
    """
