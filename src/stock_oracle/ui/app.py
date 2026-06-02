"""StockOracle GUI 启动。"""
import sys

from ..logger import log


def run():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("请先安装 PySide6: pip install PySide6", file=sys.stderr)
        sys.exit(1)

    from .main_window import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName("StockOracle")
    win = MainWindow()
    win.show()
    log.info("GUI 已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
