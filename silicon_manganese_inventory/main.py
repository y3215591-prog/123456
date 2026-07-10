import sys
from PySide6.QtWidgets import QApplication
from silicon_manganese_inventory.utils.logger import get_logger, install_excepthook


def main():
    logger = get_logger()
    install_excepthook()

    try:
        from silicon_manganese_inventory.ui.main_window import MainWindow
    except ImportError as e:
        logger.critical(f"模块导入失败: {e}")
        raise

    app = QApplication(sys.argv)
    app.setApplicationName("SiliconMnInventory")
    app.setApplicationDisplayName("硅锰合金库存管理系统")

    try:
        window = MainWindow()
        window.show()
        logger.info("主窗口已启动")
    except Exception as e:
        logger.critical(f"主窗口启动失败: {e}")
        raise

    exit_code = app.exec()
    logger.info(f"应用退出，代码: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
