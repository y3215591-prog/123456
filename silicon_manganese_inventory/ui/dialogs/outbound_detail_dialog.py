from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QWidget,
)
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class OutboundDetailDialog(BaseEasDialog):
    def __init__(self, db, outbound_id, parent=None):
        super().__init__(title="出库详情", width=820, height=580, parent=parent)
        self.db = db
        self.outbound_id = outbound_id
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.info_grid = QVBoxLayout()
        self.info_grid.setSpacing(2)
        card, cl = self.add_card()
        self.add_section_title("订单信息")
        cl.addLayout(self.info_grid)

        self.seal_count_label = QLabel("")
        self.seal_count_label.setStyleSheet("font-size: 13px; color: #DC2626; font-weight: bold; border: none; background: transparent;")
        self.add_section_title("已发货铅封号")
        self.body_layout.addWidget(self.seal_count_label)

        self.seals_table = QTableWidget()
        self.seals_table.setAlternatingRowColors(True)
        self.seals_table.setSelectionBehavior(self.seals_table.SelectRows)
        self.seals_table.setEditTriggers(self.seals_table.NoEditTriggers)
        self.seals_table.horizontalHeader().setStretchLastSection(True)
        self.seals_table.verticalHeader().setVisible(False)
        self.seals_table.setColumnCount(4)
        self.seals_table.setHorizontalHeaderLabels(["铅封号", "批次号", "原库位", "状态"])
        self.seals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.body_layout.addWidget(self.seals_table)

        self.add_close_button()

    def _load_data(self):
        with self.db.get_connection() as conn:
            order = conn.execute(
                """SELECT oo.*, c.name AS customer_name, s.name AS spec_name
                   FROM outbound_orders oo
                   LEFT JOIN customers c ON oo.customer_id=c.id
                   LEFT JOIN specs s ON oo.spec_id=s.id
                   WHERE oo.id=?""",
                (self.outbound_id,),
            ).fetchone()
        if not order:
            return
        self._title_label.setText(f"出库详情 - {order['order_no']}")
        info_items = [
            ("出库单号", order["order_no"]), ("日期", order["date"]),
            ("客户", order.get("customer_name", "")), ("品名规格", order.get("spec_name", "")),
            ("数量(吨)", str(order["quantity"])), ("销售订单号", order.get("sales_order_no", "")),
            ("合同号", order.get("contract_no", "")), ("车牌号", order.get("plate_no", "")),
            ("批次号", order.get("batch_nos", "")),
            ("铅封号范围", f"{order['seal_start']}~{order['seal_end']}" if order["seal_start"] else ""),
            ("操作人", order.get("operator", "")), ("备注", order.get("remark", "")),
        ]
        for label, value in info_items:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 1, 0, 1)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #6B7280; font-size: 13px; min-width: 90px; border: none; background: transparent;")
            val = QLabel(str(value) if value else "-")
            val.setStyleSheet("color: #374151; font-size: 13px; font-weight: 600; border: none; background: transparent;")
            row_layout.addWidget(lbl)
            row_layout.addWidget(val)
            row_layout.addStretch()
            self.info_grid.addWidget(row_widget)

        with self.db.get_connection() as conn:
            seals = conn.execute(
                "SELECT seal_code, batch_no, location_code, status FROM seal_numbers WHERE outbound_id=? ORDER BY seal_code",
                (self.outbound_id,),
            ).fetchall()
        self.seal_count_label.setText(f"共 {len(seals)} 个铅封号")
        self.seals_table.setRowCount(len(seals))
        status_map = {"shipped": "已发货", "in_stock": "在库", "unused": "未使用"}
        for r, seal in enumerate(seals):
            for c, key in enumerate(["seal_code", "batch_no", "location_code", "status"]):
                val = str(seal[key] or "")
                if key == "status":
                    val = status_map.get(val, val)
                self.seals_table.setItem(r, c, QTableWidgetItem(val))
