from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView,
)
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class LocationDetailDialog(BaseEasDialog):
    def __init__(self, db, location_code, parent=None):
        super().__init__(title=f"库位详情 - {location_code}", width=920, height=580, parent=parent)
        self.db = db
        self.location_code = location_code
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        card, cl = self.add_card()
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(40)
        self.stock_label = QLabel("计算中...")
        self.stock_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #16A34A; border: none; background: transparent;")
        summary_layout.addWidget(self.stock_label)
        self.batch_label = QLabel("计算中...")
        self.batch_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2B579A; border: none; background: transparent;")
        summary_layout.addWidget(self.batch_label)
        self.record_label = QLabel("计算中...")
        self.record_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #D97706; border: none; background: transparent;")
        summary_layout.addWidget(self.record_label)
        summary_layout.addStretch()
        cl.addLayout(summary_layout)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["类型", "单号", "日期", "批次号", "数量(吨)", "铅封号范围", "化验结果", "操作人", "备注"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.body_layout.addWidget(self.table)

        self.add_close_button()

    def _load_data(self):
        with self.db.get_connection() as conn:
            stock_count = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE location_code=? AND status='in_stock'",
                (self.location_code,),
            ).fetchone()[0]
            self.stock_label.setText(f"当前库存: {stock_count} 个")
            batch_count = conn.execute(
                "SELECT COUNT(DISTINCT batch_no) FROM pre_inbound_orders WHERE location_code=?",
                (self.location_code,),
            ).fetchone()[0]
            self.batch_label.setText(f"历史批次: {batch_count} 个")
            rows = conn.execute(
                """SELECT '预入库' AS type, order_no, date, batch_no, quantity,
                   seal_start, seal_end, lab_status, operator, remark
                   FROM pre_inbound_orders WHERE location_code=?
                   UNION ALL
                   SELECT '已入库' AS type, io.order_no, io.date,
                   io.batch_no, io.quantity,
                   pis.seal_start, pis.seal_end,
                   pis.lab_status, io.operator, ''
                   FROM inbound_orders io
                   LEFT JOIN pre_inbound_orders pis ON io.pre_inbound_id=pis.id
                   WHERE io.location_code=?
                   ORDER BY date DESC, type""",
                (self.location_code, self.location_code),
            ).fetchall()

        self.record_label.setText(f"出入库记录: {len(rows)} 条")
        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            vs = [row["type"], row["order_no"], row["date"], row["batch_no"],
                  str(row["quantity"]),
                  f"{row['seal_start']}~{row['seal_end']}" if row["seal_start"] else "",
                  "已化验" if row["lab_status"] == "tested" else ("待化验" if row["lab_status"] == "pending" else ""),
                  row["operator"] or "", row["remark"] or ""]
            for c_idx, val in enumerate(vs):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(val))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
