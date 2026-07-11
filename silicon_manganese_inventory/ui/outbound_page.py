from PySide6.QtWidgets import QLineEdit, QTableWidgetItem, QMessageBox, QHeaderView
from PySide6.QtCore import Qt
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.ui.dialogs.outbound_dialog import OutboundDialog
from silicon_manganese_inventory.ui.dialogs.outbound_detail_dialog import (
    OutboundDetailDialog,
)
from silicon_manganese_inventory.services.outbound_service import OutboundService
from silicon_manganese_inventory.services.excel_service import ExportService


class OutboundPage(BasePage):
    SEAL_COL = 8

    def __init__(self, db):
        super().__init__(db, "出库发货")
        self.outbound_svc = OutboundService(db)

        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("出库单号")
        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("开始日期")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("结束日期")
        self.add_search_field("单号:", self.order_input)
        self.add_search_field("日期:", self.date_from)
        self.add_search_field("-", self.date_to)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("+ 新增出库", self._add_outbound, "#27ae60")
        self.add_header_button("导出 Excel", self._export, "#2980b9")

        self.set_table_headers([
            "出库单号", "日期", "批次号", "品名规格", "数量(吨)", "客户",
            "销售订单号", "合同号", "铅封号范围", "车牌号", "操作人", "备注",
            "订单余量",
        ])
        self.table.cellClicked.connect(self._on_cell_clicked)
        self._outbound_ids = []

    def _do_search(self):
        self.refresh()

    def refresh(self):
        kwargs = {}
        if self.order_input.text():
            kwargs["keyword"] = self.order_input.text()
        if self.date_from.text():
            kwargs["date_from"] = self.date_from.text()
        if self.date_to.text():
            kwargs["date_to"] = self.date_to.text()
        rows = self.outbound_svc.list_outbound(**kwargs)

        order_nos = [r["sales_order_no"] for r in rows if r["sales_order_no"]]
        order_remaining = {}
        if order_nos:
            with self.db.get_connection() as conn:
                placeholders = ",".join("?" * len(order_nos))
                orders = conn.execute(
                    f"SELECT so.order_no, so.quantity, "
                    f"COALESCE(SUM(ds.load_quantity), 0) AS shipped "
                    f"FROM sales_orders so "
                    f"LEFT JOIN daily_shipments ds ON so.order_no=ds.sales_order_no "
                    f"WHERE so.order_no IN ({placeholders}) "
                    f"GROUP BY so.order_no",
                    order_nos,
                ).fetchall()
                for o in orders:
                    rem = (o["quantity"] or 0) - (o["shipped"] or 0)
                    order_remaining[o["order_no"]] = f"余{rem}吨" if rem > 0 else "已完成"

        self._outbound_ids = []
        data = []
        for r in rows:
            self._outbound_ids.append(r["id"])
            remaining = order_remaining.get(r["sales_order_no"], "") if r["sales_order_no"] else ""
            seal_text = ""
            if r["seal_start"]:
                seal_text = f"{r['seal_start']}~{r['seal_end']} ({r['quantity']}个)"
            data.append([
                r["order_no"], r["date"], r["batch_nos"] or "",
                r["spec_name"] or "",
                r["quantity"], r["customer_name"] or "",
                r["sales_order_no"] or "", r["contract_no"] or "",
                seal_text,
                r["plate_no"] or "", r["operator"], r["remark"] or "",
                remaining,
            ])
        self.populate_table(data)

    def populate_table(self, rows, highlight_col=None, highlight_threshold=None):
        super().populate_table(rows, highlight_col, highlight_threshold)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.resizeSections(QHeaderView.ResizeToContents)

    def _on_cell_clicked(self, row, col):
        if col == self.SEAL_COL:
            return
        if 0 <= row < len(self._outbound_ids):
            outbound_id = self._outbound_ids[row]
            dlg = OutboundDetailDialog(self.db, outbound_id, self)
            dlg.exec()

    def _add_outbound(self):
        dlg = OutboundDialog(self.db, self)
        if dlg.exec():
            self.refresh()

    def _export(self):
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "出库发货.xlsx")
        export.export_outbound(path)
        self.show_info(f"已导出到: {path}")
