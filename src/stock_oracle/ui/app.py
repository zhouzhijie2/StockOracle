"""StockOracle GUI 启动。"""
import sys
import os

from ..logger import log


def get_icon_path():
    """获取图标路径"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 项目根目录
    root_dir = os.path.normpath(os.path.join(current_dir, '..', '..', '..'))
    
    # 尝试多个可能的位置（优先 .ico 格式）
    possible_paths = [
        os.path.join(root_dir, 'assets', 'icons', 'app_icon.ico'),
        os.path.join(root_dir, 'assets', 'icons', 'app_icon.png'),
        os.path.join(current_dir, '..', '..', '..', 'assets', 'icons', 'app_icon.ico'),
        os.path.join(current_dir, '..', '..', '..', 'assets', 'icons', 'app_icon.png'),
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
    
    # 设置 Windows 任务栏图标（需要在创建窗口前设置）
    if sys.platform == 'win32':
        import ctypes
        app_id = "StockOracle.IntelligentStockPicker.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    # 设置应用图标
    icon_path = get_icon_path()
    if icon_path:
        from PySide6.QtGui import QIcon
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)
        log.info("应用图标: %s", icon_path)
    else:
        log.warning("未找到应用图标文件")

    # 应用金融风格主题（同花顺风格）
    app.setStyleSheet(get_qss())

    win = MainWindow()
    
    # 为窗口也设置图标
    if icon_path:
        win.setWindowIcon(icon)
    
    win.show()
    log.info("GUI 已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
