import sys
from PySide6.QtWidgets import QApplication
from silicon_manganese_inventory.utils.logger import get_logger, install_excepthook
from silicon_manganese_inventory.utils.theme_manager import ThemeManager


def main():
    logger = get_logger()
    install_excepthook()

    app = QApplication(sys.argv)
    app.setApplicationName("SiliconMnInventory")
    app.setApplicationDisplayName("硅锰合金库存管理系统")

    from silicon_manganese_inventory.ui.style import STYLE_QSS
    tm = ThemeManager.instance()
    theme_qss = tm.apply_global(app)
    app.setStyleSheet(STYLE_QSS + "\n" + theme_qss)

    try:
        from silicon_manganese_inventory.dao.database import DatabaseManager
        db = DatabaseManager()
        db.initialize()
    except Exception as e:
        logger.critical(f"数据库初始化失败: {e}")
        raise

    from silicon_manganese_inventory.ui.login_dialog import LoginDialog
    dlg = LoginDialog(db)
    if dlg.exec() != LoginDialog.Accepted:
        logger.info("用户取消登录")
        return

    try:
        from silicon_manganese_inventory.ui.main_window import MainWindow
    except ImportError as e:
        logger.critical(f"模块导入失败: {e}")
        raise

    try:
        window = MainWindow(db)
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
