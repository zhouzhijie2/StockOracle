"""StockOracle GUI 启动。"""
import sys
import os

from ..logger import log


def get_icon_path():
    """获取图标路径"""
    # 尝试多个可能的位置
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'assets', 'icons', 'app_icon.png'),
        os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons', 'app_icon.png'),
        os.path.join(os.getcwd(), 'assets', 'icons', 'app_icon.png'),
        '/Users/zhou/aicoding/StockOracle/assets/icons/app_icon.png',
    ]
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None


def run():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("请先安装 PySide6: pip install PySide6", file=sys.stderr)
        sys.exit(1)

    from .main_window import MainWindow
    from .theme import get_qss

    app = QApplication(sys.argv)
    app.setApplicationName("StockOracle")
    app.setApplicationDisplayName("StockOracle 智能选股")

    # 设置应用图标
    icon_path = get_icon_path()
    if icon_path:
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))
        log.info("应用图标: %s", icon_path)

    # 应用金融风格主题（同花顺风格）
    app.setStyleSheet(get_qss())

    win = MainWindow()
    win.show()
    log.info("GUI 已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
