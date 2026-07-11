from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QStatusBar, QLabel, QComboBox,
)
from datetime import datetime
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.ui.navbar import NavBar
from silicon_manganese_inventory.utils.logger import get_logger
from silicon_manganese_inventory.utils.themes import THEMES
from silicon_manganese_inventory.utils.theme_manager import ThemeManager
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
        (" 预入库", 0),
        (" 入库确认", 1),
        (" 出库发货", 2),
        (" 成品库存", 3),
        (" 每日发货明细", 4),
        (" 订单装车汇总", 5),
        (" Excel导入", 6),
        (" 铅封号管理", 7),
        (" 库位管理", 8),
        (" 客户/供应商", 9),
        (" 基础数据", 10),
    ]

    def __init__(self, db):
        super().__init__()
        self.logger = get_logger()
        self.db = db
        self.report_svc = ReportService(self.db)
        self.logger.info("主窗口初始化")
        self.setWindowTitle("硅锰合金库存管理系统")
        self.setMinimumSize(1280, 800)
        self._tm = ThemeManager.instance()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.top_bar = QWidget()
        self.top_bar.setObjectName("topBar")
        self.top_bar.setFixedHeight(48)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)

        title_label = QLabel("硅锰合金库存管理系统")
        title_label.setObjectName("topBarTitle")
        top_layout.addWidget(title_label)

        theme_lbl = QLabel(" 主题:")
        theme_lbl.setObjectName("topBarLabel")
        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(90)
        self.theme_combo.setStyleSheet(
            "QComboBox { border: 1px solid rgba(255,255,255,0.3); border-radius: 3px; "
            "padding: 3px 8px; font-size: 12px; background: rgba(255,255,255,0.1); "
            "color: white; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { color: #333; background: white; }")
        for key, t in THEMES.items():
            self.theme_combo.addItem(t["name"], key)
        cur = self._tm.current_key
        idx = self.theme_combo.findData(cur)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        top_layout.addStretch()
        top_layout.addWidget(theme_lbl)
        top_layout.addWidget(self.theme_combo)
        layout.addWidget(self.top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.navbar = NavBar(self.NAV_ITEMS)
        self.navbar.setFixedWidth(180)
        self.navbar.setObjectName("navBar")
        body.addWidget(self.navbar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        self.stack.setStyleSheet("background: #F5F7FA; border: none;")
        body.addWidget(self.stack)

        layout.addLayout(body)

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
        self._apply_theme()
        self._refresh_status_bar()

    def _apply_theme(self):
        t = self._tm.current
        top_style = self._tm.topbar_style()
        nav_style = self._tm.navbar_style()
        self.top_bar.setStyleSheet(top_style)
        self.navbar.setStyleSheet(nav_style)

    def _on_theme_changed(self):
        key = self.theme_combo.currentData()
        if key:
            self._tm.set_theme(key)
            app = self._get_app()
            if app:
                self._tm.apply_global(app)
            self._apply_theme()

    def _get_app(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance()

    def _refresh_status_bar(self):
        with self.db.get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE status='in_stock'"
            ).fetchone()[0]
            used = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE status='shipped'"
            ).fetchone()[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.status_bar.showMessage(
            f"  当前日期: {now}  |  库存总铅封个数: {total}  |  已用铅封号: {used}"
        )

    def _connect_signals(self):
        self.navbar.nav_changed.connect(self._on_nav_changed)
        self.pages[0].refresh()

    def _on_nav_changed(self, index):
        if index in self.pages:
            self.stack.setCurrentWidget(self.pages[index])
            self.pages[index].refresh()
        self._refresh_status_bar()
