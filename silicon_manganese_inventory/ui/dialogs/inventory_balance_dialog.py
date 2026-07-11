from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
)
from PySide6.QtCore import Qt
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class InventoryBalanceDialog(BaseEasDialog):
    def __init__(self, result, db, parent=None):
        self.result = result
        self.db = db
        items = result["items"]
        super().__init__(
            title=f"盘点数据 - 共 {len(items)} 行, 合计 {result['total_balance']} 吨",
            width=1000, height=600, parent=parent,
        )
        self._setup_ui(items)
        self._load_comparison(items)

    def _setup_ui(self, items):
        summary = QLabel(
            f"从Excel解析到 {self.result['count']} 条结余记录, "
            f"总库存 {self.result['total_balance']} 吨")
        summary.setStyleSheet("color: #374151; font-size: 13px; padding: 4px 0; border: none; background: transparent;")
        self.body_layout.addWidget(summary)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "批次号", "库位", "结余(吨)", "物料名称", "系统库存(吨)", "差异", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.body_layout.addWidget(self.table)

        self.add_close_button()

    def _load_comparison(self, items):
        with self.db.get_connection() as conn:
            sys_data = {}
            for item in items:
                batch = item["batch_no"]
                loc = item["location"]
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM seal_numbers WHERE batch_no=? AND location_code=? AND status='in_stock'",
                    (batch, loc),
                ).fetchone()
                sys_data[(batch, loc)] = row["cnt"] if row else 0

        self.table.setRowCount(len(items))
        for r_idx, item in enumerate(items):
            batch = item["batch_no"]
            loc = item["location"]
            excel_balance = item["balance"]
            sys_balance = sys_data.get((batch, loc), 0)
            diff = excel_balance - sys_balance
            status = "一致" if diff == 0 else ("盘盈" if diff > 0 else "盘亏")

            row_data = [
                batch, loc, str(excel_balance),
                str(item.get("material_name", "") or ""),
                str(sys_balance), str(diff), status,
            ]
            for c_idx, val in enumerate(row_data):
                w = QTableWidgetItem(val)
                if c_idx == 5 or c_idx == 6:
                    if diff > 0:
                        w.setForeground(Qt.red)
                    elif diff < 0:
                        w.setForeground(Qt.darkYellow)
                    else:
                        w.setForeground(Qt.darkGreen)
                self.table.setItem(r_idx, c_idx, w)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
