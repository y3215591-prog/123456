from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QStatusBar, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from datetime import datetime
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.ui.style import STYLE_QSS
from silicon_manganese_inventory.ui.navbar import NavBar
from silicon_manganese_inventory.utils.logger import get_logger, log_user_action
from silicon_manganese_inventory.ui.pre_inbound_page import PreInboundPage
from silicon_manganese_inventory.ui.inbound_confirm_page import InboundConfirmPage
from silicon_manganese_inventory.ui.outbound_page import OutboundPage
from silicon_manganese_inventory.ui.inventory_page import InventoryPage
from silicon_manganese_inventory.ui.daily_shipment_page import DailyShipmentPage
from silicon_manganese_inventory.ui.order_summary_page import OrderSummaryPage
from silicon_manganese_inventory.ui.excel_import_page import ExcelImportPage
from silicon_manganese_inventory.ui.seal_manage_page import SealManagePage
from silicon_manganese_inventory.ui.location_page import LocationPage
from silicon_manganese_inventory.ui.customer_page import CustomerPage
from silicon_manganese_inventory.ui.basic_data_page import BasicDataPage


class MainWindow(QMainWindow):
    NAV_ITEMS = [
        ("预入库", 0),
        ("入库确认", 1),
        ("出库发货", 2),
        ("成品库存", 3),
        ("每日发货明细", 4),
        ("订单装车汇总", 5),
        ("Excel导入", 6),
        ("铅封号管理", 7),
        ("库位管理", 8),
        ("客户/供应商", 9),
        ("基础数据", 10),
    ]

    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.logger.info("初始化数据库...")
        self.db = DatabaseManager()
        self.db.initialize()
        self.report_svc = ReportService(self.db)
        self.logger.info("数据库初始化完成")
        self.setWindowTitle("硅锰合金库存管理系统")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(STYLE_QSS)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.navbar = NavBar(self.NAV_ITEMS)
        self.navbar.setFixedWidth(160)
        layout.addWidget(self.navbar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f5f6fa;")
        layout.addWidget(self.stack)

        self.pages = {
            0: PreInboundPage(self.db),
            1: InboundConfirmPage(self.db),
            2: OutboundPage(self.db),
            3: InventoryPage(self.db),
            4: DailyShipmentPage(self.db),
            5: OrderSummaryPage(self.db),
            6: ExcelImportPage(self.db),
            7: SealManagePage(self.db),
            8: LocationPage(self.db),
            9: CustomerPage(self.db),
            10: BasicDataPage(self.db),
        }
        for idx, page in self.pages.items():
            self.stack.addWidget(page)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._refresh_status_bar()

    def _refresh_status_bar(self):
        svc = self.report_svc
        total = svc.get_inventory_total()
        with self.db.get_connection() as conn:
            used = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE status='shipped'"
            ).fetchone()[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.status_bar.showMessage(
            f"  当前日期: {now}  |  库存总吨数: {total}  |  已用铅封号: {used}"
        )

    def _connect_signals(self):
        self.navbar.nav_changed.connect(self._on_nav_changed)

    def _on_nav_changed(self, index):
        if index in self.pages:
            name = dict(self.NAV_ITEMS).get(index, "未知")
            self.logger.debug(f"切换到页面: {name}")
            self.stack.setCurrentWidget(self.pages[index])
            self.pages[index].refresh()
        self._refresh_status_bar()
