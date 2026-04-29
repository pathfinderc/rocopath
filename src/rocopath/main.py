from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from rocopath.ui.main_window import MainWindow
from rocopath.core.map_controller import MapController
import sys


def main():
    # Qt 6 默认已启用高 DPI，只需要设置缩放策略
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    # 创建控制器（依赖注入）
    map_controller = MapController()

    # 创建主窗口，传入控制器
    window = MainWindow(map_controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
